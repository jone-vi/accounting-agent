# Accounting Agent — CLAUDE.md

This is a competition entry for **NM i AI** (Norwegian AI Championship). The agent receives natural language task prompts (in up to 7 languages) and completes accounting tasks in Tripletex via its REST API. It is scored on **correctness** (field-level accuracy × tier multiplier) and **efficiency** (fewer API calls + zero 4xx errors = higher score).

---

## Architecture

```
POST /solve  →  main.py  →  agent.py (agentic loop)  →  tripletex_client.py  →  Tripletex REST API
```

### Files

| File | Purpose |
|---|---|
| `main.py` | FastAPI server. Single `/solve` endpoint + `/health`. Decodes base64 files, builds `TripletexClient`, calls `run_agent`. Always returns HTTP 200 (errors are in body). |
| `agent.py` | Core agentic loop. Uses `claude-opus-4-6` with `thinking={"type":"adaptive"}`. Dispatches all 36 tools via `execute_tool()` match/case. `MAX_ITERATIONS=20`. |
| `tripletex_client.py` | Thin HTTP wrapper around Tripletex REST API. Logs every request/response. `_raise_with_body` includes full response body in exceptions so Claude sees the error detail. |
| `tools.py` | 36 tool definitions verified against `tripletexapi.json`. Descriptions include required fields, valid enums, and guidance to avoid 4xx errors. |
| `lookup_api.py` | Dev utility: look up schemas, endpoints, and enums from `tripletexapi.json`. |
| `test_prompts.sh` | 18 local test cases covering Tier 1/2 tasks, multilingual prompts, and corrections. |
| `tripletexapi.json` | Tripletex OpenAPI spec (546 paths). Not committed to git — gitignored. Used only for reference. |

---

## Running Locally

```bash
# Requires .env with ANTHROPIC_API_KEY
ANTHROPIC_API_KEY=$(grep ANTHROPIC_API_KEY .env | cut -d= -f2-) python3 main.py

# Test a single case
bash test_prompts.sh create_employee

# Run all tests
bash test_prompts.sh all

# Look up an API schema
python3 lookup_api.py Employee
python3 lookup_api.py /employee post
python3 lookup_api.py enums TravelExpense
```

The server starts on port 8000 (local) or `$PORT` (Cloud Run, defaults to 8080).

---

## Request Format

```json
POST /solve
{
  "prompt": "Create an employee named Kari Hansen...",
  "files": [],
  "tripletex_credentials": {
    "base_url": "https://<sandbox>.tripletex.dev/v2",
    "session_token": "<token>"
  }
}
```

Files are base64-encoded PDFs or images. The agent passes them to Claude as document/image blocks before the prompt text.

---

## Tripletex API Auth

Basic Auth: username `"0"`, password = `session_token`. Set per request, comes from the request body — never stored anywhere.

---

## Tool Coverage (43 tools)

**Employees:** `list_employees`, `create_employee`, `update_employee`, `create_employment`, `grant_entitlements_by_template`, `grant_entitlement_template`

**Customers:** `list_customers`, `create_customer`, `update_customer`

**Suppliers:** `list_suppliers`, `create_supplier`

**Products:** `list_products`, `create_product`

**Orders/Invoices:** `create_order`, `invoice_order`, `add_order_line`, `list_invoices`, `send_invoice`, `register_payment`, `create_credit_note`

**Projects:** `list_projects`, `create_project`, `add_project_participant`

**Departments:** `list_departments`, `create_department`

**Travel Expenses:** `list_travel_expenses`, `create_travel_expense`, `add_travel_cost`, `add_mileage_allowance`, `add_per_diem_compensation`, `deliver_travel_expense`, `delete_travel_expense`

**Salary/Payroll:** `list_salary_types`, `create_salary_transaction`, `list_payslips`

**Timesheet:** `list_activities`, `create_timesheet_entry`

**Vouchers/Ledger:** `list_vouchers`, `create_voucher`, `reverse_voucher`, `list_accounts`

**Company:** `get_company_info`, `enable_module`

---

## Known Behaviours and Gotchas

### `create_employment` also sets employment details in one call
`create_employment` automatically posts to `/employee/employment/details` after creating the employment if any detail fields are provided. Pass `percentageOfFullTimeEquivalent`, `annualSalary`, `employmentType`, `remunerationType`, `workingHoursScheme` directly to `create_employment` — do **not** call a separate tool for employment details. Correct enum values: `workingHoursScheme` uses `NOT_SHIFT` (not `NOT_SHIFT_WORK`); `remunerationType` uses `COMMISION_PERCENTAGE` / `FEE` (not `PAID_ON_COMMISSION` / `FEE_EARNED`).

### Employee creation requires `userType`
Always required. Valid values: `STANDARD`, `EXTENDED`, `NO_ACCESS`. The sandbox rejects with 422 "Brukertype kan ikke være '0' eller tom" if omitted.

### Employee creation auto-injects department
`TripletexClient.create_employee` calls `_default_department_id()` to auto-fetch and inject the first available department ID if not provided. Required because the sandbox has the department module enabled.

### Admin roles — use `grant_entitlements_by_template`
For giving an employee admin access within the **same company**: set `userType=EXTENDED` on create, then call `grant_entitlements_by_template` with `ALL_PRIVILEGES`. This calls `PUT /employee/entitlement/:grantEntitlementsByTemplate` — no `customerId` needed.

`grant_entitlement_template` (the other tool) is for accountant firms granting an employee access to a **client** company — rarely needed.

### `get_company_info` uses whoAmI
`GET /company` only supports PUT in the API spec. `get_company_info` calls `GET /token/session/>whoAmI` which returns `employeeId` and `companyId`. If you need the company's actual record, it then calls `GET /company/{companyId}`.

### Invoice flow
Use `invoice_order` (one PUT call) — not a two-step `create_invoice`. The system prompt explicitly tells Claude this.

### `vatType` on products
Do not guess a `vatType` ID — Tripletex will use the company default. Passing a wrong ID causes 422 "Ugyldig mva-kode".

### Duplicate entities
The sandbox persists across test runs. If an entity already exists (e.g. same email), Claude receives a 422 with the full error body and should recover by listing the existing entity instead.

---

## Scoring Guidance (Competition)

- **Minimise API calls** — each unnecessary call reduces efficiency score
- **Avoid 4xx errors** — every error costs points
- **Don't re-fetch** — if you created something, its ID is in the response
- **Don't verify** — don't make extra GET calls just to confirm creation succeeded
- Claude is instructed via system prompt to plan before acting and stop immediately when done

---

## Deployment (Google Cloud Run)

- Linked to this GitHub repo via Cloud Run trigger
- `ANTHROPIC_API_KEY` stored in **Google Secret Manager**, mounted as env var at runtime
- Tripletex credentials come in the request body per submission — never stored
- `Dockerfile`: Python 3.12-slim, `ENV PORT=8080`, runs `python main.py`
- `.dockerignore` and `.gitignore` both exclude: `.env`, `tripletexapi.json`, `.claude/`

---

## Retrieving Cloud Run Logs

```bash
# Tail recent logs (excluding health checks)
gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="accounting-agent"' \
  --limit=200 --format="value(timestamp, textPayload)" --order=asc | grep -v "GET /health"

# Logs for a specific time window (UTC)
gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="accounting-agent" AND timestamp>="2026-03-20T21:10:00Z" AND timestamp<="2026-03-20T21:15:00Z"' \
  --limit=500 --format="value(timestamp, textPayload)" --order=asc | grep -v "GET /health"

# Filter to just agent actions and errors
... | grep -E "(Received task|Calling tool|Result:|ERROR|error|failed|→ POST|→ PUT|→ GET|✓|✗)"
```

Note: UI timestamps are CET (UTC+1). Convert to UTC when filtering (`22:12 CET` → `21:12 UTC`).

---

## Development Utilities

### Improve a failing tool
1. Run `bash test_prompts.sh <test_name>` and check server logs for the 4xx body
2. Run `python3 lookup_api.py <SchemaName>` to check correct fields/enums
3. Update the tool description in `tools.py` and/or the method in `tripletex_client.py`
4. Re-run the test

### Add a new tool
1. Add a method to `TripletexClient` in `tripletex_client.py`
2. Add a case to `execute_tool()` in `agent.py`
3. Add a tool definition dict to `TOOLS` in `tools.py`
4. Add a test case to `test_prompts.sh`
