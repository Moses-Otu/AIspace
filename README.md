# AIspace

A single home for all my AI projects — and the source for my portfolio site.

**Portfolio:** [`index.html`](index.html) — a static single page, deployed on Vercel.

---

## What is in here

### Agentic systems — [`n8n/`](n8n)

Production automation built in n8n. Each folder has a write-up of how the system works and why it
is built that way, plus sanitised workflow exports — **11 importable workflows, 191 nodes**, for
every system except Media Clippings (not exposed for programmatic export) and the Lead Intelligence
research sub-workflows.

| Project | What it does |
|---|---|
| [Internal Audit Report Drafter](n8n/iard-audit-report-drafter) | Audit artefacts → formatted draft Word report, refined by chat, with a real approval gate |
| [Opportunity Radar](n8n/opportunity-radar) | 12-stage research pipeline: ingest → abstract → pgvector retrieval → knockout → weighted scoring → one-pagers |
| [Employee Engagement Pulse](n8n/engagement-pulse) | Weekly check-in with AI severity triage, escalation and a 2-day reminder sweep |
| [Risk & Control Matrix Builder](n8n/rcm-builder) | Engagement intake → Drive corpus → FastAPI generation → reviewer approval |
| [CreatorOS](n8n/creatoros-content-pipeline) | Five-agent content pipeline with structured-output contracts and a Slack send-and-wait gate |
| [Automated Media Clippings](n8n/media-clippings) | Daily Brave sweep, agent selection, human curation, dedicated error handling |
| [Lead Intelligence](n8n/lead-intelligence) | Buyer enrichment and scoring, plus a company-research agent layer |

### Applications and models

| Project | Location |
|---|---|
| [Like I Am 5](Like-I-am-5) | RAG that explains government policy in plain language |
| [BoneAI](boneai-rag-app) | Domain-specific retrieval application |
| [Air Pollution Prediction](Air-pollution-prediction-model) | Regression models over environmental sensor data |

Other work lives in its own repositories — [FeaturePhone AI](https://github.com/Moses-Otu/featurephone-ai)
(USSD AI assistant), the [banking recommender](https://github.com/Moses-Otu/Recommender_system-Zenith-bank-Hackathon-),
and the data-engineering projects listed on the portfolio page.

---

## About the n8n exports

Workflow JSON in this repository is sanitised, not raw. Before committing, exports are run through
a script that:

- removes every `credentials` block and `webhookId`
- drops instance-specific metadata (`scopes`, `versionId`, `activeVersion`, internal IDs)
- replaces the n8n instance hostname with `https://YOUR-N8N-HOST`
- replaces real email addresses with `example.com` equivalents
- anonymises client and entity names

To use one: import the JSON into n8n, reconnect your own credentials, and replace the placeholder
host and channel IDs.

Where a workflow is not exposed for programmatic export, the folder contains the architecture
write-up without the JSON, and says so.

---

## Running the site locally

It is a single static file with no build step and no dependencies:

```bash
python -m http.server 8000
```

Then open <http://localhost:8000>.

### Deploying

On Vercel, import this repository, leave the framework preset as **Other**, and set the output
directory to the repository root. [`vercel.json`](vercel.json) handles clean URLs and security
headers; there is nothing to build.
