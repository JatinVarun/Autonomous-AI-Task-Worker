import test from "node:test";
import assert from "node:assert/strict";
import { outcomeVerifier } from "../server/agent/verifier.js";
import { erpInstance } from "../server/environment/erpService.js";

test("OutcomeVerifier - Positive verification of ERP Invoice", async () => {
  erpInstance.reset();
  erpInstance.createInvoice({
    vendorName: "Acme Industrial Solutions",
    invoiceNumber: "INV-VERIF-TEST",
    amount: 14250.00,
    dueDate: "2024-11-15"
  });

  const verification = await outcomeVerifier.verify({
    taskGoal: "Enter invoice",
    scratchpad: {
      invoiceNumber: "INV-VERIF-TEST",
      vendorName: "Acme Industrial Solutions",
      amount: 14250.00,
      dueDate: "2024-11-15"
    },
    executedActions: [{ action: "erp_create_invoice" }]
  });

  assert.equal(verification.verified, true);
  assert.ok(verification.proofSignature);
  assert.equal(verification.checks.length, 3);
  assert.ok(verification.checks.every(c => c.passed));
});

test("OutcomeVerifier - Detects discrepancy / missing record", async () => {
  erpInstance.reset();

  const verification = await outcomeVerifier.verify({
    taskGoal: "Enter invoice",
    scratchpad: {
      invoiceNumber: "NON_EXISTENT_INV",
      vendorName: "Acme",
      amount: 999.00,
      dueDate: "2024-12-31"
    },
    executedActions: []
  });

  assert.equal(verification.verified, false);
  assert.equal(verification.checks[0].passed, false);
});
