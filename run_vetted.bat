@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    py -3.12 -m venv .venv
    if errorlevel 1 goto :failed
)

".venv\Scripts\python.exe" -c "import streamlit" >nul 2>&1
if errorlevel 1 (
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 goto :failed
)

echo.
echo Vetted is starting. Open http://localhost:8501/
echo Press Ctrl+C in this window to stop the app.
echo.
".venv\Scripts\python.exe" -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501
goto :eof

:failed
echo.
echo Vetted could not start. Check that Python 3.12 is installed and try again.
pause
exit /b 1
