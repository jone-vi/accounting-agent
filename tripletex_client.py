"""Tripletex API client — thin wrapper around the REST API."""

import json
import logging

import httpx

logger = logging.getLogger(__name__)


def _log_request(method: str, url: str, body: dict | None = None, params: dict | None = None) -> None:
    parts = [f"→ {method} {url}"]
    if params:
        parts.append(f"  params: {json.dumps(params)}")
    if body:
        parts.append(f"  body:   {json.dumps(body, ensure_ascii=False)}")
    logger.info("\n".join(parts))


def _log_response(resp: httpx.Response) -> None:
    emoji = "✓" if resp.is_success else "✗"
    logger.info("%s %s %s", emoji, resp.status_code, resp.url.path)
    if resp.is_error:
        logger.error("  error body: %s", resp.text)


def _raise_with_body(resp: httpx.Response) -> None:
    if resp.is_error:
        raise httpx.HTTPStatusError(
            f"HTTP {resp.status_code}: {resp.text}",
            request=resp.request,
            response=resp,
        )


class TripletexClient:
    def __init__(self, base_url: str, session_token: str):
        self.base_url = base_url.rstrip("/")
        self.auth = ("0", session_token)

    def get(self, path: str, params: dict | None = None) -> dict:
        url = f"{self.base_url}{path}"
        _log_request("GET", url, params=params)
        resp = httpx.get(url, auth=self.auth, params=params, timeout=30)
        _log_response(resp)
        _raise_with_body(resp)
        return resp.json()

    def post(self, path: str, body: dict) -> dict:
        url = f"{self.base_url}{path}"
        _log_request("POST", url, body=body)
        resp = httpx.post(url, auth=self.auth, json=body, timeout=30)
        _log_response(resp)
        _raise_with_body(resp)
        return resp.json()

    def put(self, path: str, body: dict | None = None, params: dict | None = None) -> dict:
        url = f"{self.base_url}{path}"
        _log_request("PUT", url, body=body, params=params)
        resp = httpx.put(url, auth=self.auth, json=body or {}, params=params, timeout=30)
        _log_response(resp)
        _raise_with_body(resp)
        try:
            return resp.json()
        except Exception:
            return {}

    def delete(self, path: str) -> None:
        url = f"{self.base_url}{path}"
        _log_request("DELETE", url)
        resp = httpx.delete(url, auth=self.auth, timeout=30)
        _log_response(resp)
        _raise_with_body(resp)

    # ── Employees ────────────────────────────────────────────────────────────

    def list_employees(self, **params) -> list[dict]:
        data = self.get("/employee", params={"fields": "id,firstName,lastName,email,phoneNumberMobile,userType", **params})
        return data.get("values", [])

    def _default_department_id(self) -> int | None:
        """Return the first available department ID, or None if none exist."""
        depts = self.list_departments()
        return depts[0]["id"] if depts else None

    def create_employee(self, payload: dict) -> dict:
        # department.id is required when department module is enabled
        if "department" not in payload:
            dept_id = self._default_department_id()
            if dept_id:
                payload = {"department": {"id": dept_id}, **payload}
        return self.post("/employee", payload)["value"]

    def get_employee(self, employee_id: int) -> dict:
        return self.get(f"/employee/{employee_id}", params={"fields": "*"})["value"]

    def update_employee(self, employee_id: int, payload: dict) -> dict:
        return self.put(f"/employee/{employee_id}", payload)["value"]

    def create_employment(self, payload: dict) -> dict:
        return self.post("/employee/employment", payload)["value"]

    def grant_entitlement_template(self, employee_id: int, customer_id: int, template: str) -> dict:
        return self.put(
            "/employee/entitlement/:grantClientEntitlementsByTemplate",
            params={"employeeId": employee_id, "customerId": customer_id, "template": template},
        )

    # ── Customers ────────────────────────────────────────────────────────────

    def list_customers(self, **params) -> list[dict]:
        data = self.get("/customer", params={"fields": "id,name,email,phoneNumber,organizationNumber", **params})
        return data.get("values", [])

    def create_customer(self, payload: dict) -> dict:
        return self.post("/customer", {"isCustomer": True, **payload})["value"]

    def get_customer(self, customer_id: int) -> dict:
        return self.get(f"/customer/{customer_id}", params={"fields": "*"})["value"]

    def update_customer(self, customer_id: int, payload: dict) -> dict:
        return self.put(f"/customer/{customer_id}", payload)["value"]

    # ── Products ─────────────────────────────────────────────────────────────

    def list_products(self, **params) -> list[dict]:
        data = self.get("/product", params={"fields": "id,name,number,priceExcludingVatCurrency,costExcludingVatCurrency", **params})
        return data.get("values", [])

    def create_product(self, payload: dict) -> dict:
        return self.post("/product", payload)["value"]

    # ── Orders ───────────────────────────────────────────────────────────────

    def create_order(self, payload: dict) -> dict:
        return self.post("/order", payload)["value"]

    def invoice_order(self, order_id: int, params: dict) -> dict:
        result = self.put(f"/order/{order_id}/:invoice", params=params)
        return result.get("value", result)

    def add_order_line(self, payload: dict) -> dict:
        return self.post("/order/orderline", payload)["value"]

    # ── Invoices ─────────────────────────────────────────────────────────────

    def list_invoices(self, **params) -> list[dict]:
        data = self.get("/invoice", params={"fields": "id,invoiceNumber,customer,invoiceDate,amountCurrency,amountOutstanding", **params})
        return data.get("values", [])

    def send_invoice(self, invoice_id: int, send_type: str, override_email: str | None = None) -> dict:
        params: dict = {"sendType": send_type}
        if override_email:
            params["overrideEmailAddress"] = override_email
        return self.put(f"/invoice/{invoice_id}/:send", params=params)

    def register_payment(self, invoice_id: int, payload: dict) -> dict:
        return self.put(f"/invoice/{invoice_id}/:payment", params=payload)

    def create_credit_note(self, invoice_id: int) -> dict:
        return self.put(f"/invoice/{invoice_id}/:createCreditNote").get("value", {})

    # ── Projects ─────────────────────────────────────────────────────────────

    def list_projects(self, **params) -> list[dict]:
        data = self.get("/project", params={"fields": "id,name,number,customer,projectManager,isClosed", **params})
        return data.get("values", [])

    def create_project(self, payload: dict) -> dict:
        return self.post("/project", payload)["value"]

    def add_project_participant(self, payload: dict) -> dict:
        return self.post("/project/participant", payload)["value"]

    # ── Departments ───────────────────────────────────────────────────────────

    def list_departments(self, **params) -> list[dict]:
        data = self.get("/department", params={"fields": "id,name,departmentNumber", **params})
        return data.get("values", [])

    def create_department(self, payload: dict) -> dict:
        return self.post("/department", payload)["value"]

    # ── Travel Expenses ───────────────────────────────────────────────────────

    def list_travel_expenses(self, **params) -> list[dict]:
        data = self.get("/travelExpense", params={"fields": "id,title,employee,date,state", **params})
        return data.get("values", [])

    def create_travel_expense(self, payload: dict) -> dict:
        return self.post("/travelExpense", payload)["value"]

    def delete_travel_expense(self, expense_id: int) -> None:
        self.delete(f"/travelExpense/{expense_id}")

    def deliver_travel_expense(self, expense_id: int) -> dict:
        return self.put(f"/travelExpense/:deliver", params={"id": expense_id})

    def add_travel_cost(self, payload: dict) -> dict:
        return self.post("/travelExpense/cost", payload)["value"]

    def add_mileage_allowance(self, payload: dict) -> dict:
        return self.post("/travelExpense/mileageAllowance", payload)["value"]

    def add_per_diem_compensation(self, payload: dict) -> dict:
        return self.post("/travelExpense/perDiemCompensation", payload)["value"]

    # ── Vouchers / Ledger ─────────────────────────────────────────────────────

    def list_vouchers(self, **params) -> list[dict]:
        data = self.get("/ledger/voucher", params={"fields": "id,number,date,description,postings", **params})
        return data.get("values", [])

    def create_voucher(self, payload: dict) -> dict:
        return self.post("/ledger/voucher", payload)["value"]

    def reverse_voucher(self, voucher_id: int, date: str) -> dict:
        return self.put(f"/ledger/voucher/{voucher_id}/:reverse", params={"date": date})

    def list_accounts(self, **params) -> list[dict]:
        data = self.get("/ledger/account", params={"fields": "id,number,name,type", **params})
        return data.get("values", [])

    # ── Salary / Payroll ──────────────────────────────────────────────────────

    def list_salary_types(self, **params) -> list[dict]:
        data = self.get("/salary/type", params={"fields": "id,number,name,description,isTaxable,isPayrollTaxable", **params})
        return data.get("values", [])

    def create_salary_transaction(self, payload: dict) -> dict:
        return self.post("/salary/transaction", payload)["value"]

    def list_payslips(self, **params) -> list[dict]:
        data = self.get("/salary/payslip", params={"fields": "id,employee,year,month,grossAmount,amount", **params})
        return data.get("values", [])

    # ── Suppliers ─────────────────────────────────────────────────────────────

    def list_suppliers(self, **params) -> list[dict]:
        data = self.get("/supplier", params={"fields": "id,name,email,organizationNumber,supplierNumber", **params})
        return data.get("values", [])

    def create_supplier(self, payload: dict) -> dict:
        return self.post("/supplier", {"isSupplier": True, **payload})["value"]

    # ── Timesheet / Activities ─────────────────────────────────────────────────

    def list_activities(self, **params) -> list[dict]:
        data = self.get("/activity", params={"fields": "id,name,number,activityType,isGeneral,isProjectActivity", **params})
        return data.get("values", [])

    def create_timesheet_entry(self, payload: dict) -> dict:
        return self.post("/timesheet/entry", payload)["value"]

    # ── Company / Modules ─────────────────────────────────────────────────────

    def who_am_i(self) -> dict:
        return self.get("/token/session/>whoAmI", params={"fields": "employeeId,companyId,company"})["value"]

    def get_company(self) -> dict:
        info = self.who_am_i()
        company_id = info.get("companyId") or info.get("company", {}).get("id")
        return self.get(f"/company/{company_id}", params={"fields": "id,name,organizationNumber,customerId"})["value"]

    def grant_entitlements_by_template(self, employee_id: int, template: str) -> dict:
        return self.put(
            "/employee/entitlement/:grantEntitlementsByTemplate",
            params={"employeeId": employee_id, "template": template},
        )

    def get_modules(self) -> dict:
        return self.get("/company/modules", params={"fields": "*"})["value"]

    def enable_module(self, module_name: str) -> None:
        modules = self.get_modules()
        modules[module_name] = True
        self.put("/company/modules", modules)
