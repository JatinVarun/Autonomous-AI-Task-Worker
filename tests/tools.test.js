import test from "node:test";
import assert from "node:assert/strict";
import { globalToolRegistry } from "../server/tools/index.js";
import { erpInstance } from "../server/environment/erpService.js";

test("ToolRegistry - Tools list and schema definitions", () => {
  const schemas = globalToolRegistry.listToolSchemas();
  assert.ok(schemas.length >= 8, "Expected at least 8 tools in registry");
  const toolNames = schemas.map(s => s.name);
  assert.ok(toolNames.includes("list_files"));
  assert.ok(toolNames.includes("read_file"));
  assert.ok(toolNames.includes("erp_create_invoice"));
  assert.ok(toolNames.includes("verify_task_outcome"));
});

test("FileTool - List files in mock storage", async () => {
  const result = await globalToolRegistry.execute("list_files", { directory: "invoices" });
  assert.equal(result.success, true);
  assert.ok(result.files.length >= 2, "Expected multiple invoice files");
  const acmeFile = result.files.find(f => f.name.includes("Acme_Invoice_INV-2024-889.txt"));
  assert.ok(acmeFile, "Acme invoice file should exist in invoices directory");
});

test("FileTool - Read invoice file content", async () => {
  const result = await globalToolRegistry.execute("read_file", { filePath: "invoices/Acme_Invoice_INV-2024-889.txt" });
  assert.equal(result.success, true);
  assert.ok(result.content.includes("INV-2024-889"));
  assert.ok(result.content.includes("14,250.00"));
});

test("ERPTool - Create invoice with validations", async () => {
  erpInstance.reset();
  const createResult = await globalToolRegistry.execute("erp_create_invoice", {
    vendorName: "Acme Industrial Solutions",
    invoiceNumber: "INV-TEST-001",
    amount: 1500.00,
    dueDate: "2024-12-01"
  });

  assert.equal(createResult.success, true);
  assert.ok(createResult.invoice.id.startsWith("ERP-INV-"));
  assert.equal(createResult.invoice.amount, 1500.00);

  // Duplicate check
  const duplicateResult = await globalToolRegistry.execute("erp_create_invoice", {
    vendorName: "Acme Industrial Solutions",
    invoiceNumber: "INV-TEST-001",
    amount: 1500.00,
    dueDate: "2024-12-01"
  });
  assert.equal(duplicateResult.success, false);
  assert.ok(duplicateResult.error.includes("DuplicateInvoiceError"));
});
