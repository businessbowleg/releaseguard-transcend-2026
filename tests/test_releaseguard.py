import hashlib
import hmac
import json
import os
from pathlib import Path
import tempfile
import unittest

from releaseguard import (
    InvalidEvidence, canonical, decide, inspect_paths, sha256, synthetic_evidence,
    validate_evidence, validate_proposal, verify_approval, verify_ci_runtime,
)

SHA="a"*40

class ReleaseGuardTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        (self.root/"app.py").write_text("print('safe')\n",encoding="utf-8")
        self.proposal={"version":1,"request_id":"JOB_20261018",
                       "commit":SHA,"action":"stage","changes":["app.py"],
                       "agent_rationale":"Reasoning is advice, not permission."}
        self.evidence=synthetic_evidence(SHA,"pass")

    def test_pass_yields_staging_candidate_not_production(self):
        r=decide(self.root,self.proposal,self.evidence)
        self.assertEqual(r["decision"],"STAGING_CANDIDATE")
        self.assertFalse(r["production_permitted"])
        self.assertFalse(r["deployment_performed"])

    def test_failed_security_blocks(self):
        self.evidence["stages"]["security"]["status"]="FAIL"
        self.assertEqual(decide(self.root,self.proposal,self.evidence)["decision"],"NO_GO")

    def test_unverified_license_blocks(self):
        self.evidence["stages"]["license"]["status"]="UNVERIFIED"
        self.assertEqual(decide(self.root,self.proposal,self.evidence)["decision"],"NO_GO")

    def test_missing_file_blocks(self):
        self.proposal["changes"]=["not-here.py"]
        self.assertEqual(decide(self.root,self.proposal,self.evidence)["decision"],"NO_GO")

    def test_path_traversal_rejected(self):
        self.proposal["changes"]=["../private/secret"]
        with self.assertRaises(InvalidEvidence):
            decide(self.root,self.proposal,self.evidence)

    def test_sensitive_filename_rejected(self):
        self.proposal["changes"]=[".env"]
        with self.assertRaises(InvalidEvidence):
            validate_proposal(self.proposal)

    def test_secret_in_source_blocks(self):
        (self.root/"app.py").write_text("api_" + "key=" + chr(39) + "EXAMPLE_LONG_SECRET_TEST123" + chr(39) + "\n")
        r=decide(self.root,self.proposal,self.evidence)
        self.assertEqual(r["decision"],"NO_GO")
        self.assertEqual(r["path_findings"][0]["issue"],"possible_secret")

    def test_prompt_cannot_request_production(self):
        self.proposal["action"]="deploy-production"
        with self.assertRaises(InvalidEvidence):
            validate_proposal(self.proposal)

    def test_commit_mismatch_fails(self):
        self.evidence["commit"]="b"*40
        with self.assertRaises(InvalidEvidence):
            validate_evidence(self.evidence,self.proposal)

    def test_missing_stage_fails(self):
        del self.evidence["stages"]["rollback"]
        with self.assertRaises(InvalidEvidence):
            decide(self.root,self.proposal,self.evidence)

    def test_symlink_escape_blocks(self):
        actual=self.root/"actual.py"
        actual.write_text("pass")
        (self.root/"alias.py").symlink_to(actual)
        self.proposal["changes"]=["alias.py"]
        self.assertEqual(decide(self.root,self.proposal,self.evidence)["decision"],"NO_GO")

    def test_parent_symlink_inside_root_blocks(self):
        nested=self.root/"real"
        nested.mkdir()
        (nested/"child.py").write_text("pass")
        (self.root/"alias").symlink_to(nested,target_is_directory=True)
        self.proposal["changes"]=["alias/child.py"]
        r=decide(self.root,self.proposal,self.evidence)
        self.assertEqual(r["decision"],"NO_GO")
        self.assertEqual(r["path_findings"][0]["issue"],"path_escape")

    def test_cli_fails_closed_without_gitlab_job(self):
        import subprocess
        import sys
        source=self.root/"proposal.json"
        evidence=self.root/"evidence.json"
        decision=self.root/"decision.json"
        source.write_text(json.dumps(self.proposal))
        evidence.write_text(json.dumps(self.evidence))
        runner=Path(__file__).resolve().parents[1]/"releaseguard.py"
        env={k:v for k,v in os.environ.items() if not k.startswith("CI_") and k!="GITLAB_CI"}
        result=subprocess.run(
            [sys.executable,str(runner),"check","--root",str(self.root),
             "--proposal",str(source),"--evidence",str(evidence),
             "--output",str(decision),"--require-gitlab"],
            capture_output=True,text=True,env=env,timeout=5)
        self.assertNotEqual(result.returncode,0)
        self.assertFalse(decision.exists())
        self.assertIn("NO_GO",result.stderr)

    def test_duplicate_files_fail(self):
        self.proposal["changes"]=["app.py","app.py"]
        with self.assertRaises(InvalidEvidence):
            validate_proposal(self.proposal)

    def test_tampered_stage_source_is_rejected(self):
        self.evidence["stages"]["security"]["source"]="forged-GitLab-job"
        with self.assertRaisesRegex(InvalidEvidence,"provenance"):
            decide(self.root,self.proposal,self.evidence)

    def test_signed_staging_acknowledgement(self):
        result=decide(self.root,self.proposal,self.evidence)
        test_signing_material="local-only-test-signing-key"
        approval={"request_id":result["request_id"],
                  "decision_digest":result["decision_digest"],
                  "approver":"owner-test",
                  "intent":"acknowledge-staging-only"}
        approval["signature"]=hmac.new(test_signing_material.encode(),canonical(approval),hashlib.sha256).hexdigest()
        self.assertTrue(verify_approval(result,approval,test_signing_material))
        self.assertFalse(result["production_permitted"])

    def test_bad_signing_key_denied(self):
        result=decide(self.root,self.proposal,self.evidence)
        approval={"request_id":result["request_id"],"decision_digest":result["decision_digest"],
                  "approver":"owner-test","intent":"acknowledge-staging-only","signature":"a"*64}
        self.assertFalse(verify_approval(result,approval,"wrong-secret"))

    def test_no_signature_on_no_go(self):
        self.evidence["stages"]["security"]["status"]="FAIL"
        result=decide(self.root,self.proposal,self.evidence)
        approval={"request_id":result["request_id"],"decision_digest":result["decision_digest"],
                  "approver":"owner-test","intent":"acknowledge-staging-only","signature":"a"*64}
        self.assertFalse(verify_approval(result,approval,"test-key"))

    def test_schema_extra_keys_refused(self):
        self.proposal["untrusted_override"]=True
        with self.assertRaises(InvalidEvidence):
            validate_proposal(self.proposal)

    def test_large_source_blocks(self):
        (self.root/"app.py").write_text("x"*160000)
        self.assertEqual(decide(self.root,self.proposal,self.evidence)["decision"],"NO_GO")

    def test_mock_provenance_is_not_real_gitlab(self):
        self.assertEqual(self.evidence["provenance"]["pipeline_id"],"LOCAL_FIXTURE_NOT_GITLAB")

    def test_ci_runtime_rejects_local_fixture(self):
        with self.assertRaises(InvalidEvidence):
            verify_ci_runtime(self.proposal,self.evidence,{"GITLAB_CI":"false"})

    def test_ci_runtime_valid_identity(self):
        pipeline="982401"
        self.evidence["provenance"]["pipeline_id"]=pipeline
        for stage,record in self.evidence["stages"].items():
            record["source"]="GITLAB_PIPELINE_"+pipeline+"_"+stage
        env={"GITLAB_CI":"true","CI_PIPELINE_ID":pipeline,
             "CI_COMMIT_SHA":SHA,"CI_JOB_STAGE":"gate"}
        self.assertTrue(verify_ci_runtime(self.proposal,self.evidence,env))

    def test_ci_runtime_rejects_mismatched_job_commit(self):
        pipeline="982401"
        self.evidence["provenance"]["pipeline_id"]=pipeline
        for stage,record in self.evidence["stages"].items():
            record["source"]="GITLAB_PIPELINE_"+pipeline+"_"+stage
        env={"GITLAB_CI":"true","CI_PIPELINE_ID":pipeline,
             "CI_COMMIT_SHA":"b"*40,"CI_JOB_STAGE":"gate"}
        with self.assertRaisesRegex(InvalidEvidence,"identity mismatch"):
            verify_ci_runtime(self.proposal,self.evidence,env)

    def test_ci_runtime_rejects_pipeline_swap(self):
        pipeline="982401"
        self.evidence["provenance"]["pipeline_id"]=pipeline
        for stage,record in self.evidence["stages"].items():
            record["source"]="GITLAB_PIPELINE_"+pipeline+"_"+stage
        env={"GITLAB_CI":"true","CI_PIPELINE_ID":"982402",
             "CI_COMMIT_SHA":SHA,"CI_JOB_STAGE":"gate"}
        with self.assertRaisesRegex(InvalidEvidence,"pipeline identity mismatch"):
            verify_ci_runtime(self.proposal,self.evidence,env)

    def test_ci_runtime_rejects_wrong_stage(self):
        pipeline="982401"
        self.evidence["provenance"]["pipeline_id"]=pipeline
        for stage,record in self.evidence["stages"].items():
            record["source"]="GITLAB_PIPELINE_"+pipeline+"_"+stage
        env={"GITLAB_CI":"true","CI_PIPELINE_ID":pipeline,
             "CI_COMMIT_SHA":SHA,"CI_JOB_STAGE":"test"}
        with self.assertRaisesRegex(InvalidEvidence,"Incorrect CI stage"):
            verify_ci_runtime(self.proposal,self.evidence,env)

    def test_invalid_numeric_pipeline_source_rejected(self):
        self.evidence["provenance"]["pipeline_id"]="982401"
        with self.assertRaisesRegex(InvalidEvidence,"provenance"):
            decide(self.root,self.proposal,self.evidence)


if __name__=="__main__":
    unittest.main()
