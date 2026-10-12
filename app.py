"""AURA Worker — Streamlit Autonomous Enterprise Control Center (100% Python)."""

from __future__ import annotations

import json
from datetime import datetime

import streamlit as st

from aura_worker.environment.erp_service import erp_instance
from aura_worker.llm.provider import global_llm_provider
from aura_worker.tools.file_tools import list_files, read_file
from aura_worker.worker import AutonomousWorker

PRESETS = {
    "Acme Invoice Entry": "Find the latest invoice from Acme Corp, extract the amount and due date, enter it into our internal system, and tell me once it is done.",
    "Globex JSON Invoice": "Find the invoice from Globex Logistics Corp, parse its JSON amount and due date, register it in the ERP system, and verify.",
    "Vendor Agreement": "Locate the vendor agreement for Initech Technologies, extract approved tax ID and payment terms, update the ERP vendor master directory, and verify.",
    "Refund Ticket #842": "Process refund request in email ticket #REF-842, check order status in database, submit refund transaction, and verify completion.",
}

st.set_page_config(
    page_title="AURA Worker | Autonomous Enterprise Agent",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

      html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
      }
      code, pre, .mono {
        font-family: 'JetBrains Mono', monospace !important;
      }

      .stApp {
        background: radial-gradient(1400px 700px at 15% -10%, #1e2659 0%, #0c1126 40%, #060913 100%);
        color: #e6edff;
      }
      .block-container {
        padding-top: 1.2rem;
        padding-bottom: 2.5rem;
        max-width: 1680px;
      }

      /* Hero Banner */
      .aura-hero {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 20px;
        padding: 18px 24px;
        border: 1px solid rgba(130, 160, 255, 0.22);
        border-radius: 18px;
        background: linear-gradient(135deg, rgba(30, 42, 92, 0.75) 0%, rgba(13, 18, 38, 0.85) 100%);
        backdrop-filter: blur(12px);
        box-shadow: 0 10px 32px rgba(0, 0, 0, 0.35);
        margin-bottom: 18px;
      }
      .aura-tagline {
        font-size: 11px;
        font-weight: 700;
        color: #8da4ff;
        letter-spacing: .16em;
        text-transform: uppercase;
        margin-bottom: 4px;
      }
      .aura-title {
        font-size: 26px;
        font-weight: 800;
        letter-spacing: -0.02em;
        color: #ffffff;
      }
      .aura-gradient-text {
        background: linear-gradient(90deg, #6894ff 0%, #a27bfa 50%, #4ae3b5 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
      }

      /* Status Badges */
      .badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 5px 14px;
        border-radius: 999px;
        font-size: 11.5px;
        font-weight: 700;
        letter-spacing: .06em;
        text-transform: uppercase;
      }
      .badge-ok { background: rgba(30, 140, 90, 0.25); color: #4ae3b5; border: 1px solid rgba(74, 227, 181, 0.4); }
      .badge-run { background: rgba(220, 140, 30, 0.25); color: #ffd166; border: 1px solid rgba(255, 209, 102, 0.4); }
      .badge-wait { background: rgba(230, 50, 70, 0.25); color: #ff6b8b; border: 1px solid rgba(255, 107, 139, 0.4); animation: pulse 2s infinite; }
      .badge-idle { background: rgba(70, 90, 160, 0.25); color: #a4b8ff; border: 1px solid rgba(164, 184, 255, 0.3); }

      @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.65; }
      }

      /* Stream Cards */
      .thought {
        border-left: 3px solid #6b9cff;
        padding: 10px 14px;
        margin: 8px 0;
        background: rgba(60, 95, 210, 0.12);
        border-radius: 0 12px 12px 0;
        font-size: 13.5px;
        line-height: 1.5;
      }
      .action {
        border-left: 3px solid #f6ad55;
        padding: 10px 14px;
        margin: 8px 0;
        background: rgba(235, 150, 45, 0.12);
        border-radius: 0 12px 12px 0;
        font-size: 13px;
      }
      .obs {
        border-left: 3px solid #48bb78;
        padding: 10px 14px;
        margin: 8px 0;
        background: rgba(50, 180, 110, 0.10);
        border-radius: 0 12px 12px 0;
        font-size: 12.5px;
      }
      .verif {
        border-left: 3px solid #b794f4;
        padding: 10px 14px;
        margin: 8px 0;
        background: rgba(160, 110, 230, 0.14);
        border-radius: 0 12px 12px 0;
        font-size: 13px;
      }

      /* Pre blocks */
      pre {
        background: rgba(4, 7, 18, 0.7) !important;
        border: 1px solid rgba(130, 160, 255, 0.15) !important;
        border-radius: 8px !important;
        padding: 8px 12px !important;
        color: #cfe0ff !important;
        font-size: 11.5px !important;
      }

      /* Approval Box */
      .hitl-box {
        border: 1px solid rgba(255, 100, 120, 0.6);
        background: linear-gradient(135deg, rgba(255, 60, 90, 0.15) 0%, rgba(120, 20, 40, 0.25) 100%);
        padding: 18px;
        border-radius: 14px;
        box-shadow: 0 8px 24px rgba(230, 40, 70, 0.2);
        margin: 12px 0;
      }

      /* Tables */
      table {
        width: 100%;
        border-collapse: collapse;
        margin: 10px 0;
        font-size: 12.5px;
      }
      th {
        background: rgba(30, 45, 100, 0.6);
        color: #8da4ff;
        font-weight: 700;
        text-align: left;
        padding: 8px 10px;
        border-bottom: 2px solid rgba(130, 160, 255, 0.25);
      }
      td {
        padding: 8px 10px;
        border-bottom: 1px solid rgba(130, 160, 255, 0.1);
        color: #d6e2ff;
      }
      tr:hover {
        background: rgba(70, 100, 210, 0.08);
      }
    </style>
    """,
    unsafe_allow_html=True,
)


def init_state():
    defaults = {
        "goal": PRESETS["Acme Invoice Entry"],
        "events": [],
        "result": None,
        "worker": None,
        "status": "STANDBY / READY",
        "auto_approve": False,
        "selected_file": None,
        "provider": "BUILTIN_COGNITIVE_ENGINE",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def status_badge(status: str) -> str:
    s = (status or "").upper()
    cls = "badge-idle"
    dot = "●"
    if "WAIT" in s:
        cls = "badge-wait"
        dot = "⏸"
    elif "RUN" in s or "EXECUT" in s:
        cls = "badge-run"
        dot = "⚡"
    elif "VERIFIED" in s or "COMPLETE" in s:
        cls = "badge-ok"
        dot = "✔"
    return f'<span class="badge {cls}">{dot} {status}</span>'


def run_worker(goal: str, auto_approve: bool):
    events = []
    worker = AutonomousWorker(on_event=events.append, skip_approvals=auto_approve)
    result = worker.start_task(goal, {"skip_approvals": auto_approve})
    st.session_state.worker = worker
    st.session_state.events = worker.events
    st.session_state.result = result
    st.session_state.status = result.get("status", worker.status)


def resume_worker(decision: str, comment: str = ""):
    worker: AutonomousWorker = st.session_state.worker
    result = worker.resume(decision, comment)
    st.session_state.events = worker.events
    st.session_state.result = result
    st.session_state.status = result.get("status", worker.status)


def render_stream(events):
    if not events:
        st.info("AI Worker is on standby. Select an evaluation preset and launch the agent.")
        return

    for ev in events:
        et = ev.get("event")
        if et == "TASK_STARTED":
            st.markdown(f"**⚡ Task directive received** — `{ev.get('goal')}`")
        elif et == "PLAN_GENERATED":
            st.caption(f"🧠 Milestones Planned: {ev.get('goal_understanding', 'Plan generated')}")
        elif et == "REASONING_STEP":
            st.markdown(
                f'<div class="thought"><b>💡 Reasoner [Step {ev.get("step_index")}]</b><br/>{ev.get("thought")}</div>',
                unsafe_allow_html=True,
            )
        elif et == "ACTION_EXECUTING":
            params = json.dumps(ev.get("parameters") or {}, indent=2, default=str)
            st.markdown(
                f'<div class="action"><b>⚙️ Action Triggered</b> · <code>{ev.get("tool_name")}</code><pre>{params}</pre></div>',
                unsafe_allow_html=True,
            )
        elif et == "OBSERVATION_RECEIVED":
            obs = ev.get("observation") or {}
            compact = {k: v for k, v in obs.items() if k != "_meta"}
            preview = json.dumps(compact, indent=2, default=str)
            if len(preview) > 1200:
                preview = preview[:1200] + "\n… (truncated for readability)"
            st.markdown(f'<div class="obs"><b>👁️ Tool Observation</b><pre>{preview}</pre></div>', unsafe_allow_html=True)
        elif et == "WAITING_FOR_USER_APPROVAL":
            st.warning("⚠️ High-Risk Action Gated: Operator approval required before executing side-effect.")
        elif et == "VERIFICATION_COMPLETED":
            vr = ev.get("verification_result") or {}
            st.markdown(
                f'<div class="verif"><b>🔒 Independent Ground-Truth Verification</b><br/>'
                f'<b>Verdict:</b> {vr.get("verdict")}<br/>'
                f'<b>Proof Digest:</b> <code>{vr.get("proof_signature")}</code></div>',
                unsafe_allow_html=True,
            )
        elif et == "TASK_COMPLETED":
            st.success(f"🎉 Task finished successfully with status **{ev.get('status')}**")
        elif et == "TASK_FAILED":
            st.error(f"❌ Task failure: {ev.get('error')}")


def render_markdown_table(rows):
    if not rows:
        return
    headers = list(rows[0].keys())
    header_line = "| " + " | ".join(headers) + " |"
    sep_line = "| " + " | ".join(["---"] * len(headers)) + " |"
    data_lines = [
        "| " + " | ".join(str(r.get(h, "")).replace("|", "/") for h in headers) + " |"
        for r in rows
    ]
    st.markdown("\n".join([header_line, sep_line] + data_lines))


init_state()

status = st.session_state.status

# Top Bar Hero
st.markdown(
    f"""
    <div class="aura-hero">
      <div>
        <div class="aura-tagline">100% Python • Streamlit Control Center • Zero-Dependency ReAct Engine</div>
        <div class="aura-title">AURA <span class="aura-gradient-text">AUTONOMOUS TASK WORKER</span></div>
      </div>
      <div style="text-align:right;">
        {status_badge(status)}
        <div style="color:#8da4ff;font-size:11.5px;margin-top:6px;font-weight:600;">
          REASONER: {global_llm_provider.info()["label"]}
        </div>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

left, right = st.columns([1.15, 1], gap="large")

with left:
    st.markdown("### 🎯 Task Directive & Execution")
    preset = st.radio(
        "Evaluation presets",
        list(PRESETS.keys()),
        horizontal=True,
        label_visibility="collapsed",
    )
    if "last_preset" not in st.session_state or st.session_state.last_preset != preset:
        st.session_state.goal = PRESETS[preset]
        st.session_state.last_preset = preset

    goal = st.text_area("Natural language objective", value=st.session_state.goal, height=95)
    st.session_state.goal = goal

    col_opt1, col_opt2 = st.columns([1, 1])
    with col_opt1:
        auto = st.checkbox("⚡ Auto-approve high-risk actions (Bypass HITL)", value=st.session_state.auto_approve)
        st.session_state.auto_approve = auto

    c1, c2, c3 = st.columns([1.4, 1, 1])
    with c1:
        launch = st.button("🚀 Launch Autonomous Worker", type="primary", use_container_width=True)
    with c2:
        reset = st.button("🔄 Reset ERP & State", use_container_width=True)
    with c3:
        abort = st.button("⏹ Abort", use_container_width=True)

    if reset:
        erp_instance.reset()
        st.session_state.events = []
        st.session_state.result = None
        st.session_state.worker = None
        st.session_state.status = "STANDBY / READY"
        st.success("Simulated ERP records, database, and logs reset to clean bootstrap state.")
        st.rerun()

    if abort and st.session_state.worker:
        st.session_state.worker.stop()
        st.session_state.status = "ABORTED"
        st.rerun()

    if launch:
        run_worker(goal, auto)
        st.rerun()

    # Human-In-The-Loop Modal / Box
    result = st.session_state.result or {}
    if result.get("status") == "WAITING_FOR_APPROVAL":
        approval = result.get("approval") or {}
        risk = result.get("risk_assessment") or {}
        action = result.get("intended_action") or {}
        st.markdown(
            f"""
            <div class="hitl-box">
              <div style="font-size:16px;font-weight:800;color:#ff6b8b;margin-bottom:6px;">
                🛑 HUMAN-IN-THE-LOOP APPROVAL REQUIRED
              </div>
              <div style="color:#ffd3df;font-size:13.5px;margin-bottom:8px;">
                {risk.get("reason") or approval.get("reason")}
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.code(
            json.dumps({"action": action.get("name"), "parameters": action.get("parameters")}, indent=2, default=str),
            language="json",
        )
        comment = st.text_input("Optional authorization note or operator comment", key="hitl_comment")
        a1, a2 = st.columns(2)
        with a1:
            if st.button("✅ Approve & Continue Execution", type="primary", use_container_width=True):
                resume_worker("APPROVED", comment)
                st.rerun()
        with a2:
            if st.button("🚫 Reject Action", use_container_width=True):
                resume_worker("REJECTED", comment or "Rejected by operator policy")
                st.rerun()

    # Plan Milestone Tracker
    plan = (st.session_state.result or {}).get("plan") or []
    if plan:
        st.markdown("### 📋 Decomposed Milestone Plan")
        done = sum(1 for s in plan if s.get("status") == "COMPLETED")
        st.progress(done / len(plan), text=f"Progress: {done} / {len(plan)} milestones completed")
        for step in plan:
            mark = "✅" if step.get("status") == "COMPLETED" else "⚪"
            st.write(f"{mark} **{step.get('id')}. {step.get('title')}** — {step.get('description')}")

    st.markdown("### 🧠 Cognitive ReAct Stream (Live Execution Trace)")
    render_stream(st.session_state.events)

with right:
    tab_erp, tab_files, tab_proof, tab_summary = st.tabs(
        ["🏢 ERP Master Portal", "📁 Storage Filesystem", "🔒 Verification Proof", "📊 Executive Summary"]
    )

    with tab_erp:
        invoices = erp_instance.list_invoices()
        vendors = erp_instance.list_vendors()
        ap_total = sum(float(i.get("amount") or 0) for i in invoices if i.get("status") != "PAID")

        m1, m2, m3 = st.columns(3)
        m1.metric("Registered Invoices", len(invoices))
        m2.metric("Open Accounts Payable", f"${ap_total:,.2f}")
        m3.metric("Registered Vendors", len(vendors))

        st.markdown("#### 📑 Accounts Payable Invoices")
        if invoices:
            inv_rows = [
                {
                    "ERP ID": i.get("id"),
                    "Invoice #": i.get("invoice_number"),
                    "Vendor": i.get("vendor_name"),
                    "Amount": f"${float(i.get('amount') or 0):,.2f}",
                    "Due Date": i.get("due_date"),
                    "Status": i.get("status"),
                    "Verification": i.get("verification_status"),
                }
                for i in invoices
            ]
            render_markdown_table(inv_rows)
        else:
            st.caption("No invoices in ERP database.")

        st.markdown("#### 🏢 Vendor Master Directory")
        vend_rows = [
            {
                "Vendor ID": v.get("id"),
                "Legal Name": v.get("name"),
                "Tax ID": v.get("tax_id"),
                "Terms": v.get("payment_terms"),
                "Status": v.get("status"),
            }
            for v in vendors
        ]
        render_markdown_table(vend_rows)

        st.markdown("#### 📜 System Audit Trail (Last 10 Records)")
        logs = erp_instance.audit_logs[-10:]
        logs.reverse()
        log_rows = [
            {
                "Time": (row.get("timestamp") or "")[-12:],
                "Actor": row.get("actor"),
                "Action": row.get("action"),
                "Details": json.dumps(row.get("details"), default=str)[:70],
            }
            for row in logs
        ]
        render_markdown_table(log_rows)

    with tab_files:
        listing = list_files("")
        dirs = [f for f in listing.get("files", []) if f.get("type") == "directory"]
        st.caption("Simulated corporate file store: invoices, vendor contracts, email tickets")
        selected_dir = st.selectbox("Select Directory", [d["path"] for d in dirs] if dirs else ["invoices"])
        files = list_files(selected_dir).get("files", [])
        names = [f["path"] for f in files if f.get("type") == "file"]
        if names:
            chosen = st.selectbox("Inspect File Contents", names)
            preview = read_file(chosen)
            content = preview.get("content")
            lang = "json" if chosen.endswith(".json") else None
            st.code(
                content if isinstance(content, str) else json.dumps(content, indent=2),
                language=lang,
            )
        else:
            st.caption("No files found in directory.")

    with tab_proof:
        proof = (st.session_state.result or {}).get("verification_proof")
        if not proof:
            st.info("No completed task submitted for verification yet. Launch any directive to generate cryptographic proof.")
        else:
            verified = proof.get("verified")
            if verified:
                st.success("✅ Independent Ground-Truth Verification: PASSED")
            else:
                st.error("❌ Independent Ground-Truth Verification: FAILED")
            st.write(f"**Verdict:** {proof.get('verdict')}")
            c1, c2 = st.columns(2)
            c1.write(f"**Verification ID:** `{proof.get('verification_id')}`")
            c2.write(f"**Target System:** `{proof.get('target_system')}`")
            st.write(f"**SHA-256 Proof Signature:** `{proof.get('proof_signature')}`")
            with st.expander("Detailed Ground-Truth Assertions", expanded=True):
                st.json(proof.get("checks") or {})
            if proof.get("evidence"):
                with st.expander("Cryptographic Evidence Digest", expanded=False):
                    st.json(proof.get("evidence"))

    with tab_summary:
        res = st.session_state.result
        if not res:
            st.info("Run an autonomous worker task to view performance metrics and state discoveries.")
        else:
            summ = res.get("summary") or {}
            c_s1, c_s2, c_s3 = st.columns(3)
            c_s1.metric("Execution Time", f"{summ.get('duration_ms', 0):.2f} ms")
            c_s2.metric("Total Steps", summ.get("total_steps_executed", 0))
            c_s3.metric("Errors Recovered", summ.get("errors_encountered", 0))

            st.markdown("#### 🔍 Extracted State & Variables")
            st.json(res.get("discovered_state") or {})
