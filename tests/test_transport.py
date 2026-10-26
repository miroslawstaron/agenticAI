import asyncio
import json

import httpx
import pytest

from agenticai.models import Agent, Provider
from agenticai.transport import ModelError, Transport, bounded_messages


def test_trim_whole_turn_and_preserve_tool_exchange():
    messages = [
        {"role": "system", "content": "policy"},
        {"role": "user", "content": "old" * 300},
        {"role": "assistant", "content": "old reply"},
        {"role": "user", "content": "new"},
        {"role": "assistant", "content": None, "tool_calls": [{"id": "a"}]},
        {"role": "tool", "tool_call_id": "a", "content": "result"},
    ]
    result = bounded_messages(messages, 500)
    assert result == [messages[0], *messages[3:]]


def test_oversized_latest_turn_rejected():
    with pytest.raises(ModelError, match="context budget"):
        bounded_messages([{"role": "user", "content": "x" * 1000}], 100)


@pytest.mark.parametrize(
    "status,retries,expected", [(429, 2, 3), (503, 1, 2), (401, 2, 1), (400, 2, 1)]
)
async def test_retry_policy(status, retries, expected):
    count = 0

    def handler(request):
        nonlocal count
        count += 1
        return httpx.Response(status, json={"error": "private provider details"})

    transport = Transport(httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    with pytest.raises(ModelError) as error:
        await transport.complete(
            Provider(kind="http", retries=retries),
            Agent(),
            [{"role": "user", "content": "hello"}],
        )
    assert count == expected
    assert "private" not in str(error.value)
    await transport.close()


async def test_headers_parameters_and_usage(monkeypatch):
    monkeypatch.setenv("TEST_LLM_KEY", "key-that-must-stay-private")

    def handler(request):
        assert request.headers["Authorization"] == "Bearer key-that-must-stay-private"
        payload = json.loads(request.content)
        assert payload["max_tokens"] == 42
        assert payload["temperature"] == 0.2
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "answer"}}],
                "usage": {"total_tokens": 10},
            },
        )

    transport = Transport(httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    value = await transport.complete(
        Provider(kind="http", api_key_env="TEST_LLM_KEY"),
        Agent(max_tokens=42, temperature=0.2),
        [{"role": "user", "content": "hello"}],
    )
    assert value["usage"]["total_tokens"] == 10
    await transport.close()


async def test_endpoint_concurrency():
    current = peak = 0

    async def handler(request):
        nonlocal current, peak
        current += 1
        peak = max(peak, current)
        await asyncio.sleep(0.03)
        current -= 1
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

    transport = Transport(httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    p = Provider(kind="http", concurrency=2)
    await asyncio.gather(
        *[
            transport.complete(p, Agent(), [{"role": "user", "content": "hello"}])
            for _ in range(6)
        ]
    )
    assert peak == 2
    await transport.close()


@pytest.mark.parametrize(
    "data",
    [
        {},
        {"choices": []},
        {"choices": [{"message": {"content": None}}]},
        {"choices": [{"message": "invalid"}]},
    ],
)
async def test_malformed_response(data):
    transport = Transport(
        httpx.AsyncClient(
            transport=httpx.MockTransport(lambda _: httpx.Response(200, json=data))
        )
    )
    with pytest.raises(ModelError, match="malformed"):
        await transport.complete(
            Provider(kind="http"), Agent(), [{"role": "user", "content": "hello"}]
        )
    await transport.close()
