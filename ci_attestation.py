"""CI stage attestations: local file-bound, provenance-checked evidence.

These records are not cryptographic proof of GitLab infrastructure.
They bind the named CI job, commit, pipeline ID, and the bytes it evaluated,
and are consumed only through GitLab needs:artifacts job dependencies.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
JOBS = {
    "tests": ("unit_tests", "releaseguard.py"),
    "security": ("secret_scan", "scan_results.json"),
    "license": ("license_check", "LICENSE"),
    "documentation": ("documentation_check", "README.md"),
    "rollback": ("rollback_check", "ROLLBACK.md"),
}
MAX_ATTESTATION_BYTES = 4096


class AttestationError(ValueError):
    pass


def filename(stage):
    if stage not in JOBS:
        raise AttestationError("Unrecognized stage.")
    return "attest_" + stage + ".json"


def fingerprint(root, stage):
    if stage not in JOBS:
        raise AttestationError("Unknown attestation stage.")
    target = Path(root) / JOBS[stage][1]
    if not target.is_file() or target.is_symlink() or target.stat().st_size > 150000:
        raise AttestationError("Missing or unsafe evidence file for " + stage)
    data=target.read_bytes()
    if not data:
        raise AttestationError("Empty evidence file.")
    if stage=="security":
        try:
            report=json.loads(data)
        except ValueError as exc:
            raise AttestationError("Scanner output is not JSON.") from exc
        if (report.get("passed") is not True or report.get("findings")
                or not isinstance(report.get("scanned_files"), int)
                or report.get("scanned_files") < 1):
            raise AttestationError("Security scan lacks a clean report.")
    elif stage=="license":
        if b"MIT License" not in data:
            raise AttestationError("MIT license not detected.")
    elif stage=="documentation":
        if b"# ReleaseGuard" not in data:
            raise AttestationError("Required documentation missing.")
    elif stage=="rollback":
        if b"rollback" not in data.lower():
            raise AttestationError("No rollback plan detected.")
    return hashlib.sha256(data).hexdigest()


def emit(root, stage, env):
    job,path=JOBS[stage]
    if env.get("GITLAB_CI")!="true":
        raise AttestationError("Attestation emission requires GitLab CI.")
    if env.get("CI_JOB_NAME")!=job:
        raise AttestationError("Job name mismatch.")
    if env.get("CI_JOB_STAGE") not in {"test", "security", "license"}:
        raise AttestationError("Unexpected CI stage.")
    if env.get("CI_JOB_STAGE")!=("test" if stage=="tests" else
                                  "security" if stage=="security" else "license"):
        raise AttestationError("CI stage mismatched.")
    pid=env.get("CI_PIPELINE_ID","")
    jid=env.get("CI_JOB_ID","")
    commit=env.get("CI_COMMIT_SHA","")
    if not re.fullmatch(r"[0-9]{1,20}",pid) or not re.fullmatch(r"[0-9]{1,20}",jid):
        raise AttestationError("Invalid GitLab job or pipeline ID.")
    if not re.fullmatch(r"[0-9a-f]{40}",commit):
        raise AttestationError("Invalid GitLab commit SHA.")
    return {"version":1, "stage":stage, "job":job, "pipeline_id":pid,
            "job_id":jid, "commit":commit, "status":"PASS",
            "file":path, "sha256":fingerprint(root,stage)}


def collect(root, env):
    if env.get("GITLAB_CI")!="true" or env.get("CI_JOB_STAGE")!="evidence":
        raise AttestationError("Attestations can only be collected by the evidence job.")
    pid=env.get("CI_PIPELINE_ID","")
    commit=env.get("CI_COMMIT_SHA","")
    if not re.fullmatch(r"[0-9]{1,20}",pid) or not re.fullmatch(r"[0-9a-f]{40}",commit):
        raise AttestationError("Invalid collection context.")
    root=Path(root)
    collected={}
    job_ids=set()
    for stage,(job,file) in JOBS.items():
        path=root/filename(stage)
        if not path.is_file() or path.is_symlink() or path.stat().st_size>MAX_ATTESTATION_BYTES:
            raise AttestationError("Missing or oversized upstream artifact: "+stage)
        try:
            proof=json.loads(path.read_text(encoding="utf-8"))
        except (ValueError,UnicodeError) as exc:
            raise AttestationError("Invalid upstream artifact: "+stage) from exc
        if not isinstance(proof,dict) or set(proof)!={
             "version","stage","job","pipeline_id","job_id","commit","status","file","sha256"}:
            raise AttestationError("Wrong attestation schema: "+stage)
        if (proof["version"]!=1 or proof["stage"]!=stage or proof["job"]!=job
                or proof["pipeline_id"]!=pid or proof["commit"]!=commit
                or proof["status"]!="PASS" or proof["file"]!=file):
            raise AttestationError("Mismatched upstream job proof: "+stage)
        jid=proof["job_id"]
        if not isinstance(jid,str) or not re.fullmatch(r"[0-9]{1,20}",jid) or jid in job_ids:
            raise AttestationError("Missing or reused GitLab job identity.")
        job_ids.add(jid)
        if proof["sha256"]!=fingerprint(root,stage):
            raise AttestationError("Changed evidence bytes: "+stage)
        collected[stage]={"job":job,"job_id":jid,"sha256":proof["sha256"]}
    return collected


def main():
    parser=argparse.ArgumentParser(description="GitLab-specific CI evidence attestation")
    parser.add_argument("command",choices=("emit","collect"))
    parser.add_argument("--stage",choices=sorted(JOBS))
    args=parser.parse_args()
    try:
        if args.command=="emit":
            if not args.stage:
                raise AttestationError("Stage required.")
            proof=emit(ROOT,args.stage,os.environ)
            target=ROOT/filename(args.stage)
            target.write_text(json.dumps(proof,sort_keys=True,indent=2)+"\n",encoding="utf-8")
            print(json.dumps({"stage":args.stage,"job":proof["job"],"job_id":proof["job_id"],
                              "sha256":proof["sha256"]}))
        else:
            summary=collect(ROOT,os.environ)
            print(json.dumps({"verified_upstream_jobs":summary},sort_keys=True))
    except AttestationError as exc:
        parser.exit(3,"NO_GO: "+str(exc)+"\n")


if __name__=="__main__":
    main()
