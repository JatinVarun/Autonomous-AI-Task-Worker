/**
 * Simulated Internal Enterprise ERP System
 * Provides an in-memory and persistent REST-like service for:
 * - Accounts Payable (Invoices)
 * - Vendor Master Directory
 * - Customer Orders & Refunds
 * - System Audit Logs
 */

export class ErpService {
  constructor() {
    this.reset();
  }

  reset() {
    this.vendors = [
      {
        id: "VEND-001",
        name: "Acme Industrial Solutions",
        aliases: ["Acme Corp", "Acme", "Acme Industrial Solutions Inc."],
        taxId: "XX-9482103",
        status: "ACTIVE",
        paymentTerms: "Net 30",
        contactEmail: "billing@acme-industrial.example.com",
        currentBalance: 0
      },
      {
        id: "VEND-002",
        name: "Globex Logistics Corp",
        aliases: ["Globex", "Globex Logistics"],
        taxId: "US-8837194",
        status: "ACTIVE",
        paymentTerms: "Net 30",
        contactEmail: "accounts@globex-logistics.example.com",
        currentBalance: 0
      },
      {
        id: "VEND-003",
        name: "Initech Technologies Ltd",
        aliases: ["Initech", "Initech Technologies"],
        taxId: "IN-9948201",
        status: "PENDING_VERIFICATION",
        paymentTerms: "Net 15",
        contactEmail: "accounting@initech.example.com",
        currentBalance: 0
      }
    ];

    this.invoices = [
      {
        id: "ERP-INV-1001",
        invoiceNumber: "INV-2024-512",
        vendorId: "VEND-001",
        vendorName: "Acme Industrial Solutions",
        amount: 2400.00,
        currency: "USD",
        dueDate: "2024-06-10",
        status: "PAID",
        createdAt: "2024-05-12T10:00:00.000Z",
        source: "MANUAL_ENTRY",
        verificationStatus: "VERIFIED"
      }
    ];

    this.orders = [
      {
        orderId: "ORD-99381",
        customerId: "CUST-4412",
        customerName: "Sarah Connor",
        item: "Developer Pro License",
        amount: 79.00,
        currency: "USD",
        status: "FULFILLED",
        paymentMethod: "Credit Card (ending 4242)",
        orderDate: "2024-10-22T14:20:00.000Z",
        refunded: false
      }
    ];

    this.auditLogs = [
      {
        id: "LOG-0001",
        timestamp: new Date().toISOString(),
        actor: "SYSTEM_INIT",
        action: "ERP_BOOTSTRAP",
        details: "Initial seeded enterprise data loaded."
      }
    ];
  }

  // --- Audit Logging ---
  recordAudit(actor, action, details) {
    const entry = {
      id: `LOG-${String(this.auditLogs.length + 1).padStart(4, "0")}`,
      timestamp: new Date().toISOString(),
      actor,
      action,
      details
    };
    this.auditLogs.unshift(entry);
    return entry;
  }

  // --- Vendors ---
  findVendorByName(name) {
    if (!name) return null;
    const clean = name.trim().toLowerCase();
    return this.vendors.find(v => 
      v.name.toLowerCase() === clean ||
      v.aliases.some(alias => alias.toLowerCase() === clean) ||
      v.name.toLowerCase().includes(clean)
    ) || null;
  }

  listVendors() {
    return [...this.vendors];
  }

  updateVendor(idOrName, updates, actor = "AI_WORKER") {
    let vendor = this.vendors.find(v => v.id === idOrName);
    if (!vendor) vendor = this.findVendorByName(idOrName);
    if (!vendor) {
      throw new Error(`Vendor not found for identifier: "${idOrName}"`);
    }

    Object.assign(vendor, updates);
    this.recordAudit(actor, "UPDATE_VENDOR", { vendorId: vendor.id, updates });
    return vendor;
  }

  // --- Invoices ---
  listInvoices(filters = {}) {
    let result = [...this.invoices];
    if (filters.vendorName) {
      const q = filters.vendorName.toLowerCase();
      result = result.filter(inv => inv.vendorName.toLowerCase().includes(q));
    }
    if (filters.status) {
      result = result.filter(inv => inv.status === filters.status);
    }
    return result;
  }

  getInvoiceById(id) {
    return this.invoices.find(inv => inv.id === id || inv.invoiceNumber === id) || null;
  }

  createInvoice(payload, actor = "AI_WORKER") {
    const { vendorName, invoiceNumber, amount, dueDate, currency = "USD", poNumber, items = [] } = payload;

    if (!vendorName) throw new Error("Missing required field: vendorName");
    if (!invoiceNumber) throw new Error("Missing required field: invoiceNumber");
    if (amount === undefined || amount === null || isNaN(Number(amount))) {
      throw new Error("Missing or invalid field: amount must be a valid number");
    }
    if (!dueDate) throw new Error("Missing required field: dueDate (format: YYYY-MM-DD)");

    // Duplicate check
    const existing = this.invoices.find(
      inv => inv.invoiceNumber.toLowerCase() === invoiceNumber.toLowerCase()
    );
    if (existing) {
      throw new Error(`DuplicateInvoiceError: Invoice with number "${invoiceNumber}" is already registered (ID: ${existing.id})`);
    }

    // Resolve vendor
    const vendor = this.findVendorByName(vendorName);
    const vendorId = vendor ? vendor.id : "VEND-UNREGISTERED";
    const resolvedVendorName = vendor ? vendor.name : vendorName;

    const newInvoice = {
      id: `ERP-INV-${1000 + this.invoices.length + 1}`,
      invoiceNumber: invoiceNumber.trim(),
      vendorId,
      vendorName: resolvedVendorName,
      amount: Number(Number(amount).toFixed(2)),
      currency: currency.toUpperCase(),
      dueDate: dueDate.trim(),
      poNumber: poNumber || "N/A",
      items,
      status: "PENDING_PAYMENT",
      createdAt: new Date().toISOString(),
      source: actor,
      verificationStatus: "RECORDED_PENDING_VERIFY"
    };

    this.invoices.unshift(newInvoice);

    if (vendor) {
      vendor.currentBalance = (vendor.currentBalance || 0) + newInvoice.amount;
    }

    this.recordAudit(actor, "CREATE_INVOICE", {
      invoiceId: newInvoice.id,
      invoiceNumber: newInvoice.invoiceNumber,
      vendor: resolvedVendorName,
      amount: newInvoice.amount,
      dueDate: newInvoice.dueDate
    });

    return newInvoice;
  }

  // --- Orders & Refunds ---
  getOrder(orderId) {
    return this.orders.find(o => o.orderId === orderId) || null;
  }

  issueRefund(orderId, amount, reason, actor = "AI_WORKER") {
    const order = this.getOrder(orderId);
    if (!order) throw new Error(`Order ${orderId} not found`);
    if (order.refunded) throw new Error(`Order ${orderId} has already been refunded`);

    const refundAmount = Number(amount);
    if (refundAmount > order.amount) {
      throw new Error(`Refund amount ($${refundAmount}) exceeds original order amount ($${order.amount})`);
    }

    order.refunded = true;
    order.refundDetails = {
      refundAmount,
      reason,
      processedAt: new Date().toISOString(),
      processedBy: actor
    };
    order.status = "REFUNDED";

    this.recordAudit(actor, "PROCESS_REFUND", { orderId, amount: refundAmount, reason });
    return order;
  }

  // --- Independent State Verification Helper ---
  verifyInvoiceExists(criteria) {
    const { invoiceNumber, vendorName, amount, dueDate } = criteria;
    const inv = this.invoices.find(i => 
      i.invoiceNumber.toLowerCase() === (invoiceNumber || "").toLowerCase()
    );

    if (!inv) {
      return { verified: false, reason: `Invoice "${invoiceNumber}" not found in ERP records` };
    }

    const checks = {
      invoiceNumberMatch: inv.invoiceNumber.toLowerCase() === (invoiceNumber || "").toLowerCase(),
      vendorMatch: vendorName ? inv.vendorName.toLowerCase().includes(vendorName.toLowerCase()) : true,
      amountMatch: amount !== undefined ? Math.abs(inv.amount - Number(amount)) < 0.01 : true,
      dueDateMatch: dueDate ? inv.dueDate === dueDate : true
    };

    const allPassed = Object.values(checks).every(Boolean);

    if (allPassed) {
      inv.verificationStatus = "VERIFIED_ACCURATE";
    }

    return {
      verified: allPassed,
      invoice: inv,
      checks,
      timestamp: new Date().toISOString()
    };
  }
}

export const erpInstance = new ErpService();
