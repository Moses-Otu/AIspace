# Lead Intelligence

Two connected pieces of go-to-market automation: an inbound pipeline that qualifies buyers as they
arrive, and a research layer that answers questions about companies on demand.

> Client identifiers have been anonymised.

## Inbound pipeline

A landing-page form posts to a webhook. From there:

1. **Enrich** — an agent fills in what the form did not ask for.
2. **Score** — the buyer is classified hot / warm / cold against the qualification criteria.
3. **Flatten** — the enriched record is flattened from nested agent output into columns, because
   a sheet is what the sales side actually reads.
4. **Upsert on email** — writes to Google Sheets keyed on email address, so a returning buyer
   updates their row rather than creating a duplicate.
5. **Confirm** — the buyer gets an acknowledgement, immediately.

The flatten step is the unglamorous one that matters. Agent output is nested and variable-shaped;
a spreadsheet is neither. Doing that conversion explicitly, in its own node, is what keeps the
sheet stable when the agent's output shape shifts.

## Research layer

A chat agent over a set of research sub-workflows, so a question like *"what should I know about
this company before the call"* fans out to the specialised flows rather than being answered from
one general prompt:

- **Company research — signals and brand**
- **Vendor intelligence**
- **Financials**
- **Full report flow**, which composes the above into a single written report
- **Lead search execution**, which runs the search side rather than the analysis side

Splitting research by question type means each sub-workflow can use the right source and the right
prompt for its own domain, and can be fixed or re-tuned without regressing the others. The chat
agent is a router with a memory, not the thing doing the work.

## Stack

**n8n** · **OpenAI agents** with sub-workflows as tools · **Google Sheets** (upsert on email) ·
**Webhooks** (landing-page intake) · enrichment and search APIs

---

*Sanitised workflow exports are not included for this project. The write-up above describes the
architecture as built.*
