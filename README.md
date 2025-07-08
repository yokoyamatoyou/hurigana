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

Optionally choose the OpenAI model (defaults to `gpt-4o-mini`):

```bash
export OPENAI_MODEL="gpt-3.5-turbo"
```

Optionally specify the SQLite cache location:

```bash
export FURIGANA_DB="/path/to/cache.db"
```

The ``process_dataframe`` helper accepts an optional ``batch_size`` argument
to control how many rows are processed at once (default ``50``). Duplicate
names are consolidated globally before querying the GPT API.

## Usage

Run the app locally. The Streamlit interface now leverages the asynchronous
processing helpers to reduce waiting time on large files:

```bash
streamlit run app.py
```

Upload an Excel file, select the name and furigana columns, and download the result with confidence scores.

Both ``process_dataframe`` and ``async_process_dataframe`` now consolidate
duplicate names so the GPT API is invoked only once per unique value. The async
variant additionally allows limited concurrency for further speedups.

For details on the async implementation and tuning options, see
[docs/performance_plan.md](docs/performance_plan.md).
