# Automated Media Clippings

A daily media-monitoring pipeline: sweep the web for coverage, have an agent shortlist what is
actually relevant, put the shortlist in front of a human for curation, and fail loudly when a
source breaks.

> Client identifiers have been anonymised.

## Shape of the system

The build is split across a main workflow and several supporting workflows, which is what the
iteration history reflects — this pipeline went through a long refinement cycle in production.

| Workflow | Role |
|---|---|
| **Main** | Daily sweep. Runs Brave Search across the monitored topics, normalises results, and hands candidates to selection. |
| **Selection sub-workflow** | An agent decides what makes the cut — relevance to the monitored entities rather than keyword presence. |
| **Response form** | Human curation. The shortlist is served as a form so a person confirms or drops items before anything is circulated. |
| **Error handler** | Dedicated error workflow so a failing source surfaces as an alert instead of silently shortening the day's coverage. |
| **Logged variants** | Instrumented copies used to trace what the selection agent actually chose and why, during tuning. |

## Design notes

- **A dedicated error handler is not optional here.** The failure mode of a monitoring pipeline is
  not a crash — it is a quiet day. If a search provider rate-limits or a parser breaks, the run
  still "succeeds" with fewer items and nobody notices the gap until someone asks why a story was
  missed. Routing errors to their own workflow makes that gap visible.
- **Search relevance is not selection relevance.** Brave returns what matches the query; the
  selection agent's job is deciding what a reader of these clippings would want, which is a
  different and much less mechanical question. Separating the two into distinct workflows meant
  selection could be tuned repeatedly without touching ingestion.
- **The human is in the loop by default**, not as an exception path. The response form is part of
  the normal daily run.

## Stack

**n8n** · **Brave Search API** · **OpenAI** (selection agent) · **n8n forms** (curation) ·
**n8n error workflows**

---

*Sanitised workflow exports are not included for this project — the workflows are not currently
exposed for programmatic export. The write-up above describes the architecture as built.*
