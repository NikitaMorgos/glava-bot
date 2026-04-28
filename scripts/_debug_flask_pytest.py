"""Запускается от имени Flask-воркера — показывает что реально происходит."""
import subprocess
import sys
import os

print("sys.executable:", sys.executable)
print("cwd:", os.getcwd())

project_root = "/opt/glava"
r = subprocess.run(
    [sys.executable, "-m", "pytest", "tests/test_bot_flows_v2.py",
     "-v", "--tb=short", "--no-header"],
    capture_output=True,
    text=True,
    cwd=project_root,
    timeout=60,
)
print("returncode:", r.returncode)
print("stdout[:800]:\n", r.stdout[:800])
print("stderr[:400]:\n", r.stderr[:400])

# Проверяем парсер прямо здесь
import re
lines = r.stdout.splitlines()
test_line_re = re.compile(r"^(?P<test_id>\S+::test_\S+)\s+(?P<status>PASSED|FAILED|ERROR)")
found = [(m.group("test_id"), m.group("status")) for l in lines if (m := test_line_re.match(l))]
print(f"\nПарсер нашёл {len(found)} тестов:")
for t, s in found[:5]:
    print(f"  {s}: {t}")
