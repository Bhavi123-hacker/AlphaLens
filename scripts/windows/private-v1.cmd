@echo off
setlocal
rem Reuse the protected installed runtime; select the deployment explicitly.
if not defined ALPHALENS_PRIVATE_V1_WORKSPACE set "ALPHALENS_PRIVATE_V1_WORKSPACE=D:\al-research\p28-worktree"
set "ALPHALENS_PRIVATE_V1_PYTHON=%ALPHALENS_PRIVATE_V1_WORKSPACE%\.local-data\completion-runtime\venv\Scripts\python.exe"
if not exist "%ALPHALENS_PRIVATE_V1_PYTHON%" (
  echo Private runtime missing. No environment or account was replaced.
  exit /b 2
)
cd /d "%ALPHALENS_PRIVATE_V1_WORKSPACE%"
rem PYTHONPATH is pinned again for the backend by the manifest-aware launcher.
set "PYTHONPATH=%~dp0..\..;%~dp0..\..\apps\api\src;%~dp0..\..\ml\data\src;%~dp0..\..\ml\features\src;%~dp0..\..\ml\labels\src;%~dp0..\..\ml\training\src;%~dp0..\..\ml\evaluation\src;%~dp0..\..\backtesting\src;%~dp0..\..\decision\src;%~dp0..\..\portfolio\src"
"%ALPHALENS_PRIVATE_V1_PYTHON%" "%~dp0..\private_v1_local.py" %*
exit /b %errorlevel%
