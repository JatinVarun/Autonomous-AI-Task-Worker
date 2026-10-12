export const notificationTools = {
  notify_user_completion: {
    name: "notify_user_completion",
    description: "Send the final completion summary and evidence packet to the user once the task has been executed and verified.",
    parameters: {
      type: "object",
      required: ["summary", "outcomeStatus", "evidence"],
      properties: {
        summary: {
          type: "string",
          description: "Concise summary of actions taken and results achieved"
        },
        outcomeStatus: {
          type: "string",
          enum: ["SUCCESS", "PARTIAL", "FAILED", "BLOCKED"],
          description: "Final status of task execution"
        },
        evidence: {
          type: "object",
          description: "Structured evidence proof (e.g. { invoiceId, amount, dueDate, verificationId, proofSignature })"
        }
      }
    },
    async execute({ summary, outcomeStatus, evidence }, context) {
      return {
        success: true,
        delivered: true,
        deliveredAt: new Date().toISOString(),
        summary,
        outcomeStatus,
        evidence
      };
    }
  }
};
