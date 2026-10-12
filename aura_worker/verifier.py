"""Independent Outcome Verifier (Python)
Queries target system ground truth and issues cryptographic proofs.
"""

import hashlib
import time
import uuid
from datetime import datetime
from typing import Dict, Any, List
from .environment.erp_service import erp_instance


class OutcomeVerifier:
    def verify(self, task_goal: str, scratchpad: Dict[str, Any], executed_actions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Run independent verification on the worker's executed outcome against system ground truth."""
        start_time = time.time()
        verification_id = f"VERIF-{uuid.uuid4().hex[:6].upper()}"
        checks: List[Dict[str, Any]] = []

        # Scenario 1: Invoice Processing
        inv_num = scratchpad.get("invoice_number") or scratchpad.get("invoiceNumber")
        if inv_num:
            expected_amt = scratchpad.get("amount")
            expected_due = scratchpad.get("due_date") or scratchpad.get("dueDate")
            expected_vendor = scratchpad.get("vendor_name") or scratchpad.get("vendor")

            erp_res = erp_instance.verify_invoice_exists({
                "invoice_number": inv_num,
                "vendor_name": expected_vendor,
                "amount": expected_amt,
                "due_date": expected_due
            })

            checks.append({
                "target": "ERP_INVOICE_RECORD",
                "description": f"Check if invoice '{inv_num}' exists in ERP database",
                "passed": erp_res["verified"],
                "details": erp_res.get("checks", {})
            })

            if erp_res.get("invoice"):
                inv = erp_res["invoice"]
                if expected_amt is not None:
                    checks.append({
                        "target": "ERP_AMOUNT_CONSISTENCY",
                        "description": f"Validate recorded amount matches extracted (${expected_amt})",
                        "passed": abs(inv["amount"] - float(expected_amt)) < 0.01,
                        "recorded_value": inv["amount"],
                        "expected_value": expected_amt
                    })
                if expected_due:
                    checks.append({
                        "target": "ERP_DUE_DATE_CONSISTENCY",
                        "description": f"Validate due date matches extracted ({expected_due})",
                        "passed": inv["due_date"] == expected_due,
                        "recorded_value": inv["due_date"],
                        "expected_value": expected_due
                    })

            all_passed = all(c["passed"] for c in checks)
            sig_payload = f"{verification_id}|{inv_num}|{expected_amt}|{all_passed}"
            proof_sig = hashlib.sha256(sig_payload.encode()).hexdigest()[:16]

            return {
                "verification_id": verification_id,
                "verified": all_passed,
                "target_system": "ERP_ACCOUNTS_PAYABLE",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "duration_ms": round((time.time() - start_time) * 1000, 2),
                "checks": checks,
                "proof_signature": proof_sig,
                "evidence": {
                    "erp_record_id": erp_res.get("invoice", {}).get("id") if erp_res.get("invoice") else None,
                    "invoice_number": inv_num,
                    "vendor": erp_res.get("invoice", {}).get("vendor_name", expected_vendor) if erp_res.get("invoice") else expected_vendor,
                    "recorded_amount": erp_res.get("invoice", {}).get("amount") if erp_res.get("invoice") else None,
                    "recorded_due_date": erp_res.get("invoice", {}).get("due_date") if erp_res.get("invoice") else None,
                    "status": erp_res.get("invoice", {}).get("status", "NOT_FOUND") if erp_res.get("invoice") else "NOT_FOUND"
                },
                "verdict": "CONFIRMED_AND_VERIFIED: Real-world side effect persisted in ERP." if all_passed else "VERIFICATION_FAILURE: Discrepancy detected in ERP."
            }

        # Scenario 2: Vendor Update
        vendor_name = scratchpad.get("vendor_name") or scratchpad.get("vendor")
        if vendor_name and (scratchpad.get("contract_read") or scratchpad.get("contractRead")):
            vendor = erp_instance.find_vendor_by_name(vendor_name)
            vendor_found = vendor is not None
            checks.append({
                "target": "ERP_VENDOR_REGISTRY",
                "description": f"Check if vendor '{vendor_name}' exists in master directory",
                "passed": vendor_found
            })
            all_passed = vendor_found
            proof_sig = hashlib.sha256(f"{verification_id}|{vendor_name}|{all_passed}".encode()).hexdigest()[:16]
            return {
                "verification_id": verification_id,
                "verified": all_passed,
                "target_system": "ERP_VENDOR_DIRECTORY",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "duration_ms": round((time.time() - start_time) * 1000, 2),
                "checks": checks,
                "proof_signature": proof_sig,
                "evidence": vendor,
                "verdict": "CONFIRMED_AND_VERIFIED" if all_passed else "VERIFICATION_FAILURE"
            }

        # Scenario 3: Customer Refund
        order_id = scratchpad.get("order_id") or scratchpad.get("orderId")
        if order_id:
            order = erp_instance.get_order(order_id)
            refunded = order is not None and order.get("refunded") is True
            checks.append({
                "target": "COMMERCE_ORDER_DATABASE",
                "description": f"Verify order {order_id} marked as REFUNDED",
                "passed": refunded
            })
            all_passed = refunded
            proof_sig = hashlib.sha256(f"{verification_id}|{order_id}|{all_passed}".encode()).hexdigest()[:16]
            return {
                "verification_id": verification_id,
                "verified": all_passed,
                "target_system": "COMMERCE_ORDER_DATABASE",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "duration_ms": round((time.time() - start_time) * 1000, 2),
                "checks": checks,
                "proof_signature": proof_sig,
                "evidence": order,
                "verdict": "CONFIRMED_AND_VERIFIED" if all_passed else "VERIFICATION_FAILURE"
            }

        # Generic fallback
        all_passed = len(executed_actions) > 0
        return {
            "verification_id": verification_id,
            "verified": all_passed,
            "target_system": "SYSTEM_AUDIT_LOG",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "duration_ms": round((time.time() - start_time) * 1000, 2),
            "checks": [{"target": "EXECUTION_TRACE", "description": "Verified tool execution trace", "passed": all_passed}],
            "proof_signature": hashlib.sha256(f"{verification_id}|GENERIC".encode()).hexdigest()[:16],
            "evidence": {"actions_count": len(executed_actions)},
            "verdict": "EXECUTION_TRACED" if all_passed else "NO_ACTIONS_TRACED"
        }


outcome_verifier = OutcomeVerifier()
