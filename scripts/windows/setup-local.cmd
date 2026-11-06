@echo off
setlocal
cd /d "%~dp0..\.."
if not exist ".venv\Scripts\python.exe" (
  echo Existing AlphaLens Python environment is missing. No installation performed.
  exit /b 2
)
if "%~1"=="" (
  echo Usage: scripts\windows\setup-local.cmd path-to-private-config.json
  exit /b 2
)
call "%~dp0project-python.cmd" -m alphalens_api.local.cli --config "%~1" setup
exit /b %errorlevel%
