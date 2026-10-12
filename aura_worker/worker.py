"""Autonomous worker: plan → ReAct loop → HITL gate → verify."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from .environment.db import db_instance
from .hitl import global_hitl_manager
from .llm.provider import global_llm_provider
from .memory import AgentMemory
from .tools.registry import global_tool_registry
from .verifier import outcome_verifier


class AutonomousWorker:
    def __init__(
        self,
        on_event: Optional[Callable[[Dict[str, Any]], None]] = None,
        max_steps: int = 12,
        skip_approvals: bool = False,
    ):
        self.max_steps = max_steps
        self.skip_approvals = skip_approvals
        self.event_emitter = on_event or (lambda _e: None)
        self.is_running = False
        self.status = "IDLE"
        self.task_id = ""
        self.run_id = ""
        self.goal = ""
        self.memory: Optional[AgentMemory] = None
        self.events: List[Dict[str, Any]] = []
        self.pending_action: Optional[Dict[str, Any]] = None
        self.pending_thought = ""
        self.pending_step_index = 0
        self.pending_approval: Optional[Dict[str, Any]] = None
        self.step_count = 0
        self.final_record: Optional[Dict[str, Any]] = None

    def emit(self, event_type: str, data: Optional[Dict[str, Any]] = None):
        payload = {
            "event": event_type,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "task_id": self.task_id,
            "run_id": self.run_id,
            **(data or {}),
        }
        db_instance.add_audit(payload)
        self.events.append(payload)
        self.event_emitter(payload)
        return payload

    def start_task(self, goal: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        options = options or {}
        if self.is_running and self.status not in ("WAITING_FOR_APPROVAL", "IDLE"):
            raise RuntimeError("Worker is already executing a task.")

        self.task_id = options.get("task_id") or f"TASK-{uuid.uuid4().hex[:6].upper()}"
        self.run_id = f"RUN-{uuid.uuid4().hex[:6].upper()}"
        self.goal = goal
        self.memory = AgentMemory(goal)
        self.events = []
        self.pending_action = None
        self.pending_approval = None
        self.step_count = 0
        self.final_record = None
        self.is_running = True
        self.status = "RUNNING"
        self.skip_approvals = options.get("skip_approvals", self.skip_approvals)

        db_instance.save_task({
            "id": self.task_id,
            "goal": goal,
            "status": "RUNNING",
            "created_at": datetime.utcnow().isoformat() + "Z",
        })
        self.emit("TASK_STARTED", {"goal": goal})

        try:
            initial_plan = global_llm_provider.generate_initial_plan(goal)
            self.memory.set_plan(initial_plan)
            self.emit("PLAN_GENERATED", {
                "plan": self.memory.plan,
                "goal_understanding": f"Parsed high-level user goal. Decomposed into {len(initial_plan)} sequential milestones.",
            })
            return self._run_loop()
        except Exception as err:
            self.is_running = False
            self.status = "FAILED"
            self.emit("TASK_FAILED", {"error": str(err)})
            db_instance.save_task({
                "id": self.task_id,
                "goal": self.goal,
                "status": "FAILED",
                "error": str(err),
            })
            raise

    def resume(self, decision: str, user_comment: str = "") -> Dict[str, Any]:
        if not self.pending_approval:
            raise RuntimeError("No pending approval to resume.")

        approval_id = self.pending_approval["id"]
        global_hitl_manager.resolve_approval(approval_id, decision, user_comment)
        self.emit("APPROVAL_RESOLVED", {
            "approval_result": {"id": approval_id, "decision": decision, "user_comment": user_comment}
        })

        if decision != "APPROVED":
            self.memory.record_error(f"User rejected action {self.pending_action['name']}", {"decision": decision})
            self.emit("ACTION_REJECTED", {
                "action_name": self.pending_action["name"],
                "reason": user_comment or "Rejected by user",
            })
            self.pending_action = None
            self.pending_approval = None
            self.status = "RUNNING"
            return self._run_loop()

        thought = self.pending_thought
        action = self.pending_action
        step_index = self.pending_step_index
        self.pending_action = None
        self.pending_approval = None
        self.status = "RUNNING"
        self._execute_action(step_index, thought, action)
        return self._run_loop()

    def _run_loop(self) -> Dict[str, Any]:
        task_finished = False

        while self.step_count < self.max_steps and not task_finished and self.is_running:
            self.step_count += 1
            tool_schemas = global_tool_registry.list_tool_schemas()
            decision = global_llm_provider.decide_next_step(
                goal=self.goal,
                memory=self.memory,
                step_count=self.step_count - 1,
                tools=tool_schemas,
            )

            if decision.get("completed"):
                task_finished = True
                self.emit("REASONING_STEP", {
                    "step_index": self.step_count,
                    "thought": decision.get("thought") or "All necessary actions have been performed. Initiating verification.",
                    "is_terminal": True,
                })
                break

            thought = decision.get("thought", "")
            action = decision.get("action") or {}
            self.emit("REASONING_STEP", {
                "step_index": self.step_count,
                "thought": thought,
                "intended_action": action,
            })

            risk = global_hitl_manager.evaluate_risk(action.get("name", ""), action.get("parameters") or {})
            if risk.get("requires_approval") and not self.skip_approvals:
                self.emit("APPROVAL_REQUESTED", {
                    "step_index": self.step_count,
                    "action_name": action.get("name"),
                    "parameters": action.get("parameters"),
                    "risk_assessment": risk,
                })
                record = global_hitl_manager.request_approval(
                    task_id=self.task_id,
                    action_name=action.get("name"),
                    parameters=action.get("parameters") or {},
                    risk_assessment=risk,
                )
                self.pending_action = action
                self.pending_thought = thought
                self.pending_step_index = self.step_count
                self.pending_approval = record
                self.status = "WAITING_FOR_APPROVAL"
                self.emit("WAITING_FOR_USER_APPROVAL", {"approval_record": record, "risk_assessment": risk})
                return {
                    "status": "WAITING_FOR_APPROVAL",
                    "task_id": self.task_id,
                    "approval": record,
                    "risk_assessment": risk,
                    "intended_action": action,
                    "events": self.events,
                    "plan": self.memory.plan if self.memory else [],
                    "discovered_state": self.memory.scratchpad if self.memory else {},
                }

            if self._execute_action(self.step_count, thought, action):
                task_finished = True

        return self._finalize()

    def _execute_action(self, step_index: int, thought: str, action: Dict[str, Any]) -> bool:
        self.emit("ACTION_EXECUTING", {
            "step_index": step_index,
            "tool_name": action.get("name"),
            "parameters": action.get("parameters"),
        })
        observation = global_tool_registry.execute(
            action.get("name"),
            action.get("parameters") or {},
            {"agent_id": "AI_WORKER", "task_id": self.task_id, "run_id": self.run_id},
        )
        self.memory.record_history({
            "thought": thought,
            "action": action,
            "observation": observation,
            "status": "SUCCESS" if observation.get("success") else "FAILURE",
        })
        self.emit("OBSERVATION_RECEIVED", {
            "step_index": step_index,
            "tool_name": action.get("name"),
            "observation": observation,
            "scratchpad": self.memory.scratchpad,
        })
        self._update_plan_progress(action.get("name"), observation)
        return action.get("name") == "notify_user_completion" and observation.get("success")

    def _finalize(self) -> Dict[str, Any]:
        self.emit("VERIFICATION_STARTED", {
            "message": "Running independent verification against underlying enterprise systems of record."
        })
        verification_result = outcome_verifier.verify(
            task_goal=self.goal,
            scratchpad=self.memory.scratchpad,
            executed_actions=self.memory.history,
        )
        self.memory.set_evidence("verification", verification_result)
        self.emit("VERIFICATION_COMPLETED", {"verification_result": verification_result})

        final_status = "COMPLETED_VERIFIED" if verification_result.get("verified") else "COMPLETED_UNVERIFIED"
        summary = self.memory.get_execution_summary()
        final_record = {
            "task_id": self.task_id,
            "run_id": self.run_id,
            "goal": self.goal,
            "status": final_status,
            "verification_proof": verification_result,
            "discovered_state": self.memory.scratchpad,
            "execution_timeline": self.memory.history,
            "plan": self.memory.plan,
            "summary": summary,
            "events": self.events,
        }
        db_instance.save_task({
            "id": self.task_id,
            "goal": self.goal,
            "status": final_status,
            "result": final_record,
        })
        self.emit("TASK_COMPLETED", final_record)
        self.is_running = False
        self.status = final_status
        self.final_record = final_record
        return final_record

    def _update_plan_progress(self, tool_name: str, observation: Dict[str, Any]):
        if not observation.get("success"):
            return
        mapping = {
            "list_files": 1,
            "search_documents": 1,
            "read_file": 2,
            "erp_search_vendors": 3,
            "erp_create_invoice": 4,
            "erp_update_vendor": 4,
            "erp_process_refund": 4,
            "verify_task_outcome": 5,
            "notify_user_completion": 6,
        }
        step_id = mapping.get(tool_name)
        if step_id:
            self.memory.update_step_status(step_id, "COMPLETED")

    def stop(self):
        self.is_running = False
        self.status = "ABORTED"
        self.emit("TASK_ABORTED", {"reason": "User triggered abort"})
