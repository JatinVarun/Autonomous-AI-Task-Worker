import { erpInstance } from "../environment/erpService.js";

export const erpTools = {
  erp_search_vendors: {
    name: "erp_search_vendors",
    description: "Search or list company vendors in the internal ERP system to retrieve vendor IDs, aliases, tax IDs, and payment terms.",
    parameters: {
      type: "object",
      properties: {
        query: {
          type: "string",
          description: "Vendor name or keyword (optional; returns all if omitted)",
          default: ""
        }
      }
    },
    async execute({ query = "" }) {
      try {
        const all = erpInstance.listVendors();
        if (!query) {
          return { success: true, count: all.length, vendors: all };
        }
        const filtered = all.filter(v =>
          v.name.toLowerCase().includes(query.toLowerCase()) ||
          v.aliases.some(a => a.toLowerCase().includes(query.toLowerCase())) ||
          v.taxId.toLowerCase().includes(query.toLowerCase())
        );
        return { success: true, count: filtered.length, vendors: filtered };
      } catch (err) {
        return { success: false, error: err.message };
      }
    }
  },

  erp_update_vendor: {
    name: "erp_update_vendor",
    description: "Update details for an existing vendor in the ERP (e.g. tax ID, payment terms, contact info, status).",
    parameters: {
      type: "object",
      required: ["vendorIdOrName", "updates"],
      properties: {
        vendorIdOrName: {
          type: "string",
          description: "Vendor ID (e.g. 'VEND-001') or name (e.g. 'Initech')"
        },
        updates: {
          type: "object",
          description: "Key-value updates such as { taxId, paymentTerms, status, contactEmail }"
        }
      }
    },
    async execute({ vendorIdOrName, updates }, context) {
      try {
        const actor = context?.agentId || "AI_WORKER";
        const updated = erpInstance.updateVendor(vendorIdOrName, updates, actor);
        return {
          success: true,
          message: `Vendor '${updated.name}' updated successfully`,
          vendor: updated
        };
      } catch (err) {
        return { success: false, error: err.message };
      }
    }
  },

  erp_list_invoices: {
    name: "erp_list_invoices",
    description: "Query existing invoices in the internal ERP by vendor name, status, or date range.",
    parameters: {
      type: "object",
      properties: {
        vendorName: {
          type: "string",
          description: "Optional vendor name to filter by"
        },
        status: {
          type: "string",
          description: "Optional status ('PAID', 'PENDING_PAYMENT', 'VOID')"
        }
      }
    },
    async execute(filters = {}) {
      try {
        const invoices = erpInstance.listInvoices(filters);
        return { success: true, count: invoices.length, invoices };
      } catch (err) {
        return { success: false, error: err.message };
      }
    }
  },

  erp_get_invoice: {
    name: "erp_get_invoice",
    description: "Retrieve complete details of a specific invoice from the ERP by its ERP ID (e.g. 'ERP-INV-1001') or invoice number (e.g. 'INV-2024-889').",
    parameters: {
      type: "object",
      required: ["invoiceId"],
      properties: {
        invoiceId: {
          type: "string",
          description: "Invoice ID or Invoice Number"
        }
      }
    },
    async execute({ invoiceId }) {
      try {
        const invoice = erpInstance.getInvoiceById(invoiceId);
        if (!invoice) {
          return { success: false, error: `Invoice '${invoiceId}' not found in internal ERP system` };
        }
        return { success: true, invoice };
      } catch (err) {
        return { success: false, error: err.message };
      }
    }
  },

  erp_create_invoice: {
    name: "erp_create_invoice",
    description: "Enter and register a new vendor invoice into the internal ERP system. Required fields: vendorName, invoiceNumber, amount, dueDate. Returns created record with ERP confirmation ID.",
    parameters: {
      type: "object",
      required: ["vendorName", "invoiceNumber", "amount", "dueDate"],
      properties: {
        vendorName: {
          type: "string",
          description: "Vendor name (e.g. 'Acme Industrial Solutions' or 'Globex Logistics')"
        },
        invoiceNumber: {
          type: "string",
          description: "Unique invoice identifier from the source bill (e.g. 'INV-2024-889')"
        },
        amount: {
          type: "number",
          description: "Total invoice amount due (e.g. 14250.00)"
        },
        dueDate: {
          type: "string",
          description: "Due date in YYYY-MM-DD format (e.g. '2024-11-15')"
        },
        currency: {
          type: "string",
          description: "Currency code (default 'USD')",
          default: "USD"
        },
        poNumber: {
          type: "string",
          description: "Associated Purchase Order number if available"
        }
      }
    },
    async execute(payload, context) {
      try {
        const actor = context?.agentId || "AI_WORKER";
        const created = erpInstance.createInvoice(payload, actor);
        return {
          success: true,
          message: `Invoice ${created.invoiceNumber} recorded in internal ERP with ID ${created.id}`,
          invoice: created
        };
      } catch (err) {
        return {
          success: false,
          error: `ERP create_invoice failed: ${err.message}`
        };
      }
    }
  },

  erp_process_refund: {
    name: "erp_process_refund",
    description: "Issue a customer refund in the ERP for a specified order ID and amount. High-impact financial transaction.",
    parameters: {
      type: "object",
      required: ["orderId", "amount", "reason"],
      properties: {
        orderId: {
          type: "string",
          description: "Customer Order ID (e.g. 'ORD-99381')"
        },
        amount: {
          type: "number",
          description: "Refund amount to be credited"
        },
        reason: {
          type: "string",
          description: "Detailed reason for the refund"
        }
      }
    },
    async execute({ orderId, amount, reason }, context) {
      try {
        const actor = context?.agentId || "AI_WORKER";
        const updatedOrder = erpInstance.issueRefund(orderId, amount, reason, actor);
        return {
          success: true,
          message: `Refund of $${amount} successfully processed for Order ${orderId}`,
          order: updatedOrder
        };
      } catch (err) {
        return { success: false, error: err.message };
      }
    }
  }
};
