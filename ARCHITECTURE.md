# Architecture & Technical Deep-Dive: AURA Worker

This document provides a detailed breakdown of the cognitive architecture, execution patterns, and safety systems powering the Autonomous AI Task Worker.

---

## 1. Cognitive Architecture: The ReAct Execution Loop

The core worker engine implements the **ReAct (Reasoning + Acting)** pattern, enhanced with dynamic milestone planning, an entity scratchpad, and post-execution verification.

```
       ┌───────────────────────────────┐
       │   Goal Understanding Stage    │
       │  (Initial Milestone Planning) │
       └──────────────┬────────────────┘
                      │
                      ▼
       ┌───────────────────────────────┐
  ┌───►│        Cognitive Cycle        │
  │    │  (Perception & Step Planning) │
  │    └──────────────┬────────────────┘
  │                   │
  │                   ▼
  │    ┌───────────────────────────────┐
  │    │      Risk Assessment Gate     │◄─── Intercepts if High Risk
  │    │      (Human-in-the-Loop)      │     (Waits for UI Approval)
  │    └──────────────┬────────────────┘
  │                   │ (Approved / Low Risk)
  │                   ▼
  │    ┌───────────────────────────────┐
  │    │       Tool Execution          │
  │    │   (Sandboxed Environment)     │
  │    └──────────────┬────────────────┘
  │                   │
  │                   ▼
  │    ┌───────────────────────────────┐
  │    │      Observation Capture      │
  │    │    & Failure Self-Correction  │
  │    └──────────────┬────────────────┘
  │                   │
  │                   ▼
  │    ┌───────────────────────────────┐
  │    │    Working Memory Update      │
  │    │   (Discovered Variables State)│
  │    └──────────────┬────────────────┘
  │                   │
  └───────────────────┤ Has more steps?
                      │ (Terminal Goal Reached)
                      ▼
       ┌───────────────────────────────┐
       │ Independent Outcome Verifier  │
       │ (Queries System Ground Truth) │
       └──────────────┬────────────────┘
                      │
                      ▼
       ┌───────────────────────────────┐
       │ Evidence Packet & User Report │
       └───────────────────────────────┘
```

### Cognitive Phases

1. **Goal Decomposition**:
   - The agent parses the user's high-level directive.
   - It decomposes the goal into sequential, verifiable milestones (e.g. `Locate Document` ➔ `Extract Fields` ➔ `Query Vendor Profile` ➔ `Post ERP Invoice` ➔ `Verify Outcome`).
2. **Step-by-Step Reasoning (Thought)**:
   - Evaluates the working memory scratchpad and prior tool observations.
   - Determines the next immediate action and formats validated arguments.
3. **Safety & Policy Gating**:
   - Every candidate action is evaluated by `HumanInTheLoopManager`.
   - Financial actions exceeding the threshold ($\ge \$10,000$) or direct refunds suspend the execution loop.
   - An event is broadcast over WebSocket, and the UI displays an authorization modal. Once approved by the user, execution resumes seamlessly.
4. **Tool Execution & Sandboxing**:
   - The selected tool is executed via `ToolRegistry`.
   - Input parameters are validated against JSON Schema definitions.
   - Errors (e.g. `DuplicateInvoiceError`, `FileNotFound`) are trapped and returned as structured observations.
5. **Observation Reflection & Error Recovery**:
   - The reasoner observes the tool output. If an error is returned, the agent diagnoses the issue and selects an alternative tool or adjusts parameters.
6. **Independent Outcome Verification**:
   - The worker executes an independent query against the ERP or database.
   - Checks that the newly created record exists and that values (amount, vendor, dates) match the extracted source.
   - Emits a signed cryptographic verification token.

---

## 2. Pluggable Tool Registry (`aura_worker/tools/`)

All tools adhere to a standardized interface:
```python
class Tool:
    name: str
    description: str
    parameters: dict

    def execute(self, params: dict, context: ExecutionContext) -> dict:
        ...
```

### Integrated Tool Categories

| Tool Name | Domain | Description |
| :--- | :--- | :--- |
| `list_files` | Document Storage | Lists company files sorted by modification time and directory structure. |
| `read_file` | Document Storage | Reads `.txt`, `.json`, `.csv`, `.md` files; parses JSON structures. |
| `search_documents` | Document Storage | Full-text substring search across all directories. |
| `erp_search_vendors`| Internal ERP | Queries vendor master directory with fuzzy matching and aliases. |
| `erp_get_invoice` | Internal ERP | Queries specific invoice details by ID or invoice number. |
| `erp_create_invoice`| Internal ERP | Registers a new accounts payable invoice with validations and duplicate prevention. |
| `erp_update_vendor` | Internal ERP | Updates master vendor registry (tax ID, payment terms, status). |
| `erp_process_refund`| Internal ERP | Processes customer refunds against verified order records. |
| `browser_navigate` | Web Simulator | Navigates external supplier portals and extracts tables. |
| `db_check_order` | Commerce DB | Validates customer order state and prior refund statuses. |
| `verify_task_outcome`| Verification | Queries ground truth and generates SHA-256 evidence digests. |
| `notify_user` | Notification | Emits the executive summary and evidence packet. |

---

## 3. Independent Verification Engine (`aura_worker/verifier.py`)

Most autonomous agents fail because of **hallucinated completion**: an LLM assumes that because it called a tool, the real-world side effect succeeded.

The `OutcomeVerifier` operates as an independent auditor:
1. **Source of Truth Check**: Queries the real ERP database instance.
2. **Field-by-Field Assertions**:
   - `invoiceNumberMatch`: Exact match between invoice number extracted and stored.
   - `vendorMatch`: Vendor string resolves to the verified vendor ID.
   - `amountMatch`: Absolute difference $\Delta < \$0.01$.
   - `dueDateMatch`: ISO date format alignment.
3. **Evidence Digest Generation**:
   Computes a SHA-256 proof signature:
   $$\text{Signature} = \text{SHA256}(\text{VerificationId} \parallel \text{InvoiceNumber} \parallel \text{Amount} \parallel \text{Timestamp})$$
4. **Verdict**: If all assertions hold, marks the ERP record as `VERIFIED_ACCURATE` and reports `COMPLETED_VERIFIED`.

---

## 4. Dual-Engine Cognitive Reasoner (`aura_worker/llm/`)

To support instant zero-setup evaluation while retaining support for modern commercial foundation models, the system includes a pluggable provider abstraction:

```
                  ┌──────────────────────┐
                  │    LlmProvider       │
                  └──────────┬───────────┘
                             │
         ┌───────────────────┼───────────────────┐
         ▼                   ▼                   ▼
┌──────────────────┐┌──────────────────┐┌──────────────────┐
│ Built-in Engine  ││ Google Gemini    ││ OpenAI GPT-4o    │
│ (Rule-Based)     ││ (gemini-2.0)     ││ (gpt-4o-mini)    │
└──────────────────┘└──────────────────┘└──────────────────┘
```

- **Built-in Cognitive Reasoner**: Implements deterministic state machines with regex extractors, sorting heuristics (such as sequence number matching for "latest invoice"), error retries, and verification calls. Requires 0 external API keys.
- **External Providers**: Drop-in connectors for Google Gemini and OpenAI that format tools as JSON schemas and parse structured function-call outputs.
