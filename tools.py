"""Tool definitions for the Claude agent — one tool per Tripletex operation.

Keeping tools granular means Claude can plan precisely and minimise API calls.
"""

TOOLS = [
    # ── Employees ──────────────────────────────────────────────────────────
    {
        "name": "list_employees",
        "description": "List employees. Use to look up an existing employee by name.",
        "input_schema": {
            "type": "object",
            "properties": {
                "firstName": {"type": "string", "description": "Filter by first name (partial match)"},
                "lastName": {"type": "string", "description": "Filter by last name (partial match)"},
            },
        },
    },
    {
        "name": "create_employee",
        "description": "Create a new employee.",
        "input_schema": {
            "type": "object",
            "properties": {
                "firstName": {"type": "string"},
                "lastName": {"type": "string"},
                "email": {"type": "string"},
                "phoneNumberMobile": {"type": "string"},
                "dateOfBirth": {"type": "string", "description": "YYYY-MM-DD"},
            },
            "required": ["firstName", "lastName"],
        },
    },
    {
        "name": "update_employee",
        "description": "Update an existing employee's fields.",
        "input_schema": {
            "type": "object",
            "properties": {
                "employee_id": {"type": "integer"},
                "fields": {"type": "object", "description": "Key-value pairs of fields to update"},
            },
            "required": ["employee_id", "fields"],
        },
    },
    # ── Customers ──────────────────────────────────────────────────────────
    {
        "name": "list_customers",
        "description": "List customers. Use to find a customer by name.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Filter by customer name"},
            },
        },
    },
    {
        "name": "create_customer",
        "description": "Create a new customer.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "email": {"type": "string"},
                "phoneNumber": {"type": "string"},
                "address": {
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
        "description": "Update an existing customer.",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "integer"},
                "fields": {"type": "object"},
            },
            "required": ["customer_id", "fields"],
        },
    },
    # ── Products ───────────────────────────────────────────────────────────
    {
        "name": "list_products",
        "description": "List products.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
            },
        },
    },
    {
        "name": "create_product",
        "description": "Create a new product.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "number": {"type": "string", "description": "Product number/SKU"},
                "priceExcludingVatCurrency": {"type": "number"},
                "costExcludingVatCurrency": {"type": "number"},
                "vatType": {"type": "object", "properties": {"id": {"type": "integer"}}},
            },
            "required": ["name"],
        },
    },
    # ── Orders & Invoices ──────────────────────────────────────────────────
    {
        "name": "create_order",
        "description": "Create an order for a customer. Required before creating an invoice.",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "integer"},
                "orderDate": {"type": "string", "description": "YYYY-MM-DD"},
                "deliveryDate": {"type": "string", "description": "YYYY-MM-DD"},
                "orderLines": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "product_id": {"type": "integer"},
                            "count": {"type": "number"},
                            "unitPriceExcludingVatCurrency": {"type": "number"},
                            "description": {"type": "string"},
                        },
                    },
                },
            },
            "required": ["customer_id"],
        },
    },
    {
        "name": "create_invoice",
        "description": "Create an invoice from an order.",
        "input_schema": {
            "type": "object",
            "properties": {
                "order_id": {"type": "integer"},
                "invoiceDate": {"type": "string", "description": "YYYY-MM-DD"},
                "invoiceDueDate": {"type": "string", "description": "YYYY-MM-DD"},
            },
            "required": ["order_id", "invoiceDate", "invoiceDueDate"],
        },
    },
    {
        "name": "list_invoices",
        "description": "List invoices. Use to find an invoice by customer or date.",
        "input_schema": {
            "type": "object",
            "properties": {
                "customerId": {"type": "integer"},
                "invoiceDateFrom": {"type": "string"},
                "invoiceDateTo": {"type": "string"},
            },
        },
    },
    {
        "name": "register_payment",
        "description": "Register a payment against an invoice.",
        "input_schema": {
            "type": "object",
            "properties": {
                "invoice_id": {"type": "integer"},
                "paymentDate": {"type": "string", "description": "YYYY-MM-DD"},
                "amount": {"type": "number"},
                "paymentTypeId": {"type": "integer", "description": "Payment type ID (default 1)"},
            },
            "required": ["invoice_id", "paymentDate", "amount"],
        },
    },
    {
        "name": "create_credit_note",
        "description": "Create a credit note for an existing invoice.",
        "input_schema": {
            "type": "object",
            "properties": {
                "invoice_id": {"type": "integer"},
            },
            "required": ["invoice_id"],
        },
    },
    # ── Projects ───────────────────────────────────────────────────────────
    {
        "name": "list_projects",
        "description": "List projects.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "customerId": {"type": "integer"},
            },
        },
    },
    {
        "name": "create_project",
        "description": "Create a project, optionally linked to a customer.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "customer_id": {"type": "integer"},
                "startDate": {"type": "string", "description": "YYYY-MM-DD"},
                "endDate": {"type": "string", "description": "YYYY-MM-DD"},
                "description": {"type": "string"},
                "projectManagerId": {"type": "integer"},
            },
            "required": ["name"],
        },
    },
    # ── Departments ────────────────────────────────────────────────────────
    {
        "name": "list_departments",
        "description": "List departments.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "create_department",
        "description": "Create a department.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "departmentNumber": {"type": "string"},
            },
            "required": ["name"],
        },
    },
    # ── Travel Expenses ────────────────────────────────────────────────────
    {
        "name": "list_travel_expenses",
        "description": "List travel expense reports.",
        "input_schema": {
            "type": "object",
            "properties": {
                "employeeId": {"type": "integer"},
            },
        },
    },
    {
        "name": "create_travel_expense",
        "description": "Create a travel expense report.",
        "input_schema": {
            "type": "object",
            "properties": {
                "employee_id": {"type": "integer"},
                "description": {"type": "string"},
                "travelDetails": {"type": "object"},
                "departureDate": {"type": "string"},
                "returnDate": {"type": "string"},
            },
            "required": ["employee_id", "description"],
        },
    },
    {
        "name": "delete_travel_expense",
        "description": "Delete a travel expense report.",
        "input_schema": {
            "type": "object",
            "properties": {
                "expense_id": {"type": "integer"},
            },
            "required": ["expense_id"],
        },
    },
    # ── Modules ────────────────────────────────────────────────────────────
    {
        "name": "enable_module",
        "description": "Enable a Tripletex module (e.g. department accounting).",
        "input_schema": {
            "type": "object",
            "properties": {
                "module_name": {
                    "type": "string",
                    "description": "Module field name in company settings, e.g. 'moduleDepartment'",
                },
            },
            "required": ["module_name"],
        },
    },
]
