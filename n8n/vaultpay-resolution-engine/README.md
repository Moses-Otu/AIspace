# VaultPay Resolution Engine

An autonomous support resolution engine for a digital bank, built as a capstone brief: ten thousand
tickets a week, a previous chatbot that hallucinated a refund policy and cost the company fifty
thousand dollars, and customers who paste full card numbers into the chat box. The system has to
resolve routine tickets end to end, retrieve real policy rather than recall it, act on the bank's
APIs within limits it cannot exceed, and hand anything else to a human.

**Full sanitised export:** [`vaultpay-resolution-engine.workflow.json`](vaultpay-resolution-engine.workflow.json)
— 42 nodes, importable into any n8n instance. Credentials, webhook IDs and the instance hostname
have been stripped; replace `https://YOUR-N8N-HOST`, reconnect the OpenAI, Pinecone and API-key
credentials, and point the Pinecone nodes at your own index before running.

---

## The shape of it

A ticket arrives on a webhook and leaves as either a resolved reply or a routed escalation. In
between there are four deterministic checkpoints and one probabilistic middle. The whole design is
an argument about which of those two does what.

**1 — Sanitise.** A Code node scrubs PANs, CVVs, PINs, SSNs, expiry dates, account and routing
numbers and IBANs, replacing each with a labelled marker and recording what was found. This runs
before anything else, so no model ever sees a card number.

**2 — Identify.** The customer's email is looked up live against the bank's API. No match means no
conversation about the account: the ticket escalates for identity verification without a single
model call.

**3 — Bind the limits.** A second Code node maps the returned tier onto the policy limits from the
tier document — conditional credit cap, refund cap, overdraft fee, replacement SLA, investigation
window. Every number the system will later quote or enforce is set here, in code, from the
customer's actual tier.

**4 — Classify and route.** A text classifier splits the ticket into policy question, transaction
dispute, lost or stolen card, refund request, or none of those. Each route has its own specialist
agent. There is no single agent that does everything, and the fallback branch escalates rather than
guesses.

**5 — Guardrail, then act.** Before any agent on a money-moving path runs, a Code node has already
decided whether it is allowed to. Fraud language, an amount above the tier cap, a suspended or
overdrawn account, legal or negligence language — each of these escalates deterministically, and on
the fraud paths the card is blocked first. Only tickets that clear the guardrail reach an agent.

**6 — Draft.** The specialist agent retrieves from Pinecone and, where the route allows it, calls
the bank's API to issue a conditional credit or a fee refund. It is told the exact maximum it has
been cleared for.

**7 — Review, then decide.** A QA chain reviews the draft against eight compliance rules and returns
a structured verdict. A Code node then makes the actual decision: it re-scans the draft for
forbidden guarantee phrases and unredacted identifiers regardless of what the reviewer said, and any
failure routes to a human. The model advises; code decides.

---

## Design notes

**Retrieval is scoped by metadata, not just by similarity.** The five policy documents live in one
Pinecone index, separated by a `category` field. Each of the five knowledge-base tools filters on
one category, and each agent is wired only to the tools its route needs. The dispute agent cannot
read the refund policy. That is a structural constraint, not an instruction the model can drift
away from.

**The tier is fetched, never inferred.** The agent is handed the customer's caps and SLAs in its
system message as facts it must not recompute. Ask the same question as a Standard and a Gold
customer and the answers differ, because the numbers come from the lookup rather than from whatever
the model remembers about banking.

**Cap enforcement happens before the agent, not after.** A dispute above the tier's conditional
credit cap never reaches the dispute agent at all. The escalation reason names the policy document
and the two numbers. There is no path where a model talks itself into an over-cap credit, because
on that path no model runs.

**Card blocking is ordered by policy, not by the agent's plan.** The lost-card route blocks the card
and orders the replacement as main-flow HTTP nodes before the agent is invoked, because the policy
requires the block to happen before anything else. The agent's job is to explain what has already
happened, and it is told so.

**The QA layer is two things, and only one of them is a model.** The reviewer sees the draft plus
the verified tier facts, so accurate policy detail reads as correct rather than invented. Its
verdict is then combined with a hard-coded phrase and identifier scan that runs on every draft
regardless. A reviewer that misses `we will refund you` does not get to ship it.

**Forbidden phrasing is a list, not a vibe.** The refund policy names the exact phrases an automated
system may not use. They are in the agent prompt as a prohibition, in the QA prompt as a rejection
rule, and in the enforcement Code node as a literal string scan. Three layers, because this is the
failure that cost the fictional bank fifty thousand dollars.

**Every escalation carries its reason.** Ticket ID, tier, customer ID, intent, the actions already
taken on the card, and a reason that cites the policy document by ID. An escalation that arrives at
a human queue saying only "needs review" has thrown away the work that produced it.

---

## Things that bit, and are worth knowing

**A write node outputs its API response, not the data that flowed into it.** The escalation builder
originally read `$json` and, on the two paths where a card action precedes it, received the block
endpoint's `{"message": "Card successfully blocked."}` instead of the ticket. Every field came back
null. It now resolves context from whichever guardrail actually ran.

**Paired-item resolution breaks across HTTP nodes.** Expressions of the form
`$('Some Node').item.json.field` walk n8n's paired-item chain backwards, and that chain does not
survive two HTTP calls. On the lost-card route the entire fact sheet handed to the QA reviewer
rendered blank, so it rejected a correct answer for stating things "not supported by the facts
provided" — there were no facts provided. One ticket per execution means `.first()` is equivalent
and immune.

**A compliance reviewer will over-reject if you let it.** Rules written as broad prohibitions get
stretched over things they were never about: a rule against promising refunds was applied to a
factual sentence about pending transactions being held. The rules are now scoped to what they
actually govern, and the reviewer is given a standard-mechanics list so operational facts are not
mistaken for promises.

---

## Stack

**n8n** · **Text Classifier** · four route-specific **AI Agents** · **Pinecone** vector store with
per-category metadata filtering · **OpenAI** chat + embeddings · **HTTP Request Tool** for bank API
actions · **Basic LLM Chain** + **Structured Output Parser** for the QA verdict · **Code** nodes for
every deterministic checkpoint · **Webhook + Respond to Webhook**

## Running it

The bank API is a mock service with a Swagger UI at `/docs`, authenticated with an `X-API-Key`
header. Create one Header Auth credential and select it on all seven HTTP nodes — four on the main
canvas, three in the agent tool strip.

The five policy documents must be embedded into a Pinecone index with a `category` metadata field
set to one of `account_tiers`, `overdraft_policy`, `lost_card_policy`, `dispute_resolution`,
`refund_policy`. The embedding model in the workflow must match the one used to build the index.

[`test-payloads.json`](test-payloads.json) contains twelve request bodies, one per route, with the
expected outcome for each — including the two that must escalate deterministically and the merchant
refund case that must never produce a refund.
