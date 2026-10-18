"""Generate a read-only, self-contained evidence dashboard CI artifact.

This never deploys an application, publishes a URL, or grants production access.
Offline fixtures are prominently identified as simulations.
"""
from datetime import datetime, timezone
from html import escape
import json
import os
from pathlib import Path

from releaseguard import STAGES, decide, load_json, verify_ci_runtime

ROOT = Path(__file__).resolve().parent
STAGE_LABELS = {
    "tests": "Unit tests",
    "security": "Source security",
    "license": "License verification",
    "documentation": "Documentation",
    "rollback": "Recovery planning",
}


def _safe(value):
    return escape(str(value), quote=True)


def build_dashboard(receipt, decision, evidence):
    """Pure static HTML template; all untrusted fields are HTML-escaped."""
    if decision["decision"] != "STAGING_CANDIDATE" or receipt["production_permitted"] is not False:
        raise ValueError("Only staging candidate receipts can be presented.")
    pipeline = evidence["provenance"]["pipeline_id"]
    fixture = pipeline == "LOCAL_FIXTURE_NOT_GITLAB"
    if fixture:
        run_type = "LOCAL TEST FIXTURE"
        verification = "SIMULATED INPUT — NOT A GITLAB PIPELINE"
        note = "These statuses were generated using local fixture inputs. No live CI, GitLab Duo session, deployment, or production approval has been verified."
    else:
        run_type = "GITLAB CI CONTEXT"
        verification = "CI JOB EVIDENCE — CONFIRM IN GITLAB UI"
        note = "This record was produced within a declared GitLab CI job. Inspect the real pipeline and Duo session history before relying on this evidence; environment variables are not cryptographic attestation."
    lines = []
    for stage in STAGES:
        item=evidence["stages"][stage]
        status=item["status"]
        icon = "✓" if status == "PASS" else "!"
        lines.append(
            '<div class="stage"><span class="stage-icon">' + icon + '</span>'
            '<div class="stage-copy"><strong>' + _safe(STAGE_LABELS[stage]) +
            '</strong><small>' + _safe(item["source"]) + '</small></div>'
            '<span class="stage-status">' + _safe(status) + '</span></div>'
        )
    rows = "\n".join(lines)
    report_json = json.dumps({
        "receipt":receipt,
        "decision":decision,
        "evidence":evidence,
    }, ensure_ascii=True, indent=2)
    report_html = _safe(report_json)
    page = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow">
<title>ReleaseGuard · Evidence Audit</title>
<style>
:root { color-scheme:dark; font-family:Inter,Segoe UI,system-ui,sans-serif;
  background:#070f1c; color:#edf7ff; }
*{box-sizing:border-box}
body{margin:0;background:radial-gradient(ellipse 65% 43% at 68% 10%,#1a3f5a70,transparent 85%),#070f1c}
.shell{max-width:1130px;padding:30px 30px 75px;margin:auto}
header{display:flex;align-items:center;justify-content:space-between;gap:18px;
  padding-bottom:22px;border-bottom:1px solid #29465f}
.brand{font-weight:830;letter-spacing:-.05em;font-size:24px}
.brand-mark{display:inline-flex;align-items:center;justify-content:center;
  width:38px;height:38px;border-radius:10px;background:#75d4dd;color:#07202c;margin-right:12px}
.tag{color:#a7f2dd;background:#1c51444d;border:1px solid #5dd0af66;
  padding:9px 14px;border-radius:100px;font-size:11px;font-weight:800;letter-spacing:.1em}
.hero{padding:60px 0 35px}
.kicker{font:700 12px ui-monospace,monospace;letter-spacing:.13em;color:#8edee6}
h1{font-size:clamp(41px,5vw,63px);line-height:1.05;letter-spacing:-.06em;margin:13px 0 15px}
h1 em{font-style:normal;color:#74e1cf}
.summary{color:#a8bdd0;font-size:16px;max-width:710px;line-height:1.7}
.warning{padding:16px 19px;border-radius:11px;background:#9c6a3217;
  border:1px solid #e1b77668;color:#f6daa5;line-height:1.6;margin-top:28px}
main{display:grid;grid-template-columns:1.25fr .75fr;gap:20px;margin-top:28px}
.panel{min-width:0;background:#0f1d30e8;border:1px solid #33546e;border-radius:17px;padding:27px}
h2{font-size:19px;margin:0 0 22px;letter-spacing:-.025em}
.stage{display:flex;align-items:center;border-top:1px solid #2d465f;padding:17px 0;gap:13px}
.stage-icon{background:#234f4b;border-radius:9px;color:#83eccb;display:flex;
  align-items:center;justify-content:center;width:32px;height:32px;font-weight:900}
.stage-copy{flex:1;min-width:0}.stage-copy strong{display:block;font-size:14px}
.stage-copy small{display:block;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
  color:#91a8c3;font:11px ui-monospace,monospace;margin-top:6px}
.stage-status{color:#80e2bf;font:800 10px ui-monospace,monospace}
.stat{margin:18px 0 26px;border-bottom:1px solid #29465f;padding-bottom:20px}
.stat small{font:730 10px ui-monospace,monospace;color:#93afc6;display:block;
  letter-spacing:.1em;margin-bottom:8px}
.stat strong{font-size:21px;letter-spacing:-.035em;overflow-wrap:anywhere}
.no{color:#f5b19f}
.details{margin-top:22px}
details summary{cursor:pointer;color:#93e5ea;font-weight:700;font-size:13px}
pre{white-space:pre-wrap;word-break:break-word;line-height:1.5;padding:15px;
  color:#a9c8dd;background:#071526;border-radius:10px;font:11px ui-monospace,monospace;
  max-height:400px;overflow:auto}
footer{margin-top:34px;border-top:1px solid #29465f;padding-top:24px;
  font:12px ui-monospace,monospace;color:#7d9bb5;line-height:1.7}
@media(max-width:760px){main{grid-template-columns:minmax(0,1fr)}.shell{padding:20px 16px}
  header{flex-wrap:wrap}.hero{padding:42px 0 17px}}
</style></head><body><div class="shell">
<header><div class="brand"><span class="brand-mark">R</span>ReleaseGuard<span style="color:#71e7d9">.</span></div>
<div class="tag">__RUN_TYPE__</div></header>
<section class="hero"><div class="kicker">EVIDENCE-BASED RELEASE GOVERNANCE</div>
<h1>Review the evidence.<br><em>Not the assertion.</em></h1>
<p class="summary">A governed release workflow in which agents advise,
independent checks assess, and production access remains locked.</p>
<div class="warning"><strong>__VERIFICATION__</strong><br>__NOTE__</div>
</section>
<main><section class="panel"><h2>Release quality gates</h2>__STAGES__</section>
<aside class="panel"><h2>Release decision</h2>
<div class="stat"><small>DECISION</small><strong>STAGING CANDIDATE</strong></div>
<div class="stat"><small>PRODUCTION PERMITTED</small><strong class="no">NO</strong></div>
<div class="stat"><small>APPLICATION DEPLOYED</small><strong class="no">NO</strong></div>
<div class="stat"><small>CI PIPELINE</small><strong>__PIPELINE__</strong></div>
<div class="stat"><small>COMMIT</small><strong style="font-size:14px">__COMMIT__</strong></div>
</aside></main>
<div class="panel details"><details><summary>Inspect machine-readable evidence and digests</summary>
<pre>__JSON__</pre></details></div>
<footer>ReleaseGuard · Independent evidence gate · MIT open source<br>
Static CI artifact only. Does not certify application safety or authorize production.</footer>
</div></body></html>"""
    return (page.replace("__RUN_TYPE__", _safe(run_type))
            .replace("__VERIFICATION__", _safe(verification))
            .replace("__NOTE__", _safe(note))
            .replace("__STAGES__", rows)
            .replace("__PIPELINE__", _safe(pipeline))
            .replace("__COMMIT__", _safe(receipt["commit"]))
            .replace("__JSON__", report_html))


def construct_receipt(root, environ=None):
    env=os.environ if environ is None else environ
    root=Path(root)
    proposal=load_json(root/"release_proposal.json")
    evidence=load_json(root/"release_evidence.json")
    report=load_json(root/"release_decision.json")
    if env.get("GITLAB_CI")=="true":
        verify_ci_runtime(proposal,evidence,environ=env,stage="stage")
    elif evidence["provenance"]["pipeline_id"]!="LOCAL_FIXTURE_NOT_GITLAB":
        raise ValueError("A local artifact cannot claim GitLab pipeline provenance.")
    recomputed=decide(root,proposal,evidence)
    if report!=recomputed or report["decision"]!="STAGING_CANDIDATE":
        raise ValueError("Evidence digest mismatch or gate rejected stage admission.")
    if report["production_permitted"] is not False or report["deployment_performed"] is not False:
        raise ValueError("A deployment-permissive result is invalid.")
    receipt={
        "decision":report["decision"],
        "request_id":report["request_id"],
        "commit":report["commit"],
        "decision_digest":report["decision_digest"],
        "gitlab_pipeline":evidence["provenance"]["pipeline_id"],
        "staging_artifact_created":True,
        "application_deployed":False,
        "production_permitted":False,
    }
    return receipt,report,evidence


def main():
    receipt,decision,evidence=construct_receipt(ROOT)
    html=build_dashboard(receipt,decision,evidence)
    directory=ROOT/"public"
    directory.mkdir(exist_ok=True)
    (directory/"index.html").write_text(html,encoding="utf-8")
    (ROOT/"staging_receipt.json").write_text(
        json.dumps(receipt,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(receipt,sort_keys=True))


if __name__=="__main__":
    main()
