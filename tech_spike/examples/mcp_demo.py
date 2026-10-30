"""Demo MCP client: launches the PII Gate MCP server over stdio and calls its tools,
the same way an AI agent would. No LLM or API key needed.

Usage: python examples/mcp_demo.py
"""

import asyncio
import json
import sys

from mcp import Client, StdioServerParameters

MESSAGES = [
    "Hi, my card 4111 1111 1111 1111 was charged twice, call me on 0412 345 678.",
    "Please update my record, my TFN is 123 456 782.",
    "The branch was closed on Tuesday.",
]


def show(title: str, result) -> None:
    print(f"\n=== {title}")
    print(json.dumps(result.structured_content, indent=2))


async def main() -> None:
    params = StdioServerParameters(command=sys.executable, args=["-m", "pii_gate.mcp_server"])
    async with Client(params) as client:
        tools = await client.list_tools()
        print("Tools offered by the server:", [t.name for t in tools.tools])

        for text in MESSAGES:
            result = await client.call_tool("redact_text", {"text": text})
            show(f"redact_text({text[:40]}...)", result)

        question = "Can I send a customer's card number to an LLM?"
        result = await client.call_tool("explain_policy", {"question": question})
        top = result.structured_content["clauses"][0]
        print(f"\n=== explain_policy({question!r})\n-> {top['id']} {top['title']}: {top['text']}")


if __name__ == "__main__":
    asyncio.run(main())
