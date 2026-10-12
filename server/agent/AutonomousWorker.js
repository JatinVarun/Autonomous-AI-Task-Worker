import crypto from "node:crypto";
import { AgentMemory } from "./memory.js";
import { globalToolRegistry } from "../tools/index.js";
import { globalLlmProvider } from "./llm/provider.js";
import { globalHitlManager } from "./humanInTheLoop.js";
import { outcomeVerifier } from "./verifier.js";
import { dbInstance } from "../environment/db.js";

export class AutonomousWorker {
  constructor(options = {}) {
    this.maxSteps = options.maxSteps || 12;
    this.stepDelay = options.stepDelay ?? 600;
    this.skipApprovals = options.skipApprovals === true;
    this.eventEmitter = options.onEvent || (() => {});
    this.autoApproveThreshold = options.autoApproveThreshold; // optional override
    this.isRunning = false;
  }

  emit(eventType, data) {
    const payload = {
      event: eventType,
      timestamp: new Date().toISOString(),
      taskId: this.taskId,
      runId: this.runId,
      ...data
    };
    dbInstance.addAudit(payload);
    this.eventEmitter(payload);
  }

  async startTask(goal, options = {}) {
    if (this.isRunning) {
      throw new Error("Worker is already executing a task. Please wait or stop the current run.");
    }

    this.taskId = options.taskId || `TASK-${crypto.randomBytes(3).toString("hex").toUpperCase()}`;
    this.runId = `RUN-${Date.now().toString(36).toUpperCase()}`;
    this.goal = goal;
    this.memory = new AgentMemory(goal);
    this.isRunning = true;
    this.status = "RUNNING";

    // Save initial task record
    dbInstance.saveTask({
      id: this.taskId,
      goal,
      status: "RUNNING",
      createdAt: new Date().toISOString()
    });

    this.emit("TASK_STARTED", { goal });

    try {
      // 1. Initial Goal Understanding & Decomposition
      const initialPlan = await globalLlmProvider.generateInitialPlan(goal);
      this.memory.setPlan(initialPlan);

      this.emit("PLAN_GENERATED", {
        plan: this.memory.plan,
        goalUnderstanding: `Parsed high-level user goal. Decomposed into ${initialPlan.length} sequential milestones.`
      });

      // 2. ReAct Execution Loop
      let stepCount = 0;
      let taskFinished = false;

      while (stepCount < this.maxSteps && !taskFinished && this.isRunning) {
        stepCount++;

        // Cognitive step decision (Thought + Action)
        const toolSchemas = globalToolRegistry.listToolSchemas();
        const decision = await globalLlmProvider.decideNextStep({
          goal: this.goal,
          memory: this.memory,
          stepCount: stepCount - 1,
          tools: toolSchemas
        });

        if (decision.completed) {
          taskFinished = true;
          this.emit("REASONING_STEP", {
            stepIndex: stepCount,
            thought: decision.thought || "All necessary actions have been performed. Initiating verification.",
            isTerminal: true
          });
          break;
        }

        const { thought, action } = decision;

        this.emit("REASONING_STEP", {
          stepIndex: stepCount,
          thought,
          intendedAction: action
        });

        // 3. Human-in-the-Loop Risk Assessment
        const risk = globalHitlManager.evaluateRisk(action.name, action.parameters);
        const shouldSkipApproval = options.skipApprovals ?? this.skipApprovals;
        if (risk.requiresApproval && !shouldSkipApproval) {
          this.emit("APPROVAL_REQUESTED", {
            stepIndex: stepCount,
            actionName: action.name,
            parameters: action.parameters,
            riskAssessment: risk
          });

          // Suspend execution until human resolves via UI/API
          const approvalResult = await globalHitlManager.requestApproval({
            taskId: this.taskId,
            runId: this.runId,
            actionName: action.name,
            parameters: action.parameters,
            riskAssessment: risk,
            onApprovalPending: (record) => {
              this.emit("WAITING_FOR_USER_APPROVAL", { approvalRecord: record });
            }
          });

          this.emit("APPROVAL_RESOLVED", { approvalResult });

          if (approvalResult.decision !== "APPROVED") {
            this.memory.recordError(`User rejected action ${action.name}`, { approvalResult });
            this.emit("ACTION_REJECTED", {
              actionName: action.name,
              reason: approvalResult.userComment || "Rejected by user"
            });
            // Adapt on next iteration
            continue;
          }
        }

        // 4. Action Execution
        this.emit("ACTION_EXECUTING", {
          stepIndex: stepCount,
          toolName: action.name,
          parameters: action.parameters
        });

        const observation = await globalToolRegistry.execute(
          action.name,
          action.parameters,
          { agentId: "AI_WORKER", taskId: this.taskId, runId: this.runId }
        );

        // 5. Perception & Memory Update
        this.memory.recordHistory({
          stepNumber: stepCount,
          thought,
          action,
          observation,
          status: observation.success ? "SUCCESS" : "FAILURE"
        });

        this.emit("OBSERVATION_RECEIVED", {
          stepIndex: stepCount,
          toolName: action.name,
          observation,
          scratchpad: this.memory.scratchpad
        });

        // Update plan milestone progress
        this.updatePlanProgress(stepCount, action.name, observation);

        // If action was notify_user_completion and successful, we are ready to verify & finish
        if (action.name === "notify_user_completion" && observation.success) {
          taskFinished = true;
        }

        // Small micro-delay for smooth real-time visualization
        if (this.stepDelay > 0) {
          await new Promise(r => setTimeout(r, this.stepDelay));
        }
      }

      // 6. Independent Outcome Verification Engine
      this.emit("VERIFICATION_STARTED", {
        message: "Running independent verification against underlying enterprise systems of record."
      });

      const verificationResult = await outcomeVerifier.verify({
        taskGoal: this.goal,
        scratchpad: this.memory.scratchpad,
        executedActions: this.memory.history
      });

      this.memory.setEvidence("verification", verificationResult);

      this.emit("VERIFICATION_COMPLETED", { verificationResult });

      // 7. Final State & Evidence Packet
      const finalStatus = verificationResult.verified ? "COMPLETED_VERIFIED" : "COMPLETED_UNVERIFIED";
      const summary = this.memory.getExecutionSummary();

      const finalRecord = {
        taskId: this.taskId,
        runId: this.runId,
        goal: this.goal,
        status: finalStatus,
        verificationProof: verificationResult,
        discoveredState: this.memory.scratchpad,
        executionTimeline: this.memory.history,
        summary
      };

      dbInstance.saveTask({
        id: this.taskId,
        goal: this.goal,
        status: finalStatus,
        result: finalRecord,
        updatedAt: new Date().toISOString()
      });

      this.emit("TASK_COMPLETED", finalRecord);
      this.isRunning = false;
      return finalRecord;

    } catch (err) {
      this.isRunning = false;
      this.emit("TASK_FAILED", {
        error: err.message,
        stack: err.stack
      });
      dbInstance.saveTask({
        id: this.taskId,
        goal: this.goal,
        status: "FAILED",
        error: err.message
      });
      throw err;
    }
  }

  updatePlanProgress(stepIndex, toolName, observation) {
    if (!observation.success) return;

    if (toolName === "list_files" || toolName === "search_documents") {
      this.memory.updateStepStatus(1, "COMPLETED");
    } else if (toolName === "read_file") {
      this.memory.updateStepStatus(2, "COMPLETED");
    } else if (toolName === "erp_search_vendors") {
      this.memory.updateStepStatus(3, "COMPLETED");
    } else if (toolName === "erp_create_invoice" || toolName === "erp_update_vendor" || toolName === "erp_process_refund") {
      this.memory.updateStepStatus(4, "COMPLETED");
    } else if (toolName === "verify_task_outcome") {
      this.memory.updateStepStatus(5, "COMPLETED");
    } else if (toolName === "notify_user_completion") {
      this.memory.updateStepStatus(6, "COMPLETED");
    }
  }

  stop() {
    this.isRunning = false;
    this.emit("TASK_ABORTED", { reason: "User triggered abort" });
  }
}
