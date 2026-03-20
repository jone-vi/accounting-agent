"""Tripletex API client — thin wrapper around the REST API."""

import httpx
from typing import Any


class TripletexClient:
    def __init__(self, base_url: str, session_token: str):
        self.base_url = base_url.rstrip("/")
        self.auth = ("0", session_token)

    def get(self, path: str, params: dict | None = None) -> dict:
        url = f"{self.base_url}{path}"
        resp = httpx.get(url, auth=self.auth, params=params, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def post(self, path: str, json: dict) -> dict:
        url = f"{self.base_url}{path}"
        resp = httpx.post(url, auth=self.auth, json=json, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def put(self, path: str, json: dict) -> dict:
        url = f"{self.base_url}{path}"
        resp = httpx.put(url, auth=self.auth, json=json, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def delete(self, path: str) -> None:
        url = f"{self.base_url}{path}"
        resp = httpx.delete(url, auth=self.auth, timeout=30)
        resp.raise_for_status()

    # ── Employees ────────────────────────────────────────────────────────────

    def list_employees(self, **params) -> list[dict]:
        data = self.get("/employee", params={"fields": "id,firstName,lastName,email,phoneNumberMobile", **params})
        return data.get("values", [])

    def create_employee(self, payload: dict) -> dict:
        return self.post("/employee", payload)["value"]

    def get_employee(self, employee_id: int) -> dict:
        return self.get(f"/employee/{employee_id}", params={"fields": "*"})["value"]

    def update_employee(self, employee_id: int, payload: dict) -> dict:
        return self.put(f"/employee/{employee_id}", payload)["value"]

    def add_employee_role(self, employee_id: int, role_id: int) -> dict:
        return self.post(f"/employee/{employee_id}/employmentDetails", {"role": {"id": role_id}})

    # ── Customers ────────────────────────────────────────────────────────────

    def list_customers(self, **params) -> list[dict]:
        data = self.get("/customer", params={"fields": "id,name,email,phoneNumber", **params})
        return data.get("values", [])

    def create_customer(self, payload: dict) -> dict:
        return self.post("/customer", {"isCustomer": True, **payload})["value"]

    def get_customer(self, customer_id: int) -> dict:
        return self.get(f"/customer/{customer_id}", params={"fields": "*"})["value"]

    def update_customer(self, customer_id: int, payload: dict) -> dict:
        return self.put(f"/customer/{customer_id}", payload)["value"]

    # ── Products ─────────────────────────────────────────────────────────────

    def list_products(self, **params) -> list[dict]:
        data = self.get("/product", params={"fields": "id,name,costExcludingVatCurrency,priceExcludingVatCurrency", **params})
        return data.get("values", [])

    def create_product(self, payload: dict) -> dict:
        return self.post("/product", payload)["value"]

    def get_product(self, product_id: int) -> dict:
        return self.get(f"/product/{product_id}", params={"fields": "*"})["value"]

    # ── Orders ───────────────────────────────────────────────────────────────

    def create_order(self, payload: dict) -> dict:
        return self.post("/order", payload)["value"]

    def get_order(self, order_id: int) -> dict:
        return self.get(f"/order/{order_id}", params={"fields": "*"})["value"]

    def add_order_line(self, order_id: int, payload: dict) -> dict:
        return self.post(f"/orderline", {"order": {"id": order_id}, **payload})["value"]

    # ── Invoices ─────────────────────────────────────────────────────────────

    def create_invoice(self, payload: dict) -> dict:
        return self.post("/invoice", payload)["value"]

    def get_invoice(self, invoice_id: int) -> dict:
        return self.get(f"/invoice/{invoice_id}", params={"fields": "*"})["value"]

    def list_invoices(self, **params) -> list[dict]:
        data = self.get("/invoice", params={"fields": "id,invoiceNumber,customer,amountCurrency", **params})
        return data.get("values", [])

    def send_invoice(self, invoice_id: int, send_type: str = "EMAIL") -> None:
        self.put(f"/invoice/{invoice_id}/:send", {"sendType": send_type})

    def create_credit_note(self, invoice_id: int, payload: dict | None = None) -> dict:
        return self.post(f"/invoice/{invoice_id}/:createCreditNote", payload or {})["value"]

    # ── Payments ─────────────────────────────────────────────────────────────

    def register_payment(self, invoice_id: int, payload: dict) -> dict:
        return self.post(f"/invoice/{invoice_id}/:payment", payload)["value"]

    # ── Projects ─────────────────────────────────────────────────────────────

    def list_projects(self, **params) -> list[dict]:
        data = self.get("/project", params={"fields": "id,name,customer", **params})
        return data.get("values", [])

    def create_project(self, payload: dict) -> dict:
        return self.post("/project", payload)["value"]

    def get_project(self, project_id: int) -> dict:
        return self.get(f"/project/{project_id}", params={"fields": "*"})["value"]

    # ── Departments ───────────────────────────────────────────────────────────

    def list_departments(self, **params) -> list[dict]:
        data = self.get("/department", params={"fields": "id,name", **params})
        return data.get("values", [])

    def create_department(self, payload: dict) -> dict:
        return self.post("/department", payload)["value"]

    # ── Travel Expenses ───────────────────────────────────────────────────────

    def list_travel_expenses(self, **params) -> list[dict]:
        data = self.get("/travelExpense", params={"fields": "id,description,employee", **params})
        return data.get("values", [])

    def get_travel_expense(self, expense_id: int) -> dict:
        return self.get(f"/travelExpense/{expense_id}", params={"fields": "*"})["value"]

    def create_travel_expense(self, payload: dict) -> dict:
        return self.post("/travelExpense", payload)["value"]

    def delete_travel_expense(self, expense_id: int) -> None:
        self.delete(f"/travelExpense/{expense_id}")

    # ── Company / Modules ─────────────────────────────────────────────────────

    def get_company(self) -> dict:
        return self.get("/company", params={"fields": "*"})["value"]

    def get_modules(self) -> dict:
        return self.get("/company/modules", params={"fields": "*"})["value"]

    def enable_module(self, module_name: str) -> None:
        modules = self.get_modules()
        modules[module_name] = True
        self.put("/company/modules", modules)
