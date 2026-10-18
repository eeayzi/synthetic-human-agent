@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Set up the Python environment first using README.md.
  pause
  exit /b 2
)
".venv\Scripts\python.exe" main.py --mode live --check
if errorlevel 1 (
  pause
  exit /b 2
)
echo Starting the 15-minute session. F8 or a screen corner stops input.
".venv\Scripts\python.exe" main.py --mode live
set "agent_run_code=%errorlevel%"
echo Session exit code: %agent_run_code%
pause
exit /b %agent_run_code%
