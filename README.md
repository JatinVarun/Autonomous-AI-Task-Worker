# AURA Worker: Autonomous AI Task Worker

An autonomous AI task worker prototype that receives natural language instructions and autonomously completes real-world enterprise computer workflows using dynamic goal decomposition, perception-action loops (ReAct), multi-tool execution, self-correction, human-in-the-loop safety gating, and independent outcome verification.

---

## 🌟 Key Capabilities & Evaluation Highlights

| Capability | Implementation in AURA Worker |
| :--- | :--- |
| **Autonomy** | Decomposes high-level directives into multi-step milestone plans without requiring step-by-step human guidance. Implements a ReAct cognitive loop (`Thought` ➔ `Action` ➔ `Observation` ➔ `Reflection`). |
| **Real Execution** | Performs actual operations against simulated enterprise environments: reads disk documents (plain text, JSON invoices, contracts), queries internal ERP APIs, registers accounting records, and inspects databases. |
| **Reliability & Self-Correction** | Diagnoses tool failures (e.g., file not found, ERP duplicate conflicts, field formatting), updates memory scratchpad, and tries alternative paths. |
| **Independent Verification** | Dedicated `OutcomeVerifier` checks ground truth in target systems before declaring task completion, ensuring zero hallucinated completions and issuing cryptographic evidence tokens. |
| **Human-in-the-Loop (HITL)** | Built-in policy engine intercepts high-risk operations (transactions $\ge \$10,000$, direct refunds, ambiguous inputs), halts execution, and prompts the user via an interactive modal before continuing. |
| **Generalization** | Decoupled `ToolRegistry` and cognitive reasoner handle diverse scenarios: accounts payable processing, JSON invoices, vendor master updates, and customer refund disputes. |
| **Zero-Setup Testing** | Runs out of the box with zero external API keys required via the built-in Cognitive ReAct engine, with seamless drop-in support for Gemini 2.0 and OpenAI GPT-4o. |

---

## 🚀 Quickstart & Setup Instructions

### Prerequisites
- **Node.js**: v18.0.0 or later (Tested on Node.js v24)
- **Git**

### 1. Installation
Clone the repository and install dependencies:
```bash
git clone <repository-url>
cd assignment
npm install
```

### 2. Run Automated Verification Test Suite
Run the comprehensive test suite verifying tool execution, error handling, human approval flows, and end-to-end task completion:
```bash
npm test
```
*Expected result: 11 passing tests in <300ms.*

### 3. Launch the Live Prototype
Start the local server and web control center:
```bash
npm start
```
Open your browser to:
**[http://localhost:3000](http://localhost:3000)**

---

## 🖥️ Live Dashboard & Interactive Demo

The web dashboard is an interactive command center built with a modern dark glassmorphism design:

1. **Task Directive & Evaluation Presets**:
   - **Preset 1 (Benchmark Task)**: *"Find the latest invoice from Acme Corp, extract the amount and due date, enter it into our internal system, and tell me once it is done."*
   - **Preset 2 (JSON Invoices)**: *"Find the invoice from Globex Logistics Corp, parse its JSON amount and due date, register it in the ERP system, and verify."*
   - **Preset 3 (Vendor Onboarding)**: *"Locate the vendor agreement for Initech Technologies, extract approved tax ID and payment terms, update the ERP vendor master directory, and verify."*
   - **Preset 4 (Customer Refunds)**: *"Process refund request in email ticket #REF-842, check order status in database, submit refund transaction, and verify completion."*
   - **Custom Directives**: Type any natural language prompt into the input area.

2. **Real-Time Cognitive Stream**:
   - Live streaming of the agent's internal monologue (**Thought**), tool calls (**Action**), raw returned data (**Observation**), and dynamic memory state.

3. **Human-in-the-Loop Interactive Modal**:
   - When the worker processes the Acme invoice ($14,250.00), the safety policy detects that it exceeds the $10,000 threshold and displays an authorization dialog. Click **"✅ Approve & Authorize"** to watch the worker resume.

4. **Live System of Record (Simulated ERP)**:
   - Switch to the **Internal ERP Portal** tab to watch records appear in real-time in the Accounts Payable table with status `VERIFIED_ACCURATE`.

5. **Independent Verification Proof Inspector**:
   - Inspect the cryptographic verification receipt containing the SHA-256 proof signature, target system confirmation ID, and field assertion results.

---

## 🏛️ System Architecture

```mermaid
graph TD
    User([User Directive]) --> Controller[Autonomous Worker Engine]
    Controller --> Memory[Working Memory & Scratchpad]
    Controller --> LLM[Cognitive Reasoner / LLM Provider]
    
    LLM --> Plan[Dynamic Milestone Plan]
    LLM --> ReAct[ReAct Loop: Thought + Action Selection]
    
    ReAct --> Policy{HITL Safety Policy}
    Policy -- Risk >= Threshold --> HITL[Human Approval Modal]
    HITL -- Approved --> Tools
    Policy -- Safe / Auto-Approve --> Tools
    
    subgraph Tool Sandbox [Tool Execution Sandbox]
        Tools[Tool Registry Dispatcher]
        Tools --> FileTool[Filesystem & Document Parser]
        Tools --> ErpTool[Enterprise ERP Portal API]
        Tools --> DbTool[Commerce Database]
        Tools --> BrowserTool[Web Browser Simulator]
    end

    Tool Sandbox --> Obs[Observation Capture]
    Obs --> SelfCorrect{Error Detected?}
    SelfCorrect -- Yes --> LLM
    SelfCorrect -- No --> Memory

    Memory --> Verifier[Independent Outcome Verifier]
    Verifier --> ERP_DB[(Ground Truth System of Record)]
    Verifier --> Proof[SHA-256 Verifiable Evidence Digest]
    Proof --> Summary[Executive Summary & Audit Report]
```

### Architectural Modules
- **`server/agent/AutonomousWorker.js`**: Orchestrates the autonomous perception-action loop, safety gating, event streaming, and verification lifecycle.
- **`server/agent/memory.js`**: Manages working memory, plan milestone tracking, entity scratchpad variables, and execution history snapshots.
- **`server/agent/humanInTheLoop.js`**: Policy engine that intercepts high-impact actions, raises approval requests, and manages asynchronous resolution.
- **`server/agent/verifier.js`**: Independent verification engine that directly queries system ground truth to ensure real-world changes persisted accurately.
- **`server/agent/llm/ruleEngine.js`**: Built-in deterministic cognitive reasoner allowing instant zero-dependency testing of autonomous behaviors.
- **`server/agent/llm/provider.js`**: Pluggable LLM interface supporting Gemini 2.0, OpenAI GPT-4o, and the built-in Cognitive Reasoner.
- **`server/tools/index.js`**: Tool registry enforcing parameter validation, telemetry timing, error boundaries, and permission sandboxing.
- **`server/environment/erpService.js`**: Live simulated ERP REST service managing Accounts Payable, Vendor Directory, and Audit Logs.

---

## ⚖️ Important Technical & Design Decisions

1. **Independent Verification vs. Self-Reported Completion**:
   - *Problem*: Traditional LLM agents suffer from "hallucinated completion"—they assume that generating an API call means the job succeeded.
   - *Decision*: We built an isolated `OutcomeVerifier` that runs *after* tool execution. It queries the target system directly, matches fields against source values, and issues a cryptographic proof token. If verification fails, the task is marked as unverified.

2. **Dual-Mode Cognitive Reasoner (Built-in + Live LLM)**:
   - *Problem*: Reviewers evaluating take-home assignments frequently face API key configuration issues or quota exhaustion.
   - *Decision*: We implemented an intelligent built-in Cognitive ReAct Engine that parses intent, manages dynamic scratchpads, handles retries, and simulates realistic ReAct execution out of the box with zero keys, while also providing full integration with Gemini 2.0 and OpenAI via the settings panel.

3. **Human-in-the-Loop Safety Policy**:
   - *Problem*: Full autonomy in business operations without guardrails can trigger catastrophic errors (e.g. paying incorrect invoices or executing unauthorized refunds).
   - *Decision*: High-risk actions (transactions $\ge \$10,000$ or refund transactions) are automatically paused by the policy engine. The system exposes an interactive approval modal allowing human oversight while maintaining end-to-end task momentum.

4. **Bi-directional WebSocket Telemetry**:
   - *Problem*: Polling REST APIs creates latency and misses fine-grained cognitive steps.
   - *Decision*: We implemented a WebSocket streaming bus that delivers real-time cognitive thoughts, tool parameters, observations, and system state updates as they occur.

---

## 🔍 Assumptions Made
1. **Target Environment**: The enterprise environment consists of document repositories (invoices, contracts, emails) and internal REST-based systems (ERP, commerce database).
2. **Identification of 'Latest' Document**: Invoices for a vendor are differentiated by sequence numbering (e.g. `INV-2024-889` vs `INV-2024-512`) or document dates. The agent prioritizes higher invoice sequence numbers or newer dates over filesystem timestamp artifacts.
3. **Approval Threshold**: Enterprise policy requires explicit human approval for single disbursements or bills exceeding $10,000.

---

## ⚠️ Known Limitations
- **Headless Browser in Sandboxed Cloud VMs**: In restricted environments without display servers or where external CDN downloads for browser binaries are blocked, web navigation tools fall back to simulated HTTP response extraction.
- **Single Active Worker Concurrency**: The prototype currently runs one active autonomous worker thread at a time per server instance. Multiple concurrent workers would require distributed worker queues (e.g. Redis + BullMQ).
- **PDF Binary OCR**: The prototype parses `.txt`, `.json`, and structured text bills. Real-world deployments would integrate an OCR pipeline (e.g. Tesseract or vision-based document AI models) for scanned raster images.

---

## 🔮 What We Would Build Next With Additional Time
1. **Vision-based Multi-modal Document Parsing**: Integrate vision models (Gemini 2.0 Flash Vision) to extract unstructured layout tables from scanned multi-page PDF invoices.
2. **Dynamic Tool Synthesis**: Allow the worker to dynamically generate and execute custom JavaScript/Python data transformation scripts when encountering unknown file schemas.
3. **Rollback & Transactional Undo Engine**: Introduce state rollback mechanisms so that if verification fails at step 5, earlier mutations (such as draft invoice creation) can be cleanly reverted.
4. **Persistent Vector Memory**: Integrate vector embeddings (e.g., SQLite-vec or Chroma) to allow the agent to recall prior vendor payment terms and historical resolution decisions across sessions.

---

## 📦 Models, Services & Libraries Used
- **Runtime**: Node.js v24 (ES Modules)
- **Web Framework**: Express v4.21.2
- **Real-Time Gateway**: `ws` (v8.18.0)
- **Environment Management**: `dotenv` (v16.4.7)
- **Testing**: Node.js Native Test Runner (`node:test`, `node:assert/strict`)
- **Supported AI Models**:
  - Built-in Cognitive ReAct Engine (Zero setup)
  - Google Gemini 2.0 Flash (`gemini-2.0-flash`)
  - OpenAI GPT-4o (`gpt-4o-mini`)
