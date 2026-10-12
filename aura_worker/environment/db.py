"""Internal State & Task Database (Python)"""

from datetime import datetime
import uuid
from typing import Dict, Any, List, Optional


class Database:
    def __init__(self):
        self.tasks: Dict[str, Dict[str, Any]] = {}
        self.approvals: Dict[str, Dict[str, Any]] = {}
        self.audit_trail: List[Dict[str, Any]] = []

    def save_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        task_id = task["id"]
        task["updated_at"] = datetime.utcnow().isoformat() + "Z"
        self.tasks[task_id] = task
        return task

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        return self.tasks.get(task_id)

    def list_tasks(self) -> List[Dict[str, Any]]:
        return sorted(list(self.tasks.values()), key=lambda x: x.get("created_at", ""), reverse=True)

    def create_approval_request(self, task_id: str, action: str, parameters: Dict[str, Any], reason: str, severity: str = "HIGH") -> Dict[str, Any]:
        approval_id = f"APPR-{uuid.uuid4().hex[:6].upper()}"
        record = {
            "id": approval_id,
            "task_id": task_id,
            "action": action,
            "parameters": parameters,
            "reason": reason,
            "severity": severity,
            "status": "PENDING",  # PENDING, APPROVED, REJECTED
            "created_at": datetime.utcnow().isoformat() + "Z",
            "resolved_at": None,
            "user_comment": ""
        }
        self.approvals[approval_id] = record
        return record

    def resolve_approval(self, approval_id: str, decision: str, user_comment: str = "") -> Dict[str, Any]:
        record = self.approvals.get(approval_id)
        if not record:
            raise ValueError(f"Approval request '{approval_id}' not found")
        record["status"] = decision
        record["resolved_at"] = datetime.utcnow().isoformat() + "Z"
        record["user_comment"] = user_comment
        return record

    def get_approval(self, approval_id: str) -> Optional[Dict[str, Any]]:
        return self.approvals.get(approval_id)

    def list_pending_approvals(self, task_id: str = "") -> List[Dict[str, Any]]:
        return [
            a for a in self.approvals.values()
            if a["status"] == "PENDING" and (not task_id or a["task_id"] == task_id)
        ]

    def add_audit(self, event: Dict[str, Any]) -> Dict[str, Any]:
        record = {
            "id": f"EVT-{uuid.uuid4().hex[:6].upper()}",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            **event
        }
        self.audit_trail.insert(0, record)
        return record

    def get_audit_trail(self, task_id: str = "") -> List[Dict[str, Any]]:
        if not task_id:
            return list(self.audit_trail)
        return [e for e in self.audit_trail if e.get("task_id") == task_id or e.get("taskId") == task_id]

    def clear(self):
        self.tasks.clear()
        self.approvals.clear()
        self.audit_trail.clear()


db_instance = Database()
