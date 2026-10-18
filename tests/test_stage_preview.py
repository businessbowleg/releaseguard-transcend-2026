"""Evidence dashboard tests: safe rendering, provenance clarity, fail-closed gates."""
import json
from pathlib import Path
import tempfile
import unittest

from releaseguard import InvalidEvidence, decide, synthetic_evidence
from stage_preview import build_dashboard, construct_receipt

SHA="b"*40

class DashboardTests(unittest.TestCase):
    def setUp(self):
        self.dir=tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.root=Path(self.dir.name)
        (self.root/"safe.py").write_text("print('fixture')\n")
        self.proposal={"version":1,"request_id":"DEMO_20261018",
                       "commit":SHA,"action":"evaluate",
                       "changes":["safe.py"],"agent_rationale":"Local fixture."}
        self.evidence=synthetic_evidence(SHA)
        self.decision=decide(self.root,self.proposal,self.evidence)
        self.receipt={"decision":"STAGING_CANDIDATE","request_id":"DEMO_20261018",
                      "commit":SHA,"decision_digest":self.decision["decision_digest"],
                      "gitlab_pipeline":"LOCAL_FIXTURE_NOT_GITLAB",
                      "staging_artifact_created":True,
                      "application_deployed":False,"production_permitted":False}

    def save(self):
        (self.root/"release_proposal.json").write_text(json.dumps(self.proposal))
        (self.root/"release_evidence.json").write_text(json.dumps(self.evidence))
        (self.root/"release_decision.json").write_text(json.dumps(self.decision))

    def test_fixture_is_clearly_labelled(self):
        html=build_dashboard(self.receipt,self.decision,self.evidence)
        self.assertIn("LOCAL TEST FIXTURE",html)
        self.assertIn("NOT A GITLAB PIPELINE",html)
        self.assertIn("APPLICATION DEPLOYED",html)
        self.assertIn("PRODUCTION PERMITTED",html)
        self.assertNotIn("GITLAB CI CONTEXT</div>",html)

    def test_no_go_does_not_get_dashboard(self):
        self.decision["decision"]="NO_GO"
        with self.assertRaises(ValueError):
            build_dashboard(self.receipt,self.decision,self.evidence)

    def test_refuses_production_flag(self):
        self.receipt["production_permitted"]=True
        with self.assertRaises(ValueError):
            build_dashboard(self.receipt,self.decision,self.evidence)

    def test_escapes_injected_html_everywhere(self):
        self.evidence["stages"]["tests"]["source"]='<script>alert("example")</script>'
        html=build_dashboard(self.receipt,self.decision,self.evidence)
        self.assertNotIn('<script>',html)
        self.assertIn('&lt;script&gt;',html)
        self.assertIn('Release quality gates',html)

    def test_fixture_receipt_is_recomputable(self):
        self.save()
        rec,gate,evidence=construct_receipt(self.root,environ={})
        self.assertEqual(gate,self.decision)
        self.assertEqual(evidence,self.evidence)
        self.assertFalse(rec["application_deployed"])

    def test_swapped_gate_does_not_pass(self):
        self.save()
        self.decision["decision_digest"]="0"*64
        (self.root/"release_decision.json").write_text(json.dumps(self.decision))
        with self.assertRaises(ValueError):
            construct_receipt(self.root,environ={})

    def test_non_fixture_source_must_run_inside_ci(self):
        self.save()
        self.evidence["provenance"]["pipeline_id"]="123456"
        (self.root/"release_evidence.json").write_text(json.dumps(self.evidence))
        with self.assertRaises(ValueError):
            construct_receipt(self.root,environ={})

    def test_local_env_cannot_forge_pipeline_label(self):
        self.save()
        receipt,_,_=construct_receipt(self.root,environ={"CI_PIPELINE_ID":"123456"})
        self.assertEqual(receipt["gitlab_pipeline"],"LOCAL_FIXTURE_NOT_GITLAB")

    def test_real_ci_context_cannot_claim_fixture(self):
        self.save()
        with self.assertRaises(InvalidEvidence):
            construct_receipt(self.root,environ={
                "GITLAB_CI":"true","CI_PIPELINE_ID":"123456",
                "CI_COMMIT_SHA":SHA,"CI_JOB_STAGE":"stage"})

    def test_real_ci_label_still_requires_confirmation(self):
        self.evidence["provenance"]["pipeline_id"]="123456"
        for name,stage in self.evidence["stages"].items():
            stage["source"]="GITLAB_PIPELINE_123456_"+name
        html=build_dashboard(self.receipt,self.decision,self.evidence)
        self.assertIn("CONFIRM IN GITLAB UI",html)
        self.assertIn("environment variables are not cryptographic attestation",html)

if __name__=="__main__":
    unittest.main()
