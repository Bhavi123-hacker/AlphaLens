@echo off
setlocal
cd /d "%~dp0..\.."
rem INACTIVE proposal: installing or selecting this wrapper needs operator approval.
if "%~1"=="" goto usage
if not "%~2"=="" goto usage
if not exist "%~f1" goto missing
set "WATCHLIST_PYTHON=%CD%\.local-data\completion-runtime\venv\Scripts\python.exe"
if not exist "%WATCHLIST_PYTHON%" goto missing
set "PYTHONPATH=%CD%;%CD%\apps\api\src;%CD%\ml\data\src;%CD%\ml\features\src;%CD%\ml\labels\src;%CD%\ml\training\src;%CD%\ml\evaluation\src;%CD%\ml\backtesting\src;%CD%\ml\decision\src;%CD%\ml\portfolio\src"
set "OPENBLAS_NUM_THREADS=1"
set "OMP_NUM_THREADS=1"
set "MKL_NUM_THREADS=1"
"%WATCHLIST_PYTHON%" -m workers.providers.daily --config "%~f1"
exit /b %errorlevel%
:missing
echo Prepared patched runtime or protected configuration is missing.
exit /b 2
:usage
echo Usage: p30-daily-update-patched.cmd PRIVATE_CONFIG
echo This inactive wrapper does not register or modify scheduled tasks.
exit /b 2
