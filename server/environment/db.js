/**
 * Internal Database & State Store
 * Persists tasks, execution runs, approval tickets, and verification records.
 */

class Database {
  constructor() {
    this.tasks = new Map();
    this.runs = new Map();
    this.approvals = new Map();
    this.auditTrail = [];
  }

  saveTask(task) {
    this.tasks.set(task.id, { ...task, updatedAt: new Date().toISOString() });
    return this.tasks.get(task.id);
  }

  getTask(id) {
    return this.tasks.get(id) || null;
  }

  listTasks() {
    return Array.from(this.tasks.values()).sort(
      (a, b) => new Date(b.createdAt) - new Date(a.createdAt)
    );
  }

  saveRun(run) {
    this.runs.set(run.id, { ...run, updatedAt: new Date().toISOString() });
    return this.runs.get(run.id);
  }

  getRun(id) {
    return this.runs.get(id) || null;
  }

  createApprovalRequest({ taskId, runId, action, parameters, reason, severity = "HIGH" }) {
    const approvalId = `APPR-${Date.now().toString(36).toUpperCase()}-${Math.floor(Math.random() * 1000)}`;
    const record = {
      id: approvalId,
      taskId,
      runId,
      action,
      parameters,
      reason,
      severity,
      status: "PENDING", // PENDING, APPROVED, REJECTED
      createdAt: new Date().toISOString(),
      resolvedAt: null,
      userComment: null
    };
    this.approvals.set(approvalId, record);
    return record;
  }

  resolveApproval(approvalId, decision, userComment = "") {
    const record = this.approvals.get(approvalId);
    if (!record) throw new Error(`Approval request ${approvalId} not found`);
    record.status = decision; // "APPROVED" or "REJECTED"
    record.resolvedAt = new Date().toISOString();
    record.userComment = userComment;
    return record;
  }

  getApproval(id) {
    return this.approvals.get(id) || null;
  }

  listPendingApprovals(taskId) {
    return Array.from(this.approvals.values()).filter(
      a => a.status === "PENDING" && (!taskId || a.taskId === taskId)
    );
  }

  addAudit(event) {
    const record = {
      id: `EVT-${Date.now()}-${Math.floor(Math.random() * 1000)}`,
      timestamp: new Date().toISOString(),
      ...event
    };
    this.auditTrail.unshift(record);
    return record;
  }

  getAuditTrail(filter = {}) {
    let list = [...this.auditTrail];
    if (filter.taskId) list = list.filter(e => e.taskId === filter.taskId);
    if (filter.runId) list = list.filter(e => e.runId === filter.runId);
    return list;
  }

  clear() {
    this.tasks.clear();
    this.runs.clear();
    this.approvals.clear();
    this.auditTrail = [];
  }
}

export const dbInstance = new Database();
