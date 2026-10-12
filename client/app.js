/**
 * Autonomous AI Task Worker - Client Application
 * Handles real-time WebSocket telemetry, interactive ReAct visualization,
 * human-in-the-loop modals, ERP state sync, and verification inspection.
 */

// State
let ws = null;
let currentTaskId = null;
let currentApprovalId = null;
let timerInterval = null;
let startTime = null;
let stepCounter = 0;
let currentActiveCard = null;

// DOM Elements
const taskGoalInput = document.getElementById("taskGoalInput");
const btnRunTask = document.getElementById("btnRunTask");
const btnAbortTask = document.getElementById("btnAbortTask");
const btnResetErp = document.getElementById("btnResetErp");
const agentStatusPill = document.getElementById("agentStatusPill");
const statusDot = document.getElementById("statusDot");
const agentStatusText = document.getElementById("agentStatusText");
const activeEngineLabel = document.getElementById("activeEngineLabel");
const autoApproveToggle = document.getElementById("autoApproveToggle");

const planSection = document.getElementById("planSection");
const planStepsList = document.getElementById("planStepsList");
const planProgressBadge = document.getElementById("planProgressBadge");

const executionStream = document.getElementById("executionStream");
const statSteps = document.getElementById("statSteps");
const statDuration = document.getElementById("statDuration");

// Modals
const hitlModalBackdrop = document.getElementById("hitlModalBackdrop");
const hitlTitle = document.getElementById("hitlTitle");
const hitlReason = document.getElementById("hitlReason");
const hitlSeverity = document.getElementById("hitlSeverity");
const hitlActionName = document.getElementById("hitlActionName");
const hitlParameters = document.getElementById("hitlParameters");
const hitlUserComment = document.getElementById("hitlUserComment");
const btnApproveHitl = document.getElementById("btnApproveHitl");
const btnRejectHitl = document.getElementById("btnRejectHitl");

const summaryModalBackdrop = document.getElementById("summaryModalBackdrop");
const summaryModalBody = document.getElementById("summaryModalBody");
const btnCloseSummaryModal = document.getElementById("btnCloseSummaryModal");

// Presets
const PRESETS = {
  invoice: "Find the latest invoice from Acme Corp, extract the amount and due date, enter it into our internal system, and tell me once it is done.",
  globex: "Find the invoice from Globex Logistics Corp, parse its JSON amount and due date, register it in the ERP system, and verify.",
  vendor: "Locate the vendor agreement for Initech Technologies, extract approved tax ID and payment terms, update the ERP vendor master directory, and verify.",
  refund: "Process refund request in email ticket #REF-842, check order status in database, submit refund transaction, and verify completion."
};

// =========================================================================
// Initialization
// =========================================================================
document.addEventListener("DOMContentLoaded", () => {
  initWebSocket();
  initTabs();
  initPresets();
  refreshErp();
  refreshFiles();

  btnRunTask.addEventListener("click", launchTask);
  btnAbortTask.addEventListener("click", abortTask);
  btnResetErp.addEventListener("click", resetEnvironment);

  btnApproveHitl.addEventListener("click", () => resolveApproval("APPROVED"));
  btnRejectHitl.addEventListener("click", () => resolveApproval("REJECTED"));
  btnCloseSummaryModal.addEventListener("click", () => {
    summaryModalBackdrop.style.display = "none";
  });

  document.getElementById("btnRefreshErp").addEventListener("click", refreshErp);
  document.getElementById("btnRefreshFiles").addEventListener("click", refreshFiles);

  // Settings
  const selectProvider = document.getElementById("selectProvider");
  const geminiKeyGroup = document.getElementById("geminiKeyGroup");
  const openaiKeyGroup = document.getElementById("openaiKeyGroup");
  const btnSaveSettings = document.getElementById("btnSaveSettings");

  selectProvider.addEventListener("change", () => {
    geminiKeyGroup.style.display = selectProvider.value === "GEMINI" ? "block" : "none";
    openaiKeyGroup.style.display = selectProvider.value === "OPENAI" ? "block" : "none";
  });

  btnSaveSettings.addEventListener("click", saveSettings);
});

// =========================================================================
// WebSocket Gateway
// =========================================================================
function initWebSocket() {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const wsUrl = `${protocol}//${window.location.host}/ws`;

  ws = new WebSocket(wsUrl);

  ws.onopen = () => {
    console.log("[WS] Connected to Autonomous Agent Live Stream");
  };

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      handleAgentEvent(data);
    } catch (err) {
      console.error("[WS] Parse error:", err);
    }
  };

  ws.onclose = () => {
    console.warn("[WS] Connection lost. Reconnecting in 3s...");
    setTimeout(initWebSocket, 3000);
  };
}

// =========================================================================
// Event Handler for Agent ReAct Stream
// =========================================================================
function handleAgentEvent(data) {
  const eventType = data.event || data.type;

  switch (eventType) {
    case "CONNECTED":
      if (data.providerInfo) {
        updateActiveEngineDisplay(data.providerInfo.provider);
      }
      break;

    case "TASK_STARTED":
      setAgentStatus("running", "EXECUTING RE-ACT LOOP");
      startTimer();
      clearStream();
      btnRunTask.disabled = true;
      btnAbortTask.disabled = false;
      break;

    case "PLAN_GENERATED":
      renderPlan(data.plan);
      break;

    case "REASONING_STEP":
      stepCounter++;
      statSteps.textContent = `Steps: ${stepCounter}`;
      currentActiveCard = createStepCard(data.stepIndex || stepCounter, data.thought, data.intendedAction);
      executionStream.appendChild(currentActiveCard);
      executionStream.scrollTop = executionStream.scrollHeight;
      break;

    case "WAITING_FOR_USER_APPROVAL":
    case "APPROVAL_REQUESTED":
      setAgentStatus("waiting", "AWAITING HUMAN APPROVAL");
      const approval = data.approvalRecord || {
        id: "APPR-PENDING",
        action: data.actionName,
        parameters: data.parameters,
        reason: data.riskAssessment?.reason,
        severity: data.riskAssessment?.severity
      };
      showHitlModal(approval);
      break;

    case "APPROVAL_RESOLVED":
      hitlModalBackdrop.style.display = "none";
      setAgentStatus("running", "RESUMING EXECUTION");
      break;

    case "ACTION_EXECUTING":
      // Action executing tag
      break;

    case "OBSERVATION_RECEIVED":
      if (currentActiveCard) {
        appendObservationToCard(currentActiveCard, data.observation, data.toolName);
      }
      refreshErp();
      break;

    case "VERIFICATION_STARTED":
      setAgentStatus("running", "VERIFYING REAL-WORLD STATE");
      break;

    case "VERIFICATION_COMPLETED":
      renderVerificationProof(data.verificationResult);
      refreshErp();
      break;

    case "TASK_COMPLETED":
      setAgentStatus("success", "COMPLETED & VERIFIED");
      stopTimer();
      btnRunTask.disabled = false;
      btnAbortTask.disabled = true;
      showSummaryModal(data);
      refreshErp();
      break;

    case "TASK_FAILED":
    case "TASK_ABORTED":
      setAgentStatus("failed", eventType === "TASK_ABORTED" ? "ABORTED BY USER" : "TASK FAILED");
      stopTimer();
      btnRunTask.disabled = false;
      btnAbortTask.disabled = true;
      break;

    case "ERP_RESET":
      refreshErp();
      break;
  }
}

// =========================================================================
// UI Rendering: ReAct Step Cards
// =========================================================================
function createStepCard(stepNumber, thought, intendedAction) {
  const card = document.createElement("div");
  card.className = "react-step-card";

  const header = document.createElement("div");
  header.className = "react-step-header";
  header.innerHTML = `
    <div class="react-step-tag">
      <span>●</span> STEP ${stepNumber}
    </div>
    <span class="badge-pill">${new Date().toLocaleTimeString()}</span>
  `;
  card.appendChild(header);

  // Thought Block
  if (thought) {
    const thoughtBlock = document.createElement("div");
    thoughtBlock.className = "thought-block";
    thoughtBlock.innerHTML = `
      <span class="thought-label">Internal Reasoning:</span>
      <p>${escapeHtml(thought)}</p>
    `;
    card.appendChild(thoughtBlock);
  }

  // Action Chip
  if (intendedAction) {
    const actionChip = document.createElement("div");
    actionChip.className = "action-chip-card";
    actionChip.innerHTML = `
      <div class="action-chip-header">
        <span class="action-name">⚡ ${escapeHtml(intendedAction.name)}</span>
        <span class="badge-pill">Tool Invocation</span>
      </div>
      <pre class="action-params-json">${escapeHtml(JSON.stringify(intendedAction.parameters, null, 2))}</pre>
    `;
    card.appendChild(actionChip);
  }

  return card;
}

function appendObservationToCard(card, observation, toolName) {
  const obsCard = document.createElement("div");
  obsCard.className = `observation-card ${observation.success ? "success" : "failure"}`;

  const summary = observation.success
    ? `Tool '${toolName}' executed successfully (${observation._meta?.durationMs || 0}ms)`
    : `Tool '${toolName}' encountered an error`;

  obsCard.innerHTML = `
    <div class="observation-header">${summary}</div>
    <pre class="observation-body">${escapeHtml(JSON.stringify(observation, null, 2))}</pre>
  `;
  card.appendChild(obsCard);
  executionStream.scrollTop = executionStream.scrollHeight;
}

// =========================================================================
// UI Rendering: Plan Milestones
// =========================================================================
function renderPlan(plan) {
  if (!plan || plan.length === 0) return;
  planSection.style.display = "block";
  planStepsList.innerHTML = "";

  plan.forEach(step => {
    const item = document.createElement("div");
    item.className = "plan-step-item";
    item.id = `planStep_${step.id}`;
    item.innerHTML = `
      <div class="plan-step-num">${step.id}</div>
      <div class="plan-step-body">
        <div class="plan-step-title">${escapeHtml(step.title)}</div>
        <div class="plan-step-desc">${escapeHtml(step.description || "")}</div>
      </div>
    `;
    planStepsList.appendChild(item);
  });

  planProgressBadge.textContent = `0 / ${plan.length} Milestones`;
}

// =========================================================================
// UI Rendering: Verification Proof
// =========================================================================
function renderVerificationProof(proof) {
  if (!proof) return;
  const hero = document.getElementById("verificationHero");
  const shield = document.getElementById("verifShield");
  const title = document.getElementById("verifStatusTitle");
  const desc = document.getElementById("verifStatusDesc");
  const detailsCard = document.getElementById("verifDetailsCard");

  detailsCard.style.display = "block";

  if (proof.verified) {
    hero.className = "verification-hero verified";
    shield.textContent = "🛡️";
    title.textContent = "Outcome Confirmed & Verified!";
    title.style.color = "#34d399";
    desc.textContent = "Target system state was queried independently. Real-world changes strictly match source assertions.";
  } else {
    hero.className = "verification-hero unverified";
    shield.textContent = "⚠️";
    title.textContent = "Verification Discrepancy Detected";
    title.style.color = "#f43f5e";
    desc.textContent = proof.verdict || "System of record could not confirm the expected changes.";
  }

  document.getElementById("proofVerifId").textContent = proof.verificationId || "N/A";
  document.getElementById("proofSystem").textContent = proof.targetSystem || "ERP_SYSTEM";
  document.getElementById("proofSignature").textContent = proof.proofSignature || "N/A";
  document.getElementById("proofRecordId").textContent = proof.evidence?.erpRecordId || proof.evidence?.id || "N/A";

  const checksList = document.getElementById("verifChecksList");
  checksList.innerHTML = "";

  if (proof.checks && Array.isArray(proof.checks)) {
    proof.checks.forEach(c => {
      const item = document.createElement("div");
      item.className = `check-item ${c.passed ? "passed" : "failed"}`;
      item.innerHTML = `
        <span><span class="check-icon">${c.passed ? "✅" : "❌"}</span> ${escapeHtml(c.description)}</span>
        <span class="badge-pill">${c.passed ? "MATCH" : "MISMATCH"}</span>
      `;
      checksList.appendChild(item);
    });
  }
}

// =========================================================================
// UI Modals: Human-in-the-Loop & Summary
// =========================================================================
function showHitlModal(record) {
  currentApprovalId = record.id;
  hitlActionName.textContent = record.action || "erp_create_invoice";
  hitlReason.textContent = record.reason || "High value transaction";
  hitlSeverity.textContent = record.severity || "HIGH RISK";
  hitlParameters.textContent = JSON.stringify(record.parameters, null, 2);
  hitlUserComment.value = "";
  hitlModalBackdrop.style.display = "flex";
}

async function resolveApproval(decision) {
  const comment = hitlUserComment.value.trim();
  if (!currentApprovalId) return;

  try {
    await fetch(`/api/approvals/${currentApprovalId}/resolve`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ decision, userComment: comment })
    });
  } catch (err) {
    console.error("Failed to send approval resolution:", err);
  }
}

function showSummaryModal(taskResult) {
  const summaryModal = document.getElementById("summaryModalBackdrop");
  const modalTitle = document.getElementById("summaryModalTitle");
  const body = document.getElementById("summaryModalBody");

  modalTitle.textContent = `Task ${taskResult.status === "COMPLETED_VERIFIED" ? "Completed & Verified" : "Completed"}`;

  const proof = taskResult.verificationProof;
  const scratchpad = taskResult.discoveredState || {};

  body.innerHTML = `
    <div style="margin-bottom: 1rem;">
      <h4 style="color: #38bdf8; margin-bottom: 0.3rem;">Executive Summary</h4>
      <p>${escapeHtml(taskResult.summary?.discoveredVariables?.invoiceNumber ? 
        `Successfully processed invoice ${scratchpad.invoiceNumber} for ${scratchpad.vendorName}. Registered into internal ERP with amount $${scratchpad.amount?.toLocaleString()} and due date ${scratchpad.dueDate}.` :
        `Autonomous execution completed for: "${taskResult.goal}".`
      )}</p>
    </div>

    <div style="background: rgba(0,0,0,0.4); padding: 0.8rem; border-radius: 8px; margin-bottom: 1rem;">
      <h5 style="color: #e2e8f0; font-size: 0.8rem; text-transform: uppercase; margin-bottom: 0.4rem;">Audit Telemetry</h5>
      <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.5rem; font-size: 0.82rem;">
        <div><strong>Steps Executed:</strong> ${taskResult.summary?.totalStepsExecuted || 0}</div>
        <div><strong>Execution Time:</strong> ${((taskResult.summary?.durationMs || 0) / 1000).toFixed(1)}s</div>
        <div><strong>Errors Recovered:</strong> ${taskResult.summary?.errorsEncountered || 0}</div>
      </div>
    </div>

    ${proof ? `
      <div style="background: rgba(16, 185, 129, 0.08); border: 1px solid rgba(16, 185, 129, 0.3); padding: 0.8rem; border-radius: 8px;">
        <h5 style="color: #6ee7b7; font-size: 0.8rem; text-transform: uppercase; margin-bottom: 0.4rem;">Verification Proof Digest</h5>
        <div style="font-family: monospace; font-size: 0.78rem; color: #a7f3d0;">
          <div>Verification ID: ${proof.verificationId}</div>
          <div>Proof Signature: ${proof.proofSignature}</div>
          <div>Target System: ${proof.targetSystem}</div>
        </div>
      </div>
    ` : ""}
  `;

  summaryModal.style.display = "flex";
}

// =========================================================================
// Environment & ERP Sync
// =========================================================================
async function refreshErp() {
  try {
    const [invRes, vendRes, auditRes] = await Promise.all([
      fetch("/api/erp/invoices"),
      fetch("/api/erp/vendors"),
      fetch("/api/erp/audit")
    ]);

    const { invoices } = await invRes.json();
    const { vendors } = await vendRes.json();
    const { auditLogs } = await auditRes.json();

    // Render Invoices Table
    const invBody = document.getElementById("erpInvoicesBody");
    invBody.innerHTML = "";
    let totalAp = 0;

    invoices.forEach(inv => {
      totalAp += inv.amount;
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td class="text-mono text-accent">${inv.id}</td>
        <td class="text-mono">${escapeHtml(inv.invoiceNumber)}</td>
        <td>${escapeHtml(inv.vendorName)}</td>
        <td class="text-mono font-bold">$${inv.amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}</td>
        <td class="text-mono">${inv.dueDate}</td>
        <td><span class="status-badge ${inv.status === 'PAID' ? 'badge-paid' : 'badge-pending'}">${inv.status}</span></td>
        <td><span class="status-badge badge-verified">${inv.verificationStatus || 'RECORDED'}</span></td>
      `;
      invBody.appendChild(tr);
    });

    document.getElementById("metricInvoiceCount").textContent = invoices.length;
    document.getElementById("metricApTotal").textContent = `$${totalAp.toLocaleString(undefined, { minimumFractionDigits: 2 })}`;

    // Render Vendors Table
    const vendBody = document.getElementById("erpVendorsBody");
    vendBody.innerHTML = "";
    vendors.forEach(v => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td class="text-mono text-accent">${v.id}</td>
        <td>${escapeHtml(v.name)}</td>
        <td class="text-mono">${escapeHtml(v.taxId)}</td>
        <td>${escapeHtml(v.paymentTerms)}</td>
        <td><span class="status-badge ${v.status === 'ACTIVE' ? 'badge-paid' : 'badge-pending'}">${v.status}</span></td>
      `;
      vendBody.appendChild(tr);
    });

    // Render Audit Table
    const auditBody = document.getElementById("erpAuditBody");
    auditBody.innerHTML = "";
    (auditLogs || []).slice(0, 15).forEach(log => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td class="text-mono">${new Date(log.timestamp).toLocaleTimeString()}</td>
        <td><span class="badge-pill">${log.actor}</span></td>
        <td class="text-accent font-bold">${log.action}</td>
        <td class="text-mono">${escapeHtml(typeof log.details === 'object' ? JSON.stringify(log.details) : log.details)}</td>
      `;
      auditBody.appendChild(tr);
    });
  } catch (err) {
    console.error("Failed to refresh ERP:", err);
  }
}

async function refreshFiles() {
  try {
    const res = await fetch("/api/files");
    const data = await res.json();
    const list = document.getElementById("fileTreeList");
    list.innerHTML = "";

    if (data.files) {
      data.files.forEach(f => {
        const item = document.createElement("div");
        item.className = "file-tree-item";
        item.innerHTML = `<span>${f.type === 'directory' ? '📁' : '📄'}</span> <span>${escapeHtml(f.name)}</span>`;
        item.addEventListener("click", () => previewFile(f.path, f.name));
        list.appendChild(item);
      });
    }
  } catch (err) {
    console.error("Failed to load files:", err);
  }
}

async function previewFile(filePath, fileName) {
  try {
    const res = await fetch(`/api/files/content?path=${encodeURIComponent(filePath)}`);
    const data = await res.json();
    document.getElementById("previewFileName").textContent = fileName;
    document.getElementById("previewFileType").textContent = filePath.endsWith(".json") ? "JSON" : "Text";
    
    const content = typeof data.content === "object" ? JSON.stringify(data.content, null, 2) : data.content;
    document.getElementById("previewFileContent").textContent = content;

    document.querySelectorAll(".file-tree-item").forEach(el => el.classList.remove("active"));
    event.currentTarget.classList.add("active");
  } catch (err) {
    console.error("Failed to preview file:", err);
  }
}

async function resetEnvironment() {
  if (confirm("Reset the simulated enterprise ERP back to initial state?")) {
    await fetch("/api/erp/reset", { method: "POST" });
    refreshErp();
  }
}

// =========================================================================
// Actions: Launch & Abort
// =========================================================================
async function launchTask() {
  const goal = taskGoalInput.value.trim();
  if (!goal) return alert("Please enter a task directive.");

  const skipApprovals = autoApproveToggle.checked;

  try {
    const res = await fetch("/api/tasks", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ goal, options: { skipApprovals } })
    });

    const data = await res.json();
    if (!res.ok) {
      alert(data.error || "Failed to start task");
      return;
    }
    currentTaskId = data.taskId;
  } catch (err) {
    alert("Network error: " + err.message);
  }
}

async function abortTask() {
  await fetch("/api/tasks/abort", { method: "POST" });
}

async function saveSettings() {
  const provider = document.getElementById("selectProvider").value;
  const geminiApiKey = document.getElementById("inputGeminiKey").value.trim();
  const openaiApiKey = document.getElementById("inputOpenaiKey").value.trim();

  await fetch("/api/settings", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ provider, geminiApiKey, openaiApiKey })
  });

  updateActiveEngineDisplay(provider);
  alert("Settings updated successfully!");
}

function updateActiveEngineDisplay(provider) {
  const names = {
    BUILTIN_COGNITIVE_ENGINE: "Cognitive ReAct v1",
    GEMINI: "Google Gemini 2.0",
    OPENAI: "OpenAI GPT-4o"
  };
  activeEngineLabel.textContent = names[provider] || provider;
}

// =========================================================================
// Helpers & Utilities
// =========================================================================
function setAgentStatus(status, text) {
  statusDot.className = `status-dot status-${status}`;
  agentStatusText.textContent = text;
}

function startTimer() {
  startTime = Date.now();
  stepCounter = 0;
  statSteps.textContent = "Steps: 0";
  clearInterval(timerInterval);
  timerInterval = setInterval(() => {
    const elapsed = (Date.now() - startTime) / 1000;
    statDuration.textContent = `Time: ${elapsed.toFixed(1)}s`;
  }, 100);
}

function stopTimer() {
  clearInterval(timerInterval);
}

function clearStream() {
  executionStream.innerHTML = "";
}

function initTabs() {
  const tabs = document.querySelectorAll(".env-tab");
  tabs.forEach(tab => {
    tab.addEventListener("click", () => {
      tabs.forEach(t => t.classList.remove("active"));
      document.querySelectorAll(".env-tab-content").forEach(c => c.classList.remove("active"));

      tab.classList.add("active");
      const targetId = `tab${tab.dataset.tab.charAt(0).toUpperCase() + tab.dataset.tab.slice(1)}`;
      const targetContent = document.getElementById(targetId);
      if (targetContent) targetContent.classList.add("active");
    });
  });
}

function initPresets() {
  const presetButtons = document.querySelectorAll(".preset-btn");
  presetButtons.forEach(btn => {
    btn.addEventListener("click", () => {
      presetButtons.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      const key = btn.dataset.preset;
      if (PRESETS[key]) {
        taskGoalInput.value = PRESETS[key];
      }
    });
  });
}

function escapeHtml(str) {
  if (typeof str !== "string") return str;
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}
