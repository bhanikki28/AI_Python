"""RAG over the data-handling policy corpus.

Clauses are parsed from Markdown and indexed with BM25 (pure Python, no model
download, deterministic). Retrieval explains and cites policy; it never drives the
ALLOW/REDACT/BLOCK decision, which stays in the auditable rule table (policy.py).
"""

import math
import os
import re
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

DEFAULT_POLICY_DIR = Path(__file__).resolve().parents[2] / "policies"
ABSTAIN_SCORE = 3.0  # below this the best match is too weak to cite

CLAUSE_HEADING = re.compile(r"^### ([A-Z]{2}-\d+\.\d+)\s+(.+)$")
TOKEN = re.compile(r"[a-z0-9]+")
STOPWORDS = frozenset(
    "a an and are as at be by can do does for from how i if in is it its may must my "
    "not of on or our should so that the their them then they this to was we what "
    "when where which who why will with you your".split()
)
K1, B = 1.5, 0.75


@dataclass(frozen=True)
class Clause:
    id: str
    title: str
    body: str
    source: str

    def to_dict(self) -> dict:
        return {"id": self.id, "title": self.title, "text": self.body, "source": self.source}


@dataclass(frozen=True)
class Hit:
    clause: Clause
    score: float


def tokenize(text: str) -> list[str]:
    tokens = []
    for t in TOKEN.findall(text.lower()):
        if t in STOPWORDS:
            continue
        if len(t) > 3 and t.endswith("s") and not t.endswith("ss"):
            t = t[:-1]  # crude plural folding: numbers -> number
        tokens.append(t)
    return tokens


def parse_clauses(markdown: str, source: str) -> list[Clause]:
    clauses: list[Clause] = []
    current: tuple[str, str] | None = None
    body: list[str] = []

    def flush() -> None:
        if current:
            clauses.append(Clause(current[0], current[1], " ".join(body).strip(), source))

    for line in markdown.splitlines():
        if m := CLAUSE_HEADING.match(line):
            flush()
            current, body = (m.group(1), m.group(2).strip()), []
        elif line.startswith("#"):
            flush()
            current, body = None, []
        elif current and line.strip():
            body.append(line.strip())
    flush()
    return clauses


class PolicyIndex:
    def __init__(self, clauses: Iterable[Clause]):
        self.clauses = list(clauses)
        if not self.clauses:
            raise ValueError("Policy corpus is empty.")
        # Title counted twice: headings are the most precise description of a clause.
        docs = [tokenize(f"{c.title} {c.title} {c.body}") for c in self.clauses]
        self._tf = [Counter(d) for d in docs]
        self._len = [len(d) for d in docs]
        self._avg_len = sum(self._len) / len(docs)
        df = Counter(t for d in docs for t in set(d))
        n = len(docs)
        self._idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}
        self._by_id = {c.id: c for c in self.clauses}

    def get(self, clause_id: str) -> Clause | None:
        return self._by_id.get(clause_id)

    def search(self, query: str, k: int = 3) -> list[Hit]:
        terms = set(tokenize(query))
        hits = []
        for clause, tf, length in zip(self.clauses, self._tf, self._len, strict=True):
            norm = K1 * (1 - B + B * length / self._avg_len)
            score = sum(
                self._idf[t] * tf[t] * (K1 + 1) / (tf[t] + norm) for t in terms if t in tf
            )
            if score > 0:
                hits.append(Hit(clause, round(score, 3)))
        return sorted(hits, key=lambda h: h.score, reverse=True)[:k]


def load_index(policy_dir: Path) -> PolicyIndex:
    files = sorted(policy_dir.glob("*.md"))
    if not files:
        raise FileNotFoundError(f"No policy documents found in {policy_dir}")
    clauses = [c for f in files for c in parse_clauses(f.read_text("utf-8"), f.name)]
    return PolicyIndex(clauses)


@lru_cache(maxsize=1)
def default_index() -> PolicyIndex:
    return load_index(Path(os.environ.get("PII_GATE_POLICY_DIR", DEFAULT_POLICY_DIR)))


@dataclass(frozen=True)
class Explanation:
    answered: bool
    hits: list[Hit]
    message: str

    def to_dict(self) -> dict:
        return {
            "answered": self.answered,
            "message": self.message,
            "clauses": [{**h.clause.to_dict(), "score": h.score} for h in self.hits],
        }


def explain(question: str, index: PolicyIndex | None = None, k: int = 3) -> Explanation:
    """Answer a policy question with cited clauses, or abstain when nothing is relevant."""
    index = index or default_index()
    hits = index.search(question, k)
    if not hits or hits[0].score < ABSTAIN_SCORE:
        return Explanation(
            False,
            [],
            "No sufficiently relevant policy clause found. Please contact the Privacy Office.",
        )
    top = hits[0].clause
    return Explanation(True, hits, f"Most relevant policy: {top.id} {top.title}")
