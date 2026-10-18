"""Synthetic CI pipeline integration.

These tests intentionally MOCK GitLab environment variables to validate the
workflow contract. They never prove a GitLab job or Duo flow actually ran.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from ci_attestation import JOBS, filename

SOURCE=Path(__file__).resolve().parents[1]
COMMIT="c"*40
PIPELINE="915031"


class MockPipelineTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name)
        for name in ("ci_attestation.py","ci_evidence.py","ci_security.py",
                     "releaseguard.py","stage_preview.py","LICENSE",
                     "AGENTS.md","README.md","ROLLBACK.md","DEMO_RUNBOOK.md"):
            shutil.copy2(SOURCE/name,self.root/name)
        self.env={
            **{k:v for k,v in os.environ.items() if k not in
               {"CI_PIPELINE_ID","CI_JOB_ID","CI_COMMIT_SHA","CI_JOB_NAME","CI_JOB_STAGE","GITLAB_CI"}},
            "GITLAB_CI":"true",
            "CI_PIPELINE_ID":PIPELINE,
            "CI_COMMIT_SHA":COMMIT,
            "CI_JOB_ID":"2001",
        }

    def run_job(self,script,stage,job=None,extra=None):
        env={**self.env,"CI_JOB_STAGE":stage}
        if job is not None:
            env["CI_JOB_NAME"]=job
        if extra:
            env.update(extra)
        return subprocess.run([sys.executable,*script],cwd=self.root,env=env,
                              capture_output=True,text=True,timeout=15)

    def prepare(self):
        # Not a genuine GitLab runner: use real local checks with simulated CI env.
        (self.root/"scan_results.json").write_text(
            json.dumps({"passed":True,"findings":[],"scanned_files":10}))
        for i,(name,(job,target)) in enumerate(JOBS.items()):
            stage="test" if name=="tests" else "security" if name=="security" else "license"
            result=self.run_job(["ci_attestation.py","emit","--stage",name],stage,job,
                                {"CI_JOB_ID":str(2001+i)})
            self.assertEqual(result.returncode,0,result.stderr)

    def test_staged_pipeline_requires_all_five_artifacts(self):
        self.prepare()
        result=self.run_job(["ci_evidence.py"],"evidence","create_evidence")
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn("GITLAB_CI_UPSTREAM_JOB_SUCCESS",result.stdout)
        evidence=json.loads((self.root/"release_evidence.json").read_text())
        self.assertEqual(evidence["provenance"]["pipeline_id"],PIPELINE)
        self.assertEqual(set(evidence["stages"]),set(JOBS))
        gate=self.run_job([
            "releaseguard.py","check","--root",".",
            "--proposal","release_proposal.json","--evidence","release_evidence.json",
            "--output","release_decision.json","--require-gitlab"
        ],"gate","independent_gate")
        self.assertEqual(gate.returncode,0,gate.stderr)
        stage=self.run_job(["stage_preview.py"],"stage","staging_preview")
        self.assertEqual(stage.returncode,0,stage.stderr)
        receipt=json.loads((self.root/"staging_receipt.json").read_text())
        self.assertFalse(receipt["production_permitted"])
        self.assertFalse(receipt["application_deployed"])
        self.assertEqual(receipt["gitlab_pipeline"],PIPELINE)
        self.assertIn("CONFIRM IN GITLAB UI",(self.root/"public/index.html").read_text())

    def test_missing_upstream_prevents_evidence(self):
        self.prepare()
        (self.root/filename("rollback")).unlink()
        result=self.run_job(["ci_evidence.py"],"evidence","create_evidence")
        self.assertNotEqual(result.returncode,0)
        self.assertIn("Missing or oversized",result.stderr)
        self.assertFalse((self.root/"release_evidence.json").exists())

    def test_mismatched_commit_prevents_evidence(self):
        self.prepare()
        p=self.root/filename("tests")
        d=json.loads(p.read_text())
        d["commit"]="d"*40
        p.write_text(json.dumps(d))
        result=self.run_job(["ci_evidence.py"],"evidence","create_evidence")
        self.assertNotEqual(result.returncode,0)
        self.assertIn("Mismatched",result.stderr)

    def test_scanner_failure_prevents_attestation(self):
        self.prepare()
        (self.root/"scan_results.json").write_text(json.dumps({
            "passed":False,"findings":[{"issue":"example"}],"scanned_files":10
        }))
        result=self.run_job(["ci_attestation.py","emit","--stage","security"],"security","secret_scan")
        self.assertNotEqual(result.returncode,0)
        self.assertIn("clean report",result.stderr)


if __name__=="__main__":
    unittest.main()
