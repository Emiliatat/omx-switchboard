@echo off
py -3 -c "import sys" >nul 2>nul
if %errorlevel%==0 (
  py -3 "%~dp0omxr.py" %*
  exit /b %errorlevel%
)
python "%~dp0omxr.py" %*
