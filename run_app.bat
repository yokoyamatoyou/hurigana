@echo off
REM Launch the Hurigana Checker Streamlit app

IF "%OPENAI_API_KEY%"=="" (
    echo Please set the OPENAI_API_KEY environment variable before running.
    exit /b 1
)

streamlit run app.py
