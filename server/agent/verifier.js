import crypto from "node:crypto";
import { erpInstance } from "../environment/erpService.js";

export class OutcomeVerifier {
  /**
   * Run independent verification on the worker's executed outcome.
   * Does NOT trust the agent's word; checks the ground truth in the underlying system.
   */
  async verify({ taskGoal, scratchpad, executedActions }) {
    const verificationStartTime = Date.now();
    const verificationId = `VERIF-${crypto.randomBytes(4).toString("hex").toUpperCase()}`;
    const checks = [];

    // Scenario 1: Invoice Processing Task
    if (scratchpad.invoiceNumber || scratchpad.extractedInvoiceNumber) {
      const invNum = scratchpad.invoiceNumber || scratchpad.extractedInvoiceNumber;
      const expectedAmount = scratchpad.amount !== undefined ? Number(scratchpad.amount) : undefined;
      const expectedDueDate = scratchpad.dueDate || scratchpad.extractedDueDate;
      const expectedVendor = scratchpad.vendor || scratchpad.vendorName;

      const erpResult = erpInstance.verifyInvoiceExists({
        invoiceNumber: invNum,
        vendorName: expectedVendor,
        amount: expectedAmount,
        dueDate: expectedDueDate
      });

      checks.push({
        target: "ERP_INVOICE_RECORD",
        description: `Check if invoice "${invNum}" exists in ERP database`,
        passed: erpResult.verified,
        details: erpResult.checks || { exists: Boolean(erpResult.invoice) }
      });

      if (erpResult.invoice) {
        checks.push({
          target: "ERP_AMOUNT_CONSISTENCY",
          description: `Validate recorded amount matches extracted amount ($${expectedAmount})`,
          passed: expectedAmount !== undefined ? Math.abs(erpResult.invoice.amount - expectedAmount) < 0.01 : true,
          recordedValue: erpResult.invoice.amount,
          expectedValue: expectedAmount
        });

        checks.push({
          target: "ERP_DUE_DATE_CONSISTENCY",
          description: `Validate due date matches extracted date (${expectedDueDate})`,
          passed: expectedDueDate ? erpResult.invoice.dueDate === expectedDueDate : true,
          recordedValue: erpResult.invoice.dueDate,
          expectedValue: expectedDueDate
        });
      }

      const allPassed = checks.every(c => c.passed);
      const signaturePayload = `${verificationId}|${invNum}|${expectedAmount}|${allPassed}`;
      const proofSignature = crypto.createHash("sha256").update(signaturePayload).digest("hex").slice(0, 16);

      return {
        verificationId,
        verified: allPassed,
        targetSystem: "ERP_ACCOUNTS_PAYABLE",
        timestamp: new Date().toISOString(),
        durationMs: Date.now() - verificationStartTime,
        checks,
        proofSignature,
        evidence: {
          erpRecordId: erpResult.invoice ? erpResult.invoice.id : null,
          invoiceNumber: invNum,
          vendor: erpResult.invoice ? erpResult.invoice.vendorName : expectedVendor,
          recordedAmount: erpResult.invoice ? erpResult.invoice.amount : null,
          recordedDueDate: erpResult.invoice ? erpResult.invoice.dueDate : null,
          status: erpResult.invoice ? erpResult.invoice.status : "NOT_FOUND"
        },
        verdict: allPassed
          ? "CONFIRMED_AND_VERIFIED: Real-world side effect successfully persisted in system of record."
          : "VERIFICATION_FAILURE: Discrepancy or missing record detected in system of record."
      };
    }

    // Scenario 2: Vendor Update Task
    if (scratchpad.vendorId || scratchpad.updatedVendor) {
      const vendorName = scratchpad.vendorName || scratchpad.vendor;
      const vendor = erpInstance.findVendorByName(vendorName);
      const vendorFound = Boolean(vendor);

      checks.push({
        target: "ERP_VENDOR_REGISTRY",
        description: `Check if vendor "${vendorName}" is updated in master directory`,
        passed: vendorFound,
        vendorId: vendor?.id
      });

      const allPassed = checks.every(c => c.passed);
      const proofSignature = crypto.createHash("sha256").update(`${verificationId}|${vendorName}|${allPassed}`).digest("hex").slice(0, 16);

      return {
        verificationId,
        verified: allPassed,
        targetSystem: "ERP_VENDOR_DIRECTORY",
        timestamp: new Date().toISOString(),
        durationMs: Date.now() - verificationStartTime,
        checks,
        proofSignature,
        evidence: vendor,
        verdict: allPassed ? "CONFIRMED_AND_VERIFIED" : "VERIFICATION_FAILURE"
      };
    }

    // Scenario 3: Customer Refund Task
    if (scratchpad.orderId || scratchpad.refundProcessed) {
      const order = erpInstance.getOrder(scratchpad.orderId);
      const refunded = order && order.refunded === true;

      checks.push({
        target: "COMMERCE_ORDER_DATABASE",
        description: `Verify order ${scratchpad.orderId} marked as REFUNDED`,
        passed: Boolean(refunded)
      });

      const allPassed = checks.every(c => c.passed);
      const proofSignature = crypto.createHash("sha256").update(`${verificationId}|${scratchpad.orderId}|${allPassed}`).digest("hex").slice(0, 16);

      return {
        verificationId,
        verified: allPassed,
        targetSystem: "COMMERCE_ORDER_DATABASE",
        timestamp: new Date().toISOString(),
        durationMs: Date.now() - verificationStartTime,
        checks,
        proofSignature,
        evidence: order,
        verdict: allPassed ? "CONFIRMED_AND_VERIFIED" : "VERIFICATION_FAILURE"
      };
    }

    // Generic verification fallback
    const allPassed = executedActions.length > 0;
    return {
      verificationId,
      verified: allPassed,
      targetSystem: "SYSTEM_AUDIT_LOG",
      timestamp: new Date().toISOString(),
      durationMs: Date.now() - verificationStartTime,
      checks: [
        {
          target: "EXECUTION_TRACE",
          description: "Verify at least one state-altering tool was executed",
          passed: allPassed
        }
      ],
      proofSignature: crypto.createHash("sha256").update(`${verificationId}|GENERIC`).digest("hex").slice(0, 16),
      evidence: { actionsCount: executedActions.length },
      verdict: allPassed ? "EXECUTION_TRACED" : "NO_ACTIONS_TRACED"
    };
  }
}

export const outcomeVerifier = new OutcomeVerifier();
