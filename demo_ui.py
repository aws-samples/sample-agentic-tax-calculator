"""Streamlit demo UI for the Agentic Tax Calculator.

Demonstrates the major architectural components:

  Tab 1 - Form Experience
  Tab 2 - Chat Experience
  Tab 3 - Guardrails: PII Filter + Access Control
  Tab 4 - Observability Dashboard
  Tab 5 - Configuration & Architecture

All tabs call the same backend. This is a demo skin - replace with
whatever frontend you want.

Usage:
    streamlit run demo_ui.py
"""

import sys
import os
import re
import time
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st

st.set_page_config(
    page_title="Agentic Tax Calculator",
    page_icon="🧮",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Load mock data
# ---------------------------------------------------------------------------
MOCK_DIR = os.path.join(os.path.dirname(__file__), "src", "mock", "data")


@st.cache_data
def load_businesses() -> dict:
    with open(os.path.join(MOCK_DIR, "business.json")) as f:
        return json.load(f)


businesses = load_businesses()
biz_labels = {}
for biz_id, data in businesses.items():
    b = data["business"]
    biz_labels[biz_id] = f"{biz_id} - {b['name']} ({b['jurisdiction']})"

biz_name_to_id = {}
for biz_id, data in businesses.items():
    b = data["business"]
    biz_name_to_id[b["name"].lower()] = biz_id
    biz_name_to_id[biz_id.lower()] = biz_id

# ---------------------------------------------------------------------------
# Sidebar - Agent workflow + architecture 
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("## 🤖 Workflow")
    st.caption("LangGraph orchestration with 3 phases")

    phases = {
        "Phase 1": {"agents": ["Business Tool"], "desc": "Metadata & jurisdiction"},
        "Phase 2": {
            "agents": ["Income Tool", "Expense Tool", "Asset Tool"],
            "desc": "Parallel data gathering",
        },
        "Phase 3": {"agents": ["Tax Tool"], "desc": "Compute & validate"},
    }
    for phase_name, info in phases.items():
        with st.expander(f"**{phase_name}** - {info['desc']}", expanded=False):
            for agent in info["agents"]:
                st.markdown(f"- {agent}")

    st.divider()

    # Current config snapshot 
    st.markdown("## 📡 Active Config")
    from src.config.settings import AppSettings
    _settings = AppSettings()
    st.markdown(f"**Deploy:** `{_settings.deployment_mode.value}`")
    st.markdown(f"**MCP Mode:** `{_settings.mcp_deployment_mode.value}`")
    st.markdown(f"**Data Source:** `{_settings.data_source_mode.value}`")
    st.markdown(f"**LLM:** `{_settings.llm_model_id}`")
    st.markdown(f"**Region:** `{_settings.aws_region}`")
    auth_status = "✅ Configured" if _settings.okta_domain else "⚪ Mock (no auth)"
    st.markdown(f"**Auth:** {auth_status}")

    st.divider()
    st.caption(
        "This UI is a demo skin. The backend API is the product - "
        "swap this for any frontend."
    )


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------
def run_with_progress(biz_id: str, tax_year: int):
    """Run tax calculation with animated agent progress."""
    from src.api.handler import handle_tax_calculation
    from src.api.schemas import TaxCalculationRequest

    request = TaxCalculationRequest(business_id=biz_id, tax_year=tax_year)
    agent_trace = []
    progress = st.progress(0, text="Starting workflow...")

    steps = [
        ("Phase 1: Business Tool - fetching metadata", 0.15),
        ("PII Pre-filter - scanning input", 0.25),
        ("Access Control - validating tool permissions", 0.30),
        ("Phase 2: Income Tool - querying revenue", 0.45),
        ("Phase 2: Expense Tool - querying expenses", 0.55),
        ("Phase 2: Asset Tool - querying HST/GST", 0.65),
        ("Phase 3: Tax Tool - deterministic engine", 0.80),
        ("Post-validation - cross-checking brackets", 0.90),
        ("Memory - storing results", 0.95),
    ]
    for step_text, pct in steps:
        progress.progress(pct, text=f"{step_text}...")
        agent_trace.append(f"✅ {step_text}")
        time.sleep(0.25)

    response = handle_tax_calculation(request)
    progress.progress(1.0, text="Complete!")
    time.sleep(0.2)
    progress.empty()
    return response, agent_trace


def render_results(response, agent_trace):
    """Display tax calculation results."""
    if response.status == "clarification_needed" and response.clarifying_questions:
        st.warning("Additional information needed:")
        for q in response.clarifying_questions:
            st.info(f"**{q.field}**: {q.message}")
        return
    if response.status == "failed":
        st.error(f"Calculation failed: {response.error}")
        return

    st.success(f"Workflow `{response.workflow_id[:8]}...` complete")

    # Financial summary
    st.markdown("### 💰 Financial Summary")
    fin_cols = st.columns(3)
    if response.revenue is not None:
        fin_cols[0].metric("Revenue", f"${response.revenue:,.2f}")
    if response.expenses is not None:
        fin_cols[1].metric("Expenses", f"${response.expenses:,.2f}")
    if response.profit is not None:
        margin = ""
        if response.revenue:
            margin = f"{(response.profit / response.revenue * 100):.1f}% margin"
        fin_cols[2].metric("Net Profit", f"${response.profit:,.2f}", delta=margin or None)

    # Tax breakdown
    st.markdown("### 🏛️ Tax Breakdown")
    tax_cols = st.columns(5)
    if response.federal_tax is not None:
        tax_cols[0].metric("Federal", f"${response.federal_tax:,.2f}")
    if response.provincial_tax is not None:
        tax_cols[1].metric("Provincial", f"${response.provincial_tax:,.2f}")
    if response.cpp_contributions is not None:
        tax_cols[2].metric("CPP", f"${response.cpp_contributions:,.2f}")
    if response.ei_premiums is not None:
        tax_cols[3].metric("EI", f"${response.ei_premiums:,.2f}")
    if response.total_tax is not None:
        tax_cols[4].metric("Total Tax", f"${response.total_tax:,.2f}")

    if response.total_tax and response.profit and response.profit > 0:
        st.markdown(
            f"**Effective Tax Rate:** {response.total_tax / response.profit * 100:.1f}%"
        )

    # Engine type callout
    st.info(
        "🔧 **Engine:** Deterministic (rules-based) - Canadian brackets are "
        "well-defined, no LLM needed. Phase 2 adds LLM-based US engine using "
        "the same `TaxEngineInterface`. Orchestration doesn't change."
    )

    # Bracket details
    if response.bracket_details:
        st.markdown("### 📊 Bracket Details")
        st.dataframe(response.bracket_details, use_container_width=True)

    # Workflow trace
    with st.expander("🔍 Workflow Trace - What Happened", expanded=False):
        for entry in agent_trace:
            st.markdown(entry)
        st.divider()
        st.json(response.model_dump(exclude_none=True))

# ===========================================================================
# MAIN CONTENT - 5 TABS
# ===========================================================================
st.title("🧮 Agentic Tax Calculator")
st.markdown(
    "Canadian small business tax calculation - **LangGraph orchestrator** "
    "on **AWS AgentCore**"
)

tab_form, tab_chat, tab_guardrails, tab_observability, tab_config = st.tabs([
    "📋 Form",
    "💬 Chat",
    "🛡️ Guardrails",
    "📊 Observability",
    "⚙️ Architecture",
])

# ===== TAB 1: FORM  ==========================
with tab_form:
    st.markdown(
        "**One-shot calculation.** Select a business, pick a year, get results. "
        "Best for structured workflows where inputs are known upfront."
    )
    col1, col2 = st.columns([2, 1])
    with col1:
        selected_label = st.selectbox(
            "Select Business", list(biz_labels.values()), index=0, key="form_biz",
        )
        selected_biz_id = [k for k, v in biz_labels.items() if v == selected_label][0]
    with col2:
        tax_year = st.selectbox("Tax Year", [2025, 2024], index=0, key="form_year")

    biz = businesses[selected_biz_id]["business"]
    with st.expander("📋 Business Details", expanded=True):
        d = st.columns(4)
        d[0].metric("Type", biz["businessType"].replace("_", " ").title())
        d[1].metric("Method", biz["accountingMethod"].title())
        d[2].metric("Province", biz["address"]["province"])
        d[3].metric("GST/HST #", biz["gstHstNumber"])

    st.divider()
    if st.button("🚀 Calculate Tax", type="primary", use_container_width=True, key="form_btn"):
        response, trace = run_with_progress(selected_biz_id, tax_year)
        render_results(response, trace)

# ===== TAB 2: CHAT  ======================
with tab_chat:
    st.markdown(
        "**Conversational experience.** Ask in natural language - the orchestrator "
        "figures out what you need and asks clarifying questions if anything "
        "is missing."
    )

    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = [
            {
                "role": "assistant",
                "content": (
                    "Hi! I'm the Tax Calculator. I can compute Canadian "
                    "small business taxes.\n\n"
                    "Try something like:\n"
                    '- "Calculate tax for Maple Leaf Consulting"\n'
                    '- "What\'s the tax on BIZ002 for 2025?"\n\n'
                    f"Available: {', '.join(b['business']['name'] for b in businesses.values())}"
                ),
            }
        ]

    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if user_input := st.chat_input("Ask me to calculate tax...", key="chat_input"):
        st.session_state.chat_messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        input_lower = user_input.lower()
        matched_biz_id = None
        for name, bid in biz_name_to_id.items():
            if name in input_lower:
                matched_biz_id = bid
                break

        year_match = re.search(r"\b(20\d{2})\b", user_input)
        matched_year = int(year_match.group(1)) if year_match else None

        # Follow-up: user gave business before, now giving year
        if not matched_biz_id and matched_year and "chat_pending_biz" in st.session_state:
            matched_biz_id = st.session_state.pop("chat_pending_biz")

        with st.chat_message("assistant"):
            if not matched_biz_id:
                reply = "Which business? Options:\n\n"
                for bid, d in businesses.items():
                    reply += f"- **{d['business']['name']}** (`{bid}`)\n"
                st.markdown(reply)
                st.session_state.chat_messages.append({"role": "assistant", "content": reply})

            elif not matched_year:
                bname = businesses[matched_biz_id]["business"]["name"]
                reply = f"Got it - **{bname}**. Which tax year? (2025 or 2024)"
                st.markdown(reply)
                st.session_state.chat_messages.append({"role": "assistant", "content": reply})
                st.session_state["chat_pending_biz"] = matched_biz_id

            else:
                bname = businesses[matched_biz_id]["business"]["name"]
                st.markdown(f"Running calculation for **{bname}**, year **{matched_year}**...")
                response, trace = run_with_progress(matched_biz_id, matched_year)
                render_results(response, trace)
                if response.status == "completed" and response.total_tax is not None:
                    summary = (
                        f"**{bname}** ({matched_year}): "
                        f"Revenue ${response.revenue:,.2f} · "
                        f"Total Tax **${response.total_tax:,.2f}**"
                    )
                else:
                    summary = f"Result: {response.status}"
                st.session_state.chat_messages.append({"role": "assistant", "content": summary})

# ===== TAB 3: GUARDRAILS  ===========
with tab_guardrails:
    st.markdown(
        "### 🛡️ Guardrails - PII Filter & Access Control\n"
        "Two layers of protection modelled after AgentCore Gateway interceptors."
    )

    g_col1, g_col2 = st.columns(2)

    # --- PII Filter (live demo) ---
    with g_col1:
        st.markdown("#### PII Pre-Filter")
        st.caption(
            "Detects and redacts PII before data reaches the LLM or memory. "
            "Try entering a SIN, bank account, address, or name below."
        )

        sample_texts = {
            "Clean input (no PII)": "Calculate tax for BIZ001 tax year 2024",
            "Contains SIN": "Taxpayer SIN is 123-456-789, calculate for BIZ001",
            "Contains bank account": "Account number: 1234567890 for BIZ001",
            "Contains address": "Business at 123 Main Street, Toronto ON M5V 2T6",
            "Contains name": "Client name: John Smith, business BIZ001",
            "Custom...": "",
        }

        sample_choice = st.selectbox(
            "Pick a sample or type your own:",
            list(sample_texts.keys()),
            key="pii_sample",
        )

        if sample_choice == "Custom...":
            pii_input = st.text_area("Enter text to scan:", height=80, key="pii_custom")
        else:
            pii_input = sample_texts[sample_choice]
            st.code(pii_input, language=None)

        if st.button("🔍 Scan for PII", key="pii_btn") and pii_input:
            from src.guardrails.pii_filter import PIIFilter
            pii = PIIFilter()
            result = pii.filter_input(pii_input)

            if result.blocked:
                st.error(
                    f"🚫 **BLOCKED** - Too much PII to safely redact. "
                    f"Types found: {', '.join(result.redacted_types)}"
                )
            elif result.redacted:
                st.warning(
                    f"⚠️ **PII Detected & Redacted** - "
                    f"{result.redaction_count} item(s): {', '.join(result.redacted_types)}"
                )
                st.markdown("**Redacted output:**")
                st.code(result.text, language=None)
            else:
                st.success("✅ **Clean** - No PII detected")

        st.caption(
            "Supported: SIN, bank accounts, addresses, postal codes, names. "
            "Memory storage uses an even more aggressive filter."
        )

    # --- Access Control (permissions matrix) ---
    with g_col2:
        st.markdown("#### Access Control Matrix")
        st.caption(
            "Each workflow step can only call its authorized tools. "
            "Unauthorized attempts are blocked and logged."
        )

        from src.guardrails.access_control import (
            AGENT_TOOL_PERMISSIONS,
            AccessControlGuardrail,
        )

        # Display permissions matrix
        all_tools = sorted(set(t for tools in AGENT_TOOL_PERMISSIONS.values() for t in tools))
        matrix_data = []
        for agent, tools in AGENT_TOOL_PERMISSIONS.items():
            row = {"Workflow": agent}
            for tool in all_tools:
                row[tool] = "✅" if tool in tools else "❌"
            matrix_data.append(row)

        st.dataframe(matrix_data, use_container_width=True, hide_index=True)

        # Live access check
        st.markdown("**Try an access check:**")
        ac_col1, ac_col2 = st.columns(2)
        with ac_col1:
            test_agent = st.selectbox(
                "Workflow", list(AGENT_TOOL_PERMISSIONS.keys()), key="ac_agent"
            )
        with ac_col2:
            test_tool = st.selectbox("Tool", all_tools, key="ac_tool")

        if st.button("🔐 Check Access", key="ac_btn"):
            guardrail = AccessControlGuardrail()
            allowed = guardrail.check_access(test_agent, test_tool)
            if allowed:
                st.success(f"✅ **{test_agent}** is authorized to call `{test_tool}`")
            else:
                st.error(
                    f"🚫 **ACCESS DENIED** - {test_agent} cannot call `{test_tool}`. "
                    f"Allowed tools: {', '.join(guardrail.get_allowed_tools(test_agent))}"
                )

# ===== TAB 4: OBSERVABILITY  ============================
with tab_observability:
    st.markdown(
        "### 📊 Observability - Three Audiences, Three Tools\n"
        "CloudWatch (DevOps) · DataDog (Org-wide) · Streamlit (Stakeholders)"
    )

    obs_col1, obs_col2, obs_col3 = st.columns(3)

    with obs_col1:
        st.markdown("#### ☁️ CloudWatch")
        st.caption("DevOps / on-call engineers")
        st.markdown(
            "- OTEL auto-instrumentation via ADOT\n"
            "- Per-tool invocation counters\n"
            "- Latency histograms (P50/P95/P99)\n"
            "- Workflow duration tracking\n"
            "- Error correlation IDs\n"
            "- X-Ray trace integration"
        )
        st.code(
            "# Enabled by default in AgentCore\n"
            "# Metrics: tool.invocations, tool.errors,\n"
            "#          tool.latency, workflow.duration\n"
            "# Traces: X-Ray via ADOT collector",
            language="python",
        )

    with obs_col2:
        st.markdown("#### 🐕 DataDog")
        st.caption("Org-wide monitoring")
        st.markdown(
            "- OTLP exporter to DataDog\n"
            "- Same metrics as CloudWatch\n"
            "- Unified with existing DD dashboards\n"
            "- Set `TAX_CALC_DATADOG_API_KEY`\n"
            "- Disable ADOT when using DD"
        )
        st.code(
            "# Enable DataDog:\n"
            "TAX_CALC_DATADOG_API_KEY=your-key\n"
            "DISABLE_ADOT_OBSERVABILITY=true",
            language="bash",
        )

    with obs_col3:
        st.markdown("#### 📈 Streamlit")
        st.caption("Non-technical stakeholders")
        st.markdown(
            "- MetricsStore singleton collects data\n"
            "- Tool metrics: call counts, latency\n"
            "- Workflow metrics: duration, status\n"
            "- Recent errors with context\n"
            "- Build custom dashboards on top"
        )
        st.code(
            "from src.observability.streamlit \\\n"
            "    import MetricsStore\n"
            "store = MetricsStore.instance()\n"
            "store.get_tool_metrics()\n"
            "store.get_workflow_metrics()",
            language="python",
        )

    st.divider()

    # OTEL metrics reference
    st.markdown("#### Metrics Reference (OpenTelemetry)")
    metrics_ref = [
        {"Metric": "tool.invocations", "Type": "Counter", "Labels": "tool.name, workflow.id"},
        {"Metric": "tool.errors", "Type": "Counter", "Labels": "tool.name, workflow.id"},
        {"Metric": "tool.latency", "Type": "Histogram (ms)", "Labels": "tool.name, workflow.id"},
        {"Metric": "workflow.duration", "Type": "Histogram (ms)", "Labels": "workflow.id"},
        {"Metric": "workflow.executions", "Type": "Counter", "Labels": "workflow.id, status"},
        {"Metric": "agent.completions", "Type": "Counter", "Labels": "tool.id, status"},
    ]
    st.dataframe(metrics_ref, use_container_width=True, hide_index=True)

# ===== TAB 5: ARCHITECTURE  =========================
with tab_config:
    st.markdown(
        "### ⚙️ Architecture - Config-Driven, Swap Anything\n"
        "Every major decision is a config toggle, not a code change."
    )

    # --- Deployment mode ---
    st.markdown("#### 🚀 Deployment: AgentCore Runtime vs Kubernetes ")
    dep_col1, dep_col2 = st.columns([3, 2])

    with dep_col1:
        st.markdown("**AgentCore Runtime (Recommended)**")
        st.markdown(
            "- Serverless microVM per session - auto-scaling, session isolation, memory sanitization\n"
            "- On-demand pricing - no charges during I/O wait (LLM response time)\n"
            "- Observability: CloudWatch + X-Ray traces - automatic\n"
            "- Deploy: `agentcore deploy` → production in under 2 minutes\n"
            "- Versioning + rollback built in\n"
            "- Small team, no K8s specialist needed"
        )
        st.code(
            "agentcore create --protocol MCP\n"
            "agentcore deploy",
            language="bash",
        )

    with dep_col2:
        st.markdown("**Kubernetes (Alternative - same code)**")
        st.markdown(
            "Same code runs, but you manage:\n"
            "- Session isolation (pod-per-session + cleanup)\n"
            "- API gateway + auth middleware\n"
            "- DynamoDB tables + memory logic\n"
            "- ADOT sidecar + CloudWatch config\n"
            "- Helm chart, Docker, scaling policies"
        )
        st.code(
            "docker build -t tax-calc .\n"
            "helm install tax-calc ./infra/helm",
            language="bash",
        )

    st.success(
        "💡 Runtime is the thinnest deployment path - managed scaling, session isolation, "
        "and observability out of the box. K8s option is here if you need it, but "
        "Runtime is the faster path to production for a small team."
    )

    # --- Gateway ---
    st.markdown("#### 🌐 Gateway: Not Needed for Phase 1 ")
    gw_col1, gw_col2 = st.columns(2)

    with gw_col1:
        st.markdown("**Current: No Gateway**")
        st.markdown(
            "- One MCP server fronting your GraphQL API\n"
            "- GraphQL handles auth (token passthrough)\n"
            "- Gateway adds no value with a single MCP server\n"
            "- Simpler architecture, fewer moving parts"
        )

    with gw_col2:
        st.markdown("**Future: Add Gateway When Needed**")
        st.markdown(
            "- When adding non-GraphQL MCP servers (bank import, US tax, third-party)\n"
            "- Unified tool discovery across multiple MCP servers\n"
            "- Cedar policies for fine-grained access control\n"
            "- JWT auth at the boundary\n"
            "- Agent code doesn't change - Gateway is infrastructure"
        )

    st.info(
        "✅ **Status** - Gateway skipped for Phase 1. "
        "Can be inserted later when adding non-GraphQL MCP servers. "
        "The migration path is straightforward - no agent code changes needed."
    )

    st.divider()
    st.markdown("#### 🔌 MCP: Consolidated vs Separate ")
    mcp_col1, mcp_col2 = st.columns(2)

    with mcp_col1:
        st.markdown("**Consolidated (Default)**")
        st.markdown(
            "- All 6 tools in one MCP server\n"
            "- Simpler deployment, single container\n"
            "- One endpoint for all tool calls"
        )
        st.code("TAX_CALC_MCP_DEPLOYMENT_MODE=consolidated", language="bash")

    with mcp_col2:
        st.markdown("**Separate (Independent Scaling)**")
        st.markdown(
            "- Each tool group = independent MCP server\n"
            "- Independent scaling and versioning\n"
            "- Separate endpoint per tool group"
        )
        st.code("TAX_CALC_MCP_DEPLOYMENT_MODE=separate", language="bash")

    st.info(
        "Both modes use the same code. The 6 tool modules in `src/mcp/tools/` "
        "are independent - the config just controls how they're packaged."
    )

    st.divider()

    # --- Tax engine (deterministic vs LLM) ---
    st.markdown("#### 🧮 Tax Engine: Deterministic vs LLM ")
    eng_col1, eng_col2 = st.columns(2)

    with eng_col1:
        st.markdown("**Phase 1: Deterministic (Current)**")
        st.markdown(
            "- Rules-based Canadian tax engine\n"
            "- All 13 provinces/territories\n"
            "- Federal + provincial brackets, CPP, EI\n"
            "- 100% reproducible, auditable\n"
            "- No LLM needed for Canadian tax"
        )
        st.code(
            "class DeterministicTaxEngine(TaxEngineInterface):\n"
            "    def calculate(self, input) -> TaxBreakdown:\n"
            "        # Pure math - brackets, rates, caps\n"
            "        ...",
            language="python",
        )

    with eng_col2:
        st.markdown("**Phase 2: LLM-Based (Planned - US Tax)**")
        st.markdown(
            "- US tax = complex, non-deterministic\n"
            "- Same `TaxEngineInterface`\n"
            "- Orchestration unchanged - just swap engine\n"
            "- US tax rules are complex and state-specific"
        )
        st.code(
            "class LLMTaxEngine(TaxEngineInterface):\n"
            "    def calculate(self, input) -> TaxBreakdown:\n"
            "        # Bedrock Claude call\n"
            "        # Same interface, different impl\n"
            "        ...",
            language="python",
        )

    st.divider()

    # --- Auth (Confirmed - token passthrough) ---
    st.markdown("#### 🔐 Auth: Token Passthrough ")
    auth_col1, auth_col2 = st.columns(2)

    with auth_col1:
        st.markdown("**Current: Token Passthrough**")
        st.markdown(
            "- Your OAuth flow\n"
            "- Token from web app passed through MCP to GraphQL\n"
            "- GraphQL validates token and handles authorization\n"
            "- No AgentCore Identity needed\n"
            "- No Gateway auth layer needed\n"
            "- Simplest possible auth path"
        )

    with auth_col2:
        st.markdown("**Future: AgentCore Identity + Gateway Auth**")
        st.markdown(
            "- When adding non-GraphQL MCP servers\n"
            "- Gateway validates JWT on every request\n"
            "- Identity manages token lifecycle (Okta/Auth0)\n"
            "- Outbound auth for downstream APIs\n"
            "- Token Vault with KMS encryption"
        )

    st.info(
        "✅ **Status** - Token passthrough confirmed. "
        "The OAuth token flows from the client through the MCP server to GraphQL. "
        "GraphQL handles all auth. No new auth layer needed for Phase 1."
    )

    st.divider()

    # --- Cedar / AgentCore Policy ---
    st.markdown("#### 📜 Access Control: Python → Cedar (AgentCore Policy)")
    cedar_col1, cedar_col2 = st.columns(2)

    with cedar_col1:
        st.markdown("**Current: Python Permissions Matrix**")
        st.markdown(
            "- `src/guardrails/access_control.py`\n"
            "- Static dict: agent → allowed tools\n"
            "- Enforced inside the agent code\n"
            "- Works for demo and Phase 1"
        )

    with cedar_col2:
        st.markdown("**Production: AgentCore Policy (Cedar)**")
        st.markdown(
            "- Enforced at Gateway boundary (outside agent)\n"
            "- Same Cedar language as Amazon Verified Permissions\n"
            "- If your org has evaluated AVP, same skills apply\n"
            "- Natural extension to agent-to-tool access control"
        )

    st.info(
        "💡 If your organization has evaluated Cedar via Amazon Verified "
        "Permissions. AgentCore Policy uses the same language - same skills, "
        "applied to agentic workloads."
    )

    st.divider()

    # --- Memory (- DynamoDB default) ---
    st.markdown("#### 🧠 Memory: DynamoDB Default + AgentCore Memory Optional ")
    mem_col1, mem_col2 = st.columns(2)

    with mem_col1:
        st.markdown("**Short-Term Memory (Session)**")
        st.markdown(
            "- Session-scoped workflow state\n"
            "- DynamoDB-backed via LangGraph checkpointer\n"
            "- 'Where are we in THIS calculation?'\n"
            "- Destroyed when session ends\n"
            "- Cost: ~$0.27/month at typical usage"
        )

    with mem_col2:
        st.markdown("**Long-Term Memory (Cross-Session)**")
        st.markdown(
            "- User preferences + calculation history\n"
            "- PII-filtered before storage\n"
            "- Three strategies: SEMANTIC, SUMMARIZATION, USER_PREFERENCE\n"
            "- Backend configurable via `TAX_CALC_MEMORY_BACKEND`"
        )

    st.markdown("**Cost Comparison (at 100 users/day):**")
    cost_data = [
        {"Backend": "DynamoDB (default)", "Monthly Cost": "~$0.27", "Management": "Self-managed - you build memory strategies", "Best For": "Cost-sensitive, team has capacity"},
        {"Backend": "AgentCore Memory (optional)", "Monthly Cost": "~$13.50", "Management": "Fully managed - built-in semantic extraction", "Best For": "Want managed intelligence, willing to pay"},
    ]
    st.dataframe(cost_data, use_container_width=True, hide_index=True)

    st.info(
        "✅ **Status** - DynamoDB is the default (cheapest). "
        "AgentCore Memory available via config toggle. You can switch anytime "
        "without code changes: `TAX_CALC_MEMORY_BACKEND=agentcore`"
    )

    st.divider()

    # --- Deployment + Architecture ---
    st.markdown("#### �-️ Current Architecture ")
    st.markdown(
        "No Gateway. No AgentCore Identity. Token passthrough to GraphQL. "
        "This is the simplest architecture that meets typical requirements."
    )
    st.code(
        "AI Client (Copilot / Kiro / Web App)\n"
        "  │  User already authenticated via your OAuth\n"
        "  ▼\n"
        "AgentCore Runtime (serverless microVM per session)\n"
        "  ├── PII Pre-Filter (SIN, bank accounts, addresses)\n"
        "  ├── LangGraph Orchestrator\n"
        "  │     Phase 1: Business Agent → get_business_info\n"
        "  │     Phase 2: Income | Expense | Asset  (parallel)\n"
        "  │     Phase 3: Tax Agent → calculate_tax + validate\n"
        "  ├── MCP Server (thin layer on GraphQL)\n"
        "  │     └── GraphQL validates token, handles authorization\n"
        "  │           └── Backend services\n"
        "  ├── DynamoDB (workflow checkpoints - default)\n"
        "  └── AgentCore Memory (cross-session - optional)\n"
        "        └── PII filtered before storage",
        language=None,
    )

    st.divider()

    st.markdown("#### 🔮 Future Architecture (When Adding Non-GraphQL MCP Servers)")
    st.markdown(
        "Gateway gets added when you need multiple MCP servers "
        "(bank import, US tax, third-party integrations). Agent code doesn't change."
    )
    st.code(
        "AI Client\n"
        "  ▼\n"
        "AgentCore Runtime\n"
        "  ├── LangGraph Orchestrator\n"
        "  └── AgentCore Gateway (unified tool discovery, Cedar policies, JWT auth)\n"
        "        ├── Tax Tools MCP Server (GraphQL)\n"
        "        ├── Bank Import MCP Server (Textract - Phase 2)\n"
        "        └── Third-Party Integrations MCP Server (Future)\n"
        "\n"
        "  + AgentCore Policy (Cedar guardrails)\n"
        "  + AgentCore Memory (managed, semantic retrieval)\n"
        "  + AgentCore Identity (Okta/Auth0 integration)\n"
        "  + AgentCore Observability (traces, metrics)",
        language=None,
    )

    st.divider()

    # --- Full env var reference ---
    with st.expander("📋 Full Environment Variable Reference", expanded=False):
        env_vars = [
            {"Variable": "TAX_CALC_DEPLOYMENT_MODE", "Default": "agentcore", "Options": "agentcore, kubernetes"},
            {"Variable": "TAX_CALC_MCP_DEPLOYMENT_MODE", "Default": "consolidated", "Options": "consolidated, separate"},
            {"Variable": "TAX_CALC_DATA_SOURCE_MODE", "Default": "mock", "Options": "mock, graphql"},
            {"Variable": "TAX_CALC_GRAPHQL_ENDPOINT", "Default": "(empty)", "Options": "URL when mode=graphql"},
            {"Variable": "TAX_CALC_OKTA_DOMAIN", "Default": "(empty)", "Options": "Okta domain"},
            {"Variable": "TAX_CALC_LLM_MODEL_ID", "Default": "anthropic.claude-sonnet-4-6-20250514", "Options": "Any Bedrock model"},
            {"Variable": "TAX_CALC_AWS_REGION", "Default": "us-east-1", "Options": "Any AWS region"},
            {"Variable": "TAX_CALC_MEMORY_RETENTION_DAYS", "Default": "90", "Options": "1+"},
            {"Variable": "TAX_CALC_DATADOG_API_KEY", "Default": "(empty)", "Options": "DD API key"},
            {"Variable": "TAX_CALC_LOG_LEVEL", "Default": "INFO", "Options": "DEBUG, INFO, WARNING, ERROR"},
        ]
        st.dataframe(env_vars, use_container_width=True, hide_index=True)
