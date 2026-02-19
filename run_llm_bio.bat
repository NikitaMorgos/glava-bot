@echo off
cd /d "%~dp0"
REM Читаем OPENAI_API_KEY из .env и передаём в Python
for /f "usebackq tokens=1,* delims==" %%a in (`findstr /b "OPENAI_API_KEY=" .env 2^>nul`) do set "OPENAI_API_KEY=%%b"
python scripts\run_llm_bio.py
pause
