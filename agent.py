"""Claude-powered agent that interprets task prompts and executes Tripletex API calls."""

import json
import logging
from datetime import date

import anthropic

from tools import TOOLS
from tripletex_client import TripletexClient

logger = logging.getLogger(__name__)

MODEL = "claude-opus-4-6"
MAX_TOKENS = 4096
MAX_ITERATIONS = 12  # Safety cap — prevents runaway loops
MAX_CONSECUTIVE_ERRORS = 3  # Give up if this many tool calls in a row all fail

SYSTEM_PROMPT = """You are an expert accounting assistant that completes tasks in Tripletex (a Norwegian accounting system).

You receive task descriptions in one of 7 languages (Norwegian, English, Spanish, Portuguese, Nynorsk, German, French).
Always understand the task regardless of language.

## Your approach
1. Read the task carefully and identify exactly what needs to be done
2. Plan the minimal sequence of API calls required — think before acting
3. Execute the plan precisely using the available tools
4. Each tool call should be purposeful — no exploratory or redundant calls
5. If you create something, you know its ID from the response — don't re-fetch it

## Key rules
- Minimise API calls — every unnecessary call reduces your score
- Avoid 4xx errors — validate your understanding of required fields before calling
- If a task says "create X for customer Y", first look up customer Y (list_customers), then create X
- Dates are always YYYY-MM-DD format. Today is {today}
- For invoicing: use invoice_order (one call) instead of create_invoice (two calls)
- For employee admin roles: set userType=EXTENDED when creating, then use grant_entitlements_by_template with ALL_PRIVILEGES
- grant_entitlement_template is for giving employees access to a CLIENT company (accountant firms) — rarely needed
- For company's own customer ID (needed for grant_entitlement_template): use get_company_info
- For payroll/salary tasks: use list_salary_types to find the right wage code IDs first, then create_salary_transaction. Base salary is typically "fastlønn" or similar fixed monthly type. Bonus/tillegg is a separate specification line.
- For timesheet/hours logging: use list_activities first to find activity_id, then create_timesheet_entry
- For supplier tasks: use list_suppliers to check existence, create_supplier to create new ones

## Task completion
When all required actions are done, stop. Do not add unnecessary verification calls."""


def execute_tool(client: TripletexClient, tool_name: str, tool_input: dict) -> str:
    """Dispatch a tool call to the Tripletex client and return JSON result string."""
    try:
        match tool_name:

            # ── Employees ───────────────────────────────────────────────────
            case "list_employees":
                result = client.list_employees(**tool_input)

            case "create_employee":
                result = client.create_employee(tool_input)

            case "update_employee":
                employee_id = tool_input.pop("employee_id")
                fields = tool_input.pop("fields")
                current = client.get_employee(employee_id)
                current.update(fields)
                result = client.update_employee(employee_id, current)

            case "create_employment":
                employee_id = tool_input.pop("employee_id")
                payload = {"employee": {"id": employee_id}, **tool_input}
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
                payload = {"paymentTypeId": payment_type_id, **tool_input}
                result = client.register_payment(invoice_id, payload)

            case "create_credit_note":
                invoice_id = tool_input.pop("invoice_id")
                date = tool_input.pop("date")
                result = client.create_credit_note(invoice_id, date)

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

            case "add_travel_cost":
                expense_id = tool_input.pop("travel_expense_id")
                payload = {"travelExpense": {"id": expense_id}, **tool_input}
                result = client.add_travel_cost(payload)

            case "add_mileage_allowance":
                expense_id = tool_input.pop("travel_expense_id")
                payload = {"travelExpense": {"id": expense_id}, **tool_input}
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
                postings = []
                for p in postings_raw:
                    posting = {"date": p["date"], "amount": p["amount"]}
                    posting["account"] = {"id": p["account_id"]}
                    for fk, fv in [("customer_id", "customer"), ("employee_id", "employee"), ("project_id", "project")]:
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
                result = client.who_am_i()

            case "grant_entitlements_by_template":
                result = client.grant_entitlements_by_template(
                    employee_id=tool_input["employee_id"],
                    template=tool_input["template"],
                )

            case "enable_module":
                client.enable_module(tool_input["module_name"])
                result = {"enabled": True, "module": tool_input["module_name"]}

            case _:
                return f"Error: Unknown tool '{tool_name}'"

        return json.dumps(result, ensure_ascii=False, default=str)

    except Exception as e:
        logger.warning("Tool %s failed: %s", tool_name, e)
        return f"Error: {e}"


def run_agent(prompt: str, tripletex_client: TripletexClient, file_contents: list[dict]) -> None:
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

    consecutive_errors = 0

    for iteration in range(MAX_ITERATIONS):
        response = claude.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=system,
            tools=TOOLS,
            messages=messages,
            thinking={"type": "adaptive"},
        )

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
            result = execute_tool(tripletex_client, block.name, dict(block.input))
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
