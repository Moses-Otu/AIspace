# Risk &amp; Control Matrix Builder

Intake-to-approval pipeline for starting a new audit engagement. An auditor fills one form; the
pipeline assembles the audit function's entire standing corpus, generates a draft risk-and-control
matrix, emails the workbook to a reviewer, and blocks until that reviewer records a decision.

**Sanitised export:** [`rcm-builder.workflow.json`](rcm-builder.workflow.json) — 34 nodes.
Credentials, webhook IDs, Google Drive file IDs, the data table ID and the service host have been
replaced with placeholders.

> Client identifiers have been anonymised.

---

## Flow

```
RCM Intake Form  (entity, audit name, reviewer email, up to 6 engagement documents)
      │
      ▼
20 sequential Google Drive downloads — the standing corpus:
  IA SOP & methodology · Delegation of Authority · ERM register
  8 × IIA topical requirements + user guides (third party, cybersecurity,
      organisational resilience, organisational behaviour)
  2 × trial balance · GL account hierarchy
  4 × dimension hierarchies (business, cost centre, location, product)
  impact criteria
      │
      ▼
Fill Missing Optional Binaries  →  POST /rcm/generate  (multipart, 28 parts)
      │
      ▼  202 + job_id                        ▼ anything else
Wait 3 min ──► GET /rcm/status/{job}    Notify Submission Failed
      ▲              │
      │      ┌───────┼────────┐
      └──────┤ still_running  │
             │ failed ────────┼──► Notify Pipeline Failed
             │ completed      │
             └───────┬────────┘
                     ▼
              GET /rcm/result/{job}
                     │
        ┌────────────┴────────────┐
   Record Run (status=Pending)   (binary workbook)
        └────────────┬────────────┘
                     ▼  merge by position
              Deliver Workbook  (Gmail, .xlsx attached)
                     ▼
              Request Approval  (Gmail send-and-wait, custom form)
                     ▼
           Record Approval Decision  (status, notes, timestamp)
```

---

## The decisions worth explaining

### Generation is asynchronous, and the workflow respects that

Building an RCM from twenty-odd source documents takes minutes, not seconds. Holding an HTTP
connection open for that is how you collect gateway timeouts. So the service returns **202 with a
`job_id`**, and the workflow polls: wait three minutes, check status, and branch on a Switch with
three named outcomes — `completed`, `failed`, `still_running`. Only `still_running` loops back to
the wait.

That third branch is the one people forget. Without an explicit still-running case, a poll that
finds an unfinished job falls through to whatever the fallback happens to be, and the run either
dies or reports success on a workbook that does not exist yet.

### Two different failures get two different emails

A submission that never started (`Call RCM Builder API` did not return 202) reports the HTTP status
and `body.detail`. A job that started and then failed reports the job's own `detail`. Same
recipient, different diagnosis — and neither leaves the auditor waiting for a workbook that is
never coming. The initial request also sets `neverError`, so a non-202 response is *routed* rather
than throwing and losing the context needed to write a useful message.

### Absent optional files are stubbed, not skipped

The multipart POST names every optional binary field explicitly. A field the auditor left blank
simply does not exist on the item, and n8n fails the whole request when it cannot find the named
binary. `Fill Missing Optional Binaries` stubs each absent optional as an empty binary so one
skipped upload cannot take down the submission:

```js
const optionalKeys = ['previous_audit_rcm_files', 'final_audit_report_files',
                      'policy_business_rule_files', 'procedure_process_document_files',
                      'kickoff_minutes_files'];
const binary = $input.item.binary || {};
for (const key of optionalKeys) {
  if (!binary[key]) {
    binary[key] = { data: '', mimeType: 'application/octet-stream', fileName: '' };
  }
}
return { json: $input.item.json, binary };
```

### The merge exists because neither branch has everything

`Record Run` returns the new row's `id` but drops the binary. `Fetch Result` carries the binary but
knows nothing about the row. The delivery step needs both — the workbook to attach, and the row id
so the approval decision can be written back to the right run. Hence the position-based merge with
`Fetch Result` feeding both inputs.

### Approval is a gate, not a notification

`Request Approval` uses Gmail **send-and-wait** with a custom form: a required *Approved* /
*Not Yet Approved* dropdown and an optional notes field. The execution genuinely pauses. When the
reviewer submits, the decision, their notes and a timestamp are written back onto the run's row,
which is what turns "did anyone sign off on this?" from an email-archaeology question into a
database query.

### Why generation lives in a service

The matrix is a formatted workbook, and the generation logic is substantial enough to want tests
around it. Both belong in Python. n8n does what it is good at — triggering, gathering files,
routing failures, delivering, and holding the human decision — and calls out to FastAPI for the
document work. The same split is used in the
[Internal Audit Report Drafter](../iard-audit-report-drafter), where a `python-docx` service
renders the Word report.

---

## Before reusing this

- Replace all 20 `REPLACE_DRIVE_ID_*` placeholders with your own Drive file IDs.
- Point `https://YOUR-RCM-SERVICE-HOST` at your service. The original ran through an ngrok tunnel,
  which is fine for a pilot and should be a stable host for anything beyond that.
- Create the runs data table with the columns in `Record Run` plus `approval_notes` and
  `approval_timestamp`, and set `REPLACE_WITH_YOUR_DATA_TABLE_ID` in both data-table nodes.
- The 20 Drive downloads run **sequentially**, each waiting on the last. They are independent and
  could fan out in parallel; chaining them costs real wall-clock time on every submission.
- `process_type` is read from the form (`$json.process_type`) but there is no `process_type` field
  on the form, so it posts empty. Either add the field or drop the parameter.

## Stack

**n8n** (form trigger, Wait/Switch polling loop, send-and-wait, data tables) ·
**FastAPI** (RCM generation service, async job API) · **Google Drive** (standing corpus) ·
**Gmail** (delivery, failure alerts, approval capture)
