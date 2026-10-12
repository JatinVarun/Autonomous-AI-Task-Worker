from aura_worker.environment.erp_service import erp_instance
from aura_worker.worker import AutonomousWorker


def test_acme_invoice_end_to_end():
    erp_instance.reset()
    events = []
    worker = AutonomousWorker(on_event=events.append, skip_approvals=True)
    result = worker.start_task(
        "Find the latest invoice from Acme Corp, extract the amount and due date, enter it into our internal system, and tell me once it is done."
    )

    assert result["status"] == "COMPLETED_VERIFIED"
    state = result["discovered_state"]
    assert state["invoice_number"] == "INV-2024-889"
    assert state["amount"] == 14250.00
    assert state["due_date"] == "2024-11-15"

    erp_invoice = erp_instance.get_invoice_by_id("INV-2024-889")
    assert erp_invoice is not None
    assert erp_invoice["amount"] == 14250.00
    assert erp_invoice["due_date"] == "2024-11-15"
    assert erp_invoice["verification_status"] == "VERIFIED_ACCURATE"

    assert result["verification_proof"]["verified"] is True
    assert result["verification_proof"]["proof_signature"]

    event_types = [e["event"] for e in events]
    for required in (
        "TASK_STARTED",
        "PLAN_GENERATED",
        "REASONING_STEP",
        "OBSERVATION_RECEIVED",
        "VERIFICATION_COMPLETED",
        "TASK_COMPLETED",
    ):
        assert required in event_types


def test_globex_json_invoice():
    erp_instance.reset()
    worker = AutonomousWorker(skip_approvals=True)
    result = worker.start_task(
        "Find the invoice from Globex Logistics Corp, parse its JSON amount and due date, register it in the ERP system, and verify."
    )
    assert result["status"] == "COMPLETED_VERIFIED"
    assert result["discovered_state"]["invoice_number"] == "GL-2024-902"
    assert result["discovered_state"]["amount"] == 6850.50
    erp_invoice = erp_instance.get_invoice_by_id("GL-2024-902")
    assert erp_invoice is not None
    assert erp_invoice["amount"] == 6850.50


def test_hitl_pauses_then_resumes_on_approval():
    erp_instance.reset()
    worker = AutonomousWorker(skip_approvals=False)
    paused = worker.start_task(
        "Find the latest invoice from Acme Corp, extract the amount and due date, enter it into our internal system, and tell me once it is done."
    )
    assert paused["status"] == "WAITING_FOR_APPROVAL"
    assert paused["approval"]["severity"] == "HIGH"
    result = worker.resume("APPROVED", "Approved by testing suite")
    assert result["status"] == "COMPLETED_VERIFIED"


def test_initech_vendor_update():
    erp_instance.reset()
    worker = AutonomousWorker(skip_approvals=True)
    result = worker.start_task(
        "Locate the vendor agreement for Initech Technologies, extract approved tax ID and payment terms, update the ERP vendor master directory, and verify."
    )
    assert result["status"] == "COMPLETED_VERIFIED"
    assert result["discovered_state"]["vendor_name"] == "Initech Technologies Ltd"
    vendor = erp_instance.find_vendor_by_name("Initech")
    assert vendor is not None
    assert vendor["tax_id"] == "IN-9948201"
    assert vendor["payment_terms"] == "Net 45 Days"


def test_refund_ticket():
    erp_instance.reset()
    worker = AutonomousWorker(skip_approvals=True)
    result = worker.start_task(
        "Process refund request in email ticket #REF-842, check order status in database, submit refund transaction, and verify completion."
    )
    assert result["status"] == "COMPLETED_VERIFIED"
    assert result["discovered_state"]["order_id"] == "ORD-99381"
    assert result["discovered_state"]["refund_amount"] == 79.00
    order = erp_instance.get_order("ORD-99381")
    assert order is not None
    assert order["refunded"] is True
    assert order["status"] == "REFUNDED"
