from aura_worker.environment.erp_service import erp_instance
from aura_worker.tools.registry import global_tool_registry


def test_tool_registry_schemas():
    schemas = global_tool_registry.list_tool_schemas()
    assert len(schemas) >= 8
    names = [s["name"] for s in schemas]
    assert "list_files" in names
    assert "read_file" in names
    assert "erp_create_invoice" in names
    assert "verify_task_outcome" in names


def test_list_invoice_files():
    result = global_tool_registry.execute("list_files", {"directory": "invoices"})
    assert result["success"] is True
    assert len(result["files"]) >= 2
    acme = next((f for f in result["files"] if "Acme_Invoice_INV-2024-889.txt" in f["name"]), None)
    assert acme is not None


def test_read_invoice_file():
    result = global_tool_registry.execute("read_file", {"file_path": "invoices/Acme_Invoice_INV-2024-889.txt"})
    assert result["success"] is True
    assert "INV-2024-889" in result["content"]
    assert "14,250.00" in result["content"]


def test_erp_create_invoice_and_duplicate():
    erp_instance.reset()
    created = global_tool_registry.execute("erp_create_invoice", {
        "vendor_name": "Acme Industrial Solutions",
        "invoice_number": "INV-TEST-001",
        "amount": 1500.00,
        "due_date": "2024-12-01",
    })
    assert created["success"] is True
    assert created["invoice"]["id"].startswith("ERP-INV-")
    assert created["invoice"]["amount"] == 1500.00

    duplicate = global_tool_registry.execute("erp_create_invoice", {
        "vendor_name": "Acme Industrial Solutions",
        "invoice_number": "INV-TEST-001",
        "amount": 1500.00,
        "due_date": "2024-12-01",
    })
    assert duplicate["success"] is False
    assert "DuplicateInvoiceError" in duplicate["error"]
