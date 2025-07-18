# Project AGENTS instructions

This repository is for implementing a Streamlit GUI application that uploads an Excel file, calculates reliability of human name readings (furigana), and overwrites the Excel file with the results.

## Environment
* **Python 3.11**.
* Requires packages:
  - `sudachipy`
  - `sudachidict-full`
  - `openai>=1.30.0`
  - `pandas>=2.3`
  - `openpyxl`, `xlsxwriter`
  - `streamlit>=1.35`

Use `pip install sudachipy sudachidict-full openai pandas streamlit openpyxl xlsxwriter` to install dependencies.

## API key
The OpenAI API key is taken from the environment variable `OPENAI_API_KEY`.

## Structure
```
project/
├─ app.py            # Streamlit GUI
├─ core/
│   ├─ parser.py     # Sudachi + dictionary preprocessing
│   ├─ scorer.py     # GPT invocation & confidence scoring
│   └─ utils.py      # shared utilities
└─ requirements.txt
```

The application uses a single Streamlit page with file upload, processing, and download in one workflow. Sudachi tokenizer is held globally for speed.

## Furigana Entry Rules
These guidelines standardize how operators type readings:

1. **Use full-size characters for palatal sounds** – e.g. type `ｷﾖｳｺ` instead of `ｷｮｳｺ`.
2. **Handle voiced sounds in either form** – both `ﾀﾞ` as one half-width character and `ﾀﾞ` typed as `ﾀ` followed by `ﾞ` are accepted.
3. **Other characters** – "ヲ" and "ー" are entered as is without conversion.

## Processing Flow
1. Read Excel file with pandas.
2. For each name, use SudachiPy with `SudachiDict-full` to get the standard reading. If found, confidence 95% with reason "辞書候補1位一致".
3. For unknown words, call GPT-4.1 mini (knowledge cutoff 2025-04-14) in two steps:
   - `temperature=0.0` returning three candidates.
   - `temperature=0.7` returning five candidates.
   - Deduplicate results and keep at most 9 candidates in total.
4. Calculate confidence based on candidate ranking and provide a short reason (within 20 characters).
5. Combine results into DataFrame and export to Excel using `openpyxl` to preserve formatting.
6. Provide a download button for the processed file.
7. The previous two-phase method produced only a single candidate in some cases.
8. The updated multi-temperature approach generates more variations and flags potential keypuncher errors.

## Error handling
* Process in batches of 50 rows and retry with exponential backoff on API rate limits.
* Validate name length (≤50 chars).
* Allow user to choose the target column via `st.selectbox`.

## Deployment
Run locally with:
```bash
export OPENAI_API_KEY="sk-..."
streamlit run app.py
```

Streamlit Community Cloud or Hugging Face Spaces can host the app with `requirements.txt` and `app.py`.

## Future ideas
* Use RAG with a SQLite + ChromaDB for previously confirmed readings.
* Add accent information via Whisper.
* Support multilingual names with fallback to pykakasi and LLM.

