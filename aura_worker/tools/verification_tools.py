"""Independent Verification & Notification Tools (Python)"""

import hashlib
import uuid
from datetime import datetime
from typing import Dict, Any
from ..environment.erp_service import erp_instance


def verify_task_outcome(entity_type: str, expected: Dict[str, Any]) -> Dict[str, Any]:
    """Independently verify whether the target outcome was successfully achieved in company systems."""
    try:
        verification_id = f"VERIF-{uuid.uuid4().hex[:6].upper()}"
        timestamp = datetime.utcnow().isoformat() + "Z"

        if entity_type == "erp_invoice":
            res = erp_instance.verify_invoice_exists(expected)
            if not res["verified"]:
                return {
                    "success": False,
                    "verified": False,
                    "verification_id": verification_id,
                    "timestamp": timestamp,
                    "reason": res.get("reason"),
                    "checks": res.get("checks", {})
                }

            inv = res["invoice"]
            signature_payload = f"{inv['id']}|{inv['invoice_number']}|{inv['amount']}|{timestamp}"
            proof_sig = hashlib.sha256(signature_payload.encode()).hexdigest()[:16]

            return {
                "success": True,
                "verified": True,
                "verification_id": verification_id,
                "timestamp": timestamp,
                "proof_signature": proof_sig,
                "verified_record": {
                    "erp_id": inv["id"],
                    "invoice_number": inv["invoice_number"],
                    "vendor": inv["vendor_name"],
                    "amount": inv["amount"],
                    "due_date": inv["due_date"],
                    "status": inv["status"],
                    "verification_status": inv["verification_status"]
                },
                "checks": res["checks"],
                "summary": f"Outcome verified: Invoice {inv['invoice_number']} (${inv['amount']}) is confirmed in ERP (ID: {inv['id']})."
            }

        if entity_type == "erp_vendor":
            v_name = expected.get("vendor_name") or expected.get("name", "")
            vendor = erp_instance.find_vendor_by_name(v_name)
            if not vendor:
                return {"success": False, "verified": False, "reason": f"Vendor '{v_name}' not found in ERP"}

            checks = {}
            if "tax_id" in expected:
                checks["tax_id_match"] = vendor["tax_id"] == expected["tax_id"]
            if "payment_terms" in expected:
                checks["terms_match"] = vendor["payment_terms"] == expected["payment_terms"]

            verified = all(checks.values())
            proof_sig = hashlib.sha256(f"{verification_id}|{v_name}|{verified}".encode()).hexdigest()[:16]

            return {
                "success": True,
                "verified": verified,
                "verification_id": verification_id,
                "timestamp": timestamp,
                "proof_signature": proof_sig,
                "verified_record": vendor,
                "checks": checks,
                "summary": f"Vendor '{vendor['name']}' updates verified in ERP." if verified else "Vendor verification failed."
            }

        if entity_type == "order_refund":
            order_id = expected.get("order_id")
            order = erp_instance.get_order(order_id)
            if not order:
                return {"success": False, "verified": False, "reason": f"Order {order_id} not found"}

            verified = order.get("refunded") is True
            proof_sig = hashlib.sha256(f"{verification_id}|{order_id}|{verified}".encode()).hexdigest()[:16]

            return {
                "success": True,
                "verified": verified,
                "verification_id": verification_id,
                "timestamp": timestamp,
                "proof_signature": proof_sig,
                "verified_record": order,
                "summary": f"Refund for Order {order_id} verified in database." if verified else "Refund not marked."
            }

        return {"success": False, "error": f"Unsupported verification entity_type: '{entity_type}'"}
    except Exception as e:
        return {"success": False, "error": f"Verification failed: {str(e)}"}


def notify_user_completion(summary: str, outcome_status: str, evidence: Dict[str, Any]) -> Dict[str, Any]:
    """Send final completion summary and evidence packet to the user."""
    return {
        "success": True,
        "delivered": True,
        "delivered_at": datetime.utcnow().isoformat() + "Z",
        "summary": summary,
        "outcome_status": outcome_status,
        "evidence": evidence
    }
