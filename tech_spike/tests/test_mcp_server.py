import sys

import pytest
from mcp import Client, StdioServerParameters

from pii_gate.mcp_server import server

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


async def test_lists_read_only_tools():
    async with Client(server) as client:
        tools = {t.name: t for t in (await client.list_tools()).tools}
    assert set(tools) == {"scan_text", "redact_text", "explain_policy"}
    for tool in tools.values():
        assert tool.annotations.read_only_hint
        assert tool.annotations.open_world_hint is False


async def test_server_instructions_tell_agents_to_honour_block():
    async with Client(server) as client:
        instructions = client.instructions
    assert "BLOCK" in instructions and "released_text" in instructions


async def test_scan_text_tool():
    async with Client(server) as client:
        result = await client.call_tool("scan_text", {"text": "card 4111 1111 1111 1111"})
    assert not result.is_error
    body = result.structured_content
    assert body["decision"] == "REDACT"
    assert body["released_text"] == "card [CARD_NUMBER]"
    assert body["reasons"][0]["policy"]["id"] == "DH-2.1"


async def test_redact_text_tool_withholds_blocked_text():
    async with Client(server) as client:
        result = await client.call_tool("redact_text", {"text": "TFN 123 456 782"})
    assert result.structured_content == {"decision": "BLOCK", "released_text": None}


async def test_explain_policy_tool_abstains_off_topic():
    async with Client(server) as client:
        result = await client.call_tool("explain_policy", {"question": "best pizza in town"})
    assert result.structured_content["answered"] is False


async def test_tool_results_never_contain_raw_pii():
    async with Client(server) as client:
        result = await client.call_tool("scan_text", {"text": "card 4111 1111 1111 1111"})
    assert "4111" not in str(result.content) + str(result.structured_content)


async def test_stdio_transport_end_to_end():
    params = StdioServerParameters(command=sys.executable, args=["-m", "pii_gate.mcp_server"])
    async with Client(params) as client:
        result = await client.call_tool("redact_text", {"text": "email a.b@example.com"})
    assert result.structured_content["released_text"] == "email [EMAIL]"
