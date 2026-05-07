@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\streamlit.exe" (
    echo Virtual environment not found. Please run setup.bat first.
    exit /b 1
)

".venv\Scripts\streamlit.exe" run app.py
endlocal
