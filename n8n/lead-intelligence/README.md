# Lead Intelligence

Two connected pieces of go-to-market automation: an inbound pipeline that qualifies property buyers
as they arrive, and a research layer that answers questions about companies on demand.

**Sanitised export:** [`buyer-lead-qualifier.workflow.json`](buyer-lead-qualifier.workflow.json) —
the inbound pipeline. Credentials, webhook ID and the spreadsheet ID have been removed.

> Client identifiers have been anonymised.

## Inbound pipeline — buyer qualification

A landing-page form posts to a webhook. From there:

1. **Verify the email** against the Hunter.io email-verifier API.
2. **Qualify** — an agent scores the lead 0–100 on readiness to transact and labels it
   hot (80+) / warm (50–79) / cold (<50).
3. **Flatten** — nested agent output is flattened into 20 named columns.
4. **Upsert to Google Sheets** — so a returning buyer updates their row rather than duplicating.
5. **Confirm** — the buyer gets an acknowledgement immediately, via Respond to Webhook.

### The idea worth stealing: score intent against evidence

Most lead scorers read only what the lead *said*. This one weighs stated intent against an
independent signal of whether the lead is real, and the prompt says so explicitly:

> A VALID, deliverable email = a real, reachable lead (good). A DISPOSABLE or INVALID email =
> likely fake or low-intent (lower the score significantly). A COMPANY-DOMAIN email suggests a
> working professional (some ability-to-pay signal) versus generic free webmail (neutral, common,
> fine). A low deliverability score means you may never reach them, so lower the score.

Someone claiming a ₦120M budget with a 30-day timeline from a throwaway address is not a hot lead,
and the pipeline knows that without a human reading it. The prompt also ends with an explicit
instruction — *Do not inflate* — because a scorer that rates everything warm has told you nothing.

Two smaller decisions that matter:

- **Enrichment failure degrades the lead, it does not kill it.** The Hunter call is set to
  `neverError`, so an API outage produces an unknown email status the agent scores around rather
  than a failed execution and a lost lead.
- **The output contract is a schema, not a hope.** A structured output parser pins all 20 fields,
  including the drafted follow-up message, so the flatten step maps known keys instead of
  defensively parsing prose.

### One thing to check before reusing this

The Sheets upsert matches on **`full_name`**, not email — so two different buyers with the same
name overwrite each other, and one buyer who submits twice under a slightly different spelling
creates a duplicate. Email is the stable key here and is already captured. The export preserves the
workflow as it actually runs; changing `matchingColumns` to `["email"]` is a one-line fix.

## Research layer

A chat agent over a set of research sub-workflows, so a question like *"what should I know about
this company before the call"* fans out to specialised flows rather than being answered from one
general prompt:

- **Company research — signals and brand**
- **Vendor intelligence**
- **Financials**
- **Full report flow**, which composes the above into a single written report
- **Lead search execution**, which runs the search side rather than the analysis side

Splitting research by question type means each sub-workflow can use the right source and the right
prompt for its own domain, and can be re-tuned without regressing the others. The chat agent is a
router with a memory, not the thing doing the work.

*Exports for the research sub-workflows are not included — they are not currently exposed for
programmatic export.*

## Stack

**n8n** · **OpenAI GPT-4.1** with structured output parsers · **Hunter.io** (email verification) ·
**Google Sheets** (upsert) · **Webhooks** (landing-page intake and immediate response)
