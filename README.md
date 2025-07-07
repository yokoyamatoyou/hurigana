# Hurigana Checker

This repository provides a Streamlit application for checking the reliability of furigana (phonetic readings) in Excel files.

## Setup

Install dependencies with Python 3.11:

```bash
pip install -r requirements.txt
```

Set your OpenAI API key:

```bash
export OPENAI_API_KEY="sk-..."
```

## Usage

Run the app locally:

```bash
streamlit run app.py
```

Upload an Excel file, select the name and furigana columns, and download the result with confidence scores.
