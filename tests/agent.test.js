import test from "node:test";
import assert from "node:assert/strict";
import { AutonomousWorker } from "../server/agent/AutonomousWorker.js";
import { erpInstance } from "../server/environment/erpService.js";

test("AutonomousWorker - Executes benchmark invoice task end-to-end with verification", async () => {
  erpInstance.reset();

  const eventsEmitted = [];
  const worker = new AutonomousWorker({
    onEvent: (event) => eventsEmitted.push(event),
    skipApprovals: true, // Auto-approve for automated testing
    stepDelay: 0
  });

  const goal = "Find the latest invoice from Acme Corp, extract the amount and due date, enter it into our internal system, and tell me once it is done.";
  const result = await worker.startTask(goal);

  // Assertions on autonomous execution
  assert.equal(result.status, "COMPLETED_VERIFIED");
  assert.equal(result.discoveredState.invoiceNumber, "INV-2024-889");
  assert.equal(result.discoveredState.amount, 14250.00);
  assert.equal(result.discoveredState.dueDate, "2024-11-15");

  // Verify ERP side effect
  const erpInvoice = erpInstance.getInvoiceById("INV-2024-889");
  assert.ok(erpInvoice, "Invoice should be recorded in ERP");
  assert.equal(erpInvoice.amount, 14250.00);
  assert.equal(erpInvoice.dueDate, "2024-11-15");
  assert.equal(erpInvoice.verificationStatus, "VERIFIED_ACCURATE");

  // Verify verification proof
  assert.ok(result.verificationProof.verified);
  assert.ok(result.verificationProof.proofSignature);

  // Check event stream
  const eventTypes = eventsEmitted.map(e => e.event);
  assert.ok(eventTypes.includes("TASK_STARTED"));
  assert.ok(eventTypes.includes("PLAN_GENERATED"));
  assert.ok(eventTypes.includes("REASONING_STEP"));
  assert.ok(eventTypes.includes("OBSERVATION_RECEIVED"));
  assert.ok(eventTypes.includes("VERIFICATION_COMPLETED"));
  assert.ok(eventTypes.includes("TASK_COMPLETED"));
});

test("AutonomousWorker - Handles Globex JSON invoice task", async () => {
  erpInstance.reset();

  const worker = new AutonomousWorker({
    skipApprovals: true,
    stepDelay: 0
  });

  const goal = "Find the invoice from Globex Logistics Corp, parse its JSON amount and due date, register it in the ERP system, and verify.";
  const result = await worker.startTask(goal);

  assert.equal(result.status, "COMPLETED_VERIFIED");
  assert.equal(result.discoveredState.invoiceNumber, "GL-2024-902");
  assert.equal(result.discoveredState.amount, 6850.50);

  const erpInvoice = erpInstance.getInvoiceById("GL-2024-902");
  assert.ok(erpInvoice);
  assert.equal(erpInvoice.amount, 6850.50);
});

test("AutonomousWorker - Human-in-the-Loop intercepts high-value invoice and resumes upon approval", async () => {
  erpInstance.reset();

  let pendingApprovalRecord = null;
  const worker = new AutonomousWorker({
    skipApprovals: false, // Enforce HITL
    stepDelay: 0,
    onEvent: (event) => {
      if (event.event === "WAITING_FOR_USER_APPROVAL") {
        pendingApprovalRecord = event.approvalRecord;
        // Simulate user clicking "Approve" after 10ms
        setTimeout(async () => {
          const { globalHitlManager } = await import("../server/agent/humanInTheLoop.js");
          globalHitlManager.resolveApproval(pendingApprovalRecord.id, "APPROVED", "Approved by testing suite");
        }, 10);
      }
    }
  });

  const goal = "Find the latest invoice from Acme Corp, extract the amount and due date, enter it into our internal system, and tell me once it is done.";
  const result = await worker.startTask(goal);

  assert.ok(pendingApprovalRecord, "Should have triggered HITL approval prompt for $14,250 invoice");
  assert.equal(pendingApprovalRecord.severity, "HIGH");
  assert.equal(result.status, "COMPLETED_VERIFIED");
});

test("AutonomousWorker - Executes Initech vendor master agreement update", async () => {
  erpInstance.reset();

  const worker = new AutonomousWorker({
    skipApprovals: true,
    stepDelay: 0
  });

  const goal = "Locate the vendor agreement for Initech Technologies, extract approved tax ID and payment terms, update the ERP vendor master directory, and verify.";
  const result = await worker.startTask(goal);

  assert.equal(result.status, "COMPLETED_VERIFIED");
  assert.equal(result.discoveredState.vendorName, "Initech Technologies Ltd");

  const vendor = erpInstance.findVendorByName("Initech");
  assert.ok(vendor);
  assert.equal(vendor.taxId, "IN-9948201");
  assert.equal(vendor.paymentTerms, "Net 45 Days");
});

test("AutonomousWorker - Executes customer refund ticket with database check", async () => {
  erpInstance.reset();

  const worker = new AutonomousWorker({
    skipApprovals: true,
    stepDelay: 0
  });

  const goal = "Process refund request in email ticket #REF-842, check order status in database, submit refund transaction, and verify completion.";
  const result = await worker.startTask(goal);

  assert.equal(result.status, "COMPLETED_VERIFIED");
  assert.equal(result.discoveredState.orderId, "ORD-99381");
  assert.equal(result.discoveredState.refundAmount, 79.00);

  const order = erpInstance.getOrder("ORD-99381");
  assert.ok(order);
  assert.equal(order.refunded, true);
  assert.equal(order.status, "REFUNDED");
});
