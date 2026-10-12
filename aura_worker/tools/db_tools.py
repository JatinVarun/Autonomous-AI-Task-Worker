"""Database Query Tools (Python)"""

from typing import Dict, Any, Optional
from ..environment.db import db_instance
from ..environment.erp_service import erp_instance


def db_query_audit(limit: int = 10, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Query internal system audit logs and recent actions performed by the agent."""
    try:
        task_id = (context or {}).get("task_id", "")
        trail = db_instance.get_audit_trail(task_id)[:limit]
        return {"success": True, "count": len(trail), "logs": trail}
    except Exception as e:
        return {"success": False, "error": str(e)}


def db_check_order_status(order_id: str) -> Dict[str, Any]:
    """Check customer order status, fulfillment, and refund state."""
    try:
        order = erp_instance.get_order(order_id)
        if not order:
            return {"success": False, "error": f"Order '{order_id}' not found in database"}
        return {"success": True, "order": order}
    except Exception as e:
        return {"success": False, "error": str(e)}
