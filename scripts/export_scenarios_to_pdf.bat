@echo off
cd /d "%~dp0.."
if exist venv\Scripts\python.exe (
  venv\Scripts\python.exe scripts\export_scenarios_to_pdf.py
) else (
  python scripts\export_scenarios_to_pdf.py
)
if exist docs\USER_SCENARIOS.pdf echo PDF: docs\USER_SCENARIOS.pdf
pause
