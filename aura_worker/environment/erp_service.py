"""Simulated Enterprise ERP Service (Python)
Maintains in-memory and persistent state for:
- Accounts Payable (Invoices)
- Vendor Master Directory
- Orders & Refunds
- Enterprise Audit Trail
"""

from datetime import datetime
from typing import Dict, Any, List, Optional


class ErpService:
    def __init__(self):
        self.reset()

    def reset(self):
        self.vendors: List[Dict[str, Any]] = [
            {
                "id": "VEND-001",
                "name": "Acme Industrial Solutions",
                "aliases": ["Acme Corp", "Acme", "Acme Industrial Solutions Inc."],
                "tax_id": "XX-9482103",
                "status": "ACTIVE",
                "payment_terms": "Net 30",
                "contact_email": "billing@acme-industrial.example.com",
                "current_balance": 0.0
            },
            {
                "id": "VEND-002",
                "name": "Globex Logistics Corp",
                "aliases": ["Globex", "Globex Logistics"],
                "tax_id": "US-8837194",
                "status": "ACTIVE",
                "payment_terms": "Net 30",
                "contact_email": "accounts@globex-logistics.example.com",
                "current_balance": 0.0
            },
            {
                "id": "VEND-003",
                "name": "Initech Technologies Ltd",
                "aliases": ["Initech", "Initech Technologies"],
                "tax_id": "IN-9948201",
                "status": "PENDING_VERIFICATION",
                "payment_terms": "Net 15",
                "contact_email": "accounting@initech.example.com",
                "current_balance": 0.0
            }
        ]

        self.invoices: List[Dict[str, Any]] = [
            {
                "id": "ERP-INV-1001",
                "invoice_number": "INV-2024-512",
                "vendor_id": "VEND-001",
                "vendor_name": "Acme Industrial Solutions",
                "amount": 2400.00,
                "currency": "USD",
                "due_date": "2024-06-10",
                "status": "PAID",
                "created_at": "2024-05-12T10:00:00Z",
                "source": "MANUAL_ENTRY",
                "verification_status": "VERIFIED"
            }
        ]

        self.orders: List[Dict[str, Any]] = [
            {
                "order_id": "ORD-99381",
                "customer_id": "CUST-4412",
                "customer_name": "Sarah Connor",
                "item": "Developer Pro License",
                "amount": 79.00,
                "currency": "USD",
                "status": "FULFILLED",
                "payment_method": "Credit Card (ending 4242)",
                "order_date": "2024-10-22T14:20:00Z",
                "refunded": False,
                "refund_details": None
            }
        ]

        self.audit_logs: List[Dict[str, Any]] = [
            {
                "id": "LOG-0001",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "actor": "SYSTEM_INIT",
                "action": "ERP_BOOTSTRAP",
                "details": "Initial enterprise ERP data loaded."
            }
        ]

    # --- Audit Log ---
    def record_audit(self, actor: str, action: str, details: Any) -> Dict[str, Any]:
        entry = {
            "id": f"LOG-{str(len(self.audit_logs) + 1).zfill(4)}",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "actor": actor,
            "action": action,
            "details": details
        }
        self.audit_logs.insert(0, entry)
        return entry

    # --- Vendors ---
    def find_vendor_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        if not name:
            return None
        clean = name.strip().lower()
        for v in self.vendors:
            if v["name"].lower() == clean or clean in v["name"].lower():
                return v
            if any(clean == a.lower() or clean in a.lower() for a in v.get("aliases", [])):
                return v
        return None

    def list_vendors(self) -> List[Dict[str, Any]]:
        return list(self.vendors)

    def update_vendor(self, id_or_name: str, updates: Dict[str, Any], actor: str = "AI_WORKER") -> Dict[str, Any]:
        vendor = next((v for v in self.vendors if v["id"] == id_or_name), None)
        if not vendor:
            vendor = self.find_vendor_by_name(id_or_name)
        if not vendor:
            raise ValueError(f"Vendor not found for identifier: '{id_or_name}'")

        vendor.update(updates)
        self.record_audit(actor, "UPDATE_VENDOR", {"vendor_id": vendor["id"], "updates": updates})
        return vendor

    # --- Invoices ---
    def list_invoices(self, vendor_name: str = "", status: str = "") -> List[Dict[str, Any]]:
        res = list(self.invoices)
        if vendor_name:
            q = vendor_name.lower()
            res = [i for i in res if q in i["vendor_name"].lower()]
        if status:
            res = [i for i in res if i["status"] == status]
        return res

    def get_invoice_by_id(self, invoice_id: str) -> Optional[Dict[str, Any]]:
        return next((i for i in self.invoices if i["id"] == invoice_id or i["invoice_number"].lower() == invoice_id.lower()), None)

    def create_invoice(self, payload: Dict[str, Any], actor: str = "AI_WORKER") -> Dict[str, Any]:
        vendor_name = payload.get("vendor_name") or payload.get("vendorName")
        invoice_num = payload.get("invoice_number") or payload.get("invoiceNumber")
        amount = payload.get("amount")
        due_date = payload.get("due_date") or payload.get("dueDate")
        currency = payload.get("currency", "USD")
        po_number = payload.get("po_number") or payload.get("poNumber", "N/A")

        if not vendor_name:
            raise ValueError("Missing required field: vendor_name")
        if not invoice_num:
            raise ValueError("Missing required field: invoice_number")
        if amount is None or str(amount).strip() == "":
            raise ValueError("Missing required field: amount")
        if not due_date:
            raise ValueError("Missing required field: due_date")

        try:
            num_amount = round(float(amount), 2)
        except (ValueError, TypeError):
            raise ValueError(f"Invalid amount value: '{amount}'")

        # Duplicate check
        existing = next((i for i in self.invoices if i["invoice_number"].lower() == str(invoice_num).lower()), None)
        if existing:
            raise ValueError(f"DuplicateInvoiceError: Invoice with number '{invoice_num}' is already registered (ID: {existing['id']})")

        vendor = self.find_vendor_by_name(vendor_name)
        vendor_id = vendor["id"] if vendor else "VEND-UNREGISTERED"
        resolved_name = vendor["name"] if vendor else vendor_name

        new_invoice = {
            "id": f"ERP-INV-{1000 + len(self.invoices) + 1}",
            "invoice_number": str(invoice_num).strip(),
            "vendor_id": vendor_id,
            "vendor_name": resolved_name,
            "amount": num_amount,
            "currency": currency.upper(),
            "due_date": str(due_date).strip(),
            "po_number": str(po_number).strip(),
            "status": "PENDING_PAYMENT",
            "created_at": datetime.utcnow().isoformat() + "Z",
            "source": actor,
            "verification_status": "RECORDED_PENDING_VERIFY"
        }

        self.invoices.insert(0, new_invoice)
        if vendor:
            vendor["current_balance"] = round(vendor.get("current_balance", 0.0) + num_amount, 2)

        self.record_audit(actor, "CREATE_INVOICE", {
            "invoice_id": new_invoice["id"],
            "invoice_number": new_invoice["invoice_number"],
            "vendor": resolved_name,
            "amount": num_amount,
            "due_date": new_invoice["due_date"]
        })

        return new_invoice

    # --- Orders & Refunds ---
    def get_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        return next((o for o in self.orders if o["order_id"] == order_id), None)

    def issue_refund(self, order_id: str, amount: float, reason: str, actor: str = "AI_WORKER") -> Dict[str, Any]:
        order = self.get_order(order_id)
        if not order:
            raise ValueError(f"Order '{order_id}' not found")
        if order.get("refunded"):
            raise ValueError(f"Order '{order_id}' has already been refunded")

        refund_amt = float(amount)
        if refund_amt > order["amount"]:
            raise ValueError(f"Refund amount (${refund_amt}) exceeds order amount (${order['amount']})")

        order["refunded"] = True
        order["status"] = "REFUNDED"
        order["refund_details"] = {
            "refund_amount": refund_amt,
            "reason": reason,
            "processed_at": datetime.utcnow().isoformat() + "Z",
            "processed_by": actor
        }

        self.record_audit(actor, "PROCESS_REFUND", {"order_id": order_id, "amount": refund_amt, "reason": reason})
        return order

    # --- Independent Verification ---
    def verify_invoice_exists(self, criteria: Dict[str, Any]) -> Dict[str, Any]:
        inv_num = criteria.get("invoice_number") or criteria.get("invoiceNumber", "")
        vendor_name = criteria.get("vendor_name") or criteria.get("vendorName", "")
        expected_amount = criteria.get("amount")
        expected_due_date = criteria.get("due_date") or criteria.get("dueDate", "")

        inv = next((i for i in self.invoices if i["invoice_number"].lower() == str(inv_num).lower()), None)
        if not inv:
            return {"verified": False, "reason": f"Invoice '{inv_num}' not found in ERP records", "checks": {}}

        checks = {
            "invoice_number_match": inv["invoice_number"].lower() == str(inv_num).lower(),
            "vendor_match": vendor_name.lower() in inv["vendor_name"].lower() if vendor_name else True,
            "amount_match": abs(inv["amount"] - float(expected_amount)) < 0.01 if expected_amount is not None else True,
            "due_date_match": inv["due_date"] == expected_due_date if expected_due_date else True
        }

        all_passed = all(checks.values())
        if all_passed:
            inv["verification_status"] = "VERIFIED_ACCURATE"

        return {
            "verified": all_passed,
            "invoice": inv,
            "checks": checks,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }


erp_instance = ErpService()
