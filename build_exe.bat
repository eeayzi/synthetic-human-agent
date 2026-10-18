@echo off
rem Builds dist\SyntheticHumanAgent\SyntheticHumanAgent.exe (plus a zip of that folder).
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Creating .venv ...
  py -m venv .venv || goto :fail
)
".venv\Scripts\python.exe" -m pip install -r requirements.txt pyinstaller || goto :fail
".venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean --console --name SyntheticHumanAgent ^
  --collect-all playwright ^
  --hidden-import pythoncom --hidden-import pywintypes --hidden-import win32api --hidden-import win32gui ^
  --hidden-import win32process --hidden-import win32com.client --hidden-import winreg ^
  --hidden-import desktop --hidden-import web_agent --hidden-import office_agent ^
  exe_entry.py || goto :fail
copy /y config.json   "dist\SyntheticHumanAgent\" >nul || goto :fail
copy /y scenario.json "dist\SyntheticHumanAgent\" >nul || goto :fail
copy /y README.md     "dist\SyntheticHumanAgent\" >nul
powershell -NoProfile -Command "Compress-Archive -Force -Path 'dist\SyntheticHumanAgent\*' -DestinationPath 'dist\SyntheticHumanAgent.zip'"
echo.
echo Done: dist\SyntheticHumanAgent\SyntheticHumanAgent.exe
echo       dist\SyntheticHumanAgent.zip  (copy this to another PC and extract it)
pause
exit /b 0
:fail
echo.
echo Build failed - see the messages above.
pause
exit /b 1
