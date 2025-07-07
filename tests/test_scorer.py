import os
import sys
from unittest.mock import patch
import openai

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from core import scorer


def test_call_with_backoff_retries_api_connection_error():
    success = object()
    responses = [openai.APIConnectionError(message="fail", request=None), success]

    def side_effect(*args, **kwargs):
        result = responses.pop(0)
        if isinstance(result, Exception):
            raise result
        return result

    with patch("core.scorer.client.chat.completions.create", side_effect=side_effect) as mock_create, \
         patch("time.sleep") as sleep_mock:
        result = scorer._call_with_backoff(model="dummy", messages=[])

    assert result is success
    assert mock_create.call_count == 2
    sleep_mock.assert_called_once()
