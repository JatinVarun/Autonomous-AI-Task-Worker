import { dbInstance } from "../environment/db.js";
import { erpInstance } from "../environment/erpService.js";

export const databaseTools = {
  db_query_audit: {
    name: "db_query_audit",
    description: "Query internal system audit logs and recent actions performed by the agent or system.",
    parameters: {
      type: "object",
      properties: {
        limit: {
          type: "number",
          description: "Max number of audit log entries to return (default 10)",
          default: 10
        }
      }
    },
    async execute({ limit = 10 }, context) {
      try {
        const taskId = context?.taskId;
        const trail = dbInstance.getAuditTrail({ taskId }).slice(0, limit);
        return { success: true, count: trail.length, logs: trail };
      } catch (err) {
        return { success: false, error: err.message };
      }
    }
  },

  db_check_order_status: {
    name: "db_check_order_status",
    description: "Check customer order status, fulfillment, and refund state in the commerce database.",
    parameters: {
      type: "object",
      required: ["orderId"],
      properties: {
        orderId: {
          type: "string",
          description: "Customer Order ID (e.g. 'ORD-99381')"
        }
      }
    },
    async execute({ orderId }) {
      try {
        const order = erpInstance.getOrder(orderId);
        if (!order) {
          return { success: false, error: `Order ${orderId} not found in database` };
        }
        return { success: true, order };
      } catch (err) {
        return { success: false, error: err.message };
      }
    }
  }
};
