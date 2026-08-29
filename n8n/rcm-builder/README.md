# Risk &amp; Control Matrix Builder

Intake-to-approval workflow for starting a new audit engagement. An auditor fills one n8n form;
the pipeline gathers the standing corpus, generates a draft risk-and-control matrix, puts the
workbook in a reviewer's inbox, and records what they decided.

> Client identifiers have been anonymised.

## Flow

1. **Intake form** — engagement details for a new audit.
2. **Corpus pull** — fetches the standing-corpus documents from Google Drive, so the draft is
   generated against the audit function's own reference material rather than general knowledge.
3. **Generate** — calls the RCM Builder FastAPI service, which produces the draft matrix as a
   workbook.
4. **Deliver** — emails the workbook to the assigned reviewer.
5. **Capture the decision** — the reviewer's *Approved* / *Not Yet Approved* response comes back
   into the pipeline rather than living in an email thread.

## Why the generation sits in a service

The matrix is a spreadsheet with structure and formatting requirements, and the generation logic
is substantial enough to want tests around it. Both of those things belong in Python, not in a
chain of n8n nodes. n8n does what it is good at — triggering, routing, file movement, notification,
and holding the human decision — and calls out to FastAPI for the document work. The same split is
used in the [Internal Audit Report Drafter](../iard-audit-report-drafter), where a `python-docx`
service renders the Word report.

Capturing the approval decision as pipeline state, rather than as an email reply someone has to
remember, is the point of step 5: it is what makes the engagement's status a fact the system knows
rather than something a person has to reconstruct.

## Stack

**n8n** (form trigger, orchestration) · **FastAPI** (RCM generation service) ·
**Google Drive** (standing corpus) · **Gmail** (reviewer delivery and decision capture)
