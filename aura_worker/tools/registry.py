"""Tool Registry & Dispatcher (Python)"""

import time
from datetime import datetime
from typing import Dict, Any, List, Callable, Optional

from .file_tools import list_files, read_file, search_documents
from .erp_tools import (
    erp_search_vendors,
    erp_update_vendor,
    erp_list_invoices,
    erp_get_invoice,
    erp_create_invoice,
    erp_process_refund
)
from .browser_tools import browser_navigate_and_extract
from .db_tools import db_query_audit, db_check_order_status
from .verification_tools import verify_task_outcome, notify_user_completion


class ToolRegistry:
    def __init__(self):
        self.tools: Dict[str, Dict[str, Any]] = {}
        self._register_all()

    def _register_all(self):
        self.register(
            name="list_files",
            func=list_files,
            description="List available files and documents in company storage directories (e.g. 'invoices', 'contracts', 'emails').",
            parameters={
                "type": "object",
                "properties": {
                    "directory": {"type": "string", "description": "Subdirectory to list"}
                }
            }
        )
        self.register(
            name="read_file",
            func=read_file,
            description="Read the complete contents of a specific document or file by its relative path.",
            parameters={
                "type": "object",
                "required": ["file_path"],
                "properties": {
                    "file_path": {"type": "string", "description": "Relative file path"}
                }
            }
        )
        self.register(
            name="search_documents",
            func=search_documents,
            description="Search across company files for specific keywords.",
            parameters={
                "type": "object",
                "required": ["query"],
                "properties": {
                    "query": {"type": "string", "description": "Search keyword"}
                }
            }
        )
        self.register(
            name="erp_search_vendors",
            func=erp_search_vendors,
            description="Search or list company vendors in the internal ERP system.",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Vendor name query"}
                }
            }
        )
        self.register(
            name="erp_update_vendor",
            func=erp_update_vendor,
            description="Update details for an existing vendor in the ERP (e.g. tax ID, terms).",
            parameters={
                "type": "object",
                "required": ["vendor_id_or_name", "updates"],
                "properties": {
                    "vendor_id_or_name": {"type": "string"},
                    "updates": {"type": "object"}
                }
            }
        )
        self.register(
            name="erp_list_invoices",
            func=erp_list_invoices,
            description="Query existing invoices in the internal ERP system.",
            parameters={
                "type": "object",
                "properties": {
                    "vendor_name": {"type": "string"},
                    "status": {"type": "string"}
                }
            }
        )
        self.register(
            name="erp_get_invoice",
            func=erp_get_invoice,
            description="Retrieve details of an invoice from the ERP by ID or number.",
            parameters={
                "type": "object",
                "required": ["invoice_id"],
                "properties": {
                    "invoice_id": {"type": "string"}
                }
            }
        )
        self.register(
            name="erp_create_invoice",
            func=erp_create_invoice,
            description="Enter and register a new vendor invoice into the ERP system.",
            parameters={
                "type": "object",
                "required": ["vendor_name", "invoice_number", "amount", "due_date"],
                "properties": {
                    "vendor_name": {"type": "string"},
                    "invoice_number": {"type": "string"},
                    "amount": {"type": "number"},
                    "due_date": {"type": "string"}
                }
            }
        )
        self.register(
            name="erp_process_refund",
            func=erp_process_refund,
            description="Issue a customer refund in the ERP.",
            parameters={
                "type": "object",
                "required": ["order_id", "amount", "reason"],
                "properties": {
                    "order_id": {"type": "string"},
                    "amount": {"type": "number"},
                    "reason": {"type": "string"}
                }
            }
        )
        self.register(
            name="browser_navigate_and_extract",
            func=browser_navigate_and_extract,
            description="Navigate to a URL using a simulated headless browser to inspect web pages.",
            parameters={
                "type": "object",
                "required": ["url"],
                "properties": {"url": {"type": "string"}}
            }
        )
        self.register(
            name="db_query_audit",
            func=db_query_audit,
            description="Query internal system audit logs.",
            parameters={"type": "object", "properties": {"limit": {"type": "number"}}}
        )
        self.register(
            name="db_check_order_status",
            func=db_check_order_status,
            description="Check customer order status and refund state in database.",
            parameters={
                "type": "object",
                "required": ["order_id"],
                "properties": {"order_id": {"type": "string"}}
            }
        )
        self.register(
            name="verify_task_outcome",
            func=verify_task_outcome,
            description="Independently verify whether the target outcome was successfully achieved in the company systems.",
            parameters={
                "type": "object",
                "required": ["entity_type", "expected"],
                "properties": {
                    "entity_type": {"type": "string"},
                    "expected": {"type": "object"}
                }
            }
        )
        self.register(
            name="notify_user_completion",
            func=notify_user_completion,
            description="Send final completion summary and evidence packet to user.",
            parameters={
                "type": "object",
                "required": ["summary", "outcome_status", "evidence"],
                "properties": {
                    "summary": {"type": "string"},
                    "outcome_status": {"type": "string"},
                    "evidence": {"type": "object"}
                }
            }
        )

    def register(self, name: str, func: Callable, description: str, parameters: Dict[str, Any]):
        self.tools[name] = {
            "name": name,
            "func": func,
            "description": description,
            "parameters": parameters
        }

    def list_tool_schemas(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": t["name"],
                "description": t["description"],
                "parameters": t["parameters"]
            }
            for t in self.tools.values()
        ]

    def execute(self, name: str, params: Optional[Dict[str, Any]] = None, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        tool = self.tools.get(name)
        if not tool:
            return {
                "success": False,
                "error": f"Unknown tool: '{name}'. Available: {list(self.tools.keys())}"
            }

        params = params or {}
        context = context or {}

        # Adapt camelCase keys to snake_case if passed
        normalized_params: Dict[str, Any] = {}
        for k, v in params.items():
            snake_k = "".join(["_" + c.lower() if c.isupper() else c for c in k]).lstrip("_")
            normalized_params[snake_k] = v

        start_time = time.time()
        try:
            # Pass context if function accepts it
            import inspect
            sig = inspect.signature(tool["func"])
            call_args = {}
            for param_name in sig.parameters.keys():
                if param_name == "context":
                    call_args["context"] = context
                elif param_name in normalized_params:
                    call_args[param_name] = normalized_params[param_name]
                elif param_name in params:
                    call_args[param_name] = params[param_name]

            res = tool["func"](**call_args)
            duration_ms = round((time.time() - start_time) * 1000, 2)
            if isinstance(res, dict):
                res["_meta"] = {
                    "tool_name": name,
                    "duration_ms": duration_ms,
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                }
            return res
        except Exception as e:
            duration_ms = round((time.time() - start_time) * 1000, 2)
            return {
                "success": False,
                "error": f"Exception in tool '{name}': {str(e)}",
                "_meta": {
                    "tool_name": name,
                    "duration_ms": duration_ms,
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                }
            }


global_tool_registry = ToolRegistry()
