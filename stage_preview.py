"""Staging receipt only: does not deploy or promote anything."""
import json
import os
from pathlib import Path

from releaseguard import decide,load_json

ROOT=Path(__file__).resolve().parent
proposal=load_json(ROOT/"release_proposal.json")
evidence=load_json(ROOT/"release_evidence.json")
report=load_json(ROOT/"release_decision.json")
recomputed=decide(ROOT,proposal,evidence)
if report!=recomputed or report["decision"]!="STAGING_CANDIDATE":
    raise SystemExit("Evidence digest mismatch or staging gate not passed.")
if report["production_permitted"] is not False:
    raise SystemExit("A production-permissive result is impossible.")
dir=ROOT/"public"
dir.mkdir(exist_ok=True)
details={"decision":report["decision"],"request_id":report["request_id"],
         "commit":report["commit"],"decision_digest":report["decision_digest"],
         "gitlab_pipeline":os.getenv("CI_PIPELINE_ID","LOCAL_FIXTURE_NOT_GITLAB"),
         "staging_artifact_created":True,"application_deployed":False,
         "production_permitted":False}
(ROOT/"staging_receipt.json").write_text(json.dumps(details,indent=2)+"\n")
(dir/"index.html").write_text(
    "<!doctype html><html lang='en'><meta charset='utf-8'>"
    "<title>ReleaseGuard Evidence</title>"
    "<h1>ReleaseGuard staging candidate</h1>"
    "<p>This is a CI artifact, not a deployed application.</p>"
    "<p>Commit: "+report["commit"]+"</p>"
    "<p>Production permission: NO</p></html>",encoding="utf-8")
print(json.dumps(details,sort_keys=True))
