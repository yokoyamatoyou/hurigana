# Performance Improvement Plan

This document outlines a plan to reduce the time required for checking large numbers of
furigana readings. The current implementation calls the GPT API twice for every name in a
synchronous loop. When processing many rows this leads to long wait times because each API
call is executed sequentially and any retry delay is accumulated.

## Goals
* Keep the existing two‑phase algorithm (`gpt_candidates`) for accuracy.
* Allow multiple names to be processed concurrently so that waiting on the API happens in
  parallel.
* Limit concurrency to avoid hitting API rate limits.

## Proposed Changes
1. **Introduce asynchronous GPT calls**
   - Add `async_gpt_candidates` that mirrors `gpt_candidates` but uses the `async`
     version of `openai`'s client.
   - Each function will still perform the temperature 0.0 and 0.7 calls internally.

2. **Update `process_dataframe`**
   - Make an asynchronous variant (`async_process_dataframe`) that schedules
     `async_gpt_candidates` for each row.
   - Use `asyncio.gather` with a semaphore (e.g. max 10 tasks) so only a limited
     number of requests run at once.
   - Keep the existing batch logic to control memory usage.
   - Deduplicate names so GPT is queried once per unique value.

3. **Preserve caching**
   - Reuse the existing SQLite cache and LRU cache so previously processed names
     skip the API entirely.

4. **Streamlit integration**
   - When calling from the GUI, run `asyncio.run(async_process_dataframe(...))` so
     the user interface stays responsive while tasks run in parallel.

Implementing these steps should reduce the total runtime roughly in proportion to
 the chosen concurrency level while maintaining the current scoring algorithm.
