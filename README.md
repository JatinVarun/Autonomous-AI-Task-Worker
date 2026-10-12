# ⚡ AURA Worker — Autonomous Enterprise Task Agent (Python + Streamlit)

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Streamlit](https://img.shields.io/badge/UI-Streamlit-FF4B4B.svg)](https://streamlit.io/)
[![Architecture](https://img.shields.io/badge/Architecture-ReAct%20Loop-7928CA.svg)](#architecture)
[![Verification](https://img.shields.io/badge/Proof-SHA--256%20Cryptographic-00C7B7.svg)](#independent-verification)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](#license)

**AURA Worker** is a 100% native Python autonomous AI agent designed to execute complex enterprise workflows from natural language directives. It combines **dynamic goal decomposition**, a **ReAct loop (Reasoning + Acting)**, a **pluggable tool execution suite**, **self-correction mechanisms**, **Human-in-the-Loop (HITL) safety gating**, and **independent cryptographic outcome verification**.

Zero external API keys are required to evaluate — it comes with a built-in cognitive ReAct reasoning engine out-of-the-box.

---

## 📸 Key Features

- **🧠 Cognitive ReAct Execution**: Autonomous Reasoning, Tool Invocation, Observation Parsing, and dynamic Milestone Planning.
- **🛡️ Human-in-the-Loop (HITL) Policy Engine**: Automatically gates high-risk operations (e.g. Invoices $\ge \$10,000$ or customer refund disbursements) for manual operator authorization before side-effects occur.
- **🔒 Independent Cryptographic Verification**: Verifies real-world database mutations directly against ERP records and issues SHA-256 signed evidence digests to eliminate hallucinated completions.
- **🏢 Enterprise Simulation Suite**: Embedded In-memory ERP (Accounts Payable, Vendor Registry, Audit Trails), Commerce Order Database, and mock corporate file repositories.
- **✨ Streamlit Control Center**: Glassmorphism dark-mode UI with live ReAct event streams, interactive ERP explorer, file inspector, and execution telemetry.

---

## 🚀 Quickstart

### Prerequisites
- **Python 3.10 or higher**
- Git

### 1. Clone & Set Up Environment

```bash
git clone https://github.com/JatinVarun/Autonomous-AI-Task-Worker.git
cd Autonomous-AI-Task-Worker

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# macOS / Linux:
# source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Run Test Suite

Run the unit and integration test suite:

```bash
pytest -v
```

All 11 tests validate the ReAct loop, tool registry, HITL pause/resume flow, ERP duplicate detection, and ground-truth verification assertions:
```text
tests/test_agent.py::test_acme_invoice_end_to_end PASSED
tests/test_agent.py::test_globex_json_invoice PASSED
tests/test_agent.py::test_hitl_pauses_then_resumes_on_approval PASSED
tests/test_agent.py::test_initech_vendor_update PASSED
tests/test_agent.py::test_refund_ticket PASSED
tests/test_tools.py::test_list_invoice_files PASSED
tests/test_tools.py::test_read_invoice_file PASSED
tests/test_tools.py::test_erp_create_invoice_and_duplicate PASSED
tests/test_tools.py::test_tool_registry_schemas PASSED
tests/test_verifier.py::test_positive_invoice_verification PASSED
tests/test_verifier.py::test_missing_invoice_fails_verification PASSED
```

### 3. Launch the Streamlit Control Center

```bash
streamlit run app.py
```

Open your browser to:
👉 **[http://localhost:8501](http://localhost:8501)**

---

## 🎯 Evaluation Presets

The dashboard provides 4 instant enterprise evaluation presets:

| Preset | Objective | Safety Policy / Behavior |
| :--- | :--- | :--- |
| **1. Acme Invoice Entry** | Finds latest Acme invoice (`INV-2024-889`, $14,250.00), parses due date & amount, registers in ERP, and verifies. | 🛑 **Gated by HITL** (Amount $\ge \$10,000$). Pauses for human authorization unless bypassed. |
| **2. Globex JSON Invoice** | Discovers Globex Logistics JSON file (`GL-2024-902`), parses unstructured/structured JSON payload, and updates ERP. | ⚡ Autonomous end-to-end execution with duplicate-check protection. |
| **3. Vendor Agreement** | Locates Initech Technologies agreement, extracts approved Tax ID & payment terms (Net 45), updates Vendor Master. | ⚡ Cross-directory document analysis & vendor master persistence. |
| **4. Refund Ticket #842** | Processes support ticket for Order `#ORD-99381`, queries commerce DB, executes refund disbursement, and audits. | 🛑 **Gated by HITL** (Financial refund disbursement requires authorization). |

---

## 🏗️ System Architecture

```text
                  ┌─────────────────────────────────────────┐
                  │    Streamlit Web Dashboard (app.py)     │
                  └───────────────────▲─────────────────────┘
                                      │ Event Stream / User Input
                  ┌───────────────────▼─────────────────────┐
                  │       AutonomousWorker (worker.py)      │
                  │   - State Machine: RUNNING/PAUSED/DONE   │
                  └─────────┬─────────────────────┬─────────┘
                            │                     │
            ┌───────────────▼───────┐     ┌───────▼───────────────┐
            │   Cognitive Reasoner  │     │   HITL Policy Engine  │
            │  (llm/rule_engine.py) │     │       (hitl.py)       │
            └───────────────┬───────┘     └───────┬───────────────┘
                            │                     │
            ┌───────────────▼─────────────────────▼─────────┐
            │            Tool Registry (tools/)             │
            │  - file_tools        - erp_tools              │
            │  - db_tools          - browser_tools          │
            └───────────────────────┬───────────────────────┘
                                    │ Record Mutations
            ┌───────────────────────▼───────────────────────┐
            │         Outcome Verifier (verifier.py)        │
            │   Independent Ground-Truth Query & SHA-256    │
            └───────────────────────────────────────────────┘
```

### Module Breakdown

| Directory / File | Description |
| :--- | :--- |
| **`app.py`** | Main Streamlit interactive control center and real-time dashboard. |
| **`aura_worker/worker.py`** | ReAct orchestration engine, event dispatcher, pause/resume lifecycle. |
| **`aura_worker/hitl.py`** | Enterprise risk policy scoring (risk levels, thresholds, reason codes). |
| **`aura_worker/verifier.py`** | Independent verifier comparing real database state against target goals. |
| **`aura_worker/memory.py`** | Working scratchpad and step execution history storage. |
| **`aura_worker/llm/`** | Built-in cognitive engine with multi-step reasoning and pluggable LLM interfaces. |
| **`aura_worker/tools/`** | Standardized tool registry (`list_files`, `read_file`, `erp_create_invoice`, etc.). |
| **`aura_worker/environment/`** | In-memory ERP database, commerce DB, and mock company storage directory. |
| **`tests/`** | Full pytest test suite covering unit, integration, and edge scenarios. |

---

## 🔒 Independent Verification & Digital Proofs

A common flaw in autonomous AI workers is **hallucinated completion** (assuming that because a function was called, the real-world side-effect succeeded). 

AURA Worker solves this with an **Independent Verifier**:
1. **Direct Ground-Truth Inspection**: Performs a clean, independent query against the live ERP database.
2. **Deterministic Assertions**: Checks invoice number, vendor identity, exact floating-point amount matching ($\Delta < \$0.01$), and ISO dates.
3. **Cryptographic Proof Digest**: Generates a tamper-evident digital signature:
   $$\text{Digest} = \text{SHA256}(\text{VerificationId} \parallel \text{TargetID} \parallel \text{Amount} \parallel \text{Timestamp})$$
4. **Audit Status**: Flags the ERP entry with `VERIFIED_ACCURATE` once mathematically confirmed.

---

## 🛠️ Configuration & Customization

### Switching Models
By default, AURA Worker uses the built-in Cognitive ReAct Engine (`BUILTIN_COGNITIVE_ENGINE`), requiring **no API keys**. You can also plug in external LLM providers (e.g., Gemini, OpenAI) via [`aura_worker/llm/provider.py`](file:///c:/Users/jatin/OneDrive/Desktop/assignment/aura_worker/llm/provider.py).

---

## 📄 License

This project is licensed under the MIT License.
