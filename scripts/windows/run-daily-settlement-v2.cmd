@echo off
setlocal
cd /d "%~dp0..\.."
rem Prepared candidate only. No existing scheduled task points at this wrapper.
rem Registering a task action for it requires explicit operator approval.

set "SETTLEMENT_PYTHON=%CD%\.venv\Scripts\python.exe"
if not exist "%SETTLEMENT_PYTHON%" (
    set "SETTLEMENT_PYTHON=%CD%\..\.venv\Scripts\python.exe"
)
if not exist "%SETTLEMENT_PYTHON%" (
    set "SETTLEMENT_PYTHON=C:\Program Files\Python312\python.exe"
)
if not exist "%SETTLEMENT_PYTHON%" goto missing_python

set "WORKFLOW_SCRIPT=%CD%\scripts\daily_settlement_workflow.py"
if not exist "%WORKFLOW_SCRIPT%" goto missing_script

set "PYTHONPATH=%CD%;%CD%\apps\api\src;%CD%\ml\data\src;%CD%\ml\features\src;%CD%\ml\labels\src;%CD%\ml\training\src;%CD%\ml\evaluation\src;%CD%\backtesting\src;%CD%\decision\src;%CD%\portfolio\src"
set "OPENBLAS_NUM_THREADS=1"
set "OMP_NUM_THREADS=1"
set "MKL_NUM_THREADS=1"

"%SETTLEMENT_PYTHON%" "%WORKFLOW_SCRIPT%" --as-of-session AUTO %*
exit /b %errorlevel%

:missing_python
echo Error: Verified Python interpreter not found at %SETTLEMENT_PYTHON%
exit /b 2

:missing_script
echo Error: Workflow script not found at %WORKFLOW_SCRIPT%
exit /b 2
