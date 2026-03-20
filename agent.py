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
MAX_ITERATIONS = 20  # Safety cap — prevents runaway loops

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
- If a task says "create X for customer Y", first look up customer Y, then create X
- Dates are always YYYY-MM-DD format
- Today's date is {today}

## Task completion
When all required actions are done, stop. Do not add unnecessary verification calls."""


def execute_tool(client: TripletexClient, tool_name: str, tool_input: dict) -> str:
    """Execute a tool call and return the result as a string."""
    try:
        match tool_name:
            case "list_employees":
                result = client.list_employees(**tool_input)
            case "create_employee":
                result = client.create_employee(tool_input)
            case "update_employee":
                employee_id = tool_input.pop("employee_id")
                fields = tool_input.pop("fields")
                # Fetch current employee first to get version, then merge
                current = client.get_employee(employee_id)
                current.update(fields)
                result = client.update_employee(employee_id, current)
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
            case "list_products":
                result = client.list_products(**tool_input)
            case "create_product":
                result = client.create_product(tool_input)
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
            case "create_invoice":
                order_id = tool_input.pop("order_id")
                payload = {
                    "orders": [{"id": order_id}],
                    **tool_input,
                }
                result = client.create_invoice(payload)
            case "list_invoices":
                result = client.list_invoices(**tool_input)
            case "register_payment":
                invoice_id = tool_input.pop("invoice_id")
                payment_type_id = tool_input.pop("paymentTypeId", 1)
                payload = {
                    "paymentTypeId": payment_type_id,
                    **tool_input,
                }
                result = client.register_payment(invoice_id, payload)
            case "create_credit_note":
                invoice_id = tool_input.pop("invoice_id")
                result = client.create_credit_note(invoice_id)
            case "list_projects":
                result = client.list_projects(**tool_input)
            case "create_project":
                customer_id = tool_input.pop("customer_id", None)
                payload = {**tool_input}
                if customer_id:
                    payload["customer"] = {"id": customer_id}
                result = client.create_project(payload)
            case "list_departments":
                result = client.list_departments()
            case "create_department":
                result = client.create_department(tool_input)
            case "list_travel_expenses":
                result = client.list_travel_expenses(**tool_input)
            case "create_travel_expense":
                employee_id = tool_input.pop("employee_id")
                payload = {"employee": {"id": employee_id}, **tool_input}
                result = client.create_travel_expense(payload)
            case "delete_travel_expense":
                expense_id = tool_input.pop("expense_id")
                client.delete_travel_expense(expense_id)
                result = {"deleted": True, "id": expense_id}
            case "enable_module":
                module_name = tool_input["module_name"]
                client.enable_module(module_name)
                result = {"enabled": True, "module": module_name}
            case _:
                return f"Error: Unknown tool '{tool_name}'"

        return json.dumps(result, ensure_ascii=False)

    except Exception as e:
        logger.warning("Tool %s failed: %s", tool_name, e)
        return f"Error: {e}"


def run_agent(prompt: str, tripletex_client: TripletexClient, file_contents: list[dict]) -> None:
    """Run the agent loop until the task is complete."""
    claude = anthropic.Anthropic()

    # Build user message — include file info if present
    user_content: list = []

    if file_contents:
        for f in file_contents:
            if f["media_type"] == "application/pdf":
                user_content.append({
                    "type": "document",
                    "source": {
                        "type": "base64",
                        "media_type": "application/pdf",
                        "data": f["data"],
                    },
                    "title": f.get("filename", "attachment"),
                })
            elif f["media_type"].startswith("image/"):
                user_content.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": f["media_type"],
                        "data": f["data"],
                    },
                })

    user_content.append({"type": "text", "text": prompt})

    messages = [{"role": "user", "content": user_content}]

    system = SYSTEM_PROMPT.format(today=date.today().isoformat())

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

        # Append assistant response to history
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            break

        if response.stop_reason != "tool_use":
            logger.warning("Unexpected stop_reason: %s", response.stop_reason)
            break

        # Execute all tool calls
        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            logger.info("Calling tool: %s(%s)", block.name, json.dumps(block.input)[:200])
            result = execute_tool(tripletex_client, block.name, dict(block.input))
            logger.info("Result: %s", result[:300])
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": result,
            })

        messages.append({"role": "user", "content": tool_results})

    else:
        logger.warning("Reached max iterations (%d) without completion", MAX_ITERATIONS)
