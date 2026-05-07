@echo off
setlocal
cd /d "%~dp0"

echo Setting up InterviewCoach AI...

if not exist ".venv" (
    echo Creating virtual environment...
    py -3 -m venv .venv
    if errorlevel 1 (
        echo py launcher failed. Trying python...
        python -m venv .venv
    )
) else (
    echo Virtual environment already exists.
)

if not exist ".venv\Scripts\python.exe" (
    echo Could not find .venv\Scripts\python.exe. Please check your Python installation.
    exit /b 1
)

echo Upgrading pip...
".venv\Scripts\python.exe" -m pip install --upgrade pip

echo Installing dependencies...
".venv\Scripts\pip.exe" install -r requirements.txt

if not exist ".env" (
    echo Creating .env from .env.example...
    copy ".env.example" ".env" >nul
) else (
    echo .env already exists.
)

if not exist "data" (
    mkdir data
)

if not exist "data\.gitkeep" (
    type nul > "data\.gitkeep"
)

echo.
echo Setup complete.
echo.
echo Next steps for VS Code:
echo 1. Open the .env file.
echo 2. Add your Gemini API key to GEMINI_API_KEY or GOOGLE_API_KEY.
echo 3. Optional: add your Tavily API key to TAVILY_API_KEY for real study links.
echo 4. Run run.bat from the VS Code terminal.
echo.
endlocal
