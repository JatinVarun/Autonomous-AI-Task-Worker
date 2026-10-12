/**
 * Agent Working Memory & State Tracker
 * Maintains goal context, dynamic scratchpad variables,
 * action-observation history, discovered facts, and error logs.
 */

export class AgentMemory {
  constructor(goal) {
    this.goal = goal;
    this.plan = [];
    this.currentStepIndex = 0;
    this.scratchpad = {}; // Key-value discovered facts (e.g. { invoiceNumber: "INV-2024-889", amount: 14250.00 })
    this.history = [];    // Sequence of { step, thought, action, observation, status }
    this.errors = [];     // Captured failures and recovery attempts
    this.evidence = {};   // Verified outcomes and proof tokens
    this.startTime = Date.now();
  }

  setPlan(steps) {
    this.plan = steps.map((s, idx) => ({
      id: idx + 1,
      title: typeof s === "string" ? s : s.title,
      description: typeof s === "object" ? s.description : "",
      status: "PENDING" // PENDING, RUNNING, COMPLETED, FAILED, SKIPPED
    }));
  }

  updateStepStatus(stepId, status) {
    const step = this.plan.find(s => s.id === stepId);
    if (step) step.status = status;
  }

  setScratchpad(key, value) {
    this.scratchpad[key] = value;
  }

  getScratchpad(key) {
    return this.scratchpad[key];
  }

  recordHistory(entry) {
    const record = {
      stepNumber: this.history.length + 1,
      timestamp: new Date().toISOString(),
      ...entry
    };
    this.history.push(record);
    return record;
  }

  recordError(error, context = {}) {
    const errRecord = {
      timestamp: new Date().toISOString(),
      error: typeof error === "string" ? error : error.message,
      context,
      stepNumber: this.history.length
    };
    this.errors.push(errRecord);
    return errRecord;
  }

  setEvidence(key, value) {
    this.evidence[key] = value;
  }

  getExecutionSummary() {
    return {
      durationMs: Date.now() - this.startTime,
      totalStepsExecuted: this.history.length,
      errorsEncountered: this.errors.length,
      planProgress: {
        total: this.plan.length,
        completed: this.plan.filter(s => s.status === "COMPLETED").length,
        failed: this.plan.filter(s => s.status === "FAILED").length
      },
      discoveredVariables: this.scratchpad,
      evidence: this.evidence
    };
  }

  snapshot() {
    return {
      goal: this.goal,
      plan: this.plan,
      scratchpad: { ...this.scratchpad },
      historyCount: this.history.length,
      errors: [...this.errors],
      evidence: { ...this.evidence },
      executionSummary: this.getExecutionSummary()
    };
  }
}
