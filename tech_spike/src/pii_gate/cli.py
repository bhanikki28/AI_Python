"""Command line interface.

  pii-gate scan "text"          # or --file path, or stdin
  pii-gate explain "question"
  pii-gate assist "text"        # optional local LLM summary (Ollama); degrades without it
  pii-gate serve

scan/assist exit codes: 0 = released text is safe to use, 2 = input BLOCKed.
"""

import argparse
import json
import sys

from pii_gate import assistant, gate, knowledge
from pii_gate.config import ConfigError, load_settings
from pii_gate.logging_setup import configure_logging
from pii_gate.policy import Decision

EXIT_BLOCK = 2


def _read_input(args: argparse.Namespace) -> str:
    if args.file:
        with open(args.file, encoding="utf-8") as fh:
            return fh.read()
    if args.text is not None:
        return args.text
    return sys.stdin.read()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pii-gate", description=__doc__.splitlines()[1])
    sub = parser.add_subparsers(dest="command", required=True)

    for name, help_text in [
        ("scan", "scan text and print the decision as JSON"),
        ("assist", "gate text, then summarise it with the optional local LLM"),
    ]:
        p = sub.add_parser(name, help=help_text)
        p.add_argument("text", nargs="?")
        p.add_argument("--file")

    explain_p = sub.add_parser("explain", help="ask a data-handling policy question")
    explain_p.add_argument("question")

    sub.add_parser("serve", help="run the API and web UI")

    args = parser.parse_args(argv)
    try:
        settings = load_settings()
    except ConfigError as exc:
        print(f"config error: {exc}", file=sys.stderr)
        return 1
    configure_logging(settings.log_level)  # JSON logs on stderr; stdout stays clean JSON

    if args.command == "scan":
        result = gate.scan(_read_input(args), max_chars=settings.max_chars)
        print(json.dumps(result.to_dict(), indent=2))
        return EXIT_BLOCK if result.decision == Decision.BLOCK else 0

    if args.command == "assist":
        llm = assistant.OllamaClient(
            settings.ollama_url, settings.ollama_model, settings.llm_timeout_s,
            max_attempts=settings.llm_max_attempts,
        )
        result = assistant.assist(_read_input(args), llm, max_chars=settings.max_chars)
        print(json.dumps(result.to_dict(), indent=2))
        return EXIT_BLOCK if result.status == assistant.Status.INPUT_BLOCKED else 0

    if args.command == "explain":
        print(json.dumps(knowledge.explain(args.question).to_dict(), indent=2))
        return 0

    import uvicorn

    uvicorn.run("pii_gate.api:app", host=settings.host, port=settings.port, log_level="warning")
    return 0


if __name__ == "__main__":
    sys.exit(main())
