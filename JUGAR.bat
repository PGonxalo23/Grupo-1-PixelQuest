@echo off
setlocal
if not exist "%~dp0.venv\Scripts\python.exe" (
    echo Prepara el entorno .venv siguiendo las instrucciones de README.md.
    echo python -m venv .venv
    echo .venv\Scripts\python.exe -m pip install -r requirements.txt
    pause
    exit /b 1
)
"%~dp0.venv\Scripts\python.exe" -B "%~dp0src\main.py" %*
if errorlevel 1 pause
