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

test_update_employee() {
  run "update_employee" \
    "Update employee Kari Hansen: change her phone number to 99887766 and set her title to Senior Consultant"
}

test_update_customer() {
  run "update_customer" \
    "Update customer Bergström AS: set their email to faktura@bergstrom.no and phone to 22334455"
}

# ── Voucher / Ledger ──────────────────────────────────────────────────────────

test_voucher_supplier() {
  run "voucher_supplier" \
    "Book a supplier invoice from Bergström AS for consulting services of 20000 NOK. Debit an appropriate cost account (fremmedytelse/konsulent, 6000-series) and credit accounts payable (2400). Use today as the voucher date."
}

test_voucher_correction() {
  run "voucher_correction" \
    "Reverse the most recent ledger voucher that was created this month."
}

# ── Complex / multi-step ─────────────────────────────────────────────────────

test_employee_with_employment() {
  run "employee_with_employment" \
    "Onboard a new employee: Ingrid Larsen, email ingrid.larsen@example.no, phone 90001234. She starts 2026-04-01 as a full-time permanent employee (100% FTE) with a monthly salary of 55000 NOK. Set employment type ORDINARY and working hours scheme NOT_SHIFT."
}

test_timesheet() {
  run "timesheet" \
    "Log 7.5 hours of work for employee Kari Hansen on project Nettsideprosjekt 2026 on 2026-04-02. Use an appropriate activity."
}

test_salary() {
  run "salary" \
    "Register the monthly salary for March 2026 for employee Kari Hansen. Her monthly base salary is 48000 NOK. Use the standard fixed-salary wage type."
}

test_travel_expense_full() {
  run "travel_expense_full" \
    "Create a travel expense for Kari Hansen: trip title 'Fagkonferanse Bergen', travel date 2026-04-10. Add mileage of 85 km. Add a cost item for hotel stay of 1200 NOK. Then deliver (submit) the travel expense."
}

test_project_lifecycle() {
  run "project_lifecycle" \
    "Full project lifecycle: 1) Create project 'Digitalisering 2026' for customer Bergström AS with budget 150000 NOK, start date 2026-04-01. 2) Add Kari Hansen as project participant. 3) Log 8 hours for Kari Hansen on the project today. 4) Create an order for Bergström AS for the project (150000 NOK) and invoice it."
}

test_create_supplier() {
  run "create_supplier" \
    "Create a new supplier called TechPartner AS with organisation number 912345678 and email leverandor@techpartner.no"
}

test_portuguese() {
  run "portuguese" \
    "Crie um novo cliente chamado Lisboa Consultores com email contato@lisboaconsultores.pt e telefone 21234567"
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
  update_employee)           test_update_employee ;;
  update_customer)           test_update_customer ;;
  voucher_supplier)          test_voucher_supplier ;;
  voucher_correction)        test_voucher_correction ;;
  employee_with_employment)  test_employee_with_employment ;;
  timesheet)                 test_timesheet ;;
  salary)                    test_salary ;;
  travel_expense_full)       test_travel_expense_full ;;
  project_lifecycle)         test_project_lifecycle ;;
  create_supplier)           test_create_supplier ;;
  portuguese)                test_portuguese ;;
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
    test_update_employee
    test_update_customer
    test_voucher_supplier
    test_employee_with_employment
    test_timesheet
    test_salary
    test_travel_expense_full
    test_project_lifecycle
    test_create_supplier
    test_portuguese
    ;;
  help|*)
    echo ""
    echo "Usage: bash test_prompts.sh <test_name>"
    echo ""
    echo "Available tests (Tier 1 — basic):"
    echo "  create_employee           Create a standard employee"
    echo "  create_employee_admin     Create an employee with admin role"
    echo "  create_customer           Create a business customer"
    echo "  create_customer_private   Create a private individual customer"
    echo "  create_product            Create a product with price"
    echo "  create_department         Create a department"
    echo "  create_invoice            Create an order + invoice"
    echo "  create_invoice_english    Same in English"
    echo "  register_payment          Register payment on an invoice"
    echo "  create_supplier           Create a new supplier"
    echo ""
    echo "Available tests (Tier 2 — multi-step):"
    echo "  credit_note               Create a credit note"
    echo "  create_project            Create a project linked to customer"
    echo "  create_project_participant Project with participant"
    echo "  create_travel_expense     Travel expense with mileage"
    echo "  delete_travel_expense     Delete a travel expense"
    echo "  update_employee           Update employee fields"
    echo "  update_customer           Update customer fields"
    echo "  employee_with_employment  Onboard employee with employment + salary"
    echo "  timesheet                 Log hours on a project"
    echo "  salary                    Register monthly salary transaction"
    echo "  travel_expense_full       Travel expense with cost + mileage + deliver"
    echo "  project_lifecycle         Full project lifecycle (create→time→invoice)"
    echo ""
    echo "Available tests (Tier 3 — corrections/ledger):"
    echo "  voucher_supplier          Supplier invoice via voucher (AP posting)"
    echo "  voucher_correction        Reverse a voucher"
    echo "  enable_module             Enable accounting module"
    echo ""
    echo "Available tests (multilingual):"
    echo "  nynorsk                   Norwegian Nynorsk prompt"
    echo "  german                    German prompt"
    echo "  spanish                   Spanish prompt"
    echo "  portuguese                Portuguese prompt"
    echo ""
    echo "  all                       Run all tests in sequence"
    echo ""
    ;;
esac
