@echo off
setlocal
cd /d "%~dp0..\.."
rem Prepared candidate only. No existing scheduled task points at this wrapper.
rem Registering a task action for it requires explicit operator approval.
if "%~1"=="" goto usage
if not "%~2"=="" goto usage
if not exist "%~f1" goto missing
set "COLLECTOR_PYTHON=%CD%\.local-data\production-collector-runtime-20261024\venv\Scripts\python.exe"
if not exist "%COLLECTOR_PYTHON%" goto missing
set "PYTHONPATH=%CD%;%CD%\apps\api\src;%CD%\ml\data\src;%CD%\ml\features\src;%CD%\ml\labels\src;%CD%\ml\training\src;%CD%\ml\evaluation\src;%CD%\backtesting\src;%CD%\decision\src;%CD%\portfolio\src"
set "OPENBLAS_NUM_THREADS=1"
set "OMP_NUM_THREADS=1"
set "MKL_NUM_THREADS=1"
"%COLLECTOR_PYTHON%" -m workers.nse_market.launcher --config "%~f1"
exit /b %errorlevel%
:missing
echo Prepared isolated collector or protected configuration is missing.
exit /b 2
:usage
echo Usage: run-nse-collector-isolated.cmd PRIVATE_CONFIG
echo This prepared wrapper does not register or modify scheduled tasks.
exit /b 2
