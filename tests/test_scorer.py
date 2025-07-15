from unittest.mock import patch, AsyncMock
import types
import openai
import asyncio

from core import scorer


def test_call_with_backoff_retries_api_connection_error():
    success = object()
    responses = [openai.APIConnectionError(message="fail", request=None), success]

    def side_effect(*args, **kwargs):
        result = responses.pop(0)
        if isinstance(result, Exception):
            raise result
        return result

    with patch(
        "core.scorer.client.chat.completions.create",
        side_effect=side_effect,
    ) as mock_create, patch("time.sleep") as sleep_mock:
        result = scorer._call_with_backoff(model="dummy", messages=[])

    assert result is success
    assert mock_create.call_count == 2
    sleep_mock.assert_called_once()


def test_gpt_candidates_caches_result():
    scorer.gpt_candidates.cache_clear()
    resp1 = types.SimpleNamespace(
        choices=[
            types.SimpleNamespace(message=types.SimpleNamespace(content="カナ1")),
            types.SimpleNamespace(message=types.SimpleNamespace(content="カナ2")),
            types.SimpleNamespace(message=types.SimpleNamespace(content="カナ3")),
        ]
    )
    resp2 = types.SimpleNamespace(
        choices=[
            types.SimpleNamespace(message=types.SimpleNamespace(content="カナ4"))
            for _ in range(5)
        ]
    )
    responses = [resp1, resp2]

    def side_effect(**kwargs):
        return responses.pop(0)

    with patch("core.scorer._call_with_backoff", side_effect=side_effect) as mock_call:
        first = scorer.gpt_candidates("太郎")
        second = scorer.gpt_candidates("太郎")

    assert first == ["カナ1", "カナ2", "カナ3", "カナ4"]
    assert second == ["カナ1", "カナ2", "カナ3", "カナ4"]
    assert mock_call.call_count == 2


def test_gpt_candidates_uses_env_var(monkeypatch):
    monkeypatch.setenv("OPENAI_MODEL", "test-model")
    import importlib

    mod = importlib.reload(scorer)
    mod.gpt_candidates.cache_clear()
    resp1 = types.SimpleNamespace(
        choices=[
            types.SimpleNamespace(message=types.SimpleNamespace(content="カナ1")),
            types.SimpleNamespace(message=types.SimpleNamespace(content="カナ2")),
            types.SimpleNamespace(message=types.SimpleNamespace(content="カナ3")),
        ]
    )
    resp2 = types.SimpleNamespace(
        choices=[
            types.SimpleNamespace(message=types.SimpleNamespace(content="カナ4"))
            for _ in range(5)
        ]
    )
    with patch(
        "core.scorer._call_with_backoff", side_effect=[resp1, resp2]
    ) as mock_call:
        mod.gpt_candidates("太郎")

    assert all(
        call.kwargs["model"] == "test-model" for call in mock_call.call_args_list
    )


def test_default_model_when_env_missing(monkeypatch):
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    import importlib

    mod = importlib.reload(scorer)
    assert mod.DEFAULT_MODEL == "gpt-4.1-mini-2025-04-14"


def test_async_gpt_candidates():
    resp1 = types.SimpleNamespace(
        choices=[
            types.SimpleNamespace(message=types.SimpleNamespace(content="カナ1")),
            types.SimpleNamespace(message=types.SimpleNamespace(content="カナ2")),
            types.SimpleNamespace(message=types.SimpleNamespace(content="カナ3")),
        ]
    )
    resp2 = types.SimpleNamespace(
        choices=[
            types.SimpleNamespace(message=types.SimpleNamespace(content="カナ4"))
            for _ in range(5)
        ]
    )
    async def run_test():
        with patch(
            "core.scorer._acall_with_backoff",
            new=AsyncMock(side_effect=[resp1, resp2]),
        ) as mock_call:
            result = await scorer.async_gpt_candidates("太郎")
        assert result == ["カナ1", "カナ2", "カナ3", "カナ4"]
        assert mock_call.call_count == 2
    
    asyncio.run(run_test())


def test_gpt_candidates_normalizes_duplicates():
    scorer.gpt_candidates.cache_clear()
    resp1 = types.SimpleNamespace(
        choices=[
            types.SimpleNamespace(
                message=types.SimpleNamespace(content="ミヤガワ アキ")
            ),
            types.SimpleNamespace(
                message=types.SimpleNamespace(content="ミヤガワアキです")
            ),
            types.SimpleNamespace(
                message=types.SimpleNamespace(content="ミヤガワ  アキ")
            ),
        ]
    )
    resp2 = types.SimpleNamespace(
        choices=[
            types.SimpleNamespace(
                message=types.SimpleNamespace(content="ミヤガワアキ")
            ),
            *[
                types.SimpleNamespace(
                    message=types.SimpleNamespace(content="ミヤガワ アキ")
                )
                for _ in range(4)
            ],
            types.SimpleNamespace(
                message=types.SimpleNamespace(content="ミヤカワ アキ")
            ),
        ]
    )
    with patch("core.scorer._call_with_backoff", side_effect=[resp1, resp2]):
        result = scorer.gpt_candidates("宮川亜紀")

    assert result == ["ミヤガワアキ", "ミヤカワアキ"]
