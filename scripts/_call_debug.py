"""Вызывает debug endpoint напрямую через HTTP с сервера."""
import urllib.request
import json

# Нужна авторизованная сессия — используем внутренний вызов с bypass
# Альтернатива: запустить функцию напрямую

import sys
sys.path.insert(0, "/opt/glava")

import subprocess
import os

project_root = "/opt/glava"
python_venv = os.path.join(project_root, ".venv", "bin", "python")
python_exe = python_venv if os.path.exists(python_venv) else sys.executable

print("python_exe:", python_exe)
print("project_root:", project_root)

proc = subprocess.run(
    [python_exe, "-m", "pytest", "tests/test_bot_flows_v2.py",
     "-v", "--tb=short", "--no-header"],
    capture_output=True,
    text=True,
    cwd=project_root,
    timeout=60,
    env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
)
print("returncode:", proc.returncode)
print("stdout_lines:", len(proc.stdout.splitlines()))
print("stdout[:600]:", proc.stdout[:600])
print("stderr[:200]:", proc.stderr[:200])

# Тест парсера
import re
test_line_re = re.compile(r"^(?P<test_id>\S+::test_\S+)\s+(?P<status>PASSED|FAILED|ERROR)")
lines = proc.stdout.splitlines()
matches = [(m.group("test_id"), m.group("status")) for l in lines if (m := test_line_re.match(l))]
print(f"\nПарсер: {len(matches)} тестов")
