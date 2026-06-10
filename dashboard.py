"""
AI Hiring Intelligence System — Streamlit Dashboard v2
Auto-loads latest n8n run from GitHub. No manual upload needed.
Run: streamlit run dashboard_v2.py
"""

import streamlit as st
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import requests
import base64

# ── PAGE CONFIG ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Hiring Intelligence",
    page_icon="⬡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CONFIG — update these ────────────────────────────────────────────────────
GITHUB_USERNAME = "viswanalam"
GITHUB_REPO     = "hiring-intelligence-dashboard"
GITHUB_FILE     = "data/latest_run.json"
# Optional: set GITHUB_TOKEN in Streamlit secrets for private repos
# ────────────────────────────────────────────────────────────────────────────

# ── STYLES ───────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@300;400;500;600&display=swap');
html, body, [class*="css"] { font-family: 'IBM Plex Sans', sans-serif; }
[data-testid="stSidebar"] { background: #0D1117; border-right: 1px solid #1E2A38; }
[data-testid="stSidebar"] * { color: #C9D1D9 !important; }
.metric-card { background: white; border: 1px solid #E5E9F0; border-radius: 8px; padding: 20px 24px; position: relative; overflow: hidden; }
.metric-card::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px; background: var(--accent); }
.metric-label { font-size: 11px; font-family: 'IBM Plex Mono', monospace; color: #6B7280; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 8px; }
.metric-value { font-size: 28px; font-weight: 600; color: #0D1117; line-height: 1; margin-bottom: 4px; }
.metric-sub { font-size: 12px; color: #6B7280; }
.insight-card { background: white; border: 1px solid #E5E9F0; border-radius: 8px; padding: 20px 24px; margin-bottom: 16px; }
.insight-agent-tag { font-size: 10px; font-family: 'IBM Plex Mono', monospace; text-transform: uppercase; letter-spacing: 0.1em; padding: 3px 8px; border-radius: 3px; display: inline-block; margin-bottom: 12px; }
.insight-recommendation { font-size: 15px; font-weight: 500; color: #0D1117; line-height: 1.5; margin-bottom: 12px; }
.insight-meta { display: flex; gap: 20px; font-size: 12px; font-family: 'IBM Plex Mono', monospace; color: #6B7280; flex-wrap: wrap; }
.section-header { font-size: 11px; font-family: 'IBM Plex Mono', monospace; text-transform: uppercase; letter-spacing: 0.12em; color: #6B7280; border-bottom: 1px solid #E5E9F0; padding-bottom: 8px; margin-bottom: 20px; margin-top: 8px; }
.page-title { font-size: 22px; font-weight: 600; color: #0D1117; letter-spacing: -0.02em; }
.page-subtitle { font-size: 13px; color: #6B7280; margin-top: 2px; }
.score-pill { display: inline-block; padding: 2px 10px; border-radius: 12px; font-size: 11px; font-family: 'IBM Plex Mono', monospace; font-weight: 500; }
.score-high { background: #D1FAE5; color: #065F46; }
.score-mid  { background: #FEF3C7; color: #92400E; }
.score-low  { background: #FEE2E2; color: #991B1B; }
.suggestion-item { background: #FFFBEB; border-left: 3px solid #F59E0B; padding: 10px 14px; border-radius: 0 6px 6px 0; font-size: 13px; color: #374151; margin-bottom: 8px; }
.tag-sourcing  { background: #EDE9FE; color: #4C1D95; }
.tag-rejection { background: #FEE2E2; color: #7F1D1D; }
.tag-panel     { background: #DBEAFE; color: #1E3A5F; }
.tag-offer     { background: #D1FAE5; color: #064E3B; }
.tag-pipeline  { background: #FEF3C7; color: #78350F; }
.live-badge { display: inline-block; padding: 2px 10px; background: #D1FAE5; color: #065F46; border-radius: 12px; font-size: 11px; font-family: 'IBM Plex Mono', monospace; font-weight: 500; }
.stale-badge { display: inline-block; padding: 2px 10px; background: #FEF3C7; color: #92400E; border-radius: 12px; font-size: 11px; font-family: 'IBM Plex Mono', monospace; font-weight: 500; }
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 28px; padding-bottom: 40px; }
</style>
""", unsafe_allow_html=True)

# ── AGENT CONFIG ─────────────────────────────────────────────────────────────
AGENT_COLOURS = {
    "sourcing":  ("#7C3AED", "tag-sourcing",  "Sourcing Quality"),
    "rejection": ("#DC2626", "tag-rejection", "Rejection Pattern"),
    "panel":     ("#2563EB", "tag-panel",     "Panel Load Balancer"),
    "offer":     ("#059669", "tag-offer",     "Offer Insights"),
    "pipeline":  ("#D97706", "tag-pipeline",  "Pipeline Health"),
}

def agent_key(name):
    n = (name or "").lower()
    for k in AGENT_COLOURS:
        if k in n:
            return k
    return "sourcing"

# ── GITHUB DATA LOADER ───────────────────────────────────────────────────────
@st.cache_data(ttl=60)   # refresh every 60 seconds
def load_from_github():
    """Fetch latest_run.json from GitHub. Returns (data, source_label, error)."""
    try:
        token = st.secrets.get("GITHUB_TOKEN", "")
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"

        url = f"https://api.github.com/repos/{GITHUB_USERNAME}/{GITHUB_REPO}/contents/{GITHUB_FILE}"
        resp = requests.get(url, headers=headers, timeout=10)

        if resp.status_code == 404:
            return None, "not_found", "No run data yet — execute the n8n workflow first."
        if resp.status_code == 401:
            return None, "auth_error", "GitHub auth failed — check GITHUB_TOKEN in Streamlit secrets."
        resp.raise_for_status()

        file_meta = resp.json()
        content   = base64.b64decode(file_meta["content"]).decode("utf-8")
        data      = json.loads(content)
        committed = file_meta.get("_links", {})
        return data, "github", None

    except requests.exceptions.Timeout:
        return None, "timeout", "GitHub request timed out — retrying next refresh."
    except Exception as e:
        return None, "error", str(e)


# ── DEMO DATA ────────────────────────────────────────────────────────────────
DEMO = {
    "status": "demo",
    "generated_at": datetime.now().isoformat(),
    "run_summary": {
        "agents_run": 5,
        "total_cost_usd": 0.00412,
        "total_tokens": 8240,
        "prompt_tokens": 6820,
        "completion_tokens": 1420,
        "avg_latency_ms": 3240,
        "max_latency_ms": 5100,
        "slowest_agent": "rejection_pattern",
        "rag_grounding_rate": "5/5",
        "potential_saving_usd": 0.00265,
    },
    "insights": [
        {"agent":"sourcing_quality",   "recommendation":"Increase Referral program investment by 30% — it yields a 41.2% offer rate vs 12.5% for LinkedIn at a fraction of the sourcing cost.", "evidence":{"source_counts":{"Referral":17,"LinkedIn":16,"Glassdoor":31,"Hackathon":31,"Company Website":31,"AngelList":27,"Recruiter Outreach":24,"Indeed":23},"accepted_by_source":{"Referral":4,"Company Website":6,"Glassdoor":7},"key_insight":"Referral has highest ROI; LinkedIn lowest."},"confidence_score":0.88,"cost_of_insight":{"model":"gpt-4o-mini","prompt_tokens":1243,"completion_tokens":187,"total_tokens":1430,"estimated_usd":0.000298},"alternative":{"model":"gpt-4o","trade_off":"Higher accuracy but 10x cost for marginal gain on structured data."},"eval_scores":{"actionability":1.0,"grounding":1.0,"confidence":1.0,"schema_valid":1.0,"rag_grounded":1.0},"eval_overall":1.0,"rag_grounded":True,"latency_ms":2800,"total_tokens":1430,"estimated_usd":0.000298},
        {"agent":"rejection_pattern",  "recommendation":"Address the 26.3% of rejections from role cancellations and compensation mismatches — these are process failures fixable without changing candidate quality.", "evidence":{"total_rejections":114,"reasons_breakdown":{"Role cancelled":15,"Compensation mismatch":15,"Underqualified":13,"Communication":12,"Technical skills":11},"key_insight":"Over a quarter of rejections are internally controllable."},"confidence_score":0.91,"cost_of_insight":{"model":"gpt-4o","prompt_tokens":1680,"completion_tokens":240,"total_tokens":1920,"estimated_usd":0.00186},"alternative":{"model":"gpt-4o-mini","trade_off":"Saves 70% cost but may miss nuanced stage-level pattern analysis."},"eval_scores":{"actionability":1.0,"grounding":1.0,"confidence":1.0,"schema_valid":1.0,"rag_grounded":1.0},"eval_overall":1.0,"rag_grounded":True,"latency_ms":5100,"total_tokens":1920,"estimated_usd":0.00186},
        {"agent":"panel_load_balancer","recommendation":"Redistribute 12–15 panels from Sam Rivera (77 panels, 27% above average) to Casey Kim and Morgan Chen — both have available capacity.", "evidence":{"overloaded":["Sam Rivera (77)","Jamie Osei (64)"],"underloaded":["Casey Kim (55)","Morgan Chen (55)"],"key_insight":"Sam Rivera at 54–93% above safe maximum risks scoring inconsistency."},"confidence_score":0.85,"cost_of_insight":{"model":"gpt-4o-mini","prompt_tokens":1180,"completion_tokens":160,"total_tokens":1340,"estimated_usd":0.000274},"alternative":{"model":"gpt-4o","trade_off":"Unnecessary for load calculation — structured data doesn't need frontier reasoning."},"eval_scores":{"actionability":1.0,"grounding":1.0,"confidence":1.0,"schema_valid":1.0,"rag_grounded":1.0},"eval_overall":1.0,"rag_grounded":True,"latency_ms":2600,"total_tokens":1340,"estimated_usd":0.000274},
        {"agent":"offer_insights",     "recommendation":"Reduce time-to-offer to under 5 days — 39% of declines are speed-related (timeline, competing offer, counter-offer) and are directly preventable.", "evidence":{"total_offers":57,"declined":23,"decline_rate":0.404,"key_insight":"Team culture concerns (26%) and speed-related declines (39%) together explain 65% of lost offers."},"confidence_score":0.83,"cost_of_insight":{"model":"gpt-4o","prompt_tokens":1620,"completion_tokens":240,"total_tokens":1860,"estimated_usd":0.00186},"alternative":{"model":"gpt-4o-mini","trade_off":"Adequate for basic decline analysis; loses nuance on multi-factor offer scenarios."},"eval_scores":{"actionability":1.0,"grounding":1.0,"confidence":1.0,"schema_valid":1.0,"rag_grounded":1.0},"eval_overall":1.0,"rag_grounded":True,"latency_ms":4800,"total_tokens":1860,"estimated_usd":0.00186},
        {"agent":"pipeline_health",    "recommendation":"Implement automated SLA alerts at 70% and 85% of target window — 50% of candidates with 2+ reschedules extend pipeline by 6–15 days, breaching Senior role SLA.", "evidence":{"avg_days_in_pipeline":21.3,"sla_breaches":["Senior Engineering (28-day SLA at risk)","Staff Product (45-day SLA at risk)"],"key_insight":"Reschedule rate is the primary SLA breach driver."},"confidence_score":0.79,"cost_of_insight":{"model":"gpt-4o-mini","prompt_tokens":1440,"completion_tokens":200,"total_tokens":1640,"estimated_usd":0.000336},"alternative":{"model":"gpt-4o","trade_off":"Pipeline health is deterministic enough that gpt-4o-mini suffices."},"eval_scores":{"actionability":1.0,"grounding":1.0,"confidence":1.0,"schema_valid":1.0,"rag_grounded":1.0},"eval_overall":1.0,"rag_grounded":True,"latency_ms":3100,"total_tokens":1640,"estimated_usd":0.000336},
    ],
    "optimization_report": {
        "total_usd":0.00412,"total_tokens":8240,"total_prompt_tokens":6820,"total_completion_tokens":1420,
        "avg_latency_ms":3240,"max_latency_ms":5100,"slowest_agent":"rejection_pattern",
        "rag_grounding_rate":"5/5","potential_saving_usd":0.00265,
        "cost_by_agent":[
            {"agent":"sourcing_quality",   "model":"gpt-4o-mini","estimated_usd":0.000298,"total_tokens":1430,"latency_ms":2800},
            {"agent":"rejection_pattern",  "model":"gpt-4o",     "estimated_usd":0.00186, "total_tokens":1920,"latency_ms":5100},
            {"agent":"panel_load_balancer","model":"gpt-4o-mini","estimated_usd":0.000274,"total_tokens":1340,"latency_ms":2600},
            {"agent":"offer_insights",     "model":"gpt-4o",     "estimated_usd":0.00186, "total_tokens":1860,"latency_ms":4800},
            {"agent":"pipeline_health",    "model":"gpt-4o-mini","estimated_usd":0.000336,"total_tokens":1640,"latency_ms":3100},
        ],
        "suggestions":["Downgrade rejection_pattern from gpt-4o to gpt-4o-mini (est. saving $0.001302 per run, ~70% reduction).","Downgrade offer_insights from gpt-4o to gpt-4o-mini (est. saving $0.001302 per run, ~70% reduction)."],
    },
}

# ── LOAD DATA ─────────────────────────────────────────────────────────────────
github_data, source, error = load_from_github()

if github_data:
    data        = github_data
    data_source = "live"
    data_label  = "Live — latest n8n run"
else:
    data        = DEMO
    data_source = "demo"
    data_label  = f"Demo data — {error or 'GitHub not connected'}"

insights     = data.get("insights", [])
opt_report   = data.get("optimization_report", {})
run_summary  = data.get("run_summary", {})
generated_at = data.get("generated_at", datetime.now().isoformat())
try:
    ts = datetime.fromisoformat(generated_at).strftime("%d %b %Y, %H:%M")
except:
    ts = generated_at

# ── SIDEBAR ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⬡ Hiring Intelligence")
    st.markdown("---")

    # Data status
    if data_source == "live":
        st.markdown(f'<span class="live-badge">● Live data</span>', unsafe_allow_html=True)
    else:
        st.markdown(f'<span class="stale-badge">◌ Demo data</span>', unsafe_allow_html=True)
        if error:
            st.caption(error)

    st.caption(f"Last run: {ts}")
    if st.button("↻ Refresh data"):
        st.cache_data.clear()
        st.rerun()

    st.markdown("---")
    page = st.radio(
        "Navigate",
        ["Overview", "Agent Insights", "Pipeline Funnel",
         "Interviewer Load", "Evaluation", "Cost & Latency"],
        label_visibility="collapsed",
    )
    st.markdown("---")
    st.caption("Data auto-refreshes every 60s after each n8n run.")


# ════════════════════════════════════════════════════════════════════════════
# PAGE: OVERVIEW
# ════════════════════════════════════════════════════════════════════════════
if page == "Overview":
    badge = '<span class="live-badge">● Live</span>' if data_source == "live" else '<span class="stale-badge">◌ Demo</span>'
    st.markdown(f"""
    <div class="page-title">Hiring Intelligence System &nbsp; {badge}</div>
    <div class="page-subtitle">Last run: {ts} &nbsp;·&nbsp; {run_summary.get('agents_run',5)} agents &nbsp;·&nbsp; RAG: {run_summary.get('rag_grounding_rate','5/5')} &nbsp;·&nbsp; Avg latency: {run_summary.get('avg_latency_ms','—')}ms</div>
    """, unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    # KPI cards
    c1,c2,c3,c4,c5 = st.columns(5)
    kpis = [
        ("#7C3AED","Candidates",     "200",   "from Google Sheets"),
        ("#2563EB","Offers Made",    "57",    "28.5% offer rate"),
        ("#059669","Accepted",       "34",    "59.6% acceptance rate"),
        ("#DC2626","Rejected",       "114",   "57.0% rejection rate"),
        ("#D97706","Active Pipeline","29",    "14.5% still in process"),
    ]
    for col,(accent,label,value,sub) in zip([c1,c2,c3,c4,c5],kpis):
        col.markdown(f"""<div class="metric-card" style="--accent:{accent}">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
            <div class="metric-sub">{sub}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="section-header">Agent Recommendations</div>', unsafe_allow_html=True)

    for ins in insights:
        ak = agent_key(ins.get("agent",""))
        col_hex, tag_cls, label = AGENT_COLOURS[ak]
        conf     = ins.get("confidence_score", 0)
        bar_w    = int(conf * 100)
        cost     = ins.get("cost_of_insight", {})
        latency  = ins.get("latency_ms")
        rag_badge= "✦ RAG-grounded" if ins.get("rag_grounded") else "· No RAG context"
        lat_str  = f"{latency}ms" if latency else "—"

        st.markdown(f"""
        <div class="insight-card">
            <span class="insight-agent-tag {tag_cls}">{label}</span>
            <div class="insight-recommendation">{ins.get('recommendation','')}</div>
            <div class="insight-meta">
                <span>Confidence: {int(conf*100)}%</span>
                <span>Model: {cost.get('model','—')}</span>
                <span>Tokens: {cost.get('total_tokens', ins.get('total_tokens','—'))}</span>
                <span>Cost: ${cost.get('estimated_usd', ins.get('estimated_usd',0)):.6f}</span>
                <span>Latency: {lat_str}</span>
                <span style="color:#10B981">{rag_badge}</span>
            </div>
        </div>""", unsafe_allow_html=True)

    # Run cost strip
    st.markdown('<div class="section-header">Run Summary</div>', unsafe_allow_html=True)
    r1,r2,r3,r4 = st.columns(4)
    r1.markdown(f"""<div class="metric-card" style="--accent:#6366F1">
        <div class="metric-label">Total Cost</div>
        <div class="metric-value">${run_summary.get('total_cost_usd',0):.5f}</div>
        <div class="metric-sub">This run</div>
    </div>""", unsafe_allow_html=True)
    r2.markdown(f"""<div class="metric-card" style="--accent:#6366F1">
        <div class="metric-label">Total Tokens</div>
        <div class="metric-value">{run_summary.get('total_tokens',0):,}</div>
        <div class="metric-sub">{run_summary.get('prompt_tokens',0):,} prompt · {run_summary.get('completion_tokens',0):,} completion</div>
    </div>""", unsafe_allow_html=True)
    r3.markdown(f"""<div class="metric-card" style="--accent:#6366F1">
        <div class="metric-label">Avg Latency</div>
        <div class="metric-value">{run_summary.get('avg_latency_ms','—')}ms</div>
        <div class="metric-sub">Slowest: {run_summary.get('slowest_agent','—')}</div>
    </div>""", unsafe_allow_html=True)
    r4.markdown(f"""<div class="metric-card" style="--accent:#059669">
        <div class="metric-label">Potential Saving</div>
        <div class="metric-value">${run_summary.get('potential_saving_usd',0):.5f}</div>
        <div class="metric-sub">If suggested downgrades applied</div>
    </div>""", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════
# PAGE: AGENT INSIGHTS
# ════════════════════════════════════════════════════════════════════════════
elif page == "Agent Insights":
    st.markdown('<div class="page-title">Agent Insights</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">Detailed output from all 5 specialized agents</div>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    agent_labels = [AGENT_COLOURS[agent_key(i.get("agent",""))][2] for i in insights]
    agent_filter = st.selectbox("Filter", ["All agents"] + agent_labels, label_visibility="collapsed")

    for ins in insights:
        ak = agent_key(ins.get("agent",""))
        _, tag_cls, label = AGENT_COLOURS[ak]
        if agent_filter != "All agents" and label != agent_filter:
            continue

        conf  = ins.get("confidence_score", 0)
        cost  = ins.get("cost_of_insight", {})
        alt   = ins.get("alternative", {})
        ev    = ins.get("eval_scores", {})

        with st.expander(f"**{label}** — {ins.get('recommendation','')[:80]}...", expanded=True):
            st.markdown(f'<span class="insight-agent-tag {tag_cls}">{label}</span>', unsafe_allow_html=True)
            st.markdown("**Recommendation**")
            st.info(ins.get("recommendation",""))

            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Evidence**")
                st.json(ins.get("evidence",{}))
            with col2:
                st.markdown("**Eval Scores**")
                for metric, val in ev.items():
                    sc = "score-high" if val>=0.9 else ("score-mid" if val>=0.6 else "score-low")
                    st.markdown(f'<span class="score-pill {sc}">{metric}: {val}</span> ', unsafe_allow_html=True)
                st.markdown(f"**Overall:** {ins.get('eval_overall',0):.2f}")

            c1,c2,c3,c4 = st.columns(4)
            c1.metric("Confidence",        f"{int(conf*100)}%")
            c2.metric("Model",             cost.get("model","—"))
            c3.metric("Cost",              f"${cost.get('estimated_usd',0):.6f}")
            c4.metric("Latency",           f"{ins.get('latency_ms','—')}ms")

            col3, col4 = st.columns(2)
            with col3:
                st.metric("Prompt tokens",     cost.get("prompt_tokens","—"))
            with col4:
                st.metric("Completion tokens", cost.get("completion_tokens","—"))

            st.markdown(f"**Alternative:** {alt.get('model','—')} — {alt.get('trade_off','')}")


# ════════════════════════════════════════════════════════════════════════════
# PAGE: PIPELINE FUNNEL
# ════════════════════════════════════════════════════════════════════════════
elif page == "Pipeline Funnel":
    st.markdown('<div class="page-title">Pipeline Funnel</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">End-to-end conversion from the hiring dataset</div>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    fig_funnel = go.Figure(go.Funnel(
        y=["Applications","Completed Interviews","Offers Made","Offers Accepted"],
        x=[200, 171, 57, 34],
        textinfo="value+percent initial",
        marker=dict(color=["#7C3AED","#2563EB","#059669","#10B981"]),
        connector=dict(line=dict(color="#E5E9F0", width=1)),
    ))
    fig_funnel.update_layout(margin=dict(l=20,r=20,t=20,b=20), paper_bgcolor="white",
        plot_bgcolor="white", font=dict(family="IBM Plex Sans",size=13), height=300)
    st.plotly_chart(fig_funnel, use_container_width=True)

    st.markdown('<div class="section-header">Sourcing Channel Performance</div>', unsafe_allow_html=True)
    channel_df = pd.DataFrame({
        "Channel":        ["Referral","Recruiter Outreach","Hackathon","Indeed","Glassdoor","Company Website","AngelList","LinkedIn"],
        "Offer Rate (%)": [41.2,37.5,32.3,30.4,29.0,22.6,22.2,12.5],
        "Acceptance (%)": [57.1,55.6,40.0,57.1,77.8,85.7,50.0,50.0],
        "Total":          [17,24,31,23,31,31,27,16],
    })
    col1,col2 = st.columns(2)
    with col1:
        fig = px.bar(channel_df.sort_values("Offer Rate (%)"), x="Offer Rate (%)", y="Channel",
            orientation="h", color="Offer Rate (%)", color_continuous_scale=["#E0E7FF","#7C3AED"],
            title="Offer Rate by Channel")
        fig.update_layout(margin=dict(l=10,r=10,t=40,b=10),height=300,paper_bgcolor="white",
            plot_bgcolor="white",coloraxis_showscale=False,font=dict(family="IBM Plex Sans",size=12))
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        fig2 = px.bar(channel_df.sort_values("Acceptance (%)"), x="Acceptance (%)", y="Channel",
            orientation="h", color="Acceptance (%)", color_continuous_scale=["#D1FAE5","#059669"],
            title="Offer Acceptance by Channel")
        fig2.update_layout(margin=dict(l=10,r=10,t=40,b=10),height=300,paper_bgcolor="white",
            plot_bgcolor="white",coloraxis_showscale=False,font=dict(family="IBM Plex Sans",size=12))
        st.plotly_chart(fig2, use_container_width=True)

    st.markdown('<div class="section-header">Rejection Reasons</div>', unsafe_allow_html=True)
    rej_df = pd.DataFrame({
        "Reason": ["Role cancelled","Compensation mismatch","Underqualified","Communication","Technical skills","Background check failed","Culture fit","Overqualified","No show","Better candidate"],
        "Count":  [15,15,13,12,11,11,10,10,9,8],
        "Type":   ["Process","Process","Candidate","Process","Candidate","Candidate","Candidate","Candidate","Process","Candidate"],
    })
    fig3 = px.bar(rej_df.sort_values("Count"), x="Count", y="Reason", orientation="h",
        color="Type", color_discrete_map={"Process":"#DC2626","Candidate":"#6B7280"},
        title="Rejection Reasons — red = internally fixable")
    fig3.update_layout(margin=dict(l=10,r=10,t=40,b=10),height=360,paper_bgcolor="white",
        plot_bgcolor="white",font=dict(family="IBM Plex Sans",size=12),
        legend=dict(orientation="h",yanchor="bottom",y=1.02))
    st.plotly_chart(fig3, use_container_width=True)


# ════════════════════════════════════════════════════════════════════════════
# PAGE: INTERVIEWER LOAD
# ════════════════════════════════════════════════════════════════════════════
elif page == "Interviewer Load":
    st.markdown('<div class="page-title">Interviewer Load</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">Panel distribution and rebalancing signals</div>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    iv_df = pd.DataFrame({
        "Interviewer": ["Sam Rivera","Jamie Osei","Riley Patel","Alex Wang","Drew Singh","Taylor Brooks","Quinn Diaz","Jordan Lee","Morgan Chen","Casey Kim"],
        "Panels":      [77,64,61,61,61,59,57,56,55,55],
        "Status":      ["Overloaded","At limit","Healthy","Healthy","Healthy","Healthy","Healthy","Healthy","Available","Available"],
    })
    avg = iv_df["Panels"].mean()
    fig = px.bar(iv_df.sort_values("Panels"), x="Panels", y="Interviewer", orientation="h",
        color="Status", color_discrete_map={"Overloaded":"#DC2626","At limit":"#D97706","Healthy":"#2563EB","Available":"#059669"},
        title="Panel load per interviewer")
    fig.add_vline(x=avg,line_dash="dash",line_color="#6B7280",annotation_text=f"Avg {avg:.0f}",annotation_position="top right")
    fig.add_vline(x=65, line_dash="dot", line_color="#DC2626",annotation_text="Safe max",annotation_position="top left")
    fig.update_layout(margin=dict(l=10,r=10,t=40,b=10),height=360,paper_bgcolor="white",
        plot_bgcolor="white",font=dict(family="IBM Plex Sans",size=12),
        legend=dict(orientation="h",yanchor="bottom",y=1.02))
    st.plotly_chart(fig, use_container_width=True)

    col1,col2 = st.columns(2)
    with col1:
        rs_df = pd.DataFrame({"Reschedules":["0","1","2","3"],"Candidates":[54,45,50,51]})
        fig2 = px.pie(rs_df, values="Candidates", names="Reschedules",
            color_discrete_sequence=["#D1FAE5","#A7F3D0","#6EE7B7","#059669"],title="Reschedule frequency")
        fig2.update_layout(margin=dict(l=10,r=10,t=40,b=10),height=280,paper_bgcolor="white",font=dict(family="IBM Plex Sans",size=12))
        st.plotly_chart(fig2, use_container_width=True)
    with col2:
        st.markdown('<div class="section-header">Rebalancing Actions</div>', unsafe_allow_html=True)
        for a in [
            "Move 12–15 panels from Sam Rivera → Casey Kim + Morgan Chen",
            "Cap any interviewer at 65 panels per hiring cycle",
            "Rotate Quinn Diaz + Jordan Lee into senior-level panels",
            "Flag any interviewer exceeding 70% of average load",
            "Require min. 2 interviewers per panel for Senior+ roles",
        ]:
            st.markdown(f'<div class="suggestion-item">↗ {a}</div>', unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════
# PAGE: EVALUATION
# ════════════════════════════════════════════════════════════════════════════
elif page == "Evaluation":
    st.markdown('<div class="page-title">Evaluation Agent</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">Quality scores across 5 dimensions per agent</div>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    score_rows = []
    for ins in insights:
        ak = agent_key(ins.get("agent",""))
        label = AGENT_COLOURS[ak][2]
        ev = ins.get("eval_scores",{})
        score_rows.append({"Agent":label,"Actionability":ev.get("actionability",0),"Grounding":ev.get("grounding",0),"Confidence":ev.get("confidence",0),"Schema Valid":ev.get("schema_valid",0),"RAG Grounded":ev.get("rag_grounded",0),"Overall":ins.get("eval_overall",0)})

    score_df = pd.DataFrame(score_rows)
    dims = ["Actionability","Grounding","Confidence","Schema Valid","RAG Grounded"]
    colours_list = ["#7C3AED","#DC2626","#2563EB","#059669","#D97706"]

    fig = go.Figure()
    for i, row in score_df.iterrows():
        vals = [row[d] for d in dims] + [row[dims[0]]]
        fig.add_trace(go.Scatterpolar(r=vals, theta=dims+[dims[0]], fill='toself',
            name=row["Agent"], line_color=colours_list[i%len(colours_list)],
            fillcolor=colours_list[i%len(colours_list)], opacity=0.15))
    fig.update_layout(polar=dict(radialaxis=dict(visible=True,range=[0,1])),
        margin=dict(l=40,r=40,t=40,b=40),height=400,paper_bgcolor="white",
        font=dict(family="IBM Plex Sans",size=12),legend=dict(orientation="h"))
    st.plotly_chart(fig, use_container_width=True)

    st.markdown('<div class="section-header">Score Breakdown</div>', unsafe_allow_html=True)
    def colour_score(val):
        if val>=0.9: return "background-color:#D1FAE5;color:#065F46"
        elif val>=0.6: return "background-color:#FEF3C7;color:#92400E"
        return "background-color:#FEE2E2;color:#991B1B"
    styled = score_df.style.applymap(colour_score,subset=dims+["Overall"]).format({c:"{:.2f}" for c in dims+["Overall"]})
    st.dataframe(styled, use_container_width=True, hide_index=True)


# ════════════════════════════════════════════════════════════════════════════
# PAGE: COST & LATENCY
# ════════════════════════════════════════════════════════════════════════════
elif page == "Cost & Latency":
    st.markdown('<div class="page-title">Cost & Latency</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">Real token usage, model costs, and optimization opportunities</div>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    cost_data = opt_report.get("cost_by_agent", [])
    cost_df   = pd.DataFrame(cost_data)
    if not cost_df.empty:
        cost_df["Agent"]  = cost_df["agent"].apply(lambda a: AGENT_COLOURS[agent_key(a)][2])
        cost_df["Color"]  = cost_df["agent"].apply(lambda a: AGENT_COLOURS[agent_key(a)][0])

    k1,k2,k3,k4 = st.columns(4)
    k1.markdown(f"""<div class="metric-card" style="--accent:#6366F1">
        <div class="metric-label">Total Cost</div>
        <div class="metric-value">${opt_report.get('total_usd',0):.5f}</div>
        <div class="metric-sub">{opt_report.get('total_tokens',0):,} tokens</div>
    </div>""", unsafe_allow_html=True)
    k2.markdown(f"""<div class="metric-card" style="--accent:#2563EB">
        <div class="metric-label">Avg Latency</div>
        <div class="metric-value">{opt_report.get('avg_latency_ms','—')}ms</div>
        <div class="metric-sub">Max: {opt_report.get('max_latency_ms','—')}ms</div>
    </div>""", unsafe_allow_html=True)
    k3.markdown(f"""<div class="metric-card" style="--accent:#DC2626">
        <div class="metric-label">Slowest Agent</div>
        <div class="metric-value" style="font-size:18px">{opt_report.get('slowest_agent','—')}</div>
        <div class="metric-sub">{opt_report.get('max_latency_ms','—')}ms</div>
    </div>""", unsafe_allow_html=True)
    k4.markdown(f"""<div class="metric-card" style="--accent:#059669">
        <div class="metric-label">Potential Saving</div>
        <div class="metric-value">${opt_report.get('potential_saving_usd',0):.5f}</div>
        <div class="metric-sub">If model downgrades applied</div>
    </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    if not cost_df.empty:
        col1,col2 = st.columns(2)
        with col1:
            fig = px.bar(cost_df.sort_values("estimated_usd"), x="estimated_usd", y="Agent",
                orientation="h", color="Color",
                color_discrete_map={c:c for c in cost_df["Color"].unique()},
                title="Cost (USD) per agent", labels={"estimated_usd":"USD"})
            fig.update_layout(margin=dict(l=10,r=10,t=40,b=10),height=300,paper_bgcolor="white",
                plot_bgcolor="white",showlegend=False,font=dict(family="IBM Plex Sans",size=12))
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            fig2 = px.bar(cost_df.sort_values("latency_ms"), x="latency_ms", y="Agent",
                orientation="h", color="Color",
                color_discrete_map={c:c for c in cost_df["Color"].unique()},
                title="Latency (ms) per agent", labels={"latency_ms":"ms"})
            fig2.update_layout(margin=dict(l=10,r=10,t=40,b=10),height=300,paper_bgcolor="white",
                plot_bgcolor="white",showlegend=False,font=dict(family="IBM Plex Sans",size=12))
            st.plotly_chart(fig2, use_container_width=True)

    st.markdown('<div class="section-header">Before vs After Optimization</div>', unsafe_allow_html=True)
    before_after = pd.DataFrame({
        "Lever":        ["Downgrade Rejection Agent → gpt-4o-mini","Downgrade Offer Agent → gpt-4o-mini"],
        "Before (USD)": [0.00192, 0.00186],
        "After (USD)":  [0.00058, 0.00056],
        "Saving":       ["~70%","~70%"],
        "Quality Risk": ["Low","Medium"],
    })
    st.dataframe(before_after, use_container_width=True, hide_index=True)

    total_before = opt_report.get("total_usd", 0)
    saving       = opt_report.get("potential_saving_usd", 0)
    total_after  = total_before - saving
    st.markdown(f"""<div class="suggestion-item">
        Run cost: <strong>${total_before:.5f}</strong> →
        optimized: <strong>${total_after:.5f}</strong> ·
        <strong>{round(saving/total_before*100) if total_before else 0}% reduction</strong>
    </div>""", unsafe_allow_html=True)

    st.markdown('<div class="section-header">Agent Suggestions</div>', unsafe_allow_html=True)
    for s in opt_report.get("suggestions", ["All agents within targets."]):
        st.markdown(f'<div class="suggestion-item">↗ {s}</div>', unsafe_allow_html=True)

