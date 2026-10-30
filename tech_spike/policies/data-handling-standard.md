# Data Handling Standard for AI and Analytics (SYNTHETIC)

> Fictional policy written for this exercise. It does not represent the policy of
> any real organisation. Clause IDs (`DH-x.y`) are cited by the PII Gate.

## 1. Scope and principles

### DH-1.1 Scope
This standard applies to all free text sent to AI models, large language models,
prompts, chatbots, logs, analytics platforms, data stores and third-party services,
including customer complaints, chat transcripts, emails and case notes.

### DH-1.2 Fail closed when text cannot be inspected
If text cannot be inspected safely (for example it is empty, too large, malformed,
binary, or contains control characters, or the inspection engine errors), the text
must not be released. Treat it as blocked until it can be inspected.

## 2. Financial identifiers

### DH-2.1 Payment card numbers
Payment card numbers (PAN, credit card, debit card, Visa, Mastercard, Amex) must
never be sent to AI models, written to logs or stored in plain text. Card numbers
must be masked or redacted before release, consistent with PCI DSS.

### DH-2.2 Bank account and BSB numbers
Bank account numbers and BSB numbers identify a customer's account. Redact account
and BSB numbers before AI processing, logging or sharing with third parties.

## 3. Government and business identifiers

### DH-3.1 Tax File Numbers
Tax File Numbers (TFN) are government identifiers whose collection, use and
disclosure are restricted by law. Text containing a TFN must be blocked and must
not leave the controlled boundary, even in redacted form, without Privacy Office approval.

### DH-3.2 Medicare numbers
Medicare card numbers are government identifiers linked to health information.
Text containing a Medicare number must be blocked and referred to the Privacy Office.

### DH-3.3 Australian Business Numbers
An ABN (Australian Business Number) is public for companies but can identify a sole
trader as an individual. Redact ABNs before AI processing.

## 4. Contact details and other personal information

### DH-4.1 Email addresses and phone numbers
Email addresses, mobile numbers and phone numbers are personal information and
contact details. Redact them before sending text to AI models or logs. They may be
stored only in approved customer systems.

### DH-4.2 Unclassified long numbers
Long numeric strings that cannot be classified (possible identifiers, account,
reference or membership numbers) are treated as sensitive by default and redacted.

### DH-4.3 Names and street addresses
Customer names, dates of birth and street addresses are personal information. They
are not automatically detected by the current gate; staff must not paste them into
AI tools, and automated detection is planned.

## 5. Logging and retention

### DH-5.1 Logging
Application logs must never contain raw personal information. Log the decision,
entity types, counts and a request ID only.

### DH-5.2 Retention of redacted text
Redacted text may be retained for up to 90 days for quality assurance, after which
it is deleted. Original unredacted text must not be retained by the gate.

## 6. Bulk data

### DH-6.1 Bulk personal data
Text containing many personal identifiers (eight or more) suggests a data extract,
export or bulk dump. Bulk data must be blocked and routed to the data owner for an
approved transfer process.

## 7. AI model use and escalation

### DH-7.1 Approved AI model use
Only redacted text may be sent to approved AI models. Model outputs must be scanned
again before release, because a model can reproduce or generate personal information.

### DH-7.2 Escalation and overrides
If the gate blocks text, there is no self-service override. Raise a request with the
Privacy Office, who can approve an exception and record it in the risk register.
