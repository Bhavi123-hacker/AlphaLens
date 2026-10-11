@echo off
setlocal
cd /d "%~dp0..\.."
if "%~1"=="" (
  echo Usage: scripts\windows\start-alphalens.cmd path-to-private-config.json
  exit /b 2
)
".venv\Scripts\python.exe" -m alphalens_api.local.cli --config "%~1" start
exit /b %errorlevel%
