"""Command line interface.

  pii-gate scan "text"          # or --file path, or stdin
  pii-gate explain "question"
  pii-gate serve

scan exit codes: 0 = ALLOW/REDACT (released_text is safe to use), 2 = BLOCK.
"""

import argparse
import json
import sys

from pii_gate import gate, knowledge
from pii_gate.config import ConfigError, load_settings
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

    scan_p = sub.add_parser("scan", help="scan text and print the decision as JSON")
    scan_p.add_argument("text", nargs="?")
    scan_p.add_argument("--file")

    explain_p = sub.add_parser("explain", help="ask a data-handling policy question")
    explain_p.add_argument("question")

    sub.add_parser("serve", help="run the API and web UI")

    args = parser.parse_args(argv)
    try:
        settings = load_settings()
    except ConfigError as exc:
        print(f"config error: {exc}", file=sys.stderr)
        return 1

    if args.command == "scan":
        result = gate.scan(_read_input(args), max_chars=settings.max_chars)
        print(json.dumps(result.to_dict(), indent=2))
        return EXIT_BLOCK if result.decision == Decision.BLOCK else 0

    if args.command == "explain":
        print(json.dumps(knowledge.explain(args.question).to_dict(), indent=2))
        return 0

    import uvicorn

    uvicorn.run("pii_gate.api:app", host=settings.host, port=settings.port, log_level="warning")
    return 0


if __name__ == "__main__":
    sys.exit(main())
