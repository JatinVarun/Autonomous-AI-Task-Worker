/**
 * Human-in-the-Loop (HITL) Safety & Approval Manager
 * Intercepts high-risk actions, financial commitments above thresholds,
 * or ambiguous instructions, prompting the user for approval or clarification.
 */

import { dbInstance } from "../environment/db.js";

export class HumanInTheLoopManager {
  constructor(options = {}) {
    this.highValueThreshold = options.highValueThreshold ?? 10000; // Invoices >= $10,000 require approval
    this.requireRefundApproval = options.requireRefundApproval ?? true;
    this.activeResolvers = new Map(); // approvalId -> { resolve, reject }
  }

  /**
   * Evaluate whether an action requires human review before proceeding.
   */
  evaluateRisk(actionName, parameters, context = {}) {
    // 1. High-value Invoice Creation
    if (actionName === "erp_create_invoice") {
      const amount = Number(parameters.amount || 0);
      if (amount >= this.highValueThreshold) {
        return {
          requiresApproval: true,
          reason: `High-value financial commitment: Invoice amount of $${amount.toLocaleString()} exceeds enterprise approval limit ($${this.highValueThreshold.toLocaleString()}).`,
          severity: "HIGH",
          summary: `Approve registering high-value invoice for ${parameters.vendorName} ($${amount.toLocaleString()})?`
        };
      }
    }

    // 2. Direct Refund Issuance
    if (actionName === "erp_process_refund" && this.requireRefundApproval) {
      return {
        requiresApproval: true,
        reason: `Customer refund transaction: Processing refund of $${parameters.amount} for Order ${parameters.orderId}.`,
        severity: "MEDIUM",
        summary: `Approve issuing refund of $${parameters.amount} for Order ${parameters.orderId}?`
      };
    }

    // 3. Ambiguity / Clarification explicitly flagged by agent
    if (actionName === "request_clarification") {
      return {
        requiresApproval: true,
        reason: parameters.question || "Worker requires clarification to proceed safely.",
        severity: "INFO",
        summary: parameters.question
      };
    }

    return { requiresApproval: false };
  }

  /**
   * Request human approval and suspend agent execution until resolved.
   */
  async requestApproval({ taskId, runId, actionName, parameters, riskAssessment, onApprovalPending }) {
    const approvalRecord = dbInstance.createApprovalRequest({
      taskId,
      runId,
      action: actionName,
      parameters,
      reason: riskAssessment.reason,
      severity: riskAssessment.severity
    });

    if (onApprovalPending) {
      onApprovalPending(approvalRecord);
    }

    // Return a Promise that resolves when the user sends an approval/rejection via the API/WebSocket
    return new Promise((resolve) => {
      this.activeResolvers.set(approvalRecord.id, {
        resolve: (decision, userComment) => {
          this.activeResolvers.delete(approvalRecord.id);
          resolve({
            id: approvalRecord.id,
            decision, // "APPROVED" or "REJECTED"
            userComment,
            resolvedAt: new Date().toISOString()
          });
        }
      });
    });
  }

  /**
   * Called by the API when the user clicks Approve / Reject in the UI.
   */
  resolveApproval(approvalId, decision, userComment = "") {
    const record = dbInstance.resolveApproval(approvalId, decision, userComment);
    const resolver = this.activeResolvers.get(approvalId);
    if (resolver) {
      resolver.resolve(decision, userComment);
    }
    return record;
  }
}

export const globalHitlManager = new HumanInTheLoopManager();
