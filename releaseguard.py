"""ReleaseGuard: deterministic evidence verification for GitLab Duo proposals.

Standalone hackathon example. No network, no production deploy capability,
no access to ATLAS files. The AI proposes, this independent judge decides.
"""
import argparse
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from datetime import datetime, timezone

STAGES=("tests","security","license","documentation","rollback")
ROLES=("builder","judge","promoter")
MAX_BYTES=150_000
MAX_FILES=60
SECRET_PATTERNS=(
    r"-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----",
    r"(?i)(?:password|api_key|secret)\s*=\s*[\"'][^\"']{8,}",
    r"(?i)\b(?:sk_live_|ghp_|glpat-)[A-Za-z0-9_-]{12,}",
)
DANGEROUS_PATHS=(".env", ".env.local", "secrets.json", "id_rsa", "id_ed25519")


class InvalidEvidence(ValueError):
    pass


def canonical(payload):
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256(data):
    return hashlib.sha256(data if isinstance(data, bytes) else canonical(data)).hexdigest()


def load_json(path):
    p=Path(path)
    if not p.is_file() or p.stat().st_size>MAX_BYTES:
        raise InvalidEvidence("Missing or oversized input evidence.")
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (ValueError, UnicodeError) as exc:
        raise InvalidEvidence("Evidence is not valid JSON.") from exc


def validate_proposal(data):
    if not isinstance(data, dict):
        raise InvalidEvidence("Proposal must be a JSON object.")
    expected={"version","request_id","commit","action","changes","agent_rationale"}
    if set(data)!=expected or data["version"]!=1:
        raise InvalidEvidence("Proposal schema mismatch.")
    for name in ("request_id","commit","action","agent_rationale"):
        if not isinstance(data[name],str):
            raise InvalidEvidence("Invalid proposal field.")
    if not re.fullmatch(r"[A-Za-z0-9_-]{8,80}",data["request_id"]):
        raise InvalidEvidence("Invalid request ID.")
    if not re.fullmatch(r"[0-9a-f]{40,64}",data["commit"]):
        raise InvalidEvidence("Commit must be a full hexadecimal SHA.")
    if data["action"] not in ("evaluate","stage"):
        raise InvalidEvidence("Production deployment is forbidden for autonomous proposals.")
    if not isinstance(data["changes"],list) or len(data["changes"])>MAX_FILES:
        raise InvalidEvidence("Too many changed files.")
    if not data["changes"] or len(data["agent_rationale"])>2000:
        raise InvalidEvidence("Missing changes or excessive rationale.")
    seen=set()
    for file in data["changes"]:
        if not isinstance(file,str) or not file or len(file)>240 or "\\" in file:
            raise InvalidEvidence("Invalid changed path.")
        p=Path(file)
        if p.is_absolute() or ".." in p.parts or "\0" in file:
            raise InvalidEvidence("Unsafe changed path.")
        if p.name in DANGEROUS_PATHS or file.startswith(".git/"):
            raise InvalidEvidence("Sensitive paths are excluded.")
        if file in seen:
            raise InvalidEvidence("Duplicate changed path.")
        seen.add(file)
    return data


def inspect_paths(root,proposal):
    root=Path(root).resolve()
    findings=[]
    for relative in proposal["changes"]:
        unresolved=root/relative
        path=unresolved.resolve()
        # Check every parent, not just the final path: an in-root symlink
        # directory pointing elsewhere in-root also violates provenance.
        current=root
        linked=False
        for segment in Path(relative).parts:
            current=current/segment
            if current.is_symlink():
                linked=True
                break
        if linked or not path.is_relative_to(root) or path.is_symlink():
            findings.append({"path":relative,"issue":"path_escape"})
            continue
        if not path.is_file():
            findings.append({"path":relative,"issue":"not_found"})
            continue
        if path.stat().st_size>MAX_BYTES:
            findings.append({"path":relative,"issue":"oversized_file"})
            continue
        data=path.read_bytes()
        if b"\x00" in data or b"\r\n" in data and len(data)>MAX_BYTES//2:
            findings.append({"path":relative,"issue":"binary_or_large_file"})
            continue
        text=data.decode("utf-8",errors="replace")
        for pattern in SECRET_PATTERNS:
            if re.search(pattern,text):
                findings.append({"path":relative,"issue":"possible_secret"})
                break
    return findings


def validate_evidence(data,proposal):
    if not isinstance(data,dict) or set(data)!={"version","commit","stages","provenance"}:
        raise InvalidEvidence("Evidence schema mismatch.")
    if data["version"]!=1 or data["commit"]!=proposal["commit"]:
        raise InvalidEvidence("Evidence commit mismatch.")
    stages=data["stages"]
    if not isinstance(stages,dict) or set(stages)!=set(STAGES):
        raise InvalidEvidence("Missing required stages.")
    for name, record in stages.items():
        if not isinstance(record,dict) or set(record)!={"status","source"}:
            raise InvalidEvidence("Stage schema mismatch.")
        if record["status"] not in ("PASS","FAIL","UNVERIFIED"):
            raise InvalidEvidence("Invalid stage status.")
        if not isinstance(record["source"],str) or len(record["source"])>250:
            raise InvalidEvidence("Invalid stage provenance.")
    provenance=data["provenance"]
    if not isinstance(provenance,dict) or set(provenance)!={"pipeline_id","runner","collected_at"}:
        raise InvalidEvidence("Provenance mismatch.")
    for item in provenance.values():
        if not isinstance(item,str) or len(item)>120:
            raise InvalidEvidence("Invalid provenance.")
    pipeline_id=provenance["pipeline_id"]
    if pipeline_id=="LOCAL_FIXTURE_NOT_GITLAB":
        valid_sources={
            stage:("local-fixture-"+stage, "LOCAL_FIXTURE_NOT_GITLAB_"+stage)
            for stage in STAGES
        }
        if any(stages[stage]["source"] not in allowed
               for stage,allowed in valid_sources.items()):
            raise InvalidEvidence("Local fixture source provenance mismatch.")
    elif re.fullmatch(r"[0-9]{1,20}",pipeline_id):
        if any(stages[stage]["source"]!="GITLAB_PIPELINE_"+pipeline_id+"_"+stage
               for stage in STAGES):
            raise InvalidEvidence("GitLab stage provenance mismatch.")
    else:
        raise InvalidEvidence("Unrecognized evidence pipeline provenance.")
    return data


def verify_ci_runtime(proposal,evidence,environ=None,stage="gate"):
    """Fail closed when real GitLab CI context is absent or does not match evidence.

    GitLab environment claims alone are not cryptographic CI attestation.
    This check is supplementary to GitLab's protected job graph.
    """
    env=os.environ if environ is None else environ
    if env.get("GITLAB_CI")!="true":
        raise InvalidEvidence("Verified GitLab CI environment required.")
    pipeline_id=env.get("CI_PIPELINE_ID","")
    commit=env.get("CI_COMMIT_SHA","")
    if not re.fullmatch(r"[0-9]{1,20}",pipeline_id):
        raise InvalidEvidence("Missing real GitLab pipeline ID.")
    if not re.fullmatch(r"[0-9a-f]{40}",commit):
        raise InvalidEvidence("Missing actual GitLab commit SHA.")
    if env.get("CI_JOB_STAGE")!=stage:
        raise InvalidEvidence("Incorrect CI stage for this gate.")
    if proposal["commit"]!=commit or evidence["commit"]!=commit:
        raise InvalidEvidence("CI commit identity mismatch.")
    if evidence["provenance"]["pipeline_id"]!=pipeline_id:
        raise InvalidEvidence("CI pipeline identity mismatch.")
    validate_evidence(evidence,proposal)
    return True


def decide(root,proposal,evidence):
    proposal=validate_proposal(proposal)
    evidence=validate_evidence(evidence,proposal)
    findings=inspect_paths(root,proposal)
    failed=[key for key,rec in evidence["stages"].items() if rec["status"]!="PASS"]
    blocked=bool(findings or failed)
    result={
        "version":1,
        "request_id":proposal["request_id"],
        "commit":proposal["commit"],
        "proposal_digest":sha256(proposal),
        "evidence_digest":sha256(evidence),
        "stage_results":{k:v["status"] for k,v in evidence["stages"].items()},
        "failed_or_unverified":sorted(failed),
        "path_findings":findings,
        "decision":"NO_GO" if blocked else "STAGING_CANDIDATE",
        "production_permitted":False,
        "deployment_performed":False,
        "reason":"Evidence gate blocked staging." if blocked else
                 "Reviewable staging candidate only; separate human approval needed for production.",
    }
    result["decision_digest"]=sha256(result)
    return result


def verify_approval(decision, approval, secret):
    """Optional human-authored approval check. NEVER grants production deployment."""
    if not isinstance(approval,dict) or set(approval)!={"request_id","decision_digest","approver","intent","signature"}:
        return False
    if decision["decision"]!="STAGING_CANDIDATE" or not secret:
        return False
    unsigned={k:v for k,v in approval.items() if k!="signature"}
    if unsigned["request_id"]!=decision["request_id"] or unsigned["decision_digest"]!=decision["decision_digest"]:
        return False
    if unsigned["intent"]!="acknowledge-staging-only" or not re.fullmatch(r"[A-Za-z0-9._-]{3,90}",unsigned["approver"]):
        return False
    expected=hmac.new(secret.encode(),canonical(unsigned),hashlib.sha256).hexdigest()
    return isinstance(approval["signature"],str) and hmac.compare_digest(expected,approval["signature"])


def synthetic_evidence(commit,mode="pass"):
    if mode not in ("pass","fail"):
        raise ValueError("mode must be pass or fail")
    stages={
        s:{"status":"PASS","source":"local-fixture-"+s}
        for s in STAGES
    }
    if mode=="fail":
        stages["security"]["status"]="FAIL"
    return {"version":1,"commit":commit,"stages":stages,
            "provenance":{"pipeline_id":"LOCAL_FIXTURE_NOT_GITLAB",
                          "runner":"synthetic-test-data",
                          "collected_at":datetime.now(timezone.utc).isoformat()}}


def main(argv=None):
    parser=argparse.ArgumentParser(description="Independent CI evidence gate. Does not deploy software.")
    sub=parser.add_subparsers(dest="command",required=True)
    check=sub.add_parser("check")
    check.add_argument("--root",required=True)
    check.add_argument("--proposal",required=True)
    check.add_argument("--evidence",required=True)
    check.add_argument("--output",required=True)
    check.add_argument("--require-gitlab",action="store_true",
                       help="Fail closed unless matching GitLab CI gate runtime is present.")
    demo=sub.add_parser("fixture")
    demo.add_argument("--commit",required=True)
    demo.add_argument("--output",required=True)
    demo.add_argument("--mode",choices=("pass","fail"),default="pass")
    args=parser.parse_args(argv)
    try:
        if args.command=="check":
            proposal=load_json(args.proposal)
            evidence=load_json(args.evidence)
            if args.require_gitlab:
                verify_ci_runtime(proposal,evidence)
            result=decide(args.root,proposal,evidence)
        else:
            if not re.fullmatch(r"[0-9a-f]{40,64}",args.commit):
                raise InvalidEvidence("Fixture commit must be hex.")
            result=synthetic_evidence(args.commit,args.mode)
        p=Path(args.output)
        if not p.parent.is_dir():
            raise InvalidEvidence("Output directory does not exist.")
        p.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        print(json.dumps({"command":args.command,
            "decision":result.get("decision","FIXTURE_ONLY"),
            "output":str(p),"production_permitted":False},sort_keys=True))
        return 0 if result.get("decision")!="NO_GO" else 2
    except (InvalidEvidence,OSError,TypeError,KeyError) as exc:
        print("NO_GO: "+str(exc),file=sys.stderr)
        return 3


if __name__=="__main__":
    raise SystemExit(main())
