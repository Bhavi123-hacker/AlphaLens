@echo off
setlocal enabledelayedexpansion

rem ==============================================================================
rem  AlphaLens — One-Click Windows Daily Pipeline & Settlement Runner
rem  Executes full 15-stage daily research, ML inference, and settlement workflow.
rem ==============================================================================

cd /d "%~dp0"
set "REPO_ROOT=%~dp0"
if "%REPO_ROOT:~-1%"=="\" set "REPO_ROOT=%REPO_ROOT:~0,-1%"

rem 1. Locate Verified Python Virtual Environment
set "PYTHON_EXE="
if exist "%REPO_ROOT%\.local-data\completion-runtime\venv\Scripts\python.exe" (
    set "PYTHON_EXE=%REPO_ROOT%\.local-data\completion-runtime\venv\Scripts\python.exe"
) else if exist "D:\al-research\p28-worktree\.local-data\completion-runtime\venv\Scripts\python.exe" (
    set "PYTHON_EXE=D:\al-research\p28-worktree\.local-data\completion-runtime\venv\Scripts\python.exe"
) else if exist "%REPO_ROOT%\.venv\Scripts\python.exe" (
    set "PYTHON_EXE=%REPO_ROOT%\.venv\Scripts\python.exe"
) else if exist "%REPO_ROOT%\..\.venv\Scripts\python.exe" (
    set "PYTHON_EXE=%REPO_ROOT%\..\.venv\Scripts\python.exe"
) else (
    where python >nul 2>nul
    if !errorlevel! equ 0 (
        for /f "delims=" %%i in ('where python') do (
            if not defined PYTHON_EXE set "PYTHON_EXE=%%i"
        )
    )
)

if not defined PYTHON_EXE (
    echo [ERROR] No suitable Python interpreter found.
    echo Please ensure the AlphaLens virtualenv exists at .local-data\completion-runtime\venv or .venv.
    exit /b 2
)

rem 2. Configure Environment and Python Paths
set "PYTHONPATH=%REPO_ROOT%;%REPO_ROOT%\apps\api\src;%REPO_ROOT%\ml\data\src;%REPO_ROOT%\ml\features\src;%REPO_ROOT%\ml\labels\src;%REPO_ROOT%\ml\training\src;%REPO_ROOT%\ml\evaluation\src;%REPO_ROOT%\backtesting\src;%REPO_ROOT%\decision\src;%REPO_ROOT%\portfolio\src"
set "OPENBLAS_NUM_THREADS=1"
set "OMP_NUM_THREADS=1"
set "MKL_NUM_THREADS=1"
set "NUMEXPR_NUM_THREADS=1"

rem 3. Execute Daily Pipeline Orchestrator
"%PYTHON_EXE%" "%REPO_ROOT%\scripts\daily_pipeline_orchestrator.py" %*
set "EXIT_CODE=%errorlevel%"

exit /b %EXIT_CODE%
