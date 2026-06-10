"""
AI Hiring Intelligence System — Streamlit Dashboard
Run: streamlit run dashboard.py
"""

import streamlit as st
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import requests

# ── PAGE CONFIG ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Hiring Intelligence",
    page_icon="⬡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── DESIGN TOKENS ────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@300;400;500;600&display=swap');

/* Base */
html, body, [class*="css"] {
    font-family: 'IBM Plex Sans', sans-serif;
}

/* Dark sidebar */
[data-testid="stSidebar"] {
    background: #0D1117;
    border-right: 1px solid #1E2A38;
}
[data-testid="stSidebar"] * {
    color: #C9D1D9 !important;
}
[data-testid="stSidebar"] .stRadio label {
    font-size: 13px;
    font-family: 'IBM Plex Mono', monospace;
}

/* Main background */
.main { background: #F7F8FA; }

/* Metric cards */
.metric-card {
    background: white;
    border: 1px solid #E5E9F0;
    border-radius: 8px;
    padding: 20px 24px;
    position: relative;
    overflow: hidden;
}
.metric-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    background: var(--accent);
}
.metric-label {
    font-size: 11px;
    font-family: 'IBM Plex Mono', monospace;
    color: #6B7280;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 8px;
}
.metric-value {
    font-size: 28px;
    font-weight: 600;
    color: #0D1117;
    line-height: 1;
    margin-bottom: 4px;
}
.metric-sub {
    font-size: 12px;
    color: #6B7280;
}

/* Agent insight cards */
.insight-card {
    background: white;
    border: 1px solid #E5E9F0;
    border-radius: 8px;
    padding: 20px 24px;
    margin-bottom: 16px;
}
.insight-agent-tag {
    font-size: 10px;
    font-family: 'IBM Plex Mono', monospace;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    padding: 3px 8px;
    border-radius: 3px;
    display: inline-block;
    margin-bottom: 12px;
}
.insight-recommendation {
    font-size: 15px;
    font-weight: 500;
    color: #0D1117;
    line-height: 1.5;
    margin-bottom: 12px;
}
.insight-meta {
    display: flex;
    gap: 20px;
    font-size: 12px;
    font-family: 'IBM Plex Mono', monospace;
    color: #6B7280;
}
.confidence-bar-wrap {
    background: #F0F2F5;
    border-radius: 2px;
    height: 4px;
    width: 100px;
    display: inline-block;
    vertical-align: middle;
    margin-left: 6px;
}
.confidence-bar {
    height: 4px;
    border-radius: 2px;
    background: #10B981;
    display: inline-block;
}

/* Section headers */
.section-header {
    font-size: 11px;
    font-family: 'IBM Plex Mono', monospace;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: #6B7280;
    border-bottom: 1px solid #E5E9F0;
    padding-bottom: 8px;
    margin-bottom: 20px;
    margin-top: 8px;
}

/* Page title */
.page-title {
    font-size: 22px;
    font-weight: 600;
    color: #0D1117;
    letter-spacing: -0.02em;
}
.page-subtitle {
    font-size: 13px;
    color: #6B7280;
    margin-top: 2px;
}

/* Eval score pills */
.score-pill {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 12px;
    font-size: 11px;
    font-family: 'IBM Plex Mono', monospace;
    font-weight: 500;
}
.score-high   { background: #D1FAE5; color: #065F46; }
.score-mid    { background: #FEF3C7; color: #92400E; }
.score-low    { background: #FEE2E2; color: #991B1B; }

/* Suggestion items */
.suggestion-item {
    background: #FFFBEB;
    border-left: 3px solid #F59E0B;
    padding: 10px 14px;
    border-radius: 0 6px 6px 0;
    font-size: 13px;
    color: #374151;
    margin-bottom: 8px;
}

/* Agent colour map */
.tag-sourcing  { background: #EDE9FE; color: #4C1D95; }
.tag-rejection { background: #FEE2E2; color: #7F1D1D; }
.tag-panel     { background: #DBEAFE; color: #1E3A5F; }
.tag-offer     { background: #D1FAE5; color: #064E3B; }
.tag-pipeline  { background: #FEF3C7; color: #78350F; }

/* Hide Streamlit chrome */
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 28px; padding-bottom: 40px; }
</style>
""", unsafe_allow_html=True)

# ── AGENT COLOUR MAP ─────────────────────────────────────────────────────────
AGENT_COLOURS = {
    "sourcing":  ("#7C3AED", "tag-sourcing",  "Sourcing Quality"),
    "rejection": ("#DC2626", "tag-rejection", "Rejection Pattern"),
    "panel":     ("#2563EB", "tag-panel",     "Panel Load Balancer"),
    "offer":     ("#059669", "tag-offer",     "Offer Insights"),
    "pipeline":  ("#D97706", "tag-pipeline",  "Pipeline Health"),
}

def agent_key(name_or_agent):
    n = (name_or_agent or "").lower()
    for k in AGENT_COLOURS:
        if k in n:
            return k
    return "sourcing"

# ── SIDEBAR ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⬡ Hiring Intelligence")
    st.markdown("---")
    page = st.radio(
        "Navigate",
        ["Overview", "Agent Insights", "Pipeline Funnel",
         "Interviewer Load", "Evaluation", "Cost & Latency"],
        label_visibility="collapsed",
    )
    st.markdown("---")

    st.markdown("**Data source**")
    data_mode = st.radio(
        "mode", ["Load from file", "Paste JSON"], label_visibility="collapsed"
    )

    run_data = None

    if data_mode == "Load from file":
        uploaded = st.file_uploader("Upload n8n output JSON", type="json")
        if uploaded:
            try:
                run_data = json.load(uploaded)
                if isinstance(run_data, list):
                    run_data = run_data[0]
                st.success(f"Loaded — {len(run_data.get('insights', []))} agents")
            except Exception as e:
                st.error(f"Parse error: {e}")
    else:
        raw = st.text_area("Paste JSON output", height=200)
        if raw.strip():
            try:
                run_data = json.loads(raw)
                if isinstance(run_data, list):
                    run_data = run_data[0]
                st.success(f"Loaded — {len(run_data.get('insights', []))} agents")
            except Exception as e:
                st.error(f"Parse error: {e}")

    if run_data is None:
        st.info("No data loaded — showing demo data")

# ── DEMO DATA ────────────────────────────────────────────────────────────────
DEMO = {
    "status": "complete",
    "generated_at": datetime.now().isoformat(),
    "run_summary": {
        "agents_run": 5,
        "total_cost_usd": 0.00412,
        "total_tokens": 8240,
        "rag_grounding_rate": "5/5",
    },
    "insights": [
        {
            "agent": "sourcing_quality",
            "recommendation": "Increase Referral program investment by 30% — it yields a 41.2% offer rate vs 12.5% for LinkedIn at a fraction of the sourcing cost.",
            "evidence": {"source_counts": {"Referral":17,"LinkedIn":16,"Glassdoor":31,"Hackathon":31,"Company Website":31,"AngelList":27,"Recruiter Outreach":24,"Indeed":23}, "accepted_by_source": {"Referral":4,"Company Website":6,"Glassdoor":7}, "key_insight": "Referral has highest ROI; LinkedIn lowest."},
            "confidence_score": 0.88,
            "cost_of_insight": {"model":"gpt-4o-mini","estimated_tokens":1480,"estimated_usd":0.00059},
            "alternative": {"model":"gpt-4o","trade_off":"Higher accuracy but 10x cost for marginal gain on structured data."},
            "eval_scores": {"actionability":1.0,"grounding":1.0,"confidence":1.0,"schema_valid":1.0,"rag_grounded":1.0},
            "eval_overall": 1.0,
            "rag_grounded": True,
        },
        {
            "agent": "rejection_pattern",
            "recommendation": "Address the 26.3% of rejections from role cancellations and compensation mismatches — these are process failures fixable without changing candidate quality.",
            "evidence": {"total_rejections":114,"reasons_breakdown":{"Role cancelled":15,"Compensation mismatch":15,"Underqualified":13,"Communication":12,"Technical skills":11},"key_insight":"Over a quarter of rejections are internally controllable."},
            "confidence_score": 0.91,
            "cost_of_insight": {"model":"gpt-4o","estimated_tokens":1920,"estimated_usd":0.00192},
            "alternative": {"model":"gpt-4o-mini","trade_off":"Saves 70% cost but may miss nuanced stage-level pattern analysis."},
            "eval_scores": {"actionability":1.0,"grounding":1.0,"confidence":1.0,"schema_valid":1.0,"rag_grounded":1.0},
            "eval_overall": 1.0,
            "rag_grounded": True,
        },
        {
            "agent": "panel_load_balancer",
            "recommendation": "Redistribute 12–15 panels from Sam Rivera (77 panels, 27% above average) to Casey Kim and Morgan Chen — both have available capacity.",
            "evidence": {"overloaded":["Sam Rivera (77)","Jamie Osei (64)"],"underloaded":["Casey Kim (55)","Morgan Chen (55)"],"key_insight":"Sam Rivera at 54–93% above safe maximum risks scoring inconsistency."},
            "confidence_score": 0.85,
            "cost_of_insight": {"model":"gpt-4o-mini","estimated_tokens":1340,"estimated_usd":0.00054},
            "alternative": {"model":"gpt-4o","trade_off":"Unnecessary for load calculation — structured data doesn't need frontier reasoning."},
            "eval_scores": {"actionability":1.0,"grounding":1.0,"confidence":1.0,"schema_valid":1.0,"rag_grounded":1.0},
            "eval_overall": 1.0,
            "rag_grounded": True,
        },
        {
            "agent": "offer_insights",
            "recommendation": "Reduce time-to-offer to under 5 days — 39% of declines are speed-related (timeline, competing offer, counter-offer) and are directly preventable.",
            "evidence": {"total_offers":57,"declined":23,"decline_rate":0.404,"key_insight":"Team culture concerns (26%) and speed-related declines (39%) together explain 65% of lost offers."},
            "confidence_score": 0.83,
            "cost_of_insight": {"model":"gpt-4o","estimated_tokens":1860,"estimated_usd":0.00186},
            "alternative": {"model":"gpt-4o-mini","trade_off":"Adequate for basic decline analysis; loses nuance on multi-factor offer scenarios."},
            "eval_scores": {"actionability":1.0,"grounding":1.0,"confidence":1.0,"schema_valid":1.0,"rag_grounded":1.0},
            "eval_overall": 1.0,
            "rag_grounded": True,
        },
        {
            "agent": "pipeline_health",
            "recommendation": "Implement automated SLA alerts at 70% and 85% of target window — 50% of candidates with 2+ reschedules extend pipeline by 6–15 days, breaching Senior role SLA.",
            "evidence": {"avg_days_in_pipeline":21.3,"sla_breaches":["Senior Engineering (28-day SLA at risk)","Staff Product (45-day SLA at risk)"],"key_insight":"Reschedule rate is the primary SLA breach driver."},
            "confidence_score": 0.79,
            "cost_of_insight": {"model":"gpt-4o-mini","estimated_tokens":1640,"estimated_usd":0.00066},
            "alternative": {"model":"gpt-4o","trade_off":"Pipeline health is deterministic enough that gpt-4o-mini suffices."},
            "eval_scores": {"actionability":1.0,"grounding":1.0,"confidence":1.0,"schema_valid":1.0,"rag_grounded":1.0},
            "eval_overall": 1.0,
            "rag_grounded": True,
        },
    ],
    "optimization_report": {
        "total_usd": 0.00412,
        "total_tokens": 8240,
        "rag_grounding_rate": "5/5",
        "cost_by_agent": [
            {"agent":"sourcing_quality","model":"gpt-4o-mini","usd":0.00059,"tokens":1480},
            {"agent":"rejection_pattern","model":"gpt-4o","usd":0.00192,"tokens":1920},
            {"agent":"panel_load_balancer","model":"gpt-4o-mini","usd":0.00054,"tokens":1340},
            {"agent":"offer_insights","model":"gpt-4o","usd":0.00186,"tokens":1860},
            {"agent":"pipeline_health","model":"gpt-4o-mini","usd":0.00066,"tokens":1640},
        ],
        "suggestions": [
            "Rejection Pattern Agent uses gpt-4o ($0.00192) — downgrade to gpt-4o-mini for ~70% cost reduction.",
            "Offer Insights Agent uses gpt-4o ($0.00186) — evaluate if gpt-4o-mini meets quality bar.",
        ],
    },
}

data = run_data if run_data else DEMO
insights     = data.get("insights", [])
opt_report   = data.get("optimization_report", {})
run_summary  = data.get("run_summary", {})
generated_at = data.get("generated_at", datetime.now().isoformat())

try:
    ts = datetime.fromisoformat(generated_at).strftime("%d %b %Y, %H:%M")
except:
    ts = generated_at

# ════════════════════════════════════════════════════════════════════════════
# PAGE: OVERVIEW
# ════════════════════════════════════════════════════════════════════════════
if page == "Overview":
    st.markdown(f"""
    <div class="page-title">Hiring Intelligence System</div>
    <div class="page-subtitle">Last run: {ts} &nbsp;·&nbsp; {run_summary.get('agents_run',5)} agents &nbsp;·&nbsp; RAG grounding: {run_summary.get('rag_grounding_rate','5/5')}</div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # KPI row
    total_candidates = 200
    offers_made      = 57
    offers_accepted  = 34
    rejection_rate   = 57.0
    offer_rate       = round(offers_made / total_candidates * 100, 1)
    acceptance_rate  = round(offers_accepted / offers_made * 100, 1)

    c1, c2, c3, c4, c5 = st.columns(5)
    kpis = [
        ("#7C3AED", "Candidates",      "200",            "from Google Sheets"),
        ("#2563EB", "Offers Made",     f"{offers_made}", f"{offer_rate}% offer rate"),
        ("#059669", "Offers Accepted", f"{offers_accepted}", f"{acceptance_rate}% acceptance"),
        ("#DC2626", "Rejected",        "114",            "57.0% rejection rate"),
        ("#D97706", "Active Pipeline", "29",             "14.5% still in process"),
    ]
    for col, (accent, label, value, sub) in zip([c1,c2,c3,c4,c5], kpis):
        col.markdown(f"""
        <div class="metric-card" style="--accent:{accent}">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
            <div class="metric-sub">{sub}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Agent insights preview
    st.markdown('<div class="section-header">Agent Recommendations</div>', unsafe_allow_html=True)

    for ins in insights:
        ak   = agent_key(ins.get("agent",""))
        col, tag_cls, label = AGENT_COLOURS[ak]
        conf = ins.get("confidence_score", 0)
        conf_pct = int(conf * 100)
        bar_w = int(conf * 100)
        rag_badge = "✦ RAG-grounded" if ins.get("rag_grounded") else "· No RAG context"

        st.markdown(f"""
        <div class="insight-card">
            <span class="insight-agent-tag {tag_cls}">{label}</span>
            <div class="insight-recommendation">{ins.get('recommendation','')}</div>
            <div class="insight-meta">
                <span>Confidence: {conf_pct}%
                    <span class="confidence-bar-wrap">
                        <span class="confidence-bar" style="width:{bar_w}px"></span>
                    </span>
                </span>
                <span>Model: {ins.get('cost_of_insight',{}).get('model','—')}</span>
                <span>Tokens: {ins.get('cost_of_insight',{}).get('estimated_tokens','—')}</span>
                <span style="color:#10B981">{rag_badge}</span>
            </div>
        </div>""", unsafe_allow_html=True)

    # Cost summary
    st.markdown('<div class="section-header">Run Cost Summary</div>', unsafe_allow_html=True)
    cc1, cc2, cc3 = st.columns(3)
    cc1.markdown(f"""<div class="metric-card" style="--accent:#6366F1">
        <div class="metric-label">Total Cost</div>
        <div class="metric-value">${run_summary.get('total_cost_usd', opt_report.get('total_usd',0)):.5f}</div>
        <div class="metric-sub">This run</div>
    </div>""", unsafe_allow_html=True)
    cc2.markdown(f"""<div class="metric-card" style="--accent:#6366F1">
        <div class="metric-label">Total Tokens</div>
        <div class="metric-value">{run_summary.get('total_tokens', opt_report.get('total_tokens',0)):,}</div>
        <div class="metric-sub">Across all agents</div>
    </div>""", unsafe_allow_html=True)
    cc3.markdown(f"""<div class="metric-card" style="--accent:#6366F1">
        <div class="metric-label">RAG Grounding</div>
        <div class="metric-value">{run_summary.get('rag_grounding_rate','5/5')}</div>
        <div class="metric-sub">Agents grounded</div>
    </div>""", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════
# PAGE: AGENT INSIGHTS
# ════════════════════════════════════════════════════════════════════════════
elif page == "Agent Insights":
    st.markdown('<div class="page-title">Agent Insights</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">Detailed output from all 5 specialized agents</div>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    agent_filter = st.selectbox(
        "Filter by agent",
        ["All agents"] + [AGENT_COLOURS[agent_key(i.get("agent",""))][2] for i in insights],
        label_visibility="collapsed"
    )

    for ins in insights:
        ak = agent_key(ins.get("agent",""))
        col, tag_cls, label = AGENT_COLOURS[ak]
        if agent_filter != "All agents" and label != agent_filter:
            continue

        conf = ins.get("confidence_score", 0)
        evidence = ins.get("evidence", {})
        alt = ins.get("alternative", {})
        cost = ins.get("cost_of_insight", {})

        with st.expander(f"**{label}** — {ins.get('recommendation','')[:80]}...", expanded=True):
            st.markdown(f'<span class="insight-agent-tag {tag_cls}">{label}</span>', unsafe_allow_html=True)

            st.markdown("**Recommendation**")
            st.info(ins.get("recommendation",""))

            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Evidence**")
                st.json(evidence)
            with col2:
                st.markdown("**Eval Scores**")
                scores = ins.get("eval_scores", {})
                for metric, val in scores.items():
                    score_cls = "score-high" if val >= 0.9 else ("score-mid" if val >= 0.6 else "score-low")
                    st.markdown(f'<span class="score-pill {score_cls}">{metric}: {val}</span> ', unsafe_allow_html=True)
                st.markdown(f"**Overall:** {ins.get('eval_overall',0):.2f}")

            c1, c2, c3 = st.columns(3)
            c1.metric("Confidence", f"{int(conf*100)}%")
            c2.metric("Model", cost.get("model","—"))
            c3.metric("Cost", f"${cost.get('estimated_usd',0):.5f}")

            st.markdown(f"**Alternative:** {alt.get('model','—')} — {alt.get('trade_off','')}")


# ════════════════════════════════════════════════════════════════════════════
# PAGE: PIPELINE FUNNEL
# ════════════════════════════════════════════════════════════════════════════
elif page == "Pipeline Funnel":
    st.markdown('<div class="page-title">Pipeline Funnel</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">End-to-end conversion metrics from the hiring dataset</div>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    # Funnel chart
    stages = ["Applications", "Completed Interviews", "Offers Made", "Offers Accepted"]
    values = [200, 171, 57, 34]
    colours = ["#7C3AED", "#2563EB", "#059669", "#10B981"]

    fig_funnel = go.Figure(go.Funnel(
        y=stages, x=values,
        textinfo="value+percent initial",
        marker=dict(color=colours),
        connector=dict(line=dict(color="#E5E9F0", width=1)),
    ))
    fig_funnel.update_layout(
        margin=dict(l=20, r=20, t=20, b=20),
        paper_bgcolor="white", plot_bgcolor="white",
        font=dict(family="IBM Plex Sans", size=13),
        height=320,
    )
    st.plotly_chart(fig_funnel, use_container_width=True)

    st.markdown('<div class="section-header">Sourcing Channel Performance</div>', unsafe_allow_html=True)

    channel_df = pd.DataFrame({
        "Channel":         ["Referral","Recruiter Outreach","Hackathon","Indeed","Glassdoor","Company Website","AngelList","LinkedIn"],
        "Total":           [17, 24, 31, 23, 31, 31, 27, 16],
        "Offer Rate (%)":  [41.2, 37.5, 32.3, 30.4, 29.0, 22.6, 22.2, 12.5],
        "Acceptance (%)":  [57.1, 55.6, 40.0, 57.1, 77.8, 85.7, 50.0, 50.0],
    })

    col1, col2 = st.columns(2)
    with col1:
        fig_bar = px.bar(
            channel_df.sort_values("Offer Rate (%)", ascending=True),
            x="Offer Rate (%)", y="Channel", orientation="h",
            color="Offer Rate (%)",
            color_continuous_scale=["#E0E7FF","#7C3AED"],
            title="Offer Rate by Channel",
        )
        fig_bar.update_layout(
            margin=dict(l=10,r=10,t=40,b=10), height=320,
            paper_bgcolor="white", plot_bgcolor="white",
            coloraxis_showscale=False,
            font=dict(family="IBM Plex Sans", size=12),
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    with col2:
        fig_acc = px.bar(
            channel_df.sort_values("Acceptance (%)", ascending=True),
            x="Acceptance (%)", y="Channel", orientation="h",
            color="Acceptance (%)",
            color_continuous_scale=["#D1FAE5","#059669"],
            title="Offer Acceptance Rate by Channel",
        )
        fig_acc.update_layout(
            margin=dict(l=10,r=10,t=40,b=10), height=320,
            paper_bgcolor="white", plot_bgcolor="white",
            coloraxis_showscale=False,
            font=dict(family="IBM Plex Sans", size=12),
        )
        st.plotly_chart(fig_acc, use_container_width=True)

    st.markdown('<div class="section-header">Rejection Reasons</div>', unsafe_allow_html=True)
    rej_df = pd.DataFrame({
        "Reason":  ["Role cancelled","Compensation mismatch","Underqualified","Communication","Technical skills","Background check failed","Culture fit","Overqualified","No show","Better candidate"],
        "Count":   [15,15,13,12,11,11,10,10,9,8],
        "Type":    ["Process","Process","Candidate","Process","Candidate","Candidate","Candidate","Candidate","Process","Candidate"],
    })
    fig_rej = px.bar(
        rej_df.sort_values("Count", ascending=True),
        x="Count", y="Reason", orientation="h",
        color="Type",
        color_discrete_map={"Process":"#DC2626","Candidate":"#6B7280"},
        title="Rejection Reasons (red = internally fixable)",
    )
    fig_rej.update_layout(
        margin=dict(l=10,r=10,t=40,b=10), height=380,
        paper_bgcolor="white", plot_bgcolor="white",
        font=dict(family="IBM Plex Sans", size=12),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    st.plotly_chart(fig_rej, use_container_width=True)


# ════════════════════════════════════════════════════════════════════════════
# PAGE: INTERVIEWER LOAD
# ════════════════════════════════════════════════════════════════════════════
elif page == "Interviewer Load":
    st.markdown('<div class="page-title">Interviewer Load</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">Panel distribution and rebalancing signals</div>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    iv_df = pd.DataFrame({
        "Interviewer":   ["Sam Rivera","Jamie Osei","Riley Patel","Alex Wang","Drew Singh","Taylor Brooks","Quinn Diaz","Jordan Lee","Morgan Chen","Casey Kim"],
        "Panels":        [77, 64, 61, 61, 61, 59, 57, 56, 55, 55],
        "Status":        ["Overloaded","At limit","Healthy","Healthy","Healthy","Healthy","Healthy","Healthy","Available","Available"],
    })
    avg = iv_df["Panels"].mean()

    colour_map = {"Overloaded":"#DC2626","At limit":"#D97706","Healthy":"#2563EB","Available":"#059669"}
    fig_iv = px.bar(
        iv_df.sort_values("Panels", ascending=True),
        x="Panels", y="Interviewer", orientation="h",
        color="Status",
        color_discrete_map=colour_map,
        title="Panel load per interviewer",
    )
    fig_iv.add_vline(x=avg, line_dash="dash", line_color="#6B7280",
                     annotation_text=f"Avg {avg:.0f}", annotation_position="top right")
    fig_iv.add_vline(x=65, line_dash="dot", line_color="#DC2626",
                     annotation_text="Safe max (65)", annotation_position="top left")
    fig_iv.update_layout(
        margin=dict(l=10,r=10,t=40,b=10), height=360,
        paper_bgcolor="white", plot_bgcolor="white",
        font=dict(family="IBM Plex Sans", size=12),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    st.plotly_chart(fig_iv, use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown('<div class="section-header">Reschedule Distribution</div>', unsafe_allow_html=True)
        rs_df = pd.DataFrame({
            "Reschedules": ["0","1","2","3"],
            "Candidates":  [54, 45, 50, 51],
        })
        fig_rs = px.pie(rs_df, values="Candidates", names="Reschedules",
                        color_discrete_sequence=["#D1FAE5","#A7F3D0","#6EE7B7","#059669"],
                        title="Reschedule frequency")
        fig_rs.update_layout(
            margin=dict(l=10,r=10,t=40,b=10), height=280,
            paper_bgcolor="white", font=dict(family="IBM Plex Sans", size=12),
        )
        st.plotly_chart(fig_rs, use_container_width=True)

    with col2:
        st.markdown('<div class="section-header">Rebalancing Actions</div>', unsafe_allow_html=True)
        actions = [
            "Move 12–15 panels from Sam Rivera → Casey Kim + Morgan Chen",
            "Cap any interviewer at 65 panels per hiring cycle",
            "Rotate Quinn Diaz + Jordan Lee into senior-level panels",
            "Add scheduling rule: flag any interviewer at 70% of average",
            "Require min. 2 interviewers per panel for Senior+ roles",
        ]
        for a in actions:
            st.markdown(f'<div class="suggestion-item">↗ {a}</div>', unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════
# PAGE: EVALUATION
# ════════════════════════════════════════════════════════════════════════════
elif page == "Evaluation":
    st.markdown('<div class="page-title">Evaluation Agent</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">Quality scores across 5 dimensions per agent output</div>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    if not insights:
        st.warning("No insight data loaded.")
    else:
        score_rows = []
        for ins in insights:
            ak = agent_key(ins.get("agent",""))
            label = AGENT_COLOURS[ak][2]
            scores = ins.get("eval_scores", {})
            score_rows.append({
                "Agent": label,
                "Actionability": scores.get("actionability", 0),
                "Grounding":     scores.get("grounding", 0),
                "Confidence":    scores.get("confidence", 0),
                "Schema Valid":  scores.get("schema_valid", 0),
                "RAG Grounded":  scores.get("rag_grounded", 0),
                "Overall":       ins.get("eval_overall", 0),
            })

        score_df = pd.DataFrame(score_rows)

        # Radar chart
        dims = ["Actionability","Grounding","Confidence","Schema Valid","RAG Grounded"]
        fig_radar = go.Figure()
        colours_list = ["#7C3AED","#DC2626","#2563EB","#059669","#D97706"]
        for i, row in score_df.iterrows():
            vals = [row[d] for d in dims] + [row[dims[0]]]
            fig_radar.add_trace(go.Scatterpolar(
                r=vals,
                theta=dims + [dims[0]],
                fill='toself',
                name=row["Agent"],
                line_color=colours_list[i % len(colours_list)],
                fillcolor=colours_list[i % len(colours_list)],
                opacity=0.15,
            ))
        fig_radar.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0,1])),
            margin=dict(l=40,r=40,t=40,b=40), height=400,
            paper_bgcolor="white",
            font=dict(family="IBM Plex Sans", size=12),
            legend=dict(orientation="h"),
        )
        st.plotly_chart(fig_radar, use_container_width=True)

        # Score table
        st.markdown('<div class="section-header">Score Breakdown</div>', unsafe_allow_html=True)
        def colour_score(val):
            if val >= 0.9: return "background-color:#D1FAE5; color:#065F46"
            elif val >= 0.6: return "background-color:#FEF3C7; color:#92400E"
            else: return "background-color:#FEE2E2; color:#991B1B"
        styled = score_df.style.applymap(
            colour_score,
            subset=["Actionability","Grounding","Confidence","Schema Valid","RAG Grounded","Overall"]
        ).format({c: "{:.2f}" for c in dims + ["Overall"]})
        st.dataframe(styled, use_container_width=True, hide_index=True)


# ════════════════════════════════════════════════════════════════════════════
# PAGE: COST & LATENCY
# ════════════════════════════════════════════════════════════════════════════
elif page == "Cost & Latency":
    st.markdown('<div class="page-title">Cost & Latency</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">Token usage, model costs, and optimization suggestions</div>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    cost_data = opt_report.get("cost_by_agent", [])
    if not cost_data:
        cost_data = [
            {"agent":"sourcing_quality",   "model":"gpt-4o-mini","usd":0.00059,"tokens":1480},
            {"agent":"rejection_pattern",  "model":"gpt-4o",     "usd":0.00192,"tokens":1920},
            {"agent":"panel_load_balancer","model":"gpt-4o-mini","usd":0.00054,"tokens":1340},
            {"agent":"offer_insights",     "model":"gpt-4o",     "usd":0.00186,"tokens":1860},
            {"agent":"pipeline_health",    "model":"gpt-4o-mini","usd":0.00066,"tokens":1640},
        ]

    cost_df = pd.DataFrame(cost_data)
    cost_df["Agent"] = cost_df["agent"].apply(lambda a: AGENT_COLOURS[agent_key(a)][2])
    cost_df["Color"] = cost_df["agent"].apply(lambda a: AGENT_COLOURS[agent_key(a)][0])

    # Top KPIs
    k1, k2, k3, k4 = st.columns(4)
    k1.markdown(f"""<div class="metric-card" style="--accent:#6366F1">
        <div class="metric-label">Total Cost</div>
        <div class="metric-value">${cost_df['usd'].sum():.5f}</div>
        <div class="metric-sub">This run</div>
    </div>""", unsafe_allow_html=True)
    k2.markdown(f"""<div class="metric-card" style="--accent:#6366F1">
        <div class="metric-label">Total Tokens</div>
        <div class="metric-value">{int(cost_df['tokens'].sum()):,}</div>
        <div class="metric-sub">All agents combined</div>
    </div>""", unsafe_allow_html=True)
    k3.markdown(f"""<div class="metric-card" style="--accent:#059669">
        <div class="metric-label">Cheapest Agent</div>
        <div class="metric-value">${cost_df['usd'].min():.5f}</div>
        <div class="metric-sub">{cost_df.loc[cost_df['usd'].idxmin(),'Agent']}</div>
    </div>""", unsafe_allow_html=True)
    k4.markdown(f"""<div class="metric-card" style="--accent:#DC2626">
        <div class="metric-label">Most Expensive</div>
        <div class="metric-value">${cost_df['usd'].max():.5f}</div>
        <div class="metric-sub">{cost_df.loc[cost_df['usd'].idxmax(),'Agent']}</div>
    </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        fig_cost = px.bar(
            cost_df.sort_values("usd", ascending=True),
            x="usd", y="Agent", orientation="h",
            color="Color", color_discrete_map={c:c for c in cost_df["Color"].unique()},
            title="Cost (USD) per agent",
            labels={"usd":"Cost (USD)"},
        )
        fig_cost.update_layout(
            margin=dict(l=10,r=10,t=40,b=10), height=300,
            paper_bgcolor="white", plot_bgcolor="white",
            showlegend=False,
            font=dict(family="IBM Plex Sans", size=12),
        )
        st.plotly_chart(fig_cost, use_container_width=True)

    with col2:
        fig_tok = px.bar(
            cost_df.sort_values("tokens", ascending=True),
            x="tokens", y="Agent", orientation="h",
            color="Color", color_discrete_map={c:c for c in cost_df["Color"].unique()},
            title="Token usage per agent",
            labels={"tokens":"Tokens"},
        )
        fig_tok.update_layout(
            margin=dict(l=10,r=10,t=40,b=10), height=300,
            paper_bgcolor="white", plot_bgcolor="white",
            showlegend=False,
            font=dict(family="IBM Plex Sans", size=12),
        )
        st.plotly_chart(fig_tok, use_container_width=True)

    # Model breakdown
    st.markdown('<div class="section-header">Model Distribution</div>', unsafe_allow_html=True)
    model_summary = cost_df.groupby("model").agg(
        Agents=("Agent","count"),
        Total_USD=("usd","sum"),
        Total_Tokens=("tokens","sum"),
    ).reset_index().rename(columns={"model":"Model"})
    st.dataframe(model_summary, use_container_width=True, hide_index=True)

    # Before/after optimization
    st.markdown('<div class="section-header">Optimization Levers — Before vs After</div>', unsafe_allow_html=True)
    before_after = pd.DataFrame({
        "Lever":       ["Downgrade Rejection Agent to gpt-4o-mini","Downgrade Offer Agent to gpt-4o-mini"],
        "Before USD":  [0.00192, 0.00186],
        "After USD":   [0.00058, 0.00056],
        "Saving":      ["70%", "70%"],
        "Quality Risk":["Low — structured rejection data","Medium — offer nuance may suffer"],
    })
    st.dataframe(before_after, use_container_width=True, hide_index=True)

    total_before = cost_df["usd"].sum()
    total_after  = total_before - (0.00192 - 0.00058) - (0.00186 - 0.00056)
    st.markdown(f"""
    <div class="suggestion-item">
        Total run cost before optimization: <strong>${total_before:.5f}</strong> &nbsp;→&nbsp;
        after: <strong>${total_after:.5f}</strong> &nbsp;·&nbsp;
        <strong>{round((1 - total_after/total_before)*100)}% reduction</strong>
    </div>""", unsafe_allow_html=True)

    # Optimization suggestions
    st.markdown('<div class="section-header">Optimization Suggestions from Agent</div>', unsafe_allow_html=True)
    for s in opt_report.get("suggestions", ["All agents cost-optimized."]):
        st.markdown(f'<div class="suggestion-item">↗ {s}</div>', unsafe_allow_html=True)

