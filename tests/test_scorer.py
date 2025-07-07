from unittest.mock import patch
import types
import openai

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
        choices=[types.SimpleNamespace(message=types.SimpleNamespace(content="カナ"))]
    )
    resp2 = types.SimpleNamespace(
        choices=[types.SimpleNamespace(message=types.SimpleNamespace(content="カナ"))]
    )
    responses = [resp1, resp2]

    def side_effect(**kwargs):
        return responses.pop(0)

    with patch("core.scorer._call_with_backoff", side_effect=side_effect) as mock_call:
        first = scorer.gpt_candidates("太郎")
        second = scorer.gpt_candidates("太郎")

    assert first == ["カナ"]
    assert second == ["カナ"]
    assert mock_call.call_count == 2
