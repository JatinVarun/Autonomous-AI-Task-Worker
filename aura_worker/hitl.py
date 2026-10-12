"""Human-in-the-Loop (HITL) Safety & Approval Manager (Python)"""

from typing import Dict, Any, Optional, Callable
from .environment.db import db_instance


class HumanInTheLoopManager:
    def __init__(self, high_value_threshold: float = 10000.0, require_refund_approval: bool = True):
        self.high_value_threshold = high_value_threshold
        self.require_refund_approval = require_refund_approval
        self.active_resolvers: Dict[str, Callable] = {}

    def evaluate_risk(self, action_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate whether an action requires human review before proceeding."""
        # 1. High-value Invoice Creation
        if action_name == "erp_create_invoice":
            try:
                amt = float(parameters.get("amount", 0))
            except (ValueError, TypeError):
                amt = 0.0

            if amt >= self.high_value_threshold:
                vendor = parameters.get("vendor_name") or parameters.get("vendorName", "Vendor")
                return {
                    "requires_approval": True,
                    "reason": f"High-value financial commitment: Invoice amount of ${amt:,.2f} exceeds threshold limit (${self.high_value_threshold:,.2f}).",
                    "severity": "HIGH",
                    "summary": f"Approve registering high-value invoice for {vendor} (${amt:,.2f})?"
                }

        # 2. Direct Refund Issuance
        if action_name == "erp_process_refund" and self.require_refund_approval:
            order_id = parameters.get("order_id") or parameters.get("orderId", "N/A")
            amt = parameters.get("amount", 0)
            return {
                "requires_approval": True,
                "reason": f"Customer refund transaction: Processing refund of ${amt} for Order {order_id}.",
                "severity": "MEDIUM",
                "summary": f"Approve issuing refund of ${amt} for Order {order_id}?"
            }

        return {"requires_approval": False}

    def request_approval(self, task_id: str, action_name: str, parameters: Dict[str, Any], risk_assessment: Dict[str, Any]) -> Dict[str, Any]:
        """Create and record pending approval request in database."""
        return db_instance.create_approval_request(
            task_id=task_id,
            action=action_name,
            parameters=parameters,
            reason=risk_assessment.get("reason", "Action requires human approval"),
            severity=risk_assessment.get("severity", "HIGH")
        )

    def resolve_approval(self, approval_id: str, decision: str, user_comment: str = "") -> Dict[str, Any]:
        """Resolve a pending approval request."""
        return db_instance.resolve_approval(approval_id, decision, user_comment)


global_hitl_manager = HumanInTheLoopManager()
