"""Agent Working Memory & State Tracker (Python)"""

import time
from datetime import datetime
from typing import Dict, Any, List, Optional


class AgentMemory:
    def __init__(self, goal: str):
        self.goal = goal
        self.plan: List[Dict[str, Any]] = []
        self.scratchpad: Dict[str, Any] = {}
        self.history: List[Dict[str, Any]] = []
        self.errors: List[Dict[str, Any]] = []
        self.evidence: Dict[str, Any] = {}
        self.start_time = time.time()

    def set_plan(self, steps: List[Any]):
        self.plan = [
            {
                "id": idx + 1,
                "title": s if isinstance(s, str) else s.get("title", ""),
                "description": s.get("description", "") if isinstance(s, dict) else "",
                "status": "PENDING"
            }
            for idx, s in enumerate(steps)
        ]

    def update_step_status(self, step_id: int, status: str):
        for step in self.plan:
            if step["id"] == step_id:
                step["status"] = status
                break

    def set_scratchpad(self, key: str, value: Any):
        self.scratchpad[key] = value

    def get_scratchpad(self, key: str, default: Any = None) -> Any:
        return self.scratchpad.get(key, default)

    def record_history(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        record = {
            "step_number": len(self.history) + 1,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            **entry
        }
        self.history.append(record)
        return record

    def record_error(self, error: Any, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        err_record = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "error": str(error),
            "context": context or {},
            "step_number": len(self.history)
        }
        self.errors.append(err_record)
        return err_record

    def set_evidence(self, key: str, value: Any):
        self.evidence[key] = value

    def get_execution_summary(self) -> Dict[str, Any]:
        duration_ms = round((time.time() - self.start_time) * 1000, 2)
        return {
            "duration_ms": duration_ms,
            "total_steps_executed": len(self.history),
            "errors_encountered": len(self.errors),
            "plan_progress": {
                "total": len(self.plan),
                "completed": sum(1 for s in self.plan if s["status"] == "COMPLETED"),
                "failed": sum(1 for s in self.plan if s["status"] == "FAILED")
            },
            "discovered_variables": dict(self.scratchpad),
            "evidence": dict(self.evidence)
        }

    def snapshot(self) -> Dict[str, Any]:
        return {
            "goal": self.goal,
            "plan": list(self.plan),
            "scratchpad": dict(self.scratchpad),
            "history_count": len(self.history),
            "errors": list(self.errors),
            "evidence": dict(self.evidence),
            "execution_summary": self.get_execution_summary()
        }
