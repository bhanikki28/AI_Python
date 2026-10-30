"""MCP server: exposes the gate as tools to AI clients (Claude Code, Claude Desktop, Cursor...).

Runs over stdio, so stdout is reserved for the protocol; logs go to stderr.
Tools are read-only and closed-world: they never call out, store or modify anything.

  pii-gate-mcp            # stdio server
"""

from collections import Counter
from typing import Any

from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations

from pii_gate import __version__, gate, knowledge
from pii_gate.config import load_settings
from pii_gate.logging_setup import configure_logging, get_logger

INSTRUCTIONS = """\
PII Gate is a mandatory privacy control. Call `scan_text` on any user-supplied or
retrieved text BEFORE sending it to a model, another tool, a log or storage.
- Use only `released_text` from the result, never the original text.
- If `decision` is BLOCK, do not use the text at all: tell the user it was blocked
  and cite the policy clause from `reasons`.
- Use `explain_policy` to answer data-handling questions; if it does not answer,
  say so and refer the user to the Privacy Office rather than guessing.
"""

READ_ONLY = ToolAnnotations(read_only_hint=True, idempotent_hint=True, open_world_hint=False)

settings = load_settings()
log = get_logger("mcp")
server = MCPServer(name="pii-gate", version=__version__, instructions=INSTRUCTIONS)


def _scan(text: str, tool: str) -> gate.GateResult:
    result = gate.scan(text, max_chars=settings.max_chars)
    log.info("tool_call", extra={"fields": {
        "tool": tool,
        "decision": result.decision.name,
        "entity_counts": dict(Counter(f.entity_type for f in result.findings)),
    }})
    return result


@server.tool(title="Scan text for PII", annotations=READ_ONLY, structured_output=True)
def scan_text(text: str) -> dict[str, Any]:
    """Inspect text for sensitive data (cards, TFN, Medicare, ABN, BSB/account numbers,
    emails, AU phone numbers). Returns decision ALLOW/REDACT/BLOCK, the text that may be
    released (null when blocked), findings (types and positions, never values) and the
    policy clauses behind the decision."""
    return _scan(text, "scan_text").to_dict()


@server.tool(title="Redact text", annotations=READ_ONLY, structured_output=True)
def redact_text(text: str) -> dict[str, Any]:
    """Return only the decision and the safe-to-use text. released_text is null when the
    decision is BLOCK; in that case the text must not be used."""
    result = _scan(text, "redact_text")
    return {"decision": result.decision.name, "released_text": result.released_text}


@server.tool(title="Explain data-handling policy", annotations=READ_ONLY, structured_output=True)
def explain_policy(question: str) -> dict[str, Any]:
    """Answer a data-handling policy question with cited clauses from the policy corpus.
    Abstains (answered=false) when no clause is relevant enough."""
    result = knowledge.explain(question)
    log.info("tool_call", extra={"fields": {
        "tool": "explain_policy",
        "answered": result.answered,
        "clauses": [h.clause.id for h in result.hits],
    }})
    return result.to_dict()


def main() -> None:
    configure_logging(settings.log_level)
    server.run("stdio")


if __name__ == "__main__":
    main()
