"""Проверяет что pytest-json-report работает на сервере."""
import subprocess
import sys
import json
import os

project_root = "/opt/glava"
python_exe = os.path.join(project_root, ".venv", "bin", "python")
json_file = "/tmp/test_report_verify.json"

proc = subprocess.run(
    [python_exe, "-m", "pytest", "tests/test_bot_flows_v2.py",
     "--json-report", f"--json-report-file={json_file}",
     "--tb=short", "--no-header", "--color=no", "-q"],
    capture_output=True,
    text=True,
    cwd=project_root,
    timeout=60,
    env={**os.environ, "NO_COLOR": "1", "TERM": "dumb"},
)

print("returncode:", proc.returncode)
print("stdout:", proc.stdout[:300])
print("stderr:", proc.stderr[:200])

if os.path.exists(json_file):
    with open(json_file) as f:
        d = json.load(f)
    summary = d.get("summary", {})
    print("summary:", summary)
    print("tests count:", len(d.get("tests", [])))
    if d.get("tests"):
        print("first test:", d["tests"][0].get("nodeid"), "->", d["tests"][0].get("outcome"))
    os.unlink(json_file)
else:
    print("JSON file not created! Plugin may not be installed.")
    print("pip list:")
    r2 = subprocess.run([python_exe, "-m", "pip", "show", "pytest-json-report"],
                        capture_output=True, text=True)
    print(r2.stdout or "NOT FOUND")
