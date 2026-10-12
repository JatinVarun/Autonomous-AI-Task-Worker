import crypto from "node:crypto";
import { erpInstance } from "../environment/erpService.js";

export const verificationTools = {
  verify_task_outcome: {
    name: "verify_task_outcome",
    description: "Independently verify whether the target outcome was successfully achieved in the company systems before concluding the task. Checks actual system state against expected values and returns a cryptographic evidence receipt.",
    parameters: {
      type: "object",
      required: ["entityType", "expected"],
      properties: {
        entityType: {
          type: "string",
          enum: ["erp_invoice", "erp_vendor", "order_refund"],
          description: "Type of entity to verify in the target system"
        },
        expected: {
          type: "object",
          description: "Expected state fields (e.g. { invoiceNumber, vendorName, amount, dueDate } or { vendorName, taxId } or { orderId, refunded: true })"
        }
      }
    },
    async execute({ entityType, expected }) {
      try {
        const verificationId = `VERIF-${crypto.randomBytes(4).toString("hex").toUpperCase()}`;
        const timestamp = new Date().toISOString();

        if (entityType === "erp_invoice") {
          const res = erpInstance.verifyInvoiceExists(expected);
          if (!res.verified) {
            return {
              success: false,
              verified: false,
              verificationId,
              timestamp,
              reason: res.reason,
              checks: res.checks,
              recommendation: "Action was not verified in ERP. Re-check parameters and retry insertion."
            };
          }

          const signaturePayload = `${res.invoice.id}|${res.invoice.invoiceNumber}|${res.invoice.amount}|${timestamp}`;
          const proofSignature = crypto.createHash("sha256").update(signaturePayload).digest("hex").slice(0, 16);

          return {
            success: true,
            verified: true,
            verificationId,
            timestamp,
            proofSignature,
            verifiedRecord: {
              erpId: res.invoice.id,
              invoiceNumber: res.invoice.invoiceNumber,
              vendor: res.invoice.vendorName,
              amount: res.invoice.amount,
              dueDate: res.invoice.dueDate,
              status: res.invoice.status,
              verificationStatus: res.invoice.verificationStatus
            },
            checks: res.checks,
            summary: `Outcome successfully verified: Invoice ${res.invoice.invoiceNumber} ($${res.invoice.amount}) is confirmed registered in ERP with ID ${res.invoice.id}.`
          };
        }

        if (entityType === "erp_vendor") {
          const vendor = erpInstance.findVendorByName(expected.vendorName || expected.name);
          if (!vendor) {
            return {
              success: false,
              verified: false,
              reason: `Vendor '${expected.vendorName}' not found in ERP`
            };
          }

          const checks = {};
          if (expected.taxId) checks.taxIdMatch = vendor.taxId === expected.taxId;
          if (expected.paymentTerms) checks.termsMatch = vendor.paymentTerms === expected.paymentTerms;
          if (expected.status) checks.statusMatch = vendor.status === expected.status;

          const verified = Object.values(checks).every(Boolean);
          return {
            success: true,
            verified,
            verificationId,
            timestamp,
            verifiedRecord: vendor,
            checks,
            summary: verified
              ? `Vendor '${vendor.name}' updates verified in ERP.`
              : `Vendor verification failed: discrepancy detected in fields.`
          };
        }

        if (entityType === "order_refund") {
          const order = erpInstance.getOrder(expected.orderId);
          if (!order) {
            return { success: false, verified: false, reason: `Order ${expected.orderId} not found` };
          }
          const verified = order.refunded === true && (expected.amount ? order.refundDetails?.refundAmount === Number(expected.amount) : true);
          return {
            success: true,
            verified,
            verificationId,
            timestamp,
            verifiedRecord: order,
            summary: verified
              ? `Refund for Order ${order.orderId} verified processed in database.`
              : `Refund verification failed: order not marked as refunded.`
          };
        }

        return {
          success: false,
          error: `Unsupported verification entityType: ${entityType}`
        };
      } catch (err) {
        return { success: false, error: `Verification execution failed: ${err.message}` };
      }
    }
  }
};
