"""CI attestation quality and cross-job evidence boundary tests."""
import json
import os
from pathlib import Path
import tempfile
import unittest

from ci_attestation import AttestationError, JOBS, collect, emit, filename


class CIProofTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name)
        for stage,(job,target) in JOBS.items():
            path=self.root/target
            if stage=="security":
                path.write_text(json.dumps({"passed":True,"findings":[],"scanned_files":6}))
            elif stage=="license":
                path.write_text("MIT License\n")
            elif stage=="documentation":
                path.write_text("# ReleaseGuard\n")
            elif stage=="rollback":
                path.write_text("# Rollback plan\n")
            else:
                path.write_text("print('test target')\n")
        self.env={"GITLAB_CI":"true","CI_JOB_STAGE":"evidence",
                  "CI_PIPELINE_ID":"24680","CI_COMMIT_SHA":"a"*40}
        self.write_all()

    def write_all(self):
        for i,(stage,(job,target)) in enumerate(JOBS.items(),start=1):
            ctx={**self.env,"CI_JOB_NAME":job,"CI_JOB_ID":str(i+100),
                 "CI_JOB_STAGE":"test" if stage=="tests" else
                                "security" if stage=="security" else "license"}
            obj=emit(self.root,stage,ctx)
            (self.root/filename(stage)).write_text(json.dumps(obj))

    def adjust(self,stage,field,value):
        p=self.root/filename(stage)
        obj=json.loads(p.read_text())
        obj[field]=value
        p.write_text(json.dumps(obj))

    def test_complete_proof_graph(self):
        data=collect(self.root,self.env)
        self.assertEqual(set(data),set(JOBS))
        self.assertEqual(len({x["job_id"] for x in data.values()}),5)

    def test_missing_proof_fails_closed(self):
        (self.root/filename("rollback")).unlink()
        with self.assertRaisesRegex(AttestationError,"Missing"):
            collect(self.root,self.env)

    def test_wrong_pipeline_fails_closed(self):
        self.adjust("tests","pipeline_id","24681")
        with self.assertRaisesRegex(AttestationError,"Mismatched"):
            collect(self.root,self.env)

    def test_wrong_commit_fails_closed(self):
        self.adjust("security","commit","b"*40)
        with self.assertRaisesRegex(AttestationError,"Mismatched"):
            collect(self.root,self.env)

    def test_wrong_job_name_fails_closed(self):
        self.adjust("license","job","unit_tests")
        with self.assertRaisesRegex(AttestationError,"Mismatched"):
            collect(self.root,self.env)

    def test_failed_stage_cannot_pass(self):
        self.adjust("documentation","status","FAIL")
        with self.assertRaisesRegex(AttestationError,"Mismatched"):
            collect(self.root,self.env)

    def test_reused_job_id_fails(self):
        a=json.loads((self.root/filename("tests")).read_text())
        self.adjust("rollback","job_id",a["job_id"])
        with self.assertRaisesRegex(AttestationError,"reused"):
            collect(self.root,self.env)

    def test_modified_source_after_attestation_fails(self):
        (self.root/"releaseguard.py").write_text("print('changed')\n")
        with self.assertRaisesRegex(AttestationError,"Changed evidence"):
            collect(self.root,self.env)

    def test_fake_clean_scanner_report_fails(self):
        (self.root/"scan_results.json").write_text(json.dumps({
            "passed":True, "findings":[{"issue":"secret_pattern"}], "scanned_files":3
        }))
        with self.assertRaisesRegex(AttestationError,"clean report"):
            collect(self.root,self.env)

    def test_modified_scanner_output_digest_fails(self):
        p=self.root/"scan_results.json"
        p.write_text(json.dumps({"passed":True,"findings":[],"scanned_files":60}))
        with self.assertRaisesRegex(AttestationError,"Changed evidence"):
            collect(self.root,self.env)

    def test_emit_denies_local(self):
        with self.assertRaisesRegex(AttestationError,"requires GitLab"):
            emit(self.root,"tests",{"CI_JOB_NAME":"unit_tests"})

    def test_emit_denies_wrong_job(self):
        env={**self.env,"CI_JOB_STAGE":"test","CI_JOB_NAME":"secret_scan","CI_JOB_ID":"77"}
        with self.assertRaisesRegex(AttestationError,"Job name mismatch"):
            emit(self.root,"tests",env)

    def test_emit_denies_wrong_stage(self):
        env={**self.env,"CI_JOB_STAGE":"security","CI_JOB_NAME":"unit_tests","CI_JOB_ID":"77"}
        with self.assertRaisesRegex(AttestationError,"CI stage mismatched"):
            emit(self.root,"tests",env)

    def test_collection_denies_local_fixture(self):
        with self.assertRaises(AttestationError):
            collect(self.root,{"GITLAB_CI":"false","CI_JOB_STAGE":"evidence"})

    def test_unknown_field_is_rejected(self):
        path=self.root/filename("tests")
        obj=json.loads(path.read_text())
        obj["override"]=True
        path.write_text(json.dumps(obj))
        with self.assertRaisesRegex(AttestationError,"schema"):
            collect(self.root,self.env)

    def test_symlinked_attestation_rejected(self):
        doc=self.root/filename("security")
        content=doc.read_text()
        doc.unlink()
        real=self.root/"real_proof.json"
        real.write_text(content)
        doc.symlink_to(real)
        with self.assertRaisesRegex(AttestationError,"Missing or oversized"):
            collect(self.root,self.env)

    def test_no_automatic_promotion_actions(self):
        import ci_attestation
        text=Path(ci_attestation.__file__).read_text()
        self.assertNotIn("subprocess.run",text)
        self.assertNotIn("deploy-production",text)


if __name__=="__main__":
    unittest.main()
