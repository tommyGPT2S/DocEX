# PDF Intake - Commercial Real Estate Invoice Reconciliation

Read a commercial-real-estate (CRE) invoice PDF of arbitrary layout, extract its
fields, and reconcile it against what we *expected* to be billed. The use case:
a landlord or property manager sends an invoice as a PDF, formatted however their
system happens to format it, and we need to answer one question reliably - **does
this bill match the lease?** Base rent, CAM, tax and insurance recoveries,
square footage, pro-rata share, totals: each is checked against our recorded
actuals so an overcharge is caught before it is paid.

The design goal beyond correctness is **cost and latency**: do the cheap,
deterministic work first and only reach for a language model when the cheap work
genuinely cannot answer.

## How it works

```text
PDF ──► text ──► extract (cascade) ──► match ground truth ──► reconcile ──► escalate? ──► learn
        pdfminer   heuristic, then       by invoice / PO       per-field      LLM on only    record
                   LLM only for gaps                           w/ tolerances  disputed fields confirmed labels
```

### 1. Text extraction (`pdf.py`)

`pdfminer.six` turns the PDF into text. This is the only module that touches the
PDF binary, so everything above it is plain-text and trivially testable. The
dependency is optional (`pip install docex[pdf]`).

### 2. The extraction cascade (`extractors/`)

Fields are extracted in cost order, escalating only what the cheaper tier could
not resolve:

- **Tier 1 - Heuristic (`heuristic.py`)**: free and deterministic. It scans for
  each field's label aliases (from the canonical registry) at the start of a
  line and reads the value beside or below it, and it parses the charges table
  into typed line items. It resolves the great majority of fields on well-formed
  invoices.
- **Tier 2 - LLM (`llm.py`)**: the last resort. The model is **caller-provided**
  (`llm_fn`, a callable returning JSON), so the core takes no hard dependency on
  any provider - exactly like DocEX's `embedding_fn` pattern. It is invoked only
  for *gaps* (required fields the heuristic missed) and, after reconciliation,
  for *disputed* fields. A clean invoice never reaches it.

The cascade (`cascade.py`) owns this ordering and the merge logic.

#### Why there is no embedding-similarity tier

An obvious middle tier would map an unseen label phrasing to a field by
embedding similarity, to avoid an LLM call. We deliberately left it out:

- The **learning loop (below) already removes that cost.** The first time a novel
  phrasing appears the LLM resolves it; once confirmed, the heuristic learns it
  permanently and every later occurrence is free at Tier 1. An embedding tier
  would only save the single LLM call on the *first* sighting.
- An embedding match is a similarity score, not an auditable label-and-value on
  the page. It can confidently bind the wrong line to a field, and a wrong value
  that coincidentally matched ground truth would be learned as a real alias -
  poisoning the heuristic.
- It adds a hard dependency on a caller-supplied embedding model whose quality we
  cannot guarantee.

A one-time cost saving is not worth a false-positive risk to a loop we already
built. If the heuristic cannot read a field, we go straight to the authoritative
tier.

### 3. Ground truth (`ground_truth.py`)

A `GroundTruthInvoice` is our recorded actuals for a lease and billing period -
the schema mirrors the canonical field registry one-to-one. Two stores ship:

- `InMemoryGroundTruthStore` for tests and small in-process use.
- `DocEXGroundTruthStore`, which persists each record as a JSON document in a
  DocEX basket and mirrors the lookup keys (invoice number, PO, lease, account)
  into document metadata, so retrieval is an indexed metadata query.

### 4. Reconciliation (`reconcile.py`)

`GroundTruthMatcher` finds the record to compare against by stable identifier
(invoice number, then PO) - never by fuzzy totals, because reconciling against
the wrong lease is worse than reporting no match. `Reconciler` then compares each
field with type-aware tolerances (a cent on money, configurable days on dates,
case/whitespace-insensitive strings) and rolls line items up by charge type so a
vendor's "CAM" line is compared against the lease's expected CAM regardless of
wording. The verdict is `matched`, `discrepancy`, `incomplete`, or `unresolved`.

#### Fuzzy ground-truth retrieval (`embedding_match.py`)

Identifier matching cannot help when the incoming invoice has no clean
identifier - a typo in the invoice number, a vendor using their own numbering,
or a number the extractor could not read. `EmbeddingGroundTruthMatcher` embeds a
short fingerprint of each ground-truth record (tenant, property, suite, lease,
totals, charge descriptions) and the same fingerprint of the invoice, and ranks
records by cosine similarity (`embedding_fn` is caller-provided, the same one
you would use for DocEX vector indexing; record embeddings are cached by id).

Pass `embedding_fn` to the pipeline and it becomes an automatic fallback: an
invoice that matches no record by identifier is reconciled against the closest
record by similarity instead of being reported as unresolved. Crucially this is
*retrieval, not a verdict* - the invoice is still reconciled against the
retrieved record, so a wrong guess surfaces as a discrepancy (for example the
typo'd invoice number is flagged) rather than being silently trusted. This is
why embeddings are safe for finding the record but were deliberately kept out of
extracting field values. You can also call the matcher directly for a ranked
`candidates(...)` list to suggest matches in a UI.

### 5. The self-improving learning loop (`learning.py`)

Every extracted field carries the **label phrase** that identified it. After
reconciliation, the label of every field that *matched* ground truth is recorded
with a running count. This does two things:

- **Trend**: how customers actually phrase each field (analytics).
- **Learned alias**: a phrasing the registry did not know - usually surfaced by
  the LLM on a messy invoice - is promoted into the heuristic's alias set, so the
  next invoice that uses it is solved for free at Tier 1.

Only ground-truth-confirmed labels are ever learned, so the loop cannot teach the
heuristic a wrong mapping. Over time the cheap tier absorbs the long tail of
vendor phrasings and the LLM is needed less and less - the explicit goal being a
system that, for a stable set of vendors, may not need the LLM at all.

### 6. DocEX integration (`processor.py`)

`InvoiceIntakeProcessor` wraps the pipeline as a DocEX `BaseProcessor`, so an
invoice already stored in a basket can be reconciled in place with the verdict
written back to its metadata. It is imported separately from the core so the
pipeline stays free of any database dependency.

## Usage

```python
import asyncio
from docex.intake import InvoiceIntakePipeline, InMemoryGroundTruthStore

store = InMemoryGroundTruthStore()
store.add(my_ground_truth_invoice)  # your recorded actuals

# Heuristic-only (fully offline):
pipeline = InvoiceIntakePipeline()

# With an LLM fallback + persistent learning (recommended for production):
from docex.intake import JsonFileLearningStore
from examples.integrations.anthropic.invoice_intake_llm import make_claude_llm_fn

pipeline = InvoiceIntakePipeline(
    llm_fn=make_claude_llm_fn(),
    learning_store=JsonFileLearningStore("learned_labels.json"),
)

outcome = asyncio.run(pipeline.process_pdf("invoice.pdf", store))
print(outcome.status)                       # matched | discrepancy | incomplete | unresolved
print(outcome.reconciliation.mismatches)    # the lines that disagree with the lease
```

## How it was tested

The suite lives in `tests/intake/` and is built so the bulk runs fast and
offline, with the binary and provider boundaries exercised separately.

- **Unit tests** pin down each layer: amount/date/percent normalization across
  real-world formats (US and European grouping, parenthesised negatives, spelled
  dates), the charge taxonomy, heuristic extraction traps (a scalar `tax` field
  must not read a "Real Estate Tax Recovery" charge line; labelled metric rows
  must not become phantom charges; a specific label beats a generic one), the
  reconciler's tolerances and statuses, and the matcher.
- **The learning loop** is tested end to end: a novel label forces one LLM call,
  is confirmed against ground truth and learned, and the *same* invoice then
  reconciles with zero further LLM calls.
- **Randomized scenarios** (`test_random.py`) generate dozens of seeded invoices
  with varied layouts, label phrasings, date formats, and values. Every clean
  invoice must reconcile as matched; every overcharged one must be caught. A
  failure reports the seed that produced it.
- **The LLM tier** is covered two ways: deterministic stub tests that run
  everywhere (JSON parsing, value normalization, label capture, line items), and
  a **live** test against Claude that is skipped unless `ANTHROPIC_API_KEY` is
  set.
- **Real PDFs**: two committed, human-viewable invoices in
  `example_docs/cre_invoices/` - a positive one that matches, and a negative one
  that overstates CAM by $750 - are run through the full pipeline (pdfminer
  included). A synthetic reportlab round-trip covers the write/read boundary too.

Run the offline suite:

```sh
python -m pytest tests/intake/
```

Run the live-LLM tests (after setting a key):

```sh
ANTHROPIC_API_KEY=sk-... python -m pytest tests/intake/ -k live -s
```

## Key assumptions

These are the boundaries within which the heuristic is reliable; outside them,
extraction falls through to the LLM, and reconciliation simply reports what it
could not confirm.

1. **Text-based PDFs.** Extraction relies on a text layer. A scanned image with
   no embedded text yields no text; such invoices need an OCR step ahead of the
   intake (out of scope here).
2. **Labels lead their line.** The heuristic treats a label as valid only when it
   starts a "label: value" row. Values embedded mid-sentence, or two fields
   sharing one line, are left to the LLM. This is what makes a generic label like
   "property" safe - it cannot match the word inside "Summit Property Group".
3. **Monetary amounts are formatted as money.** A charge amount carries a
   currency symbol, decimals, or thousands grouping. A bare integer (a suite
   number, a square-foot count) is never mistaken for a charge.
4. **US conventions by default.** Ambiguous amounts and dates default to US
   formatting (`,` groups thousands, `.` is the decimal point, dates are
   month-first) unless the value itself disambiguates (both separators present,
   or a date component greater than 12).
5. **Ground truth is matched by identifier.** An invoice is reconciled against
   the record whose invoice number (or PO) it carries. Without one of those, the
   result is `unresolved` rather than a guess.
6. **The LLM is authoritative but optional.** When present it overrides the
   heuristic on disputed fields and teaches new labels; when absent the pipeline
   runs fully offline and reports unresolved fields plainly.
```
