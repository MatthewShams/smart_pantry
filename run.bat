@echo off
echo Smart Pantry - Starting...
echo.

if "%GEMINI_API_KEY%"=="" (
    echo ERROR: GEMINI_API_KEY is not set!
    echo Run this first:
    echo   set GEMINI_API_KEY=AIza...
    pause
    exit /b 1
)

python main.py
pause
