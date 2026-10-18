"""Simple zero-dependency repository secret check, not a full SAST engine."""
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parent
SKIP={".git",".venv","__pycache__","public",".local"}
EXT={".py",".md",".yml",".yaml",".toml",".json",".sh"}
KEYS=[
    re.compile(r"(?i)\b(?:sk_live_|ghp_|glpat-)[A-Za-z0-9_-]{12,}"),
    re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----"),
    re.compile(r"(?i)\b(?:password|api_key|secret)\s*=\s*['\"][^'\"]{8,}['\"]"),
]
findings=[]
scanned=0
for file in sorted(ROOT.rglob("*")):
    if not file.is_file() or file.suffix not in EXT or any(p in SKIP for p in file.relative_to(ROOT).parts):
        continue
    if file.stat().st_size>150_000:
        findings.append({"file":str(file.relative_to(ROOT)),"issue":"too_large"})
        continue
    scanned+=1
    data=file.read_text(encoding="utf-8",errors="replace")
    if any(regex.search(data) for regex in KEYS):
        findings.append({"file":str(file.relative_to(ROOT)),"issue":"secret_pattern"})
report={"version":1,"scanned_files":scanned,"findings":findings,"passed":not findings}
(ROOT/"scan_results.json").write_text(json.dumps(report,sort_keys=True,indent=2)+"\n")
print(json.dumps({"files_scanned":scanned,"findings":len(findings),"passed":not findings}))
raise SystemExit(0 if not findings else 3)
