"""Симулирует вызов pytest из Flask subprocess — проверяем вывод."""
import subprocess
import sys

r = subprocess.run(
    [sys.executable, "-m", "pytest", "tests/test_bot_flows_v2.py",
     "-v", "--tb=short", "--no-header"],
    capture_output=True,
    text=True,
    cwd="/opt/glava",
)
print("RC:", r.returncode)
print("--- STDOUT ---")
print(r.stdout[:1000])
print("--- STDERR ---")
print(r.stderr[:300])
