@echo off
setlocal
rem One command to inspect existing local AlphaLens evidence. No provider GETs,
rem task registration, database updates, or receipt creation.
cd /d "%~dp0..\.."
call "%~dp0project-python.cmd" "%CD%\scripts\check_local_release.py" --root "%CD%" --check-windows-tasks
exit /b %errorlevel%
