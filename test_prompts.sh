#!/bin/bash
# Local test prompts for the Tripletex accounting agent.
# Usage: bash test_prompts.sh [test_name]
# Example: bash test_prompts.sh create_employee
# Run all: bash test_prompts.sh all

BASE_URL="http://localhost:8000/solve"
TRIPLETEX_URL="https://kkpqfuj-amager.tripletex.dev/v2"
TOKEN="eyJ0b2tlbklkIjoyMTQ3NjMyODA3LCJ0b2tlbiI6IjI1YmJjMTYyLTJkODctNDdjZi1iODI4LWFiMGI0M2JiOGRlMCJ9"

CREDS='"tripletex_credentials": {"base_url": "'"$TRIPLETEX_URL"'", "session_token": "'"$TOKEN"'"}'

run() {
  local name="$1"
  local prompt="$2"
  echo ""
  echo "════════════════════════════════════════"
  echo "  TEST: $name"
  echo "════════════════════════════════════════"
  curl -s -X POST "$BASE_URL" \
    -H "Content-Type: application/json" \
    -d "{\"prompt\": \"$prompt\", \"files\": [], $CREDS}" | python3 -m json.tool
  echo ""
}

# ── Tier 1: Basic entity creation ─────────────────────────────────────────────

test_create_employee() {
  run "create_employee" \
    "Create an employee named Kari Hansen with email kari.hansen@example.no and phone 91234567"
}

test_create_employee_admin() {
  run "create_employee_admin" \
    "Create an employee named Lars Eriksen with email lars@example.no. Assign administrator role."
}

test_create_customer() {
  run "create_customer" \
    "Register a new customer called Bergström AS with email post@bergstrom.no and phone 22334455"
}

test_create_customer_private() {
  run "create_customer_private" \
    "Create a private customer named Per Olsen with email per.olsen@gmail.com"
}

test_create_product() {
  run "create_product" \
    "Create a product called Konsulenttime with product number KT-01 and price 1200 NOK excluding VAT"
}

test_create_department() {
  run "create_department" \
    "Create a new department called Salg og marked with department number 10"
}

# ── Tier 1: Invoice flow ───────────────────────────────────────────────────────

test_create_invoice() {
  run "create_invoice" \
    "Create an invoice for customer Bergström AS for 5 units of Konsulenttime at 1200 NOK each. Invoice date today."
}

test_create_invoice_english() {
  run "create_invoice_english" \
    "Create an invoice for customer Bergström AS. Add a line item: 3 hours of consulting at 1500 NOK per hour. Set invoice date to today and due date 30 days from now."
}

# ── Tier 1: Payment ────────────────────────────────────────────────────────────

test_register_payment() {
  run "register_payment" \
    "Register a payment of 6000 NOK for the latest invoice for customer Bergström AS. Payment date today."
}

# ── Tier 2: Credit note ────────────────────────────────────────────────────────

test_credit_note() {
  run "credit_note" \
    "Create a credit note for the latest invoice issued to Bergström AS"
}

# ── Tier 2: Project ────────────────────────────────────────────────────────────

test_create_project() {
  run "create_project" \
    "Create a project called Nettsideprosjekt 2026 linked to customer Bergström AS. Start date 2026-04-01, end date 2026-12-31."
}

test_create_project_with_participant() {
  run "create_project_with_participant" \
    "Create an internal project called Internopplæring Q2. Add employee Kari Hansen as a project participant."
}

# ── Tier 2: Travel expense ────────────────────────────────────────────────────

test_create_travel_expense() {
  run "create_travel_expense" \
    "Register a travel expense for employee Kari Hansen. Trip title: Kundemøte Oslo. Travel date 2026-03-25. Add mileage of 120 km from Bergen to Oslo."
}

test_delete_travel_expense() {
  run "delete_travel_expense" \
    "Delete the travel expense report titled Kundemøte Oslo for employee Kari Hansen"
}

# ── Multilingual tests ────────────────────────────────────────────────────────

test_norwegian_nynorsk() {
  run "nynorsk" \
    "Opprett ein tilsett med namnet Bjørn Olsen og e-post bjorn.olsen@firma.no"
}

test_german() {
  run "german" \
    "Erstelle einen neuen Kunden mit dem Namen Müller GmbH und der E-Mail info@mueller.de"
}

test_spanish() {
  run "spanish" \
    "Crea un empleado llamado Carlos García con correo carlos@empresa.com"
}

# ── Correction / Tier 3 ───────────────────────────────────────────────────────

test_enable_module() {
  run "enable_module" \
    "Enable the department accounting module in Tripletex"
}

# ── Run target ────────────────────────────────────────────────────────────────

TARGET="${1:-help}"

case "$TARGET" in
  create_employee)           test_create_employee ;;
  create_employee_admin)     test_create_employee_admin ;;
  create_customer)           test_create_customer ;;
  create_customer_private)   test_create_customer_private ;;
  create_product)            test_create_product ;;
  create_department)         test_create_department ;;
  create_invoice)            test_create_invoice ;;
  create_invoice_english)    test_create_invoice_english ;;
  register_payment)          test_register_payment ;;
  credit_note)               test_credit_note ;;
  create_project)            test_create_project ;;
  create_project_participant) test_create_project_with_participant ;;
  create_travel_expense)     test_create_travel_expense ;;
  delete_travel_expense)     test_delete_travel_expense ;;
  nynorsk)                   test_norwegian_nynorsk ;;
  german)                    test_german ;;
  spanish)                   test_spanish ;;
  enable_module)             test_enable_module ;;
  all)
    test_create_employee
    test_create_employee_admin
    test_create_customer
    test_create_customer_private
    test_create_product
    test_create_department
    test_create_invoice
    test_register_payment
    test_credit_note
    test_create_project
    test_create_project_with_participant
    test_create_travel_expense
    test_delete_travel_expense
    test_norwegian_nynorsk
    test_german
    test_spanish
    ;;
  help|*)
    echo ""
    echo "Usage: bash test_prompts.sh <test_name>"
    echo ""
    echo "Available tests:"
    echo "  create_employee           Create a standard employee"
    echo "  create_employee_admin     Create an employee with admin role"
    echo "  create_customer           Create a business customer"
    echo "  create_customer_private   Create a private individual customer"
    echo "  create_product            Create a product with price"
    echo "  create_department         Create a department"
    echo "  create_invoice            Create an order + invoice"
    echo "  create_invoice_english    Same in English"
    echo "  register_payment          Register payment on an invoice"
    echo "  credit_note               Create a credit note"
    echo "  create_project            Create a project linked to customer"
    echo "  create_project_participant Project with participant"
    echo "  create_travel_expense     Travel expense with mileage"
    echo "  delete_travel_expense     Delete a travel expense"
    echo "  nynorsk                   Norwegian Nynorsk prompt"
    echo "  german                    German prompt"
    echo "  spanish                   Spanish prompt"
    echo "  enable_module             Enable accounting module"
    echo "  all                       Run all tests in sequence"
    echo ""
    ;;
esac
