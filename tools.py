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
            "Pass department_id to assign the correct department — otherwise the default department is used."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "firstName": {"type": "string"},
                "lastName": {"type": "string"},
                "email": {"type": "string"},
                "phoneNumberMobile": {"type": "string"},
                "dateOfBirth": {"type": "string", "description": "YYYY-MM-DD"},
                "nationalIdentityNumber": {"type": "string", "description": "National ID / personnummer"},
                "employeeNumber": {"type": "string"},
                "department_id": {"type": "integer", "description": "Department ID to assign employee to"},
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
        "description": (
            "Update fields on an existing employee (e.g. add email, phone, address). "
            "To change department, pass department_id as a flat integer — it is automatically "
            "converted to the nested {\"department\": {\"id\": ...}} format the API requires. "
            "Do NOT wrap department_id manually."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "employee_id": {"type": "integer"},
                "fields": {
                    "type": "object",
                    "description": (
                        "Key-value pairs to update. Examples: "
                        "{\"email\": \"new@email.com\"}, {\"department_id\": 123}. "
                        "Use department_id (integer) to change department."
                    ),
                },
            },
            "required": ["employee_id", "fields"],
        },
    },
    {
        "name": "create_employment",
        "description": (
            "Create an employment record for an employee. Required for formal employment setup. "
            "startDate is required. Also sets employment details (salary, percentage, hours) in one call. "
            "Use percentageOfFullTimeEquivalent for part-time (e.g. 80 for 80%), annualSalary for yearly salary. "
            "IMPORTANT: The employee must have dateOfBirth set before this call or the API returns 422 "
            "'employee.dateOfBirth: Feltet må fylles ut'. If dateOfBirth was not set at create_employee time, "
            "call update_employee first to add a placeholder (e.g. '1990-01-01')."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "employee_id": {"type": "integer"},
                "startDate": {"type": "string", "description": "YYYY-MM-DD, required"},
                "endDate": {"type": "string", "description": "YYYY-MM-DD, leave empty for ongoing"},
                "isMainEmployer": {"type": "boolean", "description": "Default true"},
                "employmentType": {
                    "type": "string",
                    "enum": ["ORDINARY", "MARITIME", "FREELANCE", "NOT_CHOSEN"],
                    "description": "Default: ORDINARY. Goes into EmploymentDetails.",
                },
                "employmentForm": {
                    "type": "string",
                    "enum": ["PERMANENT", "TEMPORARY", "PERMANENT_AND_HIRED_OUT", "TEMPORARY_AND_HIRED_OUT", "TEMPORARY_ON_CALL", "NOT_CHOSEN"],
                    "description": "Default: PERMANENT. Goes into EmploymentDetails.",
                },
                "remunerationType": {
                    "type": "string",
                    "enum": ["MONTHLY_WAGE", "HOURLY_WAGE", "COMMISION_PERCENTAGE", "FEE", "NOT_CHOSEN", "PIECEWORK_WAGE"],
                    "description": "Default: MONTHLY_WAGE. Goes into EmploymentDetails.",
                },
                "workingHoursScheme": {
                    "type": "string",
                    "enum": ["NOT_SHIFT", "ROUND_THE_CLOCK", "SHIFT_365", "OFFSHORE_336", "CONTINUOUS", "OTHER_SHIFT", "NOT_CHOSEN"],
                    "description": "Default: NOT_SHIFT. Goes into EmploymentDetails.",
                },
                "percentageOfFullTimeEquivalent": {"type": "number", "description": "Work percentage, e.g. 100 for full-time, 80 for 80%. Goes into EmploymentDetails."},
                "annualSalary": {"type": "number", "description": "Annual salary in NOK. Goes into EmploymentDetails."},
                "monthlySalary": {"type": "number", "description": "Monthly salary in NOK. Goes into EmploymentDetails."},
                "hourlyWage": {"type": "number", "description": "Hourly wage in NOK. Goes into EmploymentDetails."},
                "occupationCode_id": {"type": "integer", "description": "Occupation code ID from list_occupation_codes. Goes into EmploymentDetails."},
            },
            "required": ["employee_id", "startDate"],
        },
    },
    {
        "name": "list_occupation_codes",
        "description": (
            "Search occupation/profession codes (STYRK-08) used in employment details. "
            "Search by nameNO (Norwegian name) or code number. "
            "Use when the task specifies an occupation code or job title that maps to a STYRK code."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "nameNO": {"type": "string", "description": "Norwegian occupation name (partial match)"},
                "code": {"type": "string", "description": "STYRK-08 code number"},
            },
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
            "Include orderLines with product details if known. "
            "If you include orderLines here, do NOT call add_order_line separately for those same lines."
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
            "invoiceDate is required (YYYY-MM-DD). "
            "To send the invoice after creation, call send_invoice separately."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "order_id": {"type": "integer"},
                "invoiceDate": {"type": "string", "description": "YYYY-MM-DD, required"},
                "sendToCustomer": {"type": "boolean", "description": "Send invoice to customer. API default is TRUE — pass false to suppress sending."},
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
            "paymentDate and amount (full invoice amount) are required. "
            "paymentTypeId: use 1 for default bank payment if unknown."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "invoice_id": {"type": "integer"},
                "paymentDate": {"type": "string", "description": "YYYY-MM-DD"},
                "amount": {"type": "number", "description": "Amount paid (maps to paidAmount in the API)"},
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
            "Create a project. name and projectManager_id are required — "
            "the API returns 422 'Feltet Prosjektleder må fylles ut' if projectManager_id is omitted. "
            "Use list_employees to find the employee ID before calling this tool. "
            "Link to a customer with customer_id. "
            "NOTE: projectManager must have project manager privileges in Tripletex — "
            "if the employee does not have PM access the API returns 422 "
            "'prosjektleder har ikke fått tilgang som prosjektleder'."
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
            "required": ["name", "projectManager_id"],
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
        "name": "list_travel_payment_types",
        "description": (
            "List available payment types for travel expense cost lines. "
            "Call this before add_travel_cost to find the paymentType_id. "
            "Use showOnTravelExpenses=true to filter to types valid for travel expense reports."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "showOnTravelExpenses": {"type": "boolean"},
                "showOnEmployeeExpenses": {"type": "boolean"},
            },
        },
    },
    {
        "name": "create_travel_expense",
        "description": (
            "Create a travel expense report header. "
            "employee_id and title are required. "
            "IMPORTANT: always include travelDetails with at least departureFrom and destination — "
            "omitting travelDetails may cause the report to be created as an employee expense "
            "(ansattutlegg) instead of a travel expense (reiseregning), which blocks add_mileage_allowance. "
            "After creating, add cost lines with add_travel_cost (requires paymentType_id), "
            "mileage with add_mileage_allowance, per diem with add_per_diem_compensation."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "employee_id": {"type": "integer"},
                "title": {"type": "string", "description": "Required. Short description of the trip."},
                "date": {"type": "string", "description": "YYYY-MM-DD, travel date"},
                "project_id": {"type": "integer", "description": "Link to project (optional)"},
                "travelDetails": {
                    "type": "object",
                    "description": "Travel details — always include departureFrom and destination.",
                    "properties": {
                        "departureDate": {"type": "string", "description": "YYYY-MM-DD"},
                        "returnDate": {"type": "string", "description": "YYYY-MM-DD"},
                        "departureFrom": {"type": "string", "description": "Where the trip started"},
                        "destination": {"type": "string", "description": "Where the trip went"},
                        "isForeignTravel": {"type": "boolean"},
                        "isDayTrip": {"type": "boolean"},
                        "purpose": {"type": "string"},
                    },
                },
            },
            "required": ["employee_id", "title"],
        },
    },
    {
        "name": "add_travel_cost",
        "description": (
            "Add a cost line (receipt/expense) to a travel expense report. "
            "paymentType_id is REQUIRED — call list_travel_payment_types first to get valid IDs. "
            "Use showOnTravelExpenses=true when listing to filter to applicable types."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "travel_expense_id": {"type": "integer"},
                "paymentType_id": {"type": "integer", "description": "Required. Get ID from list_travel_payment_types."},
                "amountCurrencyIncVat": {"type": "number", "description": "Amount including VAT"},
                "comments": {"type": "string", "description": "Description of the cost"},
                "category": {"type": "string", "description": "Cost category description"},
            },
            "required": ["travel_expense_id", "paymentType_id", "amountCurrencyIncVat"],
        },
    },
    {
        "name": "add_mileage_allowance",
        "description": (
            "Add a mileage/driving allowance line to a travel expense report. "
            "rateCategory_id is REQUIRED for deliver to work — use 120 for standard domestic car (Bil inntil 9000 km). "
            "Without it, deliver_travel_expense returns 422 'Sats eller satskategori må spesifiseres'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "travel_expense_id": {"type": "integer"},
                "date": {"type": "string", "description": "YYYY-MM-DD"},
                "departureLocation": {"type": "string", "description": "Required. Where the trip started."},
                "destination": {"type": "string", "description": "Required. Where the trip ended."},
                "km": {"type": "number", "description": "Distance in kilometres"},
                "rateCategory_id": {"type": "integer", "description": "Required for delivery. Standard domestic car = 120."},
                "isCompanyCar": {"type": "boolean", "description": "Company car? Default false."},
            },
            "required": ["travel_expense_id", "date", "km", "departureLocation", "destination", "rateCategory_id"],
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
            "date and postings are required. Each posting needs account_id, "
            "amount (positive=debit, negative=credit), and date. "
            "MANDATORY RULE: any posting to account 2400 (Leverandørgjeld / accounts payable) "
            "MUST include supplier_id — without it the API always returns 422 'Leverandør mangler'. "
            "If you have a supplier involved in the transaction, pass their supplier_id on the 2400 posting."
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
                            "supplier_id": {"type": "integer", "description": "REQUIRED on the account-2400 posting. Omitting it causes 422."},
                            "customer_id": {"type": "integer"},
                            "employee_id": {"type": "integer"},
                            "project_id": {"type": "integer"},
                            "department_id": {"type": "integer", "description": "Department to assign this posting to"},
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
        "description": "List ledger accounts (chart of accounts). Use to find account IDs for voucher postings. Pass 'number' for exact match, or 'numberFrom'/'numberTo' for a range.",
        "input_schema": {
            "type": "object",
            "properties": {
                "number": {"type": "integer", "description": "Account number (exact match)"},
                "numberFrom": {"type": "integer", "description": "Filter accounts with number >= this value"},
                "numberTo": {"type": "integer", "description": "Filter accounts with number <= this value"},
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
            "Use for tasks like 'kjør lønn', 'exécutez la paie', 'run payroll', 'process salary'. "
            "ERRORS: If you get 'Ansatt nr. er ikke registrert med et arbeidsforhold' the employee "
            "has no employment record — call create_employment first. "
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
            "Use list_activities to find activity_id first. "
            "IMPORTANT: date must be on or after the project's startDate — "
            "logging hours before the project start date returns 422 "
            "'Det kan ikke registreres timer før startdatoen'. "
            "If the project start date is in the future, use the project's start date as the timesheet entry date."
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
            "Get current company info: id, name, organizationNumber. "
            "Use this only when you need the company's own ID — it costs 2 API calls."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "enable_module",
        "description": (
            "Activate a sales/addon module via POST /company/salesmodules. "
            "The sandbox has all standard modules (salary, travel, project, department) "
            "pre-enabled — do NOT call this unless another tool explicitly returned a "
            "'module not enabled' error. Wrong usage wastes iterations."
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
    {
        "name": "record_session_note",
        "description": (
            "Record a factual note for use in future tasks within this session (same sandbox). "
            "Use ONLY for specific, verified facts — entity IDs, salary type mappings, etc. "
            "Format: 'salary type fastlonn has id=100' or 'department Salg has id=42'. "
            "Do NOT record guesses or task-specific context (amounts, dates). "
            "Call ONLY after the primary task is complete."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "note": {"type": "string", "description": "Short factual note, e.g. 'salary type fastlonn has id=100'"},
            },
            "required": ["note"],
        },
    },
]
