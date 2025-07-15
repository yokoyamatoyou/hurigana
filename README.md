# Hurigana Checker

This repository provides a Streamlit application for checking the reliability of furigana (phonetic readings) in Excel files.

## Setup

Install dependencies with Python 3.11.  You can use ``requirements.txt`` or
install the key packages individually:

```bash
pip install -r requirements.txt
```

```bash
pip install sudachipy sudachidict-full openai pandas streamlit openpyxl xlsxwriter
```

Set your OpenAI API key:

```bash
export OPENAI_API_KEY="sk-..."
```

Optionally choose the OpenAI model (defaults to `gpt-4.1-mini-2025-04-14`):

```bash
export OPENAI_MODEL="gpt-3.5-turbo"
```

Optionally specify the SQLite cache location:

```bash
export FURIGANA_DB="/path/to/cache.db"
```

On Windows you can run ``run_app.bat`` after setting ``OPENAI_API_KEY``.
The script simply calls ``streamlit run app.py``.

The ``process_dataframe`` helper accepts an optional ``batch_size`` argument
to control how many rows are processed at once (default ``50``). Duplicate
names are consolidated globally before querying the GPT API.

## Furigana Entry Rules

When typing readings into Excel, follow these conventions so the checker can
produce consistent results:

1. Use **full-size characters** for palatal sounds—for example, type ``ｷﾖｳｺ``
   instead of ``ｷｮｳｺ``.
2. Both forms of voiced sounds are accepted: either the single half-width
   character ``ﾀﾞ`` or the base character ``ﾀ`` followed by ``ﾞ``.
3. Characters like ``ヲ`` and ``ー`` are entered as is without conversion.

### Candidate Generation

Unknown names are first looked up with Sudachi. If a dictionary reading is found
it becomes the top candidate. The list is then expanded by two GPT calls:

* ``temperature=0.0`` returning three candidates
* ``temperature=0.7`` returning five candidates

Duplicates are removed before scoring. The final list keeps at most
``9`` unique candidates.

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

## Example

The library can also be used programmatically. The snippet below
demonstrates checking a single pair of name and reading:

```python
import pandas as pd
from core.utils import process_dataframe

df = pd.DataFrame({"名前": ["田中　堅"], "フリガナ": ["ﾀﾅｶ ｶﾀｼ"]})
out = process_dataframe(df, "名前", "フリガナ")
print(out)
```

Running this prints a DataFrame with the confidence score and reason.
The exact values depend on the GPT candidate readings, but it will look
similar to the following:

```
     名前     フリガナ  信頼度       理由
0  田中　堅  ﾀﾅｶ ｶﾀｼ   30  候補外･要確認
```
