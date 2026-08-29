# CreatorOS — Multi-Agent Content Pipeline

Five agents in sequence — research, write, edit, fact-check, SEO — ending at a Slack approval that
genuinely blocks publication. This is version 2; most of what is interesting about it is what
version 1 got wrong.

---

## Chain

```
Manual start
   │
Content Brief ──→ Brief Filled In? ──(no)──→ Slack alert, stop
   │ (yes)
Research Agent  [structured output: summary, citations, counterarguments]
   │
Research Valid? ──(no)──→ Slack alert, stop
   │ (yes)
Writer Agent    [free-text markdown]
   │
Editor Agent    [free-text markdown]
   │
Fact Check Agent [structured output: article, flags[{claim, issue}]]
   │
SEO Agent       [structured output: article, seoTitle, slug, description,
   │             keywords, tags, ogDescription, flags]
   │
SEO Output Valid? ──(no)──→ Slack alert, stop
   │ (yes)
Send for Approval  ← Slack send-and-wait: execution genuinely pauses here
   │
Approved? ──(no)──→ Slack "rejected", nothing published
   │ (yes)
Publish to Hashnode (createDraft mutation) ──→ Slack "published"
```

## Three fixes carried over from v1

**Structured output contracts instead of free text.** The Research, Fact Check and SEO agents use
Structured Output Parsers, so they return real parsed JSON fields. The previous design returned
free text that downstream nodes had to `JSON.parse()`, and when that parse failed it silently
produced nulls — an empty article would sail through the whole chain and reach the publish step.
Writer and Editor stay as free-text markdown agents, because prose is what they are for.

**Validation gates that stop rather than cascade.** Gates sit after the brief, after Research, and
after SEO. Each one halts the run and posts a specific Slack alert naming what failed. The SEO
gate checks the things that make a publish valid — non-empty title, non-empty slug, article at
least 300 characters — not just that the node returned something.

**An approval that actually gates.** `Send for Approval` uses Slack send-and-wait with a
double-confirm and an explicit *Reject* label. The execution pauses; nothing downstream runs until
a human clicks. In v1 "approval" was a notification with no gate behind it, which is to say it was
not approval at all.

The placeholder-detection gate is worth calling out too: the Content Brief ships with
`<__PLACEHOLDER_VALUE__...__>` defaults and the first IF node checks the fields do not still
contain `PLACEHOLDER_VALUE`. This is the specific bug that broke the earlier version — placeholder
text flowing into the agents and producing a plausible-looking article about nothing.

## Setup

Fill in before running: the Slack channel ID on all Slack nodes, a Hashnode API token as an HTTP
Header Auth credential (`Authorization: Bearer <PAT>`), and `publicationId` in the GraphQL request
body. Slack interactivity must be enabled on the app with the request URL pointed at your n8n
instance, per the n8n *Approvals in Slack* docs. Verify the send-and-wait output field name
against a real test run — it varies by n8n version; this workflow reads `$json.approved`.

## Stack

**n8n** · **LangChain agent nodes** with Structured Output Parsers · **OpenAI GPT-4.1** ·
**Slack** (send-and-wait HITL + alerting) · **Hashnode GraphQL API**
