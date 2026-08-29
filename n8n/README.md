# n8n — Agentic Systems

Production automation. Each folder documents one system: what it does, how it is put together,
and the decisions that are not obvious from the node graph.

| Project | Scale | Export |
|---|---|---|
| [Internal Audit Report Drafter](iard-audit-report-drafter) | 5 workflows, ~65 nodes | write-up |
| [Opportunity Radar](opportunity-radar) | 12 stages, two parallel instances | write-up |
| [Employee Engagement Pulse](engagement-pulse) | 1 workflow, 30 nodes, 4 triggers | ✅ full JSON |
| [Risk & Control Matrix Builder](rcm-builder) | 1 workflow + FastAPI service | write-up |
| [CreatorOS](creatoros-content-pipeline) | 1 workflow, 26 nodes, 5 agents | write-up |
| [Automated Media Clippings](media-clippings) | main + 4 supporting workflows | write-up |
| [Lead Intelligence](lead-intelligence) | inbound pipeline + research agents | write-up |

## Recurring patterns

A few things show up across all of these, and they are the parts worth stealing:

**Gate on structure, not on prompt wording.** Where output has to be a particular shape, it goes
through a structured output parser or a strict-JSON contract with a validation node behind it —
not a prompt asking politely for JSON. Free text that gets `JSON.parse()`d downstream fails
silently, and silent nulls travel a long way before anyone notices.

**Fail loudly, in a named branch.** Every pipeline here has explicit terminal states for the
things that go wrong — missing mandatory input, unmatched record, agent returned nothing, source
errored — each with its own alert. The default failure mode of an automation is not a crash, it is
a quiet day that looks like a successful one.

**Human approval means the execution pauses.** Slack send-and-wait, a form response, an approval
that flips engagement status to final and short-circuits every edit path afterwards. A
notification that says "please approve" while the pipeline carries on publishing is not an
approval gate.

**Push heavy document work into a service.** Word rendering (`python-docx`) and workbook
generation live behind FastAPI endpoints that n8n calls. n8n orchestrates, routes and holds human
decisions; Python does the things that want tests and a debugger.

**Restartable status machines over long chains.** Long pipelines advance a status column on a row
(`scraped → abstracted → validated → published`) rather than passing one giant payload end to end.
Every stage becomes independently runnable and idempotent over what it has already processed.

## Sanitising exports

[`sanitise_export.py`](sanitise_export.py) strips credentials, webhook IDs and instance metadata
from a raw export, and applies substitutions for hostnames and email addresses. Extend `REPLACE`
with project-specific client names before running, and read the output before committing it.

```bash
python sanitise_export.py raw-export.json engagement-pulse/engagement-pulse.workflow.json
```
