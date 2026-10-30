"""Generate the labelled synthetic eval set (deterministic: fixed seed).

All identifiers are random values constructed to pass checksums; emails use
reserved example domains. Expected decisions come from an independent oracle
restating the policy (TFN/Medicare or >= 8 identifiers -> BLOCK, any -> REDACT),
not from the engine under test.

Usage: python -m evals.generate_dataset
"""

import json
import random
from pathlib import Path

from pii_gate import checksums

SEED = 42
OUT = Path(__file__).resolve().parents[1] / "sample-data"

FIRST = ["alex", "sam", "jordan", "priya", "wei", "olivia", "noah", "mia", "liam", "zara"]
LAST = ["citizen", "nguyen", "smith", "patel", "chen", "brown", "kaur", "wilson"]
DOMAINS = ["example.com", "example.org", "example.net"]

BLOCKING = {"TFN", "MEDICARE"}
BULK_THRESHOLD = 8


def _rand_digits(rng: random.Random, n: int) -> list[int]:
    return [rng.randint(0, 9) for _ in range(n)]


def card(rng: random.Random) -> str:
    prefix, length, groups = rng.choice(
        [([4], 16, (4, 4, 4, 4)), ([5, rng.randint(1, 5)], 16, (4, 4, 4, 4)),
         ([3, 7], 15, (4, 6, 5))]
    )
    while True:
        digits = prefix + _rand_digits(rng, length - len(prefix))
        if checksums.luhn_valid("".join(map(str, digits))):
            break
    raw = "".join(map(str, digits))
    sep = rng.choice([" ", "-", ""])
    parts, i = [], 0
    for g in groups:
        parts.append(raw[i : i + g])
        i += g
    return sep.join(parts)


def tfn(rng: random.Random) -> str:
    while True:
        raw = "".join(map(str, _rand_digits(rng, 9)))
        if checksums.tfn_valid(raw):
            return f"{raw[:3]} {raw[3:6]} {raw[6:]}" if rng.random() < 0.7 else raw


def abn(rng: random.Random) -> str:
    while True:
        raw = str(rng.randint(1, 9)) + "".join(map(str, _rand_digits(rng, 10)))
        if checksums.abn_valid(raw):
            return f"{raw[:2]} {raw[2:5]} {raw[5:8]} {raw[8:]}"


def medicare(rng: random.Random) -> str:
    while True:
        raw = str(rng.randint(2, 6)) + "".join(map(str, _rand_digits(rng, 7)))
        check = sum(w * int(d) for w, d in zip(checksums.MEDICARE_WEIGHTS, raw, strict=True)) % 10
        full = f"{raw}{check}{rng.randint(1, 9)}"
        if checksums.medicare_valid(full):
            return f"{full[:4]} {full[4:9]} {full[9]}"


def phone(rng: random.Random) -> str:
    d = "".join(map(str, _rand_digits(rng, 8)))
    return rng.choice(
        [
            f"04{d[:2]} {d[2:5]} {d[5:]}",
            f"+61 4{d[:2]} {d[2:5]} {d[5:]}",
            f"04{d[:2]}{d[2:5]}{d[5:]}",
            f"(0{rng.choice('2378')}) {d[:4]} {d[4:]}",
        ]
    )


def email(rng: random.Random) -> str:
    return f"{rng.choice(FIRST)}.{rng.choice(LAST)}{rng.randint(1, 99)}@{rng.choice(DOMAINS)}"


def bsb(rng: random.Random) -> str:
    d = "".join(map(str, _rand_digits(rng, 6)))
    return f"{d[:3]}-{d[3:]}"


def account(rng: random.Random) -> str:
    # 6-8 digits: avoids lengths that collide with TFN/Medicare/ABN/card checksums.
    return "".join(map(str, _rand_digits(rng, rng.randint(6, 8))))


GENERATORS = {
    "CARD_NUMBER": card, "TFN": tfn, "ABN": abn, "MEDICARE": medicare,
    "PHONE_AU": phone, "EMAIL": email, "BSB": bsb, "ACCOUNT_NUMBER": account,
}

TEMPLATES = [
    "Hi, I was charged twice on my card {CARD_NUMBER}. Please call me on {PHONE_AU}.",
    "Please refund the $89.95 to BSB {BSB} account number {ACCOUNT_NUMBER}.",
    "My TFN is {TFN}, why was tax withheld from my interest?",
    "Medicare number {MEDICARE} was rejected at the pharmacy on 14/03/2026.",
    "Our business ABN is {ABN} and the merchant invoice is wrong.",
    "Email me at {EMAIL} about case 4471, I'm free after 5pm.",
    "Contact {EMAIL} or {PHONE_AU} after 5pm on 12/06/2026.",
    "Scam alert - the full number was {CARD_NUMBER} and I lost $1,249.00.",
    "Transfer from acc {ACCOUNT_NUMBER} failed twice this week.",
    "Customer rang from {PHONE_AU} disputing $42.10 on card {CARD_NUMBER}.",
    "Update my details: email {EMAIL}, mobile {PHONE_AU}, TFN {TFN}.",
    "Direct debit from BSB {BSB} acct {ACCOUNT_NUMBER} bounced, reach me at {EMAIL}.",
    "Sole trader here, ABN {ABN}, phone {PHONE_AU}, the fee is unfair.",
    "Claim declined, Medicare {MEDICARE}, contact {EMAIL}.",
]

NEGATIVES = [
    "Your payment of $1,234.56 was received on 12/05/2026.",
    "Reference INV-2026-000123 has been closed.",
    "Call us on 1300 650 000 between 9am and 5pm.",
    "I've been waiting 45 minutes on hold, this is the 3rd time.",
    "Branch 042 closed at 4:30pm without notice.",
    "The interest rate went from 5.99% to 6.24% in 2025.",
    "Case 88231 was escalated on 01-02-2026.",
    "On 2026-03-14 at 10:45 I tried to log in and it failed.",
    "My postcode is 2150 and the parcel went to unit 4/12.",
    "Order #A7731 arrived damaged.",
    "Version 2.3.1 of the app crashes on start.",
    "I paid 3 instalments of $250 each, total $750.",
    "The 1800 222 333 hotline is always busy.",
    "Fees of $15, $15 and $30 were charged in March.",
]

# (text, entities) with obfuscation; entity values are the normalised form.
ADVERSARIAL = [
    ("card 4111​1111​1111​1111 please refund",
     [("CARD_NUMBER", "4111111111111111")]),
    ("my tfn is １２３ ４５６ ７８２",
     [("TFN", "123 456 782")]),
    ("CARD 5555-5555-5555-4444 WAS STOLEN", [("CARD_NUMBER", "5555-5555-5555-4444")]),
    ("ring +61412345678 urgently", [("PHONE_AU", "+61412345678")]),
    ("EMAIL: JANE.CITIZEN@EXAMPLE.COM", [("EMAIL", "JANE.CITIZEN@EXAMPLE.COM")]),
    ("amex 378282246310005, exp 09/28", [("CARD_NUMBER", "378282246310005")]),
]

INVALID = ["", "hello\x00world"]  # expected BLOCK (input rejected, fail closed)

# Known out-of-scope gap (DH-4.3): reported, not gated.
PROBES = [
    ("My name is Priya Patel and I live at 12 Example St, Sydney NSW 2000.",
     [("NAME", "Priya Patel"), ("ADDRESS", "12 Example St, Sydney NSW 2000")]),
    ("Please ask for Wei Chen, DOB 03/07/1985.",
     [("NAME", "Wei Chen"), ("DATE_OF_BIRTH", "03/07/1985")]),
]


def oracle_decision(entity_types: list[str]) -> str:
    if not entity_types:
        return "ALLOW"
    if BLOCKING & set(entity_types) or len(entity_types) >= BULK_THRESHOLD:
        return "BLOCK"
    return "REDACT"


def _case(case_id, category, text, entities, decision=None, probe=False):
    return {
        "id": case_id,
        "category": category,
        "text": text,
        "entities": [{"type": t, "value": v} for t, v in entities],
        "expected_decision": decision or oracle_decision([t for t, _ in entities]),
        "probe": probe,
    }


def fill(template: str, rng: random.Random) -> tuple[str, list[tuple[str, str]]]:
    entities = []
    text = template
    while "{" in text:
        start = text.index("{")
        end = text.index("}", start)
        etype = text[start + 1 : end]
        value = GENERATORS[etype](rng)
        entities.append((etype, value))
        text = text[:start] + value + text[end + 1 :]
    return text, entities


def build(rng: random.Random) -> list[dict]:
    cases = []
    for i in range(42):
        text, entities = fill(TEMPLATES[i % len(TEMPLATES)], rng)
        cases.append(_case(f"pos-{i:03d}", "positive", text, entities))
    for i in range(3):
        entities = [(t, GENERATORS[t](rng)) for t in rng.choices(["EMAIL", "PHONE_AU"], k=9)]
        text = "Customer export: " + "; ".join(v for _, v in entities)
        cases.append(_case(f"bulk-{i:03d}", "bulk", text, entities))
    for i, text in enumerate(NEGATIVES):
        cases.append(_case(f"neg-{i:03d}", "negative", text, []))
    for i, (text, entities) in enumerate(ADVERSARIAL):
        cases.append(_case(f"adv-{i:03d}", "adversarial", text, entities))
    for i, text in enumerate(INVALID):
        cases.append(_case(f"inv-{i:03d}", "invalid", text, [], decision="BLOCK"))
    for i, (text, entities) in enumerate(PROBES):
        cases.append(_case(f"probe-{i:03d}", "probe", text, entities, decision="BLOCK", probe=True))
    return cases


def main() -> None:
    OUT.mkdir(exist_ok=True)
    cases = build(random.Random(SEED))
    path = OUT / "eval_cases.jsonl"
    path.write_text("".join(json.dumps(c, ensure_ascii=False) + "\n" for c in cases), "utf-8")
    print(f"wrote {len(cases)} cases to {path}")


if __name__ == "__main__":
    main()
