import pytest

from pii_gate.knowledge import default_index, explain, parse_clauses, tokenize

SAMPLE = """# Title
## Section
### DH-9.1 First clause
Line one
line two.
### DH-9.2 Second clause
Body.
## Next section
not part of a clause
"""


def test_parse_clauses():
    clauses = parse_clauses(SAMPLE, "x.md")
    assert [(c.id, c.title, c.body) for c in clauses] == [
        ("DH-9.1", "First clause", "Line one line two."),
        ("DH-9.2", "Second clause", "Body."),
    ]


def test_tokenize_drops_stopwords_and_folds_plurals():
    assert tokenize("Can I log the Card Numbers?") == ["log", "card", "number"]


def test_tokenize_drops_possessives():
    assert tokenize("a customer's card, the customer’s phone") == [
        "customer", "card", "customer", "phone"
    ]


def test_possessive_does_not_skew_ranking():
    # Regression: a stray "s" token from "customer's" used to rank DH-2.2 above DH-2.1.
    result = explain("Can I send a customer's card number to an LLM?")
    assert result.hits[0].clause.id == "DH-2.1"


def test_corpus_loads():
    assert len(default_index().clauses) >= 10


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        ("Can I send a customer's credit card number to an LLM?", "DH-2.1"),
        ("What do I do with a tax file number in a complaint?", "DH-3.1"),
        ("Is it ok to put email addresses in application logs?", "DH-5.1"),
        ("The gate blocked my text, how do I get an override?", "DH-7.2"),
    ],
)
def test_explain_cites_relevant_clause_in_top_3(question, expected):
    result = explain(question)
    assert result.answered
    assert expected in [h.clause.id for h in result.hits]


@pytest.mark.parametrize(
    "question",
    ["What's the weather in Sydney tomorrow?", "Give me a chocolate cake recipe"],
)
def test_explain_abstains_on_unrelated_questions(question):
    result = explain(question)
    assert not result.answered
    assert result.hits == []
    assert "Privacy Office" in result.message
