@echo off
setlocal
cd /d "%~dp0..\.."
if not exist ".venv\Scripts\python.exe" (
  echo Existing Python environment is missing. No installation performed.
  exit /b 2
)
rem A shared editable environment may point at a different checkout. Pin this tree.
set "PYTHONPATH=%CD%;%CD%\apps\api\src;%CD%\ml\data\src;%CD%\ml\features\src;%CD%\ml\labels\src;%CD%\ml\training\src;%CD%\ml\evaluation\src;%CD%\backtesting\src;%CD%\decision\src;%CD%\portfolio\src"
".venv\Scripts\python.exe" %*
exit /b %errorlevel%
