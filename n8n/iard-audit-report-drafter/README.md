# Internal Audit Report Drafter (IARD)

An agentic system that turns the artefacts an internal audit team already produces — a completed
audit working file, a kick-off deck, an audit notification — into a formatted draft Word report,
then lets the auditor refine it conversationally until they approve it.

Built in n8n as five co-operating workflows over a Supabase schema, with a self-hosted
FastAPI + `python-docx` service doing the actual document rendering.

**Sanitised exports** — all five workflows, 65 nodes:
[01 Orchestrator](01-orchestrator.workflow.json) ·
[02 Intake & Parse](02-intake-and-parse.workflow.json) ·
[03 Front-Matter Assembly](03-front-matter-assembly.workflow.json) ·
[04 Document Assembly](04-document-assembly.workflow.json) ·
[05 Refinement](05-refinement.workflow.json)

Import 02–05 first, then set the `REPLACE_WITH_*_ID` placeholders in the orchestrator to the ids
they get in your instance. Also set `RENDER_SERVICE_URL` as an n8n variable and reconnect Supabase
and OpenAI credentials.

> Client identifiers have been anonymised throughout. Entity names appear as
> *Operating Company A/B/C*.

---

## Why it is built this way

The hard part of this problem is not generation, it is **restraint**. An audit report is a
regulated document: some sections must be reproduced byte-for-byte from a template, some are
fixed sentences with names substituted, and only a small number may genuinely be written by a
model. Getting that wrong is not a cosmetic bug — it is a compliance failure.

So every section of the report is classified into one of three kinds, and the pipeline enforces
the classification structurally rather than by prompting nicely:

| Kind | Example sections | How it is produced |
|---|---|---|
| **Verbatim** | Limitations of Internal Audit, Risk Classification scale, kick-off objectives and scope | Copied from template / parsed source. Never passes through a model. |
| **Fill** | Acknowledgment paragraph, audit team block, overall opinion paragraph | Fixed sentence structure with values substituted from the engagement record or a held configuration table. |
| **Generated** | Background / introduction | The one LLM call, explicitly constrained to the supplied sources. |
| **Derived** | Table of contents, List of Audit Issues, Audit Issues Dashboard | Rebuilt deterministically on every generation from the observation rows. |

The overall-opinion text is a good illustration. It started as a hardcoded lookup table inside a
Code node; it now reads from a versioned `configuration` table so the wording is owned by the
audit function, not by the workflow author — the workflow just picks the latest version for the
engagement's opinion label.

---

## Architecture

```
                    Form: New Engagement            Chat: refinement message
                            │                                │
                            ▼                                │
              ┌──────────── 01 Orchestrator ─────────────────┘
              │
   ┌──────────┼───────────────┬────────────────────┐
   ▼          ▼               ▼                    ▼
02 Intake  03 Front-Matter  04 Document       05 Refinement
 & Parse     Assembly        Assembly         (Detailed Audit Issues)
   │            │               │                    │
   └────────────┴───────┬───────┴────────────────────┘
                        ▼
             Supabase: engagement, source_document,
             observation, observation_root_cause,
             appendix_item, configuration, change_log
                        │
                        ▼
          FastAPI render service (python-docx) → .docx
```

### 01 — Orchestrator
Two entry points into one system: a **form trigger** for a new engagement (audit title, quarter,
year, entity, overall opinion, plus the file uploads) and a **chat trigger** for refinement
instructions on an existing report. The form's `Overall Opinion` dropdown is constrained to the
four-grade scale plus *Not Rated*, so the opinion label is always a valid key into the opinion
library.

### 02 — Intake & Parse
Filters out empty file slots, registers each real upload as a `source_document` row with
`parse_status = 'pending'`, then fans out to per-format parsers (xlsx working file, pptx kick-off
deck, optional inputs including legacy `.ppt`).

The interesting node is **Compute Input Gaps**. Missing *mandatory* inputs throw and stop the run;
missing *optional* inputs are recorded on the engagement as `input_gaps` so the report can state
what was unavailable rather than quietly proceeding as if it had everything:

```js
const required = ['completed_audit_working_file', 'kickoff_deck', 'audit_notification'];
const optional = ['process_understanding', 'analysis_sheet'];
const present  = new Set(items.map(i => i.json.doc_type).filter(Boolean));

const missingRequired = required.filter(t => !present.has(t));
if (missingRequired.length) {
  throw new Error('Missing mandatory input(s): ' + missingRequired.join(', '));
}
return [{ json: { engagement_id: engagementId, input_gaps: optional.filter(t => !present.has(t)) } }];
```

### 03 — Front-Matter Assembly
Six parallel branches — verbatim sections, fill sections, background generation, opinion-library
lookup, entity-logo lookup, and the engagement read — merged by position into a single
`front_matter` JSON blob written back to the engagement row.

The background prompt is the whole grounding contract in three sentences:

> Draft a one-page background/introduction for this internal audit report, consistent with the
> audit notification, process understanding, and completed audit working file provided below.
> Do not state anything not supported by these sources. If an analysis sheet is provided,
> reference it is placed and captioned separately — do not fabricate figures.

**A real bug worth recording.** The verbatim and fill builders originally read engagement fields
(`title`, `quarter`, `entity`, `audit_team`) off the trigger's passthrough data. But the trigger
only ever carries what Intake & Parse forwarded — per-file classification items, never the
engagement row — so every one of those fields silently rendered as `undefined`. Caught in a test
execution, fixed by adding an explicit `Get Engagement` read that the builders reference by node
name. The comments in the workflow still document it, because the same class of mistake is easy
to repeat anywhere n8n passthrough is assumed to carry more than it does.

### 04 — Document Assembly
Reads observations, their root causes, appendix items and the engagement in parallel; groups root
causes by observation (Supabase's filter set has no `IN` operator, so it fetches and filters in a
Code node); builds the render payload; POSTs it to the render service; and validates that a
non-empty document actually came back before logging a `generate` entry in the change log.

Observations rated `area_for_improvement` are deliberately **excluded** from both the dashboard
counts and the List of Audit Issues — they are improvements, not issues, and conflating them
inflates the issue count.

### 05 — Refinement
A classifier turns a free-text auditor instruction into strict JSON:

```
{"action": "merge|split|reword|re-rate|attach_evidence|move_to_appendix|approve|query_status|other",
 "observation_ids": ["..."]}
```

which a Switch routes to the matching handler. Two design decisions matter here:

- **Scope is deliberately narrow.** This sub-workflow only edits Section 7, Detailed Audit
  Issues. It will not accept edits to background, front matter, or appendices outside an
  observation's own appendix items — a smaller surface that can be reasoned about is worth more
  than a chat agent that can touch anything.
- **Approval is a real gate.** Approval moved from per-observation freezing to a single
  engagement-level `status = 'final'`. Once final, an IF short-circuits every edit path and
  returns a refusal. Un-finalising is not supported by design.

Every path — including no-op status queries — writes to `change_log` with actor (`human` /
`agent`) and action, so the report has a complete provenance trail.

---

## Stack

- **n8n** — orchestration, form and chat triggers, sub-workflow execution
- **Supabase (Postgres)** — engagement, source_document, observation, observation_root_cause,
  appendix_item, configuration, change_log
- **OpenAI GPT-4.1** — background drafting and instruction classification
- **FastAPI + python-docx** — self-hosted render service (`POST /render-report`), returning the
  binary `.docx`

## Status and known gaps

Pilot. Honest about what is not done:

- Per-format parsers (xlsx / pptx / legacy ppt) are wired but disabled pending Increment 2.
- Embedded images from source decks are not auto-placed.
- Template fidelity validation is currently a non-empty-document check; the full structural diff
  against the template is not built.
- Entity logo lookup is wired but the render service does not yet place logos.
- Stable paragraph IDs for round-trip reconciliation (re-uploading an edited Word file and
  diffing it back to observation rows) are scaffolded but not active.
