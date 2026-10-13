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

# Theme Variables and Global Overrides
if is_dark:
    theme_vars = """
      --bg-page: #0b0f17;
      --bg-surface: #111827;
      --bg-surface-elevated: #1e293b;
      --bg-surface-subtle: #0f172a;
      --border-main: #1f2937;
      --border-strong: #374151;
      --text-heading: #f9fafb;
      --text-body: #e5e7eb;
      --text-muted: #9ca3af;
      --text-dim: #6b7280;
      --primary: #3b82f6;
      --primary-hover: #2563eb;
      --primary-glow: rgba(59, 130, 246, 0.15);
      --card-thought-bg: rgba(59, 130, 246, 0.08);
      --card-thought-text: #bfdbfe;
      --card-action-bg: rgba(245, 158, 11, 0.08);
      --card-action-text: #fde68a;
      --card-obs-bg: rgba(16, 185, 129, 0.08);
      --card-obs-text: #a7f3d0;
      --card-verif-bg: rgba(139, 92, 246, 0.08);
      --card-verif-text: #ddd6fe;
      --input-bg: #111827;
      --btn-sec-bg: #1e293b;
      --btn-sec-color: #f1f5f9;
      --btn-sec-border: #334155;
      --btn-sec-hover-bg: #273549;
      --table-header: #1f2937;
      --table-row-hover: #162032;
    """
else:
    theme_vars = """
      --bg-page: #f8fafc;
      --bg-surface: #ffffff;
      --bg-surface-elevated: #ffffff;
      --bg-surface-subtle: #f1f5f9;
      --border-main: #e2e8f0;
      --border-strong: #cbd5e1;
      --text-heading: #0f172a;
      --text-body: #1e293b;
      --text-muted: #475569;
      --text-dim: #64748b;
      --primary: #2563eb;
      --primary-hover: #1d4ed8;
      --primary-glow: rgba(37, 99, 235, 0.08);
      --card-thought-bg: #eff6ff;
      --card-thought-text: #1e3a8a;
      --card-action-bg: #fffbeb;
      --card-action-text: #78350f;
      --card-obs-bg: #f0fdf4;
      --card-obs-text: #064e3b;
      --card-verif-bg: #faf5ff;
      --card-verif-text: #581c87;
      --input-bg: #ffffff;
      --btn-sec-bg: #ffffff;
      --btn-sec-color: #0f172a;
      --btn-sec-border: #cbd5e1;
      --btn-sec-hover-bg: #f1f5f9;
      --table-header: #f1f5f9;
      --table-row-hover: #f8fafc;
    """

st.markdown(
    f"""
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

      :root {{
        {theme_vars}
      }}

      /* Base layout & typography */
      html, body, [class*="css"], .stMarkdown, .stText {{
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
      }}
      code, pre, .mono {{
        font-family: 'JetBrains Mono', Consolas, monospace !important;
      }}

      .stApp {{
        background-color: var(--bg-page) !important;
        color: var(--text-body) !important;
      }}
      header, footer, header[data-testid="stHeader"] {{
        background: transparent !important;
        z-index: 99 !important;
      }}

      /* Header clear space to prevent any cut off on cloud */
      .block-container {{
        padding-top: 5rem !important;
        padding-bottom: 3rem !important;
        max-width: 1560px !important;
      }}

      /* Text color enforcement */
      h1, h2, h3, h4, h5, h6, strong {{
        color: var(--text-heading) !important;
      }}
      p, span, label {{
        color: var(--text-body);
      }}
      .stCaption, small {{
        color: var(--text-muted) !important;
      }}

      /* Unified Clean Top Bar */
      .app-navbar {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 16px;
        background: var(--bg-surface);
        border: 1px solid var(--border-main);
        border-radius: 12px;
        padding: 16px 22px;
        margin-bottom: 18px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
      }}
      .app-brand {{
        display: flex;
        align-items: center;
        gap: 12px;
      }}
      .app-logo {{
        width: 38px;
        height: 38px;
        border-radius: 10px;
        background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
        color: #ffffff;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 18px;
        font-weight: 800;
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.25);
      }}
      .app-title-box {{
        display: flex;
        flex-direction: column;
      }}
      .app-title {{
        font-size: 19px;
        font-weight: 800;
        color: var(--text-heading) !important;
        letter-spacing: -0.02em;
        line-height: 1.2;
      }}
      .app-subtitle {{
        font-size: 11.5px;
        font-weight: 600;
        color: var(--text-muted);
        letter-spacing: 0.04em;
      }}
      .app-status-box {{
        display: flex;
        align-items: center;
        gap: 12px;
      }}

      /* Status Pill */
      .status-pill {{
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 6px 14px;
        border-radius: 20px;
        font-size: 11.5px;
        font-weight: 700;
        letter-spacing: 0.04em;
        text-transform: uppercase;
      }}
      .status-pill-ok {{
        background: rgba(16, 185, 129, 0.12);
        color: #10b981 !important;
        border: 1px solid rgba(16, 185, 129, 0.3);
      }}
      .status-pill-run {{
        background: rgba(245, 158, 11, 0.12);
        color: #f59e0b !important;
        border: 1px solid rgba(245, 158, 11, 0.3);
      }}
      .status-pill-wait {{
        background: rgba(239, 68, 68, 0.12);
        color: #ef4444 !important;
        border: 1px solid rgba(239, 68, 68, 0.3);
        animation: pulse-ring 2s infinite;
      }}
      .status-pill-idle {{
        background: var(--bg-surface-elevated);
        color: var(--text-muted) !important;
        border: 1px solid var(--border-main);
      }}

      @keyframes pulse-ring {{
        0%, 100% {{ opacity: 1; }}
        50% {{ opacity: 0.65; }}
      }}

      /* Streamlit Button System Overhaul (Light & Dark Mode) */
      .stButton > button {{
        background-color: var(--btn-sec-bg) !important;
        color: var(--btn-sec-color) !important;
        border: 1px solid var(--btn-sec-border) !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        font-size: 13px !important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05) !important;
        transition: all 0.15s ease-in-out !important;
      }}
      .stButton > button p, .stButton > button span, .stButton > button div {{
        color: var(--btn-sec-color) !important;
      }}
      .stButton > button:hover {{
        background-color: var(--btn-sec-hover-bg) !important;
        border-color: var(--primary) !important;
        color: var(--primary) !important;
      }}
      .stButton > button:hover p, .stButton > button:hover span {{
        color: var(--primary) !important;
      }}

      /* Primary Button Styling */
      .stButton > button[kind="primary"], button[data-testid="baseButton-primary"] {{
        background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%) !important;
        color: #ffffff !important;
        border: 1px solid #2563eb !important;
        box-shadow: 0 2px 4px rgba(37, 99, 235, 0.2) !important;
      }}
      .stButton > button[kind="primary"] p, button[data-testid="baseButton-primary"] p,
      .stButton > button[kind="primary"] span, button[data-testid="baseButton-primary"] span {{
        color: #ffffff !important;
      }}
      .stButton > button[kind="primary"]:hover {{
        background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%) !important;
        border-color: #1d4ed8 !important;
        color: #ffffff !important;
      }}

      /* Radio Buttons & Checkboxes */
      div[data-testid="stRadio"] label, div[data-testid="stRadio"] div, div[data-testid="stRadio"] p {{
        color: var(--text-heading) !important;
      }}
      div[data-testid="stRadio"] > div {{
        gap: 16px;
      }}
      div[data-testid="stRadio"] [data-testid="stWidgetLabel"] p {{
        color: var(--text-muted) !important;
        font-weight: 600;
        font-size: 12.5px;
      }}
      div[data-testid="stCheckbox"] label, div[data-testid="stCheckbox"] p, div[data-testid="stCheckbox"] span {{
        color: var(--text-heading) !important;
        font-size: 13.5px !important;
      }}

      /* Input Fields */
      .stTextInput input, .stTextArea textarea, .stSelectbox select, div[data-baseweb="select"] > div {{
        background-color: var(--input-bg) !important;
        color: var(--text-heading) !important;
        border: 1px solid var(--border-strong) !important;
        border-radius: 8px !important;
        font-size: 14px !important;
      }}
      .stTextInput input:focus, .stTextArea textarea:focus {{
        border-color: var(--primary) !important;
        box-shadow: 0 0 0 2px var(--primary-glow) !important;
      }}

      /* Cards for stream events */
      .stream-card {{
        padding: 14px 18px;
        margin: 10px 0;
        border-radius: 8px;
        font-size: 13.5px;
        line-height: 1.5;
        border-left-width: 4px;
        border-left-style: solid;
        border-top: 1px solid var(--border-main);
        border-right: 1px solid var(--border-main);
        border-bottom: 1px solid var(--border-main);
        box-shadow: 0 1px 2px rgba(0,0,0,0.03);
      }}
      .thought {{
        border-left-color: #3b82f6;
        background-color: var(--card-thought-bg);
        color: var(--card-thought-text);
      }}
      .action {{
        border-left-color: #f59e0b;
        background-color: var(--card-action-bg);
        color: var(--card-action-text);
      }}
      .obs {{
        border-left-color: #10b981;
        background-color: var(--card-obs-bg);
        color: var(--card-obs-text);
      }}
      .verif {{
        border-left-color: #8b5cf6;
        background-color: var(--card-verif-bg);
        color: var(--card-verif-text);
      }}

      /* Code / Pre Blocks */
      pre {{
        background: var(--bg-surface-subtle) !important;
        border: 1px solid var(--border-main) !important;
        border-radius: 6px !important;
        padding: 10px 14px !important;
        color: var(--text-heading) !important;
        font-size: 12px !important;
      }}
      code {{
        color: var(--primary) !important;
      }}

      /* Metrics styling */
      div[data-testid="stMetric"] {{
        background: var(--bg-surface) !important;
        border: 1px solid var(--border-main) !important;
        border-radius: 10px !important;
        padding: 14px 16px !important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.03) !important;
      }}
      div[data-testid="stMetricValue"] {{
        font-size: 24px !important;
        font-weight: 800 !important;
        color: var(--text-heading) !important;
      }}
      div[data-testid="stMetricLabel"] p, div[data-testid="stMetricLabel"] span {{
        font-size: 11.5px !important;
        font-weight: 700 !important;
        color: var(--text-muted) !important;
        text-transform: uppercase !important;
        letter-spacing: 0.05em !important;
      }}

      /* Tabs styling */
      .stTabs [data-baseweb="tab-list"] {{
        gap: 8px;
        border-bottom: 1px solid var(--border-main) !important;
      }}
      .stTabs [data-baseweb="tab"] {{
        font-weight: 600;
        font-size: 13.5px;
        color: var(--text-muted) !important;
        padding: 10px 16px;
        border-radius: 6px 6px 0 0;
      }}
      .stTabs [aria-selected="true"] {{
        color: var(--primary) !important;
        border-bottom: 2px solid var(--primary) !important;
        background: var(--primary-glow);
      }}

      /* Tables */
      table {{
        width: 100%;
        border-collapse: collapse;
        margin: 12px 0 16px 0;
        font-size: 13px;
        border: 1px solid var(--border-main);
        border-radius: 8px;
        overflow: hidden;
        background-color: var(--bg-surface);
      }}
      th {{
        background-color: var(--table-header);
        color: var(--text-muted) !important;
        font-weight: 700;
        text-align: left;
        padding: 10px 14px;
        border-bottom: 1px solid var(--border-main);
        font-size: 11.5px;
        text-transform: uppercase;
        letter-spacing: 0.05em;
      }}
      td {{
        padding: 10px 14px;
        border-bottom: 1px solid var(--border-main);
        color: var(--text-heading) !important;
      }}
      tr:hover {{
        background-color: var(--table-row-hover);
      }}

      /* Human-in-the-loop box */
      .hitl-alert {{
        border: 1px solid #ef4444;
        background: rgba(239, 68, 68, 0.08);
        border-radius: 10px;
        padding: 16px 20px;
        margin: 14px 0;
      }}
      .hitl-title {{
        font-size: 15px;
        font-weight: 700;
        color: #ef4444;
        margin-bottom: 6px;
      }}
      .hitl-desc {{
        font-size: 13px;
        color: var(--text-heading);
      }}
    </style>
    """,
    unsafe_allow_html=True,
)


def status_badge(status: str) -> str:
    s = (status or "").upper()
    cls = "status-pill-idle"
    dot = "●"
    if "WAIT" in s:
        cls = "status-pill-wait"
        dot = "⏸"
    elif "RUN" in s or "EXECUT" in s:
        cls = "status-pill-run"
        dot = "⚡"
    elif "VERIFIED" in s or "COMPLETE" in s:
        cls = "status-pill-ok"
        dot = "✔"
    return f'<span class="status-pill {cls}">{dot} {status}</span>'


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
        st.info("System is ready. Select an evaluation directive and launch the worker.")
        return

    for ev in events:
        et = ev.get("event")
        if et == "TASK_STARTED":
            st.markdown(f"**⚡ Directive Initialized** — `{ev.get('goal')}`")
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


# Top Header Navigation Bar
status = st.session_state.status

st.markdown(
    f"""
    <div class="app-navbar">
      <div class="app-brand">
        <div class="app-logo">⚡</div>
        <div class="app-title-box">
          <div class="app-title">AURA Autonomous Task Worker</div>
          <div class="app-subtitle">Autonomous Enterprise Agent • Zero-Dependency ReAct Engine</div>
        </div>
      </div>
      <div class="app-status-box">
        {status_badge(status)}
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# Utility Row for Controls (Theme Toggle & System Reset)
# In Light Mode -> button offers option "🌙 Dark Mode"
# In Dark Mode -> button offers option "☀️ Light Mode"
theme_switch_label = "🌙 Dark Mode" if not is_dark else "☀️ Light Mode"

ctrl_col1, ctrl_col2, ctrl_col3 = st.columns([3, 1, 1])
with ctrl_col1:
    st.caption(f"Reasoning Core: **{global_llm_provider.info()['label']}** • Enterprise Edition v1.0")
with ctrl_col2:
    if st.button(theme_switch_label, use_container_width=True):
        st.session_state.theme_mode = "dark" if not is_dark else "light"
        st.rerun()
with ctrl_col3:
    if st.button("🔄 Reset Environment", use_container_width=True):
        erp_instance.reset()
        st.session_state.events = []
        st.session_state.result = None
        st.session_state.worker = None
        st.session_state.status = "STANDBY / READY"
        st.rerun()

st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

# Main Application Layout
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
            <div class="hitl-alert">
              <div class="hitl-title">🛑 Operator Authorization Required</div>
              <div class="hitl-desc">{risk.get("reason") or approval.get("reason")}</div>
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
