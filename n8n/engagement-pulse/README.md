# Employee Engagement Pulse

A weekly wellbeing check-in that closes the loop instead of collecting sentiment into a void.
All four stages live in one workflow, separated by sticky notes, because they share the same case
record and splitting them across files made the state harder to follow, not easier.

**Full sanitised export:** [`engagement-pulse.workflow.json`](engagement-pulse.workflow.json) —
30 nodes, importable into any n8n instance. Credentials, webhook IDs and the instance hostname
have been stripped; replace `https://YOUR-N8N-HOST` and reconnect Gmail before running.

---

## The four stages

**1 — Friday dispatch.** A schedule trigger fires every Friday at 09:00, reads active employees
from a data table, and sends each one a pulse invite linking to the hosted form.

**2 — Submission handler.** The form posts to a webhook. The submission is normalised, the
employee looked up by ID, and — if they match a record — an Information Extractor node classifies
the severity of what they wrote. The case is assembled, logged to a data table, and emailed to the
right business partner. Critical severity additionally escalates to the HR lead. Submissions that
match no employee record raise their own alert rather than being dropped.

**3 — Attended callback.** The business-partner email carries a one-click *attended* link back to
a webhook. It finds the open case, marks it attended, and responds with a confirmation page — or,
if the case is already closed or was never found, with an honest "not found or already attended"
page rather than a false success.

**4 — Reminder sweep.** A daily 09:00 schedule pulls pending cases, filters to those open more
than two days, sends a reminder to the business partner, and flags the reminder so the same case
is not chased twice.

---

## Design notes

- **The severity classifier is an extractor, not a chat agent.** It returns a typed field against
  a schema. There is no free text to re-parse and no room for the model to answer a question that
  was not asked.
- **The attended link is a GET webhook that responds with HTML.** No app, no login, no
  authentication ceremony for a one-click acknowledgement — the case ID in the URL is the token.
  That is a deliberate trade of strictness for the thing that actually determines whether this
  system works: whether a busy business partner clicks the button.
- **Every terminal state has a response.** Unmatched submission, case not found, case already
  attended — each has its own branch and its own message. Silent failure in a wellbeing pipeline
  means someone reported something and nobody came.
- **State lives in n8n data tables**, so the case record is queryable from every stage without
  standing up a database for a four-stage workflow.

## Stack

**n8n** · **Information Extractor** (OpenAI) · **n8n data tables** · **Gmail** · **Webhooks +
Respond to Webhook** · form front-end deployed on Vercel
