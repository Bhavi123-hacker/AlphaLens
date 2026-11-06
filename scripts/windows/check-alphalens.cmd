@echo off
setlocal
cd /d "%~dp0..\.."
if "%~1"=="" (
  echo Usage: scripts\windows\check-alphalens.cmd path-to-private-config.json
  exit /b 2
)
call "%~dp0project-python.cmd" -m alphalens_api.local.cli --config "%~1" check
exit /b %errorlevel%
