"""Simulated Enterprise ERP Tools (Python)"""

from typing import Dict, Any, Optional
from ..environment.erp_service import erp_instance


def erp_search_vendors(query: str = "") -> Dict[str, Any]:
    """Search or list vendors in the ERP system."""
    try:
        all_vendors = erp_instance.list_vendors()
        if not query:
            return {"success": True, "count": len(all_vendors), "vendors": all_vendors}

        q = query.lower()
        filtered = [
            v for v in all_vendors
            if q in v["name"].lower() or any(q in a.lower() for a in v.get("aliases", [])) or q in v["tax_id"].lower()
        ]
        return {"success": True, "count": len(filtered), "vendors": filtered}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _normalize_vendor_updates(updates: Dict[str, Any]) -> Dict[str, Any]:
    key_map = {
        "taxId": "tax_id",
        "tax_id": "tax_id",
        "paymentTerms": "payment_terms",
        "payment_terms": "payment_terms",
        "status": "status",
        "contactEmail": "contact_email",
        "contact_email": "contact_email",
    }
    normalized = {}
    for k, v in (updates or {}).items():
        normalized[key_map.get(k, k)] = v
    return normalized


def erp_update_vendor(vendor_id_or_name: str, updates: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Update details for an existing vendor in the ERP."""
    try:
        actor = (context or {}).get("agent_id", "AI_WORKER")
        updated = erp_instance.update_vendor(vendor_id_or_name, _normalize_vendor_updates(updates), actor)
        return {
            "success": True,
            "message": f"Vendor '{updated['name']}' updated successfully",
            "vendor": updated
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def erp_list_invoices(vendor_name: str = "", status: str = "") -> Dict[str, Any]:
    """Query existing invoices in the ERP."""
    try:
        invoices = erp_instance.list_invoices(vendor_name, status)
        return {"success": True, "count": len(invoices), "invoices": invoices}
    except Exception as e:
        return {"success": False, "error": str(e)}


def erp_get_invoice(invoice_id: str) -> Dict[str, Any]:
    """Retrieve details of an invoice from the ERP by ID or invoice number."""
    try:
        inv = erp_instance.get_invoice_by_id(invoice_id)
        if not inv:
            return {"success": False, "error": f"Invoice '{invoice_id}' not found in internal ERP"}
        return {"success": True, "invoice": inv}
    except Exception as e:
        return {"success": False, "error": str(e)}


def erp_create_invoice(vendor_name: str, invoice_number: str, amount: float, due_date: str, currency: str = "USD", po_number: str = "N/A", context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Enter and register a new vendor invoice into the internal ERP system."""
    try:
        actor = (context or {}).get("agent_id", "AI_WORKER")
        created = erp_instance.create_invoice({
            "vendor_name": vendor_name,
            "invoice_number": invoice_number,
            "amount": amount,
            "due_date": due_date,
            "currency": currency,
            "po_number": po_number
        }, actor)
        return {
            "success": True,
            "message": f"Invoice {created['invoice_number']} recorded in ERP with ID {created['id']}",
            "invoice": created
        }
    except Exception as e:
        return {"success": False, "error": f"ERP create_invoice failed: {str(e)}"}


def erp_process_refund(order_id: str, amount: float, reason: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Issue a customer refund in the ERP."""
    try:
        actor = (context or {}).get("agent_id", "AI_WORKER")
        updated_order = erp_instance.issue_refund(order_id, amount, reason, actor)
        return {
            "success": True,
            "message": f"Refund of ${amount} processed for Order {order_id}",
            "order": updated_order
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
