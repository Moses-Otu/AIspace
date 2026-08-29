# Opportunity Radar

A twelve-stage research pipeline that reads what startups are building somewhere else, strips out
what is specific to those companies, and asks a much harder question: **would this actually work
here, given what this country has already committed to and already built?**

Built in n8n over Postgres with pgvector. Two isolated instances of the same pipeline ran in
parallel — a production instance and a federal pilot writing to its own `*_federal` tables — so
the pivot could be tested without touching the working end-to-end system.

> Client and geography identifiers have been anonymised. The firm is referred to as *the firm*;
> the retrieval corpus is described as a *national policy corpus*.

---

## The pipeline

```
Stage 2   Ingest        YC batches (Apify) ─┐
Stage 2b  Ingest        Perplexity sonar    ├─→ ideas.status = 'scraped'
Stage 2c  Ingest        Exa findSimilar    ─┘
              │
Stage 3   Abstract      strip company specifics → pattern / enabling shift /
              │         transferable thesis / category      → 'abstracted'
              │
Stage 4-6 Knowledge     seed policy corpus → chunk → embed → kb_index (pgvector)
              │
Stage 8   Validate      retrieve top-k evidence → contextualize → KNOCKOUT
              │         → weighted rubric scoring   → 'validated' | 'knocked_out'
              │
Stage 11  Generate      one-pager fields per surviving idea    → 'published'
Stage 11b Rank          decision tier: top5 / appendix
Stage 11c Enrich        global signal, market gap, indicative economics
Stage 12  Report        decision-matrix cards + appendix table + HTML email digest
Stage 14  Query         standing shortlist interface (GET webhook → HTML)
```

Ideas move through the pipeline as a status machine on a single row —
`scraped → abstracted → validated | knocked_out → published` — which means every stage is
restartable, independently testable, and idempotent over what it has already processed.

---

## The parts that were actually hard

### Retrieval that does not let one document dominate

A naive top-k over the whole corpus returns eight chunks from whichever document happens to be
most semantically similar, and the model never sees the strategy document, the entities registry,
or the existing-initiatives document at all. The fix is a window function that takes the top 3
chunks **per document type**:

```sql
WITH ranked AS (
  SELECT metadata->>'doc_type'  AS doc_type,
         metadata->>'doc_title' AS doc_title,
         chunk_text,
         embedding <=> $1::vector AS distance,
         ROW_NUMBER() OVER (
           PARTITION BY metadata->>'doc_type'
           ORDER BY embedding <=> $1::vector
         ) AS rn
  FROM kb_index
  WHERE metadata->>'doc_type' <> 'guiding_principles'
)
SELECT doc_type, doc_title, chunk_index, kb_snapshot_id, chunk_text,
       ROUND(distance::numeric, 4) AS distance
FROM ranked
WHERE rn <= 3
ORDER BY distance, doc_type;
```

Guiding principles are excluded from retrieval on purpose — they are not evidence, they are the
scoring rubric, and they are injected separately at the scoring step.

Retrieved chunks are assembled into a labelled evidence block, and every claim the model makes has
to cite one of those bracketed labels. The labels are de-duplicated with `§n` suffixes so two
chunks from the same document stay individually addressable.

### A knockout filter with a category exception

Before anything gets scored, it has to survive four knockout conditions: saturated by private
players, hard regulatory barrier, no plausible anchor buyer, or **already implemented by
government**. That fourth one is the condition that a generic "is this a good idea" prompt never
catches, and it is kept deliberately narrow — building a specific application *on top of* an
existing national platform does not trigger it; only substantially duplicating the platform's
core mechanism does.

The condition that needed the most care was "no plausible anchor buyer". Applied naively it kills
every frontier idea — fusion, quantum hardware, advanced propulsion, novel materials — because
none of them have a near-term paying commercial customer. The prompt carries an explicit carve-out:
for genuinely capital-intensive, multi-year technology, a sovereign wealth fund or strategic
investment vehicle with a plausible mandate counts as an anchor buyer. And the carve-out is fenced:
it does not extend to ordinary software ventures just because they are ambitious.

### Scoring where the confidence is computed, not claimed

The model scores eight criteria 0–5 and, critically, is told **not** to compute the total itself —
it returns per-criterion scores plus an `evidence_ref` for each. The workflow applies the weights:

```js
const weightTable = {
  'Strategic alignment with national agenda':                          0.20,
  'Economic impact (GDP / jobs / FDI)':                                0.15,
  'Feasibility (talent, capital, regulatory readiness)':               0.15,
  'Anchor-demand clarity':                                             0.15,
  'Differentiation vs. existing national players':                     0.10,
  'Defensibility / moat':                                              0.10,
  'Time to first value':                                               0.10,
  'Capital efficiency':                                                0.05
};
```

Then it derives a **confidence band from the share of criteria that cite real evidence** rather
than asking the model how confident it feels: `≥60%` grounded is high, `≥30%` medium, below that
low. Shortlist eligibility requires both a weighted total of 60+ *and* a medium-or-high band — so
a confidently-argued, entirely ungrounded 80 does not make the shortlist. Criterion names that do
not match the weight table are collected in `unmatched_criteria` instead of being silently
dropped, which is how rubric drift gets noticed.

### Generation that is allowed to say no

The one-pager generator produces a `why_it_might_fail` field with instructions to give the single
most honest failure mode, no hedging, and an `act_watch_kill` recommendation where **Kill** is a
legitimate output for an idea that cleared the score threshold. An analyst pipeline that can only
say yes is a marketing pipeline.

The parser handles the reality that models rename fields, mapping aliases
(`venture_name`, `title`, `idea_name` → `name`) onto canonical keys and recording anything still
missing in `generation_missing_fields` rather than writing empty strings and moving on.

---

## Engineering notes

- **n8n cycles accumulate items.** Stage 12's first design used a raw graph cycle to loop email
  batches and hit n8n's item-accumulation behaviour. The second attempt used a recursive
  Execute-Workflow self-call, which is blocked for inactive workflows. The version that works uses
  `splitInBatches`, matching the pattern already proven in Stages 2b, 2c, 8 and 11.
- **Chunking was silently truncating.** The default document loader + splitter combination was
  cutting documents to 48–579 characters regardless of extraction method. Replaced with manual
  Code-node chunking by markdown section, feeding pre-chunked text to the embedder.
- **Template literals in expressions truncated long text.** Full document bodies had to be built
  in a Code node and inserted via a short parameterised query instead.
- **Migrations ran as one-off workflows.** Renaming a field across 73 published rows and
  backfilling a new `execution_level` was done rule-based, with no LLM cost, as a disposable
  workflow — and a separate read-only diagnostic workflow ran first to confirm the row counts
  before anything was written.

## Stack

**n8n** · **Postgres + pgvector** · **OpenAI** `text-embedding-3-small` (1536d) and `gpt-5.5` ·
**Apify** (YC batches) · **Perplexity sonar** (structured-output discovery) · **Exa** (findSimilar
discovery) · **Gmail** (HTML digest delivery)
