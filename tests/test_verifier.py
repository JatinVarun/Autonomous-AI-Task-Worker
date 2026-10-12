from aura_worker.environment.erp_service import erp_instance
from aura_worker.verifier import outcome_verifier


def test_positive_invoice_verification():
    erp_instance.reset()
    erp_instance.create_invoice({
        "vendor_name": "Acme Industrial Solutions",
        "invoice_number": "INV-VERIF-TEST",
        "amount": 14250.00,
        "due_date": "2024-11-15",
    })
    verification = outcome_verifier.verify(
        task_goal="Enter invoice",
        scratchpad={
            "invoice_number": "INV-VERIF-TEST",
            "vendor_name": "Acme Industrial Solutions",
            "amount": 14250.00,
            "due_date": "2024-11-15",
        },
        executed_actions=[{"action": "erp_create_invoice"}],
    )
    assert verification["verified"] is True
    assert verification["proof_signature"]
    assert len(verification["checks"]) == 3
    assert all(c["passed"] for c in verification["checks"])


def test_missing_invoice_fails_verification():
    erp_instance.reset()
    verification = outcome_verifier.verify(
        task_goal="Enter invoice",
        scratchpad={
            "invoice_number": "NON_EXISTENT_INV",
            "vendor_name": "Acme",
            "amount": 999.00,
            "due_date": "2024-12-31",
        },
        executed_actions=[],
    )
    assert verification["verified"] is False
    assert verification["checks"][0]["passed"] is False
