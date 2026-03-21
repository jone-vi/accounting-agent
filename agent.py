"""Claude-powered agent that interprets task prompts and executes Tripletex API calls."""

import json
import logging
import time
from datetime import date

import anthropic

from tools import TOOLS
from tripletex_client import TripletexClient

logger = logging.getLogger(__name__)

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 8000
MAX_ITERATIONS = 12  # Safety cap — prevents runaway loops
MAX_CONSECUTIVE_ERRORS = 3  # Give up if this many tool calls in a row all fail

SYSTEM_PROMPT = """You are an expert accounting assistant that completes tasks in Tripletex (a Norwegian accounting system).

You receive task descriptions in one of 7 languages (Norwegian, English, Spanish, Portuguese, Nynorsk, German, French).
Always understand the task regardless of language.

## Your approach
Before making ANY API calls, output a short pre-flight analysis as plain text
in your first response. This costs nothing — it is in the same response turn as
your first tool calls. Format:

ENTITIES: [named entities from the task that need IDs — customer, employee, product…]
GIVEN:    [IDs or concrete values already stated in the task text]
LOOKUP:   [entities that need a list_X call to get their ID]
CREATE:   [entities that need to be created]
SEQUENCE: [ordered steps; mark parallel steps with | e.g. "1. list_customers | list_products → 2. create_order → 3. invoice_order"]

Then immediately issue your first tool calls in the same response.
Do NOT wait for a separate turn before acting.

4. When multiple independent lookups are needed, call both tools in the same
   response turn as the analysis. Do not wait for one before calling the other.
5. Each tool call should be purposeful — no exploratory or redundant calls.
6. If you create something, its ID is in the response — don't re-fetch it.

## Key rules
- Minimise API calls — every unnecessary call reduces your score
- Avoid 4xx errors — validate your understanding of required fields before calling
- If a task says "create X for customer Y", first look up customer Y (list_customers), then create X
- Dates are always YYYY-MM-DD format. Today is {today}
- For invoicing: use invoice_order (one call) instead of create_invoice (two calls)
- For employee admin roles: set userType=EXTENDED when creating, then use grant_entitlements_by_template with ALL_PRIVILEGES
- grant_entitlement_template is for giving employees access to a CLIENT company (accountant firms) — rarely needed
- For company's own customer ID (needed for grant_entitlement_template): use get_company_info
- For payroll/salary tasks: use list_salary_types to find the right wage code IDs first, then create_salary_transaction. Base salary is typically "fastlønn" or similar fixed monthly type (search name='fastlønn'). Bonus/tillegg is a separate specification line. year and month come from the task — use the current month if not specified. count=1, rate=<monthly_amount> for monthly base salary. Do NOT use list_accounts or create_voucher for payroll — that is wrong.
- For payment registration: if the task states the exact invoice amount, pass it directly. If the amount is unclear or only the product price (ex VAT) is known, call list_invoices first to get the exact outstanding amount field before calling register_payment.
- For timesheet/hours logging: use list_activities first to find activity_id, then create_timesheet_entry. The timesheet date must be >= the project's startDate — if project starts in the future, use the project startDate as the timesheet date.
- For travel expenses: always include travelDetails (departureFrom + destination) in create_travel_expense. For add_mileage_allowance always pass rateCategory_id=120 (standard domestic car). For add_travel_cost always pass paymentType_id (call list_travel_payment_types first with showOnTravelExpenses=true).
- For create_project: only set projectManager_id if you know the employee has project manager privileges. If unsure, omit it — otherwise API returns 422.
- For employee onboarding with salary/hours: pass percentageOfFullTimeEquivalent, annualSalary, employmentType, remunerationType, workingHoursScheme directly to create_employment — it sets employment details automatically in one call. Use NOT_SHIFT (not NOT_SHIFT_WORK) for workingHoursScheme, MONTHLY_WAGE for remunerationType.
- Always pass department_id, nationalIdentityNumber, and all other known fields directly to create_employee — do NOT use update_employee afterwards to add fields you already knew at creation time.
- When creating an employee who will also get create_employment: ALWAYS include dateOfBirth in create_employee (use '1990-01-01' as placeholder if not given) — create_employment requires it and will 422 without it.
- For supplier tasks: use list_suppliers to check existence, create_supplier to create new ones
- For credit notes: always pass today's date ({today}) as the date parameter to create_credit_note
- For update_employee with department change: pass department_id as a flat integer in the fields dict — it is auto-converted. Do NOT wrap it as {{"department": {{"id": ...}}}} yourself.
- Do NOT call enable_module unless a prior tool call returned an explicit "module not enabled" error — all sandbox modules are pre-enabled. Calling it speculatively wastes iterations and returns errors.
- For voucher postings to accounts payable (account 2400): MUST include supplier_id on that posting, otherwise API returns 422 "Leverandør mangler"
- For create_order: if you include orderLines in the create_order call, do NOT call add_order_line separately for those same lines. Using both creates duplicate lines on the order.

## Handling errors
If a tool returns an error:
- Read the error message carefully — it usually states exactly what is wrong (missing field, wrong value, etc.)
- Fix that specific issue and retry once
- Do NOT retry with the same parameters, and do NOT try unrelated workarounds
- If the error persists after one corrected attempt, stop — do not loop
- If invoice_order fails with "bankkontonummer": this is handled automatically by the client — it will register a bank account and retry. You do not need to do anything.

## Task completion
When the required action succeeds, stop immediately:
- Create/update tasks: done on 2xx response — the response IS the confirmation
- Invoice tasks: done when invoice_order succeeds, OR when order is created and invoicing is blocked by a bank account error (report the order_id and stop)
- Payment tasks: done when register_payment succeeds
- Payroll tasks: done when create_salary_transaction succeeds
NEVER call list_X or get_X after creating/updating just to confirm it worked.
NEVER re-fetch an entity whose ID you already have from a prior response.

## Session memory
Call record_session_note in the SAME response turn as your last real tool call (not after).
Save facts that help future tasks skip redundant lookups:
- Salary type IDs (e.g. "salary type 'fastlønn' has id=100")
- Department IDs (e.g. "default department has id=42")
- Frequently used customer/supplier/employee IDs
Only record confirmed facts from API responses — never guesses."""


_MAX_LIST_ITEMS = 30  # Truncate list results longer than this to reduce context size


def _truncate_result(result: str) -> str:
    """Cap large JSON list results to avoid blowing up context with huge account/employee lists."""
    try:
        data = json.loads(result)
        if isinstance(data, list) and len(data) > _MAX_LIST_ITEMS:
            omitted = len(data) - _MAX_LIST_ITEMS
            truncated = json.dumps(data[:_MAX_LIST_ITEMS], ensure_ascii=False, default=str)
            return truncated[:-1] + f', {{"_truncated": "{omitted} more items omitted"}}]'
    except Exception:
        pass
    return result


def execute_tool(client: TripletexClient, tool_name: str, tool_input: dict, session_notes: list[str] | None = None) -> str:
    """Dispatch a tool call to the Tripletex client and return JSON result string."""
    try:
        match tool_name:

            # ── Employees ───────────────────────────────────────────────────
            case "list_employees":
                result = client.list_employees(**tool_input)

            case "create_employee":
                dept_id = tool_input.pop("department_id", None)
                if dept_id:
                    tool_input["department"] = {"id": dept_id}
                result = client.create_employee(tool_input)

            case "update_employee":
                employee_id = tool_input.pop("employee_id")
                fields = tool_input.pop("fields")
                # Transform flat foreign keys to nested objects expected by the API
                if "department_id" in fields:
                    fields["department"] = {"id": fields.pop("department_id")}
                current = client.get_employee(employee_id)
                current.update(fields)
                updated = client.update_employee(employee_id, current)
                result = {"id": updated["id"], "version": updated["version"], "updated_fields": list(fields.keys())}

            case "list_occupation_codes":
                result = client.list_occupation_codes(**tool_input)

            case "create_employment":
                employee_id = tool_input.pop("employee_id")
                occ_id = tool_input.pop("occupationCode_id", None)
                payload = {"employee": {"id": employee_id}, **tool_input}
                if occ_id:
                    payload["occupationCode"] = {"id": occ_id}
                result = client.create_employment(payload)

            case "grant_entitlement_template":
                result = client.grant_entitlement_template(
                    employee_id=tool_input["employee_id"],
                    customer_id=tool_input["customer_id"],
                    template=tool_input["template"],
                )

            # ── Customers ───────────────────────────────────────────────────
            case "list_customers":
                result = client.list_customers(**tool_input)

            case "create_customer":
                result = client.create_customer(tool_input)

            case "update_customer":
                customer_id = tool_input.pop("customer_id")
                fields = tool_input.pop("fields")
                current = client.get_customer(customer_id)
                current.update(fields)
                result = client.update_customer(customer_id, current)

            # ── Products ────────────────────────────────────────────────────
            case "list_products":
                result = client.list_products(**tool_input)

            case "create_product":
                result = client.create_product(tool_input)

            # ── Orders ──────────────────────────────────────────────────────
            case "create_order":
                customer_id = tool_input.pop("customer_id")
                order_lines_raw = tool_input.pop("orderLines", [])
                order_lines = []
                for line in order_lines_raw:
                    ol = {k: v for k, v in line.items() if k != "product_id"}
                    if "product_id" in line:
                        ol["product"] = {"id": line["product_id"]}
                    order_lines.append(ol)
                payload = {
                    "customer": {"id": customer_id},
                    "orderLines": order_lines,
                    **tool_input,
                }
                result = client.create_order(payload)

            case "invoice_order":
                order_id = tool_input.pop("order_id")
                result = client.invoice_order(order_id, params=tool_input)

            case "add_order_line":
                order_id = tool_input.pop("order_id")
                product_id = tool_input.pop("product_id", None)
                payload = {"order": {"id": order_id}, **tool_input}
                if product_id:
                    payload["product"] = {"id": product_id}
                result = client.add_order_line(payload)

            # ── Invoices ────────────────────────────────────────────────────
            case "list_invoices":
                result = client.list_invoices(**tool_input)

            case "send_invoice":
                invoice_id = tool_input.pop("invoice_id")
                send_type = tool_input.pop("sendType")
                override_email = tool_input.pop("overrideEmailAddress", None)
                result = client.send_invoice(invoice_id, send_type, override_email)

            case "register_payment":
                invoice_id = tool_input.pop("invoice_id")
                payment_type_id = tool_input.pop("paymentTypeId", 1)
                amount = tool_input.pop("amount", None)
                payload = {"paymentTypeId": payment_type_id, **tool_input}
                if amount is not None:
                    payload["paidAmount"] = amount
                result = client.register_payment(invoice_id, payload)

            case "create_credit_note":
                invoice_id = tool_input.pop("invoice_id")
                credit_date = tool_input.pop("date", None) or date.today().isoformat()
                result = client.create_credit_note(invoice_id, credit_date)

            # ── Projects ────────────────────────────────────────────────────
            case "list_projects":
                result = client.list_projects(**tool_input)

            case "create_project":
                customer_id = tool_input.pop("customer_id", None)
                manager_id = tool_input.pop("projectManager_id", None)
                payload = {**tool_input}
                if customer_id:
                    payload["customer"] = {"id": customer_id}
                if manager_id:
                    payload["projectManager"] = {"id": manager_id}
                result = client.create_project(payload)

            case "add_project_participant":
                project_id = tool_input.pop("project_id")
                employee_id = tool_input.pop("employee_id")
                payload = {
                    "project": {"id": project_id},
                    "employee": {"id": employee_id},
                    **tool_input,
                }
                result = client.add_project_participant(payload)

            # ── Departments ─────────────────────────────────────────────────
            case "list_departments":
                result = client.list_departments()

            case "create_department":
                manager_id = tool_input.pop("departmentManager", {}).get("id") if isinstance(tool_input.get("departmentManager"), dict) else None
                payload = {k: v for k, v in tool_input.items() if k != "departmentManager"}
                if manager_id:
                    payload["departmentManager"] = {"id": manager_id}
                result = client.create_department(payload)

            # ── Travel Expenses ─────────────────────────────────────────────
            case "list_travel_expenses":
                result = client.list_travel_expenses(**tool_input)

            case "create_travel_expense":
                employee_id = tool_input.pop("employee_id")
                project_id = tool_input.pop("project_id", None)
                payload = {"employee": {"id": employee_id}, **tool_input}
                if project_id:
                    payload["project"] = {"id": project_id}
                result = client.create_travel_expense(payload)

            case "list_travel_payment_types":
                result = client.list_travel_payment_types(**tool_input)

            case "add_travel_cost":
                expense_id = tool_input.pop("travel_expense_id")
                payment_type_id = tool_input.pop("paymentType_id", None)
                payload = {"travelExpense": {"id": expense_id}, **tool_input}
                if payment_type_id:
                    payload["paymentType"] = {"id": payment_type_id}
                result = client.add_travel_cost(payload)

            case "add_mileage_allowance":
                expense_id = tool_input.pop("travel_expense_id")
                rate_category_id = tool_input.pop("rateCategory_id", None)
                payload = {"travelExpense": {"id": expense_id}, **tool_input}
                if rate_category_id:
                    payload["rateCategory"] = {"id": rate_category_id}
                result = client.add_mileage_allowance(payload)

            case "add_per_diem_compensation":
                expense_id = tool_input.pop("travel_expense_id")
                payload = {"travelExpense": {"id": expense_id}, **tool_input}
                result = client.add_per_diem_compensation(payload)

            case "deliver_travel_expense":
                result = client.deliver_travel_expense(tool_input["travel_expense_id"])

            case "delete_travel_expense":
                client.delete_travel_expense(tool_input["travel_expense_id"])
                result = {"deleted": True, "id": tool_input["travel_expense_id"]}

            # ── Vouchers / Corrections ──────────────────────────────────────
            case "list_vouchers":
                result = client.list_vouchers(**tool_input)

            case "create_voucher":
                postings_raw = tool_input.pop("postings", [])
                # Pre-flight: catch missing supplier_id on account-2400 postings early
                accounts_needing_supplier = {p["account_id"] for p in postings_raw if "supplier_id" not in p}
                if accounts_needing_supplier:
                    resolved = client.list_accounts(numberFrom=2400, numberTo=2400)
                    ap_ids = {a["id"] for a in resolved if a.get("number") == 2400}
                    missing = accounts_needing_supplier & ap_ids
                    if missing:
                        return (
                            "Error: One or more postings use account 2400 (Leverandørgjeld) but are "
                            "missing supplier_id. Add supplier_id to every posting that targets account 2400. "
                            "Example posting: {\"account_id\": <2400_id>, \"supplier_id\": <supplier_id>, ...}"
                        )
                postings = []
                for i, p in enumerate(postings_raw):
                    posting = {"row": i + 1, "date": p["date"], "amount": p["amount"]}
                    posting["account"] = {"id": p["account_id"]}
                    for fk, fv in [("supplier_id", "supplier"), ("customer_id", "customer"), ("employee_id", "employee"), ("project_id", "project"), ("department_id", "department")]:
                        if fk in p:
                            posting[fv] = {"id": p[fk]}
                    if "description" in p:
                        posting["description"] = p["description"]
                    postings.append(posting)
                payload = {"postings": postings, **tool_input}
                result = client.create_voucher(payload)

            case "reverse_voucher":
                result = client.reverse_voucher(tool_input["voucher_id"], tool_input["date"])

            case "list_accounts":
                result = client.list_accounts(**tool_input)

            # ── Salary / Payroll ────────────────────────────────────────────
            case "list_salary_types":
                result = client.list_salary_types(**tool_input)

            case "create_salary_transaction":
                year = tool_input["year"]
                month = tool_input["month"]
                payslips_raw = tool_input["payslips"]
                payslips = []
                for ps in payslips_raw:
                    specs = []
                    for s in ps.get("specifications", []):
                        spec = {
                            "salaryType": {"id": s["salary_type_id"]},
                            "rate": s["rate"],
                            "count": s["count"],
                        }
                        if "description" in s:
                            spec["description"] = s["description"]
                        specs.append(spec)
                    payslips.append({
                        "employee": {"id": ps["employee_id"]},
                        "specifications": specs,
                    })
                result = client.create_salary_transaction({
                    "year": year,
                    "month": month,
                    "payslips": payslips,
                })

            case "list_payslips":
                result = client.list_payslips(**tool_input)

            # ── Suppliers ───────────────────────────────────────────────────
            case "list_suppliers":
                result = client.list_suppliers(**tool_input)

            case "create_supplier":
                result = client.create_supplier(tool_input)

            # ── Timesheet / Activities ───────────────────────────────────────
            case "list_activities":
                result = client.list_activities(**tool_input)

            case "create_timesheet_entry":
                employee_id = tool_input.pop("employee_id")
                activity_id = tool_input.pop("activity_id")
                project_id = tool_input.pop("project_id", None)
                payload = {
                    "employee": {"id": employee_id},
                    "activity": {"id": activity_id},
                    **tool_input,
                }
                if project_id:
                    payload["project"] = {"id": project_id}
                result = client.create_timesheet_entry(payload)

            # ── Company / Modules ───────────────────────────────────────────
            case "get_company_info":
                result = client.get_company()

            case "grant_entitlements_by_template":
                result = client.grant_entitlements_by_template(
                    employee_id=tool_input["employee_id"],
                    template=tool_input["template"],
                )

            case "enable_module":
                client.enable_module(tool_input["module_name"])
                result = {"enabled": True, "module": tool_input["module_name"]}

            case "record_session_note":
                note = tool_input.get("note", "").strip()
                if note and session_notes is not None:
                    session_notes.append(note)
                    result = {"recorded": True, "note": note, "total_notes": len(session_notes)}
                else:
                    result = {"recorded": False}

            case _:
                return f"Error: Unknown tool '{tool_name}'"

        return _truncate_result(json.dumps(result, ensure_ascii=False, default=str))

    except Exception as e:
        logger.warning("Tool %s failed: %s", tool_name, e)
        return f"Error: {e}"


def run_agent(prompt: str, tripletex_client: TripletexClient, file_contents: list[dict], session_notes: list[str] | None = None) -> None:
    """Run the agent loop until the task is complete."""
    claude = anthropic.Anthropic()

    user_content: list = []

    for f in file_contents:
        if f["media_type"] == "application/pdf":
            user_content.append({
                "type": "document",
                "source": {"type": "base64", "media_type": "application/pdf", "data": f["data"]},
                "title": f.get("filename", "attachment"),
            })
        elif f["media_type"].startswith("image/"):
            user_content.append({
                "type": "image",
                "source": {"type": "base64", "media_type": f["media_type"], "data": f["data"]},
            })

    user_content.append({"type": "text", "text": prompt})

    messages = [{"role": "user", "content": user_content}]
    system = SYSTEM_PROMPT.format(today=date.today().isoformat())

    if session_notes:
        notes_block = "\n".join(f"- {n}" for n in session_notes)
        system += (
            "\n\n## Session memory (facts from prior tasks in this sandbox)\n"
            "These were recorded during earlier tasks. Trust them — do not re-fetch these IDs.\n"
            + notes_block
        )

    consecutive_errors = 0

    for iteration in range(MAX_ITERATIONS):
        for attempt in range(4):
            try:
                response = claude.messages.create(
                    model=MODEL,
                    max_tokens=MAX_TOKENS,
                    system=system,
                    tools=TOOLS,
                    messages=messages,
                    thinking={"type": "adaptive"},
                )
                break
            except (anthropic.RateLimitError, anthropic.APIStatusError) as e:
                if attempt == 3:
                    raise
                wait = 30 * (attempt + 1)
                logger.warning("Anthropic API error (%s), retrying in %ds", e.__class__.__name__, wait)
                time.sleep(wait)

        logger.info("Iteration %d: stop_reason=%s, blocks=%d", iteration, response.stop_reason, len(response.content))
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            break

        if response.stop_reason != "tool_use":
            logger.warning("Unexpected stop_reason: %s", response.stop_reason)
            break

        tool_results = []
        iteration_had_error = False
        for block in response.content:
            if block.type != "tool_use":
                continue
            logger.info("Calling tool: %s(%s)", block.name, json.dumps(block.input)[:200])
            result = execute_tool(tripletex_client, block.name, dict(block.input), session_notes)
            logger.info("Result: %s", result[:300])
            if result.startswith("Error:"):
                iteration_had_error = True
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": result,
            })

        if iteration_had_error:
            consecutive_errors += 1
            if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                logger.warning("Giving up after %d consecutive error iterations", consecutive_errors)
                break
        else:
            consecutive_errors = 0

        messages.append({"role": "user", "content": tool_results})

    else:
        logger.warning("Reached max iterations (%d) without completion", MAX_ITERATIONS)
