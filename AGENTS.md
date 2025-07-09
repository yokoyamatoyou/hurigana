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
3. For unknown words, call GPT-4.1 mini in two phases:
   - Phase 1: `temperature=0.0`, `logprobs=5` to get top reading.
   - Phase 2: `temperature=0.7`, `top_p=1.0`, `n=5` to get up to five candidates.
   - This two-phase algorithm is kept as-is for consistent scoring.
4. Calculate confidence based on candidate ranking and provide a short reason (within 20 characters).
5. Combine results into DataFrame and export to Excel using `openpyxl` to preserve formatting.
6. Provide a download button for the processed file.
7. 上記のアルゴリズムでは不具合発生中、指示内容ではアルゴリズムが目標を達成できません。
8. 具体的に言うと、宮川　亜紀という名前に対して1パターンの名前 宮川　亜紀     ﾐﾔｶﾜ ｱｷ   がフリガナとして登録されており、結果は候補外･要確認です。
しかし名前の候補は   [ミヤガワアキ, ]のみで複数パターンが推論されていません。
アルゴリズムを変更して、上位ｎ件を一回のプロンプトで温度0で3件、温度2で5件を出して、温度5で5件、sudachiの結果は今まで通りで、重複しないように確認しながら推論して、フリガナに当てはまるかに変更します。現在のアルゴリズムでは1パターン以外が出てこないのでなぜ1パターンしか出ないのかを解決する必要があります、複数のフリガナを推論して、キーパンチャーの入力間違いの可能性が高い内容にフラグを立てるのがこのリポジトリの目標です。

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

