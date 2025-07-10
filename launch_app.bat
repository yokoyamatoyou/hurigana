@echo off
REM Start the Hurigana Checker Streamlit app
SETLOCAL
cd /d %~dp0

IF "%OPENAI_API_KEY%"=="" (
    echo Please set the OPENAI_API_KEY environment variable before running.
    exit /b 1
)

streamlit run app.py
