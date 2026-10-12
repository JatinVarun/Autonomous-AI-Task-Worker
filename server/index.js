import express from "express";
import http from "node:http";
import path from "node:path";
import fs from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { WebSocketServer, WebSocket } from "ws";
import dotenv from "dotenv";

import { erpInstance } from "./environment/erpService.js";
import { dbInstance } from "./environment/db.js";
import { globalToolRegistry } from "./tools/index.js";
import { globalLlmProvider } from "./agent/llm/provider.js";
import { globalHitlManager } from "./agent/humanInTheLoop.js";
import { AutonomousWorker } from "./agent/AutonomousWorker.js";

dotenv.config();

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PORT = process.env.PORT || 3000;
const CLIENT_DIR = path.resolve(__dirname, "../client");
const MOCK_FILES_DIR = path.resolve(__dirname, "./environment/mockFiles");

const app = express();
app.use(express.json());
app.use(express.static(CLIENT_DIR));

const server = http.createServer(app);
const wss = new WebSocketServer({ server, path: "/ws" });

// Connected WebSocket clients
const clients = new Set();

wss.on("connection", (ws) => {
  clients.add(ws);
  ws.send(JSON.stringify({
    type: "CONNECTED",
    message: "Connected to Autonomous AI Task Worker Live Gateway",
    providerInfo: globalLlmProvider.getProviderInfo(),
    toolsCount: globalToolRegistry.listToolSchemas().length
  }));

  ws.on("message", (msg) => {
    try {
      const data = JSON.parse(msg.toString());
      if (data.type === "RESOLVE_APPROVAL") {
        globalHitlManager.resolveApproval(data.approvalId, data.decision, data.userComment);
      }
    } catch (err) {
      console.error("[WS] Message error:", err.message);
    }
  });

  ws.on("close", () => clients.delete(ws));
});

function broadcastEvent(payload) {
  const msg = JSON.stringify(payload);
  for (const client of clients) {
    if (client.readyState === WebSocket.OPEN) {
      client.send(msg);
    }
  }
}

// Active worker instance
let activeWorker = null;

// =========================================================================
// REST API ROUTES
// =========================================================================

// 1. System Status & Settings
app.get("/api/status", (req, res) => {
  res.json({
    status: "ONLINE",
    version: "1.0.0",
    provider: globalLlmProvider.getProviderInfo(),
    tools: globalToolRegistry.listToolSchemas(),
    isWorkerBusy: activeWorker ? activeWorker.isRunning : false
  });
});

app.post("/api/settings", (req, res) => {
  const { provider, geminiApiKey, openaiApiKey, anthropicApiKey, modelName } = req.body;
  globalLlmProvider.setProvider(provider, { geminiApiKey, openaiApiKey, anthropicApiKey, modelName });
  broadcastEvent({
    event: "SETTINGS_UPDATED",
    providerInfo: globalLlmProvider.getProviderInfo()
  });
  res.json({ success: true, providerInfo: globalLlmProvider.getProviderInfo() });
});

// 2. Start Task
app.post("/api/tasks", async (req, res) => {
  const { goal, options = {} } = req.body;
  if (!goal || typeof goal !== "string") {
    return res.status(400).json({ error: "Field 'goal' is required" });
  }

  if (activeWorker && activeWorker.isRunning) {
    return res.status(409).json({ error: "Another task is currently running. Please wait or abort." });
  }

  activeWorker = new AutonomousWorker({
    onEvent: (eventData) => broadcastEvent(eventData),
    skipApprovals: options.skipApprovals === true
  });

  // Start asynchronously so client gets immediate task ID response
  const taskId = `TASK-${Date.now().toString(36).toUpperCase()}`;
  res.json({
    success: true,
    taskId,
    message: "Task accepted and execution started.",
    goal
  });

  // Execute worker loop
  activeWorker.startTask(goal, { taskId, ...options }).catch(err => {
    console.error("[AutonomousWorker] Task error:", err.message);
  });
});

// 3. Abort Active Task
app.post("/api/tasks/abort", (req, res) => {
  if (activeWorker && activeWorker.isRunning) {
    activeWorker.stop();
    return res.json({ success: true, message: "Task abort signal sent." });
  }
  res.json({ success: false, message: "No active task running." });
});

// 4. Resolve Human-in-the-Loop Approval
app.post("/api/approvals/:id/resolve", (req, res) => {
  const { id } = req.params;
  const { decision = "APPROVED", userComment = "" } = req.body;

  try {
    const record = globalHitlManager.resolveApproval(id, decision, userComment);
    broadcastEvent({
      event: "APPROVAL_RESOLVED",
      approvalId: id,
      decision,
      userComment
    });
    res.json({ success: true, record });
  } catch (err) {
    res.status(400).json({ error: err.message });
  }
});

// 5. Query Tasks & History
app.get("/api/tasks", (req, res) => {
  res.json({ tasks: dbInstance.listTasks() });
});

app.get("/api/tasks/:id", (req, res) => {
  const task = dbInstance.getTask(req.params.id);
  if (!task) return res.status(404).json({ error: "Task not found" });
  res.json({ task });
});

// 6. Simulated ERP Endpoints
app.get("/api/erp/invoices", (req, res) => {
  res.json({ invoices: erpInstance.listInvoices(req.query) });
});

app.get("/api/erp/vendors", (req, res) => {
  res.json({ vendors: erpInstance.listVendors() });
});

app.get("/api/erp/orders", (req, res) => {
  res.json({ orders: erpInstance.orders });
});

app.get("/api/erp/audit", (req, res) => {
  res.json({ auditLogs: erpInstance.auditLogs });
});

app.post("/api/erp/reset", (req, res) => {
  erpInstance.reset();
  broadcastEvent({ event: "ERP_RESET", message: "Simulated ERP re-seeded to initial state." });
  res.json({ success: true, message: "ERP data reset successfully" });
});

// 7. Mock Files Explorer
app.get("/api/files", async (req, res) => {
  try {
    const result = await globalToolRegistry.execute("list_files", { directory: "" });
    res.json(result);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.get("/api/files/content", async (req, res) => {
  const { path: filePath } = req.query;
  if (!filePath) return res.status(400).json({ error: "Missing 'path' query parameter" });

  const result = await globalToolRegistry.execute("read_file", { filePath });
  res.json(result);
});

// Launch HTTP & WS server
server.listen(PORT, () => {
  console.log(`\n======================================================`);
  console.log(`🤖 Autonomous AI Task Worker is running!`);
  console.log(`📍 Web Dashboard: http://localhost:${PORT}`);
  console.log(`⚡ WebSocket Stream: ws://localhost:${PORT}/ws`);
  console.log(`📁 Simulated Storage: ${MOCK_FILES_DIR}`);
  console.log(`======================================================\n`);
});
