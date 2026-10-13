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


def init_state():
    defaults = {
        "theme_mode": "dark",
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


init_state()

is_dark = st.session_state.theme_mode == "dark"

# Dynamic CSS Theme Tokens
if is_dark:
    theme_css = """
    :root {
      --bg-primary: #0a0d14;
      --bg-surface: #121722;
      --bg-surface-elevated: #182030;
      --border-color: #232c40;
      --border-subtle: #1c2436;
      --text-main: #f1f5f9;
      --text-muted: #94a3b8;
      --text-dim: #64748b;
      --brand-primary: #3b82f6;
      --brand-glow: rgba(59, 130, 246, 0.15);
      --code-bg: #0d111a;
      --card-thought-bg: rgba(59, 130, 246, 0.08);
      --card-thought-border: #3b82f6;
      --card-action-bg: rgba(245, 158, 11, 0.08);
      --card-action-border: #f59e0b;
      --card-obs-bg: rgba(16, 185, 129, 0.08);
      --card-obs-border: #10b981;
      --card-verif-bg: rgba(139, 92, 246, 0.08);
      --card-verif-border: #8b5cf6;
      --table-header-bg: #161e2e;
      --table-row-hover: #192234;
      --badge-idle-bg: #1e2638;
      --badge-idle-text: #94a3b8;
      --badge-idle-border: #334155;
    }
    .stApp {
      background-color: var(--bg-primary);
      color: var(--text-main);
    }
    """
else:
    theme_css = """
    :root {
      --bg-primary: #f8fafc;
      --bg-surface: #ffffff;
      --bg-surface-elevated: #ffffff;
      --border-color: #e2e8f0;
      --border-subtle: #edf2f7;
      --text-main: #0f172a;
      --text-muted: #475569;
      --text-dim: #64748b;
      --brand-primary: #2563eb;
      --brand-glow: rgba(37, 99, 235, 0.10);
      --code-bg: #f1f5f9;
      --code-text: #0f172a;
      --card-thought-bg: #eff6ff;
      --card-thought-border: #3b82f6;
      --card-action-bg: #fffbeb;
      --card-action-border: #d97706;
      --card-obs-bg: #f0fdf4;
      --card-obs-border: #059669;
      --card-verif-bg: #faf5ff;
      --card-verif-border: #7c3aed;
      --table-header-bg: #f1f5f9;
      --table-row-hover: #f8fafc;
      --badge-idle-bg: #f1f5f9;
      --badge-idle-text: #475569;
      --badge-idle-border: #cbd5e1;
    }
    .stApp {
      background-color: var(--bg-primary);
      color: var(--text-main);
    }
    header, footer {
      background-color: var(--bg-primary) !important;
    }
    """

st.markdown(
    f"""
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

      {theme_css}

      html, body, [class*="css"], .stMarkdown, .stText {{
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
      }}
      code, pre, .mono {{
        font-family: 'JetBrains Mono', Consolas, monospace !important;
      }}

      .block-container {{
        padding-top: 1.25rem !important;
        padding-bottom: 2.5rem !important;
        max-width: 1600px !important;
      }}

      /* Hero Header */
      .aura-header {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 20px;
        padding: 20px 24px;
        background-color: var(--bg-surface);
        border: 1px solid var(--border-color);
        border-radius: 12px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
        margin-bottom: 20px;
      }}
      .aura-tagline {{
        font-size: 11px;
        font-weight: 700;
        color: var(--brand-primary);
        letter-spacing: 0.12em;
        text-transform: uppercase;
        margin-bottom: 4px;
      }}
      .aura-title {{
        font-size: 22px;
        font-weight: 800;
        letter-spacing: -0.02em;
        color: var(--text-main);
        display: flex;
        align-items: center;
        gap: 8px;
      }}
      .aura-title-badge {{
        font-size: 11px;
        font-weight: 600;
        padding: 2px 8px;
        border-radius: 6px;
        background: var(--brand-glow);
        color: var(--brand-primary);
        border: 1px solid var(--border-color);
      }}

      /* Badges */
      .badge {{
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 5px 12px;
        border-radius: 999px;
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 0.04em;
        text-transform: uppercase;
      }}
      .badge-ok {{
        background: rgba(16, 185, 129, 0.12);
        color: #10b981;
        border: 1px solid rgba(16, 185, 129, 0.3);
      }}
      .badge-run {{
        background: rgba(245, 158, 11, 0.12);
        color: #f59e0b;
        border: 1px solid rgba(245, 158, 11, 0.3);
      }}
      .badge-wait {{
        background: rgba(239, 68, 68, 0.12);
        color: #ef4444;
        border: 1px solid rgba(239, 68, 68, 0.3);
        animation: pulse-ring 2s infinite;
      }}
      .badge-idle {{
        background: var(--badge-idle-bg);
        color: var(--badge-idle-text);
        border: 1px solid var(--badge-idle-border);
      }}

      @keyframes pulse-ring {{
        0%, 100% {{ opacity: 1; }}
        50% {{ opacity: 0.6; }}
      }}

      /* Cards & Execution Stream */
      .stream-card {{
        padding: 12px 16px;
        margin: 10px 0;
        border-radius: 8px;
        font-size: 13.5px;
        line-height: 1.5;
        border-left-width: 4px;
        border-left-style: solid;
        background-color: var(--bg-surface);
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
      }}
      .thought {{
        border-left-color: var(--card-thought-border);
        background-color: var(--card-thought-bg);
        color: var(--text-main);
      }}
      .action {{
        border-left-color: var(--card-action-border);
        background-color: var(--card-action-bg);
        color: var(--text-main);
      }}
      .obs {{
        border-left-color: var(--card-obs-border);
        background-color: var(--card-obs-bg);
        color: var(--text-main);
      }}
      .verif {{
        border-left-color: var(--card-verif-border);
        background-color: var(--card-verif-bg);
        color: var(--text-main);
      }}

      /* Code & Pre Blocks */
      pre {{
        background: var(--code-bg) !important;
        border: 1px solid var(--border-color) !important;
        border-radius: 6px !important;
        padding: 10px 14px !important;
        color: var(--text-main) !important;
        font-size: 12px !important;
        overflow-x: auto !important;
      }}
      code {{
        color: var(--brand-primary) !important;
      }}

      /* Human-in-the-Loop Box */
      .hitl-container {{
        border: 1px solid #ef4444;
        background: rgba(239, 68, 68, 0.06);
        padding: 16px 20px;
        border-radius: 10px;
        margin: 14px 0;
      }}
      .hitl-title {{
        font-size: 15px;
        font-weight: 700;
        color: #ef4444;
        margin-bottom: 6px;
        display: flex;
        align-items: center;
        gap: 8px;
      }}
      .hitl-body {{
        color: var(--text-muted);
        font-size: 13.5px;
        margin-bottom: 10px;
      }}

      /* Tables */
      table {{
        width: 100%;
        border-collapse: collapse;
        margin: 10px 0 16px 0;
        font-size: 13px;
        border: 1px solid var(--border-color);
        border-radius: 8px;
        overflow: hidden;
      }}
      th {{
        background-color: var(--table-header-bg);
        color: var(--text-muted);
        font-weight: 600;
        text-align: left;
        padding: 10px 12px;
        border-bottom: 1px solid var(--border-color);
        font-size: 12px;
        text-transform: uppercase;
        letter-spacing: 0.05em;
      }}
      td {{
        padding: 9px 12px;
        border-bottom: 1px solid var(--border-subtle);
        color: var(--text-main);
      }}
      tr:hover {{
        background-color: var(--table-row-hover);
      }}

      /* Streamlit Element Overrides for Seamless Polish */
      .stTextInput input, .stTextArea textarea, .stSelectbox select {{
        border-radius: 6px !important;
        border: 1px solid var(--border-color) !important;
        background-color: var(--bg-surface) !important;
        color: var(--text-main) !important;
      }}
      div[data-testid="stMetricValue"] {{
        font-size: 24px !important;
        font-weight: 700 !important;
        color: var(--text-main) !important;
      }}
      div[data-testid="stMetricLabel"] {{
        font-size: 12px !important;
        color: var(--text-dim) !important;
        font-weight: 600 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.05em !important;
      }}
      .stTabs [data-baseweb="tab-list"] {{
        gap: 12px;
        border-bottom: 1px solid var(--border-color);
      }}
      .stTabs [data-baseweb="tab"] {{
        font-weight: 600;
        font-size: 13.5px;
        color: var(--text-muted);
        padding-bottom: 8px;
      }}
      .stTabs [aria-selected="true"] {{
        color: var(--brand-primary) !important;
      }}
    </style>
    """,
    unsafe_allow_html=True,
)


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
        st.info("Agent is standing by. Choose a preset or specify a directive to begin execution.")
        return

    for ev in events:
        et = ev.get("event")
        if et == "TASK_STARTED":
            st.markdown(f"**⚡ Task Directive Initialized** — `{ev.get('goal')}`")
        elif et == "PLAN_GENERATED":
            st.caption(f"🧠 Milestones Planned: {ev.get('goal_understanding', 'Plan generated')}")
        elif et == "REASONING_STEP":
            st.markdown(
                f'<div class="stream-card thought"><b>💡 Reasoner [Step {ev.get("step_index")}]</b><br/>{ev.get("thought")}</div>',
                unsafe_allow_html=True,
            )
        elif et == "ACTION_EXECUTING":
            params = json.dumps(ev.get("parameters") or {}, indent=2, default=str)
            st.markdown(
                f'<div class="stream-card action"><b>⚙️ Action Triggered</b> · <code>{ev.get("tool_name")}</code><pre>{params}</pre></div>',
                unsafe_allow_html=True,
            )
        elif et == "OBSERVATION_RECEIVED":
            obs = ev.get("observation") or {}
            compact = {k: v for k, v in obs.items() if k != "_meta"}
            preview = json.dumps(compact, indent=2, default=str)
            if len(preview) > 1200:
                preview = preview[:1200] + "\n… (truncated for readability)"
            st.markdown(f'<div class="stream-card obs"><b>👁️ Tool Observation</b><pre>{preview}</pre></div>', unsafe_allow_html=True)
        elif et == "WAITING_FOR_USER_APPROVAL":
            st.warning("⚠️ High-Risk Action Gated: Operator approval required before executing side-effect.")
        elif et == "VERIFICATION_COMPLETED":
            vr = ev.get("verification_result") or {}
            st.markdown(
                f'<div class="stream-card verif"><b>🔒 Independent Ground-Truth Verification</b><br/>'
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


# Top Header Navigation & Theme Switcher
status = st.session_state.status
theme_icon = "☀️ Light Mode" if is_dark else "🌙 Dark Mode"

top_left, top_right = st.columns([3.5, 1.5])
with top_left:
    st.markdown(
        f"""
        <div class="aura-header">
          <div>
            <div class="aura-tagline">Autonomous Enterprise Task Worker • Zero-Dependency ReAct Engine</div>
            <div class="aura-title">
              AURA WORKER <span class="aura-title-badge">v1.0 Production</span>
            </div>
          </div>
          <div style="text-align:right;">
            {status_badge(status)}
            <div style="color:var(--text-dim);font-size:11.5px;margin-top:6px;font-weight:600;">
              ENGINE: {global_llm_provider.info()["label"]}
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with top_right:
    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
    theme_btn_col1, theme_btn_col2 = st.columns([1, 1])
    with theme_btn_col1:
        if st.button(theme_icon, use_container_width=True):
            st.session_state.theme_mode = "light" if is_dark else "dark"
            st.rerun()
    with theme_btn_col2:
        if st.button("🔄 Reset App", use_container_width=True):
            erp_instance.reset()
            st.session_state.events = []
            st.session_state.result = None
            st.session_state.worker = None
            st.session_state.status = "STANDBY / READY"
            st.rerun()

left, right = st.columns([1.15, 1], gap="large")

with left:
    st.markdown("#### 🎯 Directive & Execution Control")
    preset = st.radio(
        "Evaluation presets",
        list(PRESETS.keys()),
        horizontal=True,
        label_visibility="collapsed",
    )
    if "last_preset" not in st.session_state or st.session_state.last_preset != preset:
        st.session_state.goal = PRESETS[preset]
        st.session_state.last_preset = preset

    goal = st.text_area("Task Objective", value=st.session_state.goal, height=95)
    st.session_state.goal = goal

    col_opt1, _ = st.columns([1.2, 0.8])
    with col_opt1:
        auto = st.checkbox("⚡ Auto-approve high-risk actions (Bypass HITL)", value=st.session_state.auto_approve)
        st.session_state.auto_approve = auto

    c1, c2, c3 = st.columns([1.5, 1, 1])
    with c1:
        launch = st.button("🚀 Launch Worker", type="primary", use_container_width=True)
    with c2:
        reset_erp = st.button("🔄 Reset ERP", use_container_width=True)
    with c3:
        abort = st.button("⏹ Abort", use_container_width=True)

    if reset_erp:
        erp_instance.reset()
        st.session_state.events = []
        st.session_state.result = None
        st.session_state.worker = None
        st.session_state.status = "STANDBY / READY"
        st.success("Simulated ERP database, file systems, and logs restored to clean bootstrap state.")
        st.rerun()

    if abort and st.session_state.worker:
        st.session_state.worker.stop()
        st.session_state.status = "ABORTED"
        st.rerun()

    if launch:
        run_worker(goal, auto)
        st.rerun()

    # Human-In-The-Loop Approval Box
    result = st.session_state.result or {}
    if result.get("status") == "WAITING_FOR_APPROVAL":
        approval = result.get("approval") or {}
        risk = result.get("risk_assessment") or {}
        action = result.get("intended_action") or {}
        st.markdown(
            f"""
            <div class="hitl-container">
              <div class="hitl-title">
                🛑 Human-in-the-Loop Operator Authorization Required
              </div>
              <div class="hitl-body">
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
        comment = st.text_input("Authorization note or operator comment", key="hitl_comment")
        a1, a2 = st.columns(2)
        with a1:
            if st.button("✅ Authorize Action", type="primary", use_container_width=True):
                resume_worker("APPROVED", comment)
                st.rerun()
        with a2:
            if st.button("🚫 Reject Action", use_container_width=True):
                resume_worker("REJECTED", comment or "Rejected by operator policy")
                st.rerun()

    # Plan Milestone Tracker
    plan = (st.session_state.result or {}).get("plan") or []
    if plan:
        st.markdown("#### 📋 Milestone Plan Execution")
        done = sum(1 for s in plan if s.get("status") == "COMPLETED")
        st.progress(done / len(plan), text=f"Progress: {done} / {len(plan)} milestones completed")
        for step in plan:
            mark = "✅" if step.get("status") == "COMPLETED" else "⚪"
            st.write(f"{mark} **{step.get('id')}. {step.get('title')}** — {step.get('description')}")

    st.markdown("#### 🧠 Live Execution Trace (ReAct Engine)")
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

        st.markdown("##### 📑 Accounts Payable Invoices")
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

        st.markdown("##### 🏢 Vendor Master Directory")
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

        st.markdown("##### 📜 System Audit Trail (Last 10 Records)")
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

            st.markdown("##### 🔍 Extracted State & Variables")
            st.json(res.get("discovered_state") or {})
