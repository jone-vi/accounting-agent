"""Tool definitions for the Claude agent — one tool per Tripletex operation.

Verified against tripletexapi.json. Descriptions include known required fields,
valid enum values, and usage guidance to minimise 4xx errors.
"""

TOOLS = [
    # ── Employees ──────────────────────────────────────────────────────────
    {
        "name": "list_employees",
        "description": (
            "Search existing employees by name. Use before creating to avoid duplicates, "
            "or to find an employee ID. Returns id, firstName, lastName, email."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "firstName": {"type": "string", "description": "Partial first name match"},
                "lastName": {"type": "string", "description": "Partial last name match"},
            },
        },
    },
    {
        "name": "create_employee",
        "description": (
            "Create a new employee. "
            "userType is ALWAYS required. Use STANDARD for normal employees, "
            "EXTENDED for administrators/managers, NO_ACCESS if login not needed. "
            "department is auto-filled if not provided."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "firstName": {"type": "string"},
                "lastName": {"type": "string"},
                "email": {"type": "string"},
                "phoneNumberMobile": {"type": "string"},
                "dateOfBirth": {"type": "string", "description": "YYYY-MM-DD"},
                "employeeNumber": {"type": "string"},
                "userType": {
                    "type": "string",
                    "description": "Required. STANDARD=normal user, EXTENDED=admin/manager, NO_ACCESS=no login.",
                    "enum": ["STANDARD", "EXTENDED", "NO_ACCESS"],
                },
            },
            "required": ["firstName", "lastName", "userType"],
        },
    },
    {
        "name": "update_employee",
        "description": "Update fields on an existing employee (e.g. add email, phone, address).",
        "input_schema": {
            "type": "object",
            "properties": {
                "employee_id": {"type": "integer"},
                "fields": {
                    "type": "object",
                    "description": "Key-value pairs to update, e.g. {\"email\": \"new@email.com\"}",
                },
            },
            "required": ["employee_id", "fields"],
        },
    },
    {
        "name": "create_employment",
        "description": (
            "Create an employment record for an employee. Required for formal employment setup. "
            "startDate is required."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "employee_id": {"type": "integer"},
                "startDate": {"type": "string", "description": "YYYY-MM-DD, required"},
                "endDate": {"type": "string", "description": "YYYY-MM-DD, leave empty for ongoing"},
                "isMainEmployer": {"type": "boolean", "description": "Default true"},
            },
            "required": ["employee_id", "startDate"],
        },
    },
    {
        "name": "grant_entitlements_by_template",
        "description": (
            "Grant a role/privilege template to an employee within the same company. "
            "Use this to assign admin or manager roles. "
            "Templates: ALL_PRIVILEGES (full admin), INVOICING_MANAGER, PERSONELL_MANAGER, "
            "ACCOUNTANT, AUDITOR, DEPARTMENT_LEADER, NONE_PRIVILEGES."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "employee_id": {"type": "integer"},
                "template": {
                    "type": "string",
                    "enum": [
                        "NONE_PRIVILEGES",
                        "ALL_PRIVILEGES",
                        "INVOICING_MANAGER",
                        "PERSONELL_MANAGER",
                        "ACCOUNTANT",
                        "AUDITOR",
                        "DEPARTMENT_LEADER",
                    ],
                },
            },
            "required": ["employee_id", "template"],
        },
    },
    {
        "name": "grant_entitlement_template",
        "description": (
            "Grant a role/privilege template to an employee for a CLIENT account (accountant access). "
            "Use grant_entitlements_by_template instead for granting roles within the same company. "
            "customerId is the client company's Tripletex customer ID (from get_company_info)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "employee_id": {"type": "integer"},
                "customer_id": {"type": "integer", "description": "The client company's Tripletex customer ID"},
                "template": {
                    "type": "string",
                    "enum": [
                        "NONE_PRIVILEGES",
                        "STANDARD_PRIVILEGES_ACCOUNTANT",
                        "STANDARD_PRIVILEGES_AUDITOR",
                        "ALL_PRIVILEGES",
                        "AGRO_READ_ONLY",
                        "AGRO_READ_APPROVE",
                        "AGRO_READ_WRITE",
                        "AGRO_READ_WRITE_APPROVE",
                        "AGRO_PAYROLL_ADMIN",
                        "AGRO_PAYROLL_CLERK",
                        "AGRO_INVOICE_ADMIN",
                        "AGRO_INVOICE_CLERK",
                    ],
                },
            },
            "required": ["employee_id", "customer_id", "template"],
        },
    },

    # ── Customers ──────────────────────────────────────────────────────────
    {
        "name": "list_customers",
        "description": "Search customers by name. Use to find customer ID before creating orders/invoices/projects.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Customer name filter (partial match)"},
            },
        },
    },
    {
        "name": "create_customer",
        "description": "Create a new customer. Only name is required.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "organizationNumber": {"type": "string"},
                "email": {"type": "string"},
                "invoiceEmail": {"type": "string"},
                "phoneNumber": {"type": "string"},
                "isPrivateIndividual": {"type": "boolean", "description": "True for private persons, false for companies"},
                "postalAddress": {
                    "type": "object",
                    "properties": {
                        "addressLine1": {"type": "string"},
                        "postalCode": {"type": "string"},
                        "city": {"type": "string"},
                        "country": {"type": "object", "properties": {"id": {"type": "integer"}}},
                    },
                },
            },
            "required": ["name"],
        },
    },
    {
        "name": "update_customer",
        "description": "Update fields on an existing customer.",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "integer"},
                "fields": {"type": "object", "description": "Key-value pairs to update"},
            },
            "required": ["customer_id", "fields"],
        },
    },

    # ── Products ───────────────────────────────────────────────────────────
    {
        "name": "list_products",
        "description": "Search products by name. Use to find product ID before adding to orders.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "isInactive": {"type": "boolean", "description": "Default false — only active products"},
            },
        },
    },
    {
        "name": "create_product",
        "description": "Create a new product/service. Only name is required.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "number": {"type": "string", "description": "Product number / SKU"},
                "description": {"type": "string"},
                "priceExcludingVatCurrency": {"type": "number", "description": "Sales price excl. VAT"},
                "costExcludingVatCurrency": {"type": "number", "description": "Cost price excl. VAT"},
                "vatType": {
                    "type": "object",
                    "properties": {"id": {"type": "integer"}},
                    "description": "VAT type object. Omit this field — Tripletex will use the company default. Do NOT guess an ID.",
                },
                "isStockItem": {"type": "boolean"},
            },
            "required": ["name"],
        },
    },

    # ── Orders ─────────────────────────────────────────────────────────────
    {
        "name": "create_order",
        "description": (
            "Create an order for a customer. "
            "Use invoice_order afterwards to convert it to an invoice. "
            "customer_id is required. orderDate defaults to today if omitted. "
            "Include orderLines with product details if known."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "integer"},
                "orderDate": {"type": "string", "description": "YYYY-MM-DD, defaults to today"},
                "deliveryDate": {"type": "string", "description": "YYYY-MM-DD"},
                "invoiceComment": {"type": "string"},
                "ourContactEmployee": {
                    "type": "object",
                    "properties": {"id": {"type": "integer"}},
                    "description": "Our contact employee for this order",
                },
                "orderLines": {
                    "type": "array",
                    "description": "Line items for the order",
                    "items": {
                        "type": "object",
                        "properties": {
                            "product_id": {"type": "integer", "description": "Product ID (optional)"},
                            "description": {"type": "string"},
                            "count": {"type": "number", "description": "Quantity"},
                            "unitPriceExcludingVatCurrency": {"type": "number"},
                        },
                    },
                },
            },
            "required": ["customer_id"],
        },
    },
    {
        "name": "invoice_order",
        "description": (
            "Convert an order to an invoice in one step. "
            "Preferred over create_invoice — fewer API calls. "
            "invoiceDate is required (YYYY-MM-DD). "
            "Set sendToCustomer=true to also send the invoice by email."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "order_id": {"type": "integer"},
                "invoiceDate": {"type": "string", "description": "YYYY-MM-DD, required"},
                "sendToCustomer": {"type": "boolean", "description": "Send invoice by email. Default false."},
                "sendType": {
                    "type": "string",
                    "description": "Send method if sendToCustomer=true",
                    "enum": ["EMAIL", "EHF", "AVTALEGIRO", "EFAKTURA", "VIPPS", "PAPER", "MANUAL"],
                },
                "paymentTypeId": {"type": "integer", "description": "Payment type ID if paying immediately"},
                "paidAmount": {"type": "number", "description": "Amount paid if paying immediately"},
            },
            "required": ["order_id", "invoiceDate"],
        },
    },
    {
        "name": "add_order_line",
        "description": "Add a line item to an existing order.",
        "input_schema": {
            "type": "object",
            "properties": {
                "order_id": {"type": "integer"},
                "product_id": {"type": "integer", "description": "Product ID (optional)"},
                "description": {"type": "string"},
                "count": {"type": "number"},
                "unitPriceExcludingVatCurrency": {"type": "number"},
            },
            "required": ["order_id"],
        },
    },

    # ── Invoices ───────────────────────────────────────────────────────────
    {
        "name": "list_invoices",
        "description": "Search invoices. Use to find an invoice for payment or credit note. invoiceDateFrom and invoiceDateTo are REQUIRED — always provide them (e.g. '2025-01-01' to today).",
        "input_schema": {
            "type": "object",
            "properties": {
                "customerId": {"type": "integer"},
                "invoiceDateFrom": {"type": "string", "description": "YYYY-MM-DD. Required."},
                "invoiceDateTo": {"type": "string", "description": "YYYY-MM-DD. Required."},
                "invoiceNumber": {"type": "integer"},
            },
            "required": ["invoiceDateFrom", "invoiceDateTo"],
        },
    },
    {
        "name": "send_invoice",
        "description": "Send an invoice to the customer by email or other method.",
        "input_schema": {
            "type": "object",
            "properties": {
                "invoice_id": {"type": "integer"},
                "sendType": {
                    "type": "string",
                    "description": "Required. Use EMAIL for standard email delivery.",
                    "enum": ["EMAIL", "EHF", "AVTALEGIRO", "EFAKTURA", "VIPPS", "PAPER", "MANUAL"],
                },
                "overrideEmailAddress": {"type": "string", "description": "Override recipient email"},
            },
            "required": ["invoice_id", "sendType"],
        },
    },
    {
        "name": "register_payment",
        "description": (
            "Register a payment against an invoice. "
            "paymentDate and amount are required. "
            "paymentTypeId: use 1 for default bank payment if unknown."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "invoice_id": {"type": "integer"},
                "paymentDate": {"type": "string", "description": "YYYY-MM-DD"},
                "amount": {"type": "number", "description": "Amount paid"},
                "paymentTypeId": {"type": "integer", "description": "Payment type ID. Default: 1"},
            },
            "required": ["invoice_id", "paymentDate", "amount"],
        },
    },
    {
        "name": "create_credit_note",
        "description": "Create a credit note (reversal) for an existing invoice. date is required (YYYY-MM-DD, use today's date).",
        "input_schema": {
            "type": "object",
            "properties": {
                "invoice_id": {"type": "integer"},
                "date": {"type": "string", "description": "Credit note date, YYYY-MM-DD. Required."},
            },
            "required": ["invoice_id", "date"],
        },
    },

    # ── Projects ───────────────────────────────────────────────────────────
    {
        "name": "list_projects",
        "description": "Search projects by name or customer.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "customerId": {"type": "integer"},
                "isClosed": {"type": "boolean"},
            },
        },
    },
    {
        "name": "create_project",
        "description": (
            "Create a project. name is required. "
            "Link to a customer with customer_id. "
            "Assign a project manager with projectManager_id (employee ID)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "number": {"type": "string", "description": "Project number (optional)"},
                "description": {"type": "string"},
                "customer_id": {"type": "integer"},
                "projectManager_id": {"type": "integer", "description": "Employee ID of project manager"},
                "startDate": {"type": "string", "description": "YYYY-MM-DD"},
                "endDate": {"type": "string", "description": "YYYY-MM-DD"},
                "isInternal": {"type": "boolean", "description": "True for internal projects"},
            },
            "required": ["name"],
        },
    },
    {
        "name": "add_project_participant",
        "description": "Add an employee as a participant to a project.",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "integer"},
                "employee_id": {"type": "integer"},
                "adminAccess": {"type": "boolean", "description": "Give admin access to project. Default false."},
            },
            "required": ["project_id", "employee_id"],
        },
    },

    # ── Departments ────────────────────────────────────────────────────────
    {
        "name": "list_departments",
        "description": "List all departments.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "create_department",
        "description": "Create a new department. name is required.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "departmentNumber": {"type": "string"},
                "departmentManager": {
                    "type": "object",
                    "properties": {"id": {"type": "integer"}},
                    "description": "Employee ID of department manager",
                },
            },
            "required": ["name"],
        },
    },

    # ── Travel Expenses ────────────────────────────────────────────────────
    {
        "name": "list_travel_expenses",
        "description": "List travel expense reports. Filter by employee or date.",
        "input_schema": {
            "type": "object",
            "properties": {
                "employeeId": {"type": "integer"},
                "dateFrom": {"type": "string", "description": "YYYY-MM-DD"},
                "dateTo": {"type": "string", "description": "YYYY-MM-DD"},
            },
        },
    },
    {
        "name": "create_travel_expense",
        "description": (
            "Create a travel expense report header. "
            "employee_id and title are required. "
            "After creating, add cost lines with add_travel_cost, "
            "mileage with add_mileage_allowance, per diem with add_per_diem_compensation."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "employee_id": {"type": "integer"},
                "title": {"type": "string", "description": "Required. Short description of the trip."},
                "date": {"type": "string", "description": "YYYY-MM-DD, travel date"},
                "departureDate": {"type": "string", "description": "YYYY-MM-DD"},
                "returnDate": {"type": "string", "description": "YYYY-MM-DD"},
                "project_id": {"type": "integer", "description": "Link to project (optional)"},
            },
            "required": ["employee_id", "title"],
        },
    },
    {
        "name": "add_travel_cost",
        "description": "Add a cost line (receipt/expense) to a travel expense report.",
        "input_schema": {
            "type": "object",
            "properties": {
                "travel_expense_id": {"type": "integer"},
                "amountCurrencyIncVat": {"type": "number", "description": "Amount including VAT"},
                "comments": {"type": "string", "description": "Description of the cost"},
                "category": {"type": "string", "description": "Cost category description"},
            },
            "required": ["travel_expense_id", "amountCurrencyIncVat"],
        },
    },
    {
        "name": "add_mileage_allowance",
        "description": "Add a mileage/driving allowance line to a travel expense report.",
        "input_schema": {
            "type": "object",
            "properties": {
                "travel_expense_id": {"type": "integer"},
                "date": {"type": "string", "description": "YYYY-MM-DD"},
                "departureLocation": {"type": "string"},
                "destination": {"type": "string"},
                "km": {"type": "number", "description": "Distance in kilometres"},
                "isCompanyCar": {"type": "boolean", "description": "Company car? Default false."},
            },
            "required": ["travel_expense_id", "date", "km"],
        },
    },
    {
        "name": "add_per_diem_compensation",
        "description": "Add a per diem (daily allowance) line to a travel expense report.",
        "input_schema": {
            "type": "object",
            "properties": {
                "travel_expense_id": {"type": "integer"},
                "countryCode": {"type": "string", "description": "ISO country code e.g. 'NO', 'DE'"},
                "count": {"type": "integer", "description": "Number of days"},
                "overnightAccommodation": {
                    "type": "string",
                    "enum": ["NONE", "HOTEL", "BOARDING_HOUSE_WITHOUT_COOKING", "BOARDING_HOUSE_WITH_COOKING"],
                },
            },
            "required": ["travel_expense_id", "count"],
        },
    },
    {
        "name": "deliver_travel_expense",
        "description": "Submit a travel expense report for approval.",
        "input_schema": {
            "type": "object",
            "properties": {
                "travel_expense_id": {"type": "integer"},
            },
            "required": ["travel_expense_id"],
        },
    },
    {
        "name": "delete_travel_expense",
        "description": "Delete a travel expense report.",
        "input_schema": {
            "type": "object",
            "properties": {
                "travel_expense_id": {"type": "integer"},
            },
            "required": ["travel_expense_id"],
        },
    },

    # ── Vouchers / Corrections ─────────────────────────────────────────────
    {
        "name": "list_vouchers",
        "description": "Search ledger vouchers/journal entries. Use to find a voucher to reverse or correct. dateTo is exclusive — set it to the day AFTER the last date you want (e.g. dateFrom='2026-03-01', dateTo='2026-03-02' to search March 1).",
        "input_schema": {
            "type": "object",
            "properties": {
                "dateFrom": {"type": "string", "description": "YYYY-MM-DD (inclusive)"},
                "dateTo": {"type": "string", "description": "YYYY-MM-DD (exclusive — use day after last date wanted)"},
                "number": {"type": "integer", "description": "Voucher number"},
            },
        },
    },
    {
        "name": "create_voucher",
        "description": (
            "Create a manual ledger voucher (journal entry). "
            "date and postings are required. Each posting needs account (id), "
            "amount (positive=debit, negative=credit), and date."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "date": {"type": "string", "description": "YYYY-MM-DD"},
                "description": {"type": "string"},
                "postings": {
                    "type": "array",
                    "description": "Journal lines. Debits and credits must balance to zero.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "account_id": {"type": "integer", "description": "Ledger account ID"},
                            "amount": {"type": "number", "description": "Positive=debit, negative=credit"},
                            "date": {"type": "string", "description": "YYYY-MM-DD"},
                            "description": {"type": "string"},
                            "customer_id": {"type": "integer"},
                            "employee_id": {"type": "integer"},
                            "project_id": {"type": "integer"},
                        },
                        "required": ["account_id", "amount", "date"],
                    },
                },
            },
            "required": ["date", "postings"],
        },
    },
    {
        "name": "reverse_voucher",
        "description": "Reverse (negate) an existing ledger voucher. Creates a counter-entry.",
        "input_schema": {
            "type": "object",
            "properties": {
                "voucher_id": {"type": "integer"},
                "date": {"type": "string", "description": "YYYY-MM-DD, date of the reversal entry"},
            },
            "required": ["voucher_id", "date"],
        },
    },
    {
        "name": "list_accounts",
        "description": "List ledger accounts (chart of accounts). Use to find account IDs for voucher postings. Filter by number (exact match) or name.",
        "input_schema": {
            "type": "object",
            "properties": {
                "number": {"type": "integer", "description": "Account number (exact match)"},
                "name": {"type": "string"},
            },
        },
    },

    # ── Salary / Payroll ───────────────────────────────────────────────────
    {
        "name": "list_salary_types",
        "description": (
            "List available salary/wage types (lønnarter). Use to find the salary type ID "
            "for base salary, bonus, overtime, holiday pay, etc. before creating a salary transaction. "
            "Filter by name to find the right type (e.g. 'fastlønn', 'bonus', 'overtid')."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Filter by salary type name"},
                "number": {"type": "string", "description": "Filter by wage code number"},
            },
        },
    },
    {
        "name": "create_salary_transaction",
        "description": (
            "Run payroll for one or more employees (create a salary transaction). "
            "Requires year, month, and at least one payslip with salary specifications. "
            "Each specification needs a salary_type_id (from list_salary_types), rate (amount per unit), "
            "and count (number of units, typically 1 for monthly salary). "
            "Use for tasks like 'kjør lønn', 'exécutez la paie', 'run payroll', 'process salary'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "year": {"type": "integer", "description": "Payroll year, e.g. 2026"},
                "month": {"type": "integer", "description": "Payroll month (1-12)"},
                "payslips": {
                    "type": "array",
                    "description": "One entry per employee",
                    "items": {
                        "type": "object",
                        "properties": {
                            "employee_id": {"type": "integer"},
                            "specifications": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "salary_type_id": {"type": "integer", "description": "ID from list_salary_types"},
                                        "rate": {"type": "number", "description": "Amount per unit (e.g. monthly salary amount)"},
                                        "count": {"type": "number", "description": "Number of units, typically 1"},
                                        "description": {"type": "string", "description": "Line description"},
                                    },
                                    "required": ["salary_type_id", "rate", "count"],
                                },
                            },
                        },
                        "required": ["employee_id", "specifications"],
                    },
                },
            },
            "required": ["year", "month", "payslips"],
        },
    },
    {
        "name": "list_payslips",
        "description": "List existing payslips for an employee. Use to check if payroll has already been run.",
        "input_schema": {
            "type": "object",
            "properties": {
                "employeeId": {"type": "integer"},
                "yearFrom": {"type": "integer"},
                "yearTo": {"type": "integer"},
                "monthFrom": {"type": "integer"},
                "monthTo": {"type": "integer"},
            },
        },
    },

    # ── Suppliers ──────────────────────────────────────────────────────────
    {
        "name": "list_suppliers",
        "description": "Search suppliers by name. Use to find supplier ID or check for duplicates before creating.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Supplier name filter (partial match not supported — use exact or leave empty to list all)"},
            },
        },
    },
    {
        "name": "create_supplier",
        "description": "Create a new supplier. Only name is required.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "organizationNumber": {"type": "string"},
                "email": {"type": "string"},
                "invoiceEmail": {"type": "string"},
                "phoneNumber": {"type": "string"},
                "isPrivateIndividual": {"type": "boolean"},
                "postalAddress": {
                    "type": "object",
                    "properties": {
                        "addressLine1": {"type": "string"},
                        "postalCode": {"type": "string"},
                        "city": {"type": "string"},
                    },
                },
            },
            "required": ["name"],
        },
    },

    # ── Timesheet / Activities ─────────────────────────────────────────────
    {
        "name": "list_activities",
        "description": (
            "List available activities (aktiviteter) for timesheet entries. "
            "Returns id, name, number, and type. Use to find activity_id before creating timesheet entries. "
            "General activities (isGeneral=true) can be used on any project."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Filter by activity name"},
                "projectId": {"type": "integer", "description": "Filter activities available for a specific project"},
            },
        },
    },
    {
        "name": "create_timesheet_entry",
        "description": (
            "Log hours for an employee on a project/activity (timesheet). "
            "employee_id, activity_id, date, and hours are required. "
            "Use list_activities to find activity_id first."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "employee_id": {"type": "integer"},
                "activity_id": {"type": "integer", "description": "Required. Get from list_activities."},
                "project_id": {"type": "integer", "description": "Project to log hours against (optional for general activities)"},
                "date": {"type": "string", "description": "YYYY-MM-DD"},
                "hours": {"type": "number", "description": "Number of hours worked"},
                "comment": {"type": "string"},
            },
            "required": ["employee_id", "activity_id", "date", "hours"],
        },
    },

    # ── Company / Modules ──────────────────────────────────────────────────
    {
        "name": "get_company_info",
        "description": (
            "Get current user and company info: employeeId, companyId. "
            "Use to find the company's customer ID for grant_entitlement_template (client access)."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "enable_module",
        "description": (
            "Enable a Tripletex accounting module. "
            "Common module names: 'moduleDepartment' (department accounting), "
            "'moduleProject' (project accounting), 'moduleTravel' (travel expenses)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "module_name": {
                    "type": "string",
                    "description": "Field name in company modules settings. E.g. 'moduleDepartment'.",
                },
            },
            "required": ["module_name"],
        },
    },
]
