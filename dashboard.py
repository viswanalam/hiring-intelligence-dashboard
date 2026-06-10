"""
AI Hiring Intelligence System — Streamlit Dashboard v3
All metrics driven from n8n output. No hardcoded counts.
Run: streamlit run dashboard_v3.py
"""

import streamlit as st
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timezone
import requests, base64, pytz

# ── PAGE CONFIG ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Hiring Intelligence",
    page_icon="⬡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CONFIG ────────────────────────────────────────────────────────────────────
GITHUB_USERNAME  = "viswanalam"
GITHUB_REPO      = "hiring-intelligence-dashboard"
GITHUB_FILE      = "data/latest_run.json"
DISPLAY_TIMEZONE = "US/Eastern"   # change to your timezone e.g. "Europe/London", "Asia/Kolkata"

# ── STYLES ────────────────────────────────────────────────────────────────────
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
.live-badge  { display:inline-block; padding:2px 10px; background:#D1FAE5; color:#065F46; border-radius:12px; font-size:11px; font-family:'IBM Plex Mono',monospace; font-weight:500; }
.stale-badge { display:inline-block; padding:2px 10px; background:#FEF3C7; color:#92400E; border-radius:12px; font-size:11px; font-family:'IBM Plex Mono',monospace; font-weight:500; }
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 28px; padding-bottom: 40px; }
</style>
""", unsafe_allow_html=True)

# ── HELPERS ───────────────────────────────────────────────────────────────────
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
        if k in n: return k
    return "sourcing"

def fmt_ts(iso_str):
    """Convert UTC ISO timestamp to display timezone with label."""
    try:
        dt_utc = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        if dt_utc.tzinfo is None:
            dt_utc = dt_utc.replace(tzinfo=timezone.utc)
        tz      = pytz.timezone(DISPLAY_TIMEZONE)
        dt_local= dt_utc.astimezone(tz)
        tz_abbr = dt_local.strftime("%Z")
        return dt_local.strftime(f"%d %b %Y, %H:%M {tz_abbr}")
    except Exception:
        return iso_str

# ── GITHUB LOADER ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=60)
def load_from_github():
    try:
        token   = st.secrets.get("GITHUB_TOKEN", "")
        headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        url  = f"https://api.github.com/repos/{GITHUB_USERNAME}/{GITHUB_REPO}/contents/{GITHUB_FILE}"
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 404:
            return None, "not_found", "No run data yet — execute the n8n workflow first."
        if resp.status_code == 401:
            return None, "auth_error", "GitHub auth failed — check GITHUB_TOKEN in Streamlit secrets."
        resp.raise_for_status()
        file_meta = resp.json()
        content   = base64.b64decode(file_meta["content"]).decode("utf-8")
        return json.loads(content), "github", None
    except requests.exceptions.Timeout:
        return None, "timeout", "GitHub request timed out."
    except Exception as e:
        return None, "error", str(e)

# ── DEMO DATA ─────────────────────────────────────────────────────────────────
DEMO = {
    "status": "demo",
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "run_summary": {"agents_run":5,"total_cost_usd":0.00412,"total_tokens":8240,"prompt_tokens":6820,"completion_tokens":1420,"avg_latency_ms":3240,"max_latency_ms":5100,"slowest_agent":"rejection_pattern","rag_grounding_rate":"5/5","potential_saving_usd":0.00265},
    "pipeline_stats": {"total":200,"offered":57,"accepted":34,"rejected":114,"active":29,"completed":171,"offer_rate":28.5,"accept_rate":59.6,"reject_rate":57.0,"active_rate":14.5},
    "channel_stats": [
        {"channel":"Referral",          "total":17,"offers":7, "accepted":4,"offer_rate":41.2,"accept_rate":57.1},
        {"channel":"Recruiter Outreach","total":24,"offers":9, "accepted":5,"offer_rate":37.5,"accept_rate":55.6},
        {"channel":"Hackathon",         "total":31,"offers":10,"accepted":4,"offer_rate":32.3,"accept_rate":40.0},
        {"channel":"Indeed",            "total":23,"offers":7, "accepted":4,"offer_rate":30.4,"accept_rate":57.1},
        {"channel":"Glassdoor",         "total":31,"offers":9, "accepted":7,"offer_rate":29.0,"accept_rate":77.8},
        {"channel":"Company Website",   "total":31,"offers":7, "accepted":6,"offer_rate":22.6,"accept_rate":85.7},
        {"channel":"AngelList",         "total":27,"offers":6, "accepted":3,"offer_rate":22.2,"accept_rate":50.0},
        {"channel":"LinkedIn",          "total":16,"offers":2, "accepted":1,"offer_rate":12.5,"accept_rate":50.0},
    ],
    "rejection_reasons": [
        {"reason":"Role cancelled","count":15},{"reason":"Compensation mismatch","count":15},
        {"reason":"Underqualified","count":13},{"reason":"Communication","count":12},
        {"reason":"Technical skills","count":11},{"reason":"Background check failed","count":11},
        {"reason":"Culture fit","count":10},{"reason":"Overqualified","count":10},
        {"reason":"No show","count":9},{"reason":"Better candidate","count":8},
    ],
    "reschedule_dist": [{"reschedules":"0","count":54},{"reschedules":"1","count":45},{"reschedules":"2","count":50},{"reschedules":"3","count":51}],
    "interviewer_stats": [
        {"name":"Sam Rivera", "panels_this_month":77,"status":"Overloaded"},
        {"name":"Jamie Osei", "panels_this_month":64,"status":"At limit"},
        {"name":"Riley Patel","panels_this_month":61,"status":"Healthy"},
        {"name":"Alex Wang",  "panels_this_month":61,"status":"Healthy"},
        {"name":"Drew Singh", "panels_this_month":61,"status":"Healthy"},
        {"name":"Taylor Brooks","panels_this_month":59,"status":"Healthy"},
        {"name":"Quinn Diaz", "panels_this_month":57,"status":"Healthy"},
        {"name":"Jordan Lee", "panels_this_month":56,"status":"Healthy"},
        {"name":"Morgan Chen","panels_this_month":55,"status":"Available"},
        {"name":"Casey Kim",  "panels_this_month":55,"status":"Available"},
    ],
    "avg_interviewer_load": 60.6,
    "insights": [
        {"agent":"sourcing_quality",   "recommendation":"Increase Referral program investment by 30% — it yields a 41.2% offer rate vs 12.5% for LinkedIn at a fraction of the sourcing cost.","evidence":{"key_insight":"Referral has highest ROI; LinkedIn lowest."},"confidence_score":0.88,"cost_of_insight":{"model":"gpt-4o-mini","prompt_tokens":1243,"completion_tokens":187,"total_tokens":1430,"estimated_usd":0.000298},"alternative":{"model":"gpt-4o","trade_off":"Higher accuracy but 10x cost for marginal gain on structured data."},"eval_scores":{"actionability":1.0,"grounding":1.0,"confidence":1.0,"schema_valid":1.0,"rag_grounded":1.0},"eval_overall":1.0,"rag_grounded":True,"latency_ms":2800,"total_tokens":1430,"estimated_usd":0.000298},
        {"agent":"rejection_pattern",  "recommendation":"Address the 26.3% of rejections from role cancellations and compensation mismatches — these are process failures fixable without changing candidate quality.","evidence":{"key_insight":"Over a quarter of rejections are internally controllable."},"confidence_score":0.91,"cost_of_insight":{"model":"gpt-4o","prompt_tokens":1680,"completion_tokens":240,"total_tokens":1920,"estimated_usd":0.00186},"alternative":{"model":"gpt-4o-mini","trade_off":"Saves 70% cost but may miss nuanced stage-level pattern analysis."},"eval_scores":{"actionability":1.0,"grounding":1.0,"confidence":1.0,"schema_valid":1.0,"rag_grounded":1.0},"eval_overall":1.0,"rag_grounded":True,"latency_ms":5100,"total_tokens":1920,"estimated_usd":0.00186},
        {"agent":"panel_load_balancer","recommendation":"Redistribute 12–15 panels from Sam Rivera (77 panels, 27% above average) to Casey Kim and Morgan Chen — both have available capacity.","evidence":{"key_insight":"Sam Rivera at 54–93% above safe maximum risks scoring inconsistency."},"confidence_score":0.85,"cost_of_insight":{"model":"gpt-4o-mini","prompt_tokens":1180,"completion_tokens":160,"total_tokens":1340,"estimated_usd":0.000274},"alternative":{"model":"gpt-4o","trade_off":"Unnecessary for load calculation."},"eval_scores":{"actionability":1.0,"grounding":1.0,"confidence":1.0,"schema_valid":1.0,"rag_grounded":1.0},"eval_overall":1.0,"rag_grounded":True,"latency_ms":2600,"total_tokens":1340,"estimated_usd":0.000274},
        {"agent":"offer_insights",     "recommendation":"Reduce time-to-offer to under 5 days — 39% of declines are speed-related and are directly preventable.","evidence":{"key_insight":"Speed-related declines explain 39% of lost offers."},"confidence_score":0.83,"cost_of_insight":{"model":"gpt-4o","prompt_tokens":1620,"completion_tokens":240,"total_tokens":1860,"estimated_usd":0.00186},"alternative":{"model":"gpt-4o-mini","trade_off":"Loses nuance on multi-factor offer scenarios."},"eval_scores":{"actionability":1.0,"grounding":1.0,"confidence":1.0,"schema_valid":1.0,"rag_grounded":1.0},"eval_overall":1.0,"rag_grounded":True,"latency_ms":4800,"total_tokens":1860,"estimated_usd":0.00186},
        {"agent":"pipeline_health",    "recommendation":"Implement automated SLA alerts at 70% and 85% of target window — 50% of candidates with 2+ reschedules extend pipeline by 6–15 days.","evidence":{"key_insight":"Reschedule rate is the primary SLA breach driver."},"confidence_score":0.79,"cost_of_insight":{"model":"gpt-4o-mini","prompt_tokens":1440,"completion_tokens":200,"total_tokens":1640,"estimated_usd":0.000336},"alternative":{"model":"gpt-4o","trade_off":"Pipeline health is deterministic enough that gpt-4o-mini suffices."},"eval_scores":{"actionability":1.0,"grounding":1.0,"confidence":1.0,"schema_valid":1.0,"rag_grounded":1.0},"eval_overall":1.0,"rag_grounded":True,"latency_ms":3100,"total_tokens":1640,"estimated_usd":0.000336},
    ],
    "optimization_report": {"total_usd":0.00412,"total_tokens":8240,"total_prompt_tokens":6820,"total_completion_tokens":1420,"avg_latency_ms":3240,"max_latency_ms":5100,"slowest_agent":"rejection_pattern","rag_grounding_rate":"5/5","potential_saving_usd":0.00265,"cost_by_agent":[{"agent":"sourcing_quality","model":"gpt-4o-mini","estimated_usd":0.000298,"total_tokens":1430,"latency_ms":2800},{"agent":"rejection_pattern","model":"gpt-4o","estimated_usd":0.00186,"total_tokens":1920,"latency_ms":5100},{"agent":"panel_load_balancer","model":"gpt-4o-mini","estimated_usd":0.000274,"total_tokens":1340,"latency_ms":2600},{"agent":"offer_insights","model":"gpt-4o","estimated_usd":0.00186,"total_tokens":1860,"latency_ms":4800},{"agent":"pipeline_health","model":"gpt-4o-mini","estimated_usd":0.000336,"total_tokens":1640,"latency_ms":3100}],"suggestions":["Downgrade rejection_pattern from gpt-4o to gpt-4o-mini (est. saving $0.001302 per run).","Downgrade offer_insights from gpt-4o to gpt-4o-mini (est. saving $0.001302 per run)."]},
}

# ── LOAD ──────────────────────────────────────────────────────────────────────
github_data, source, error = load_from_github()
data        = github_data if github_data else DEMO
data_source = "live" if github_data else "demo"

# ── EXTRACT ───────────────────────────────────────────────────────────────────
insights      = data.get("insights", [])
opt_report    = data.get("optimization_report", {})
run_summary   = data.get("run_summary", {})
ps            = data.get("pipeline_stats", {})
channel_stats = data.get("channel_stats", [])
rej_reasons   = data.get("rejection_reasons", [])
resched_dist  = data.get("reschedule_dist", [])
iv_stats      = data.get("interviewer_stats", [])
avg_iv_load   = data.get("avg_interviewer_load", 0)
ts            = fmt_ts(data.get("generated_at", datetime.now(timezone.utc).isoformat()))

# ── CONTROLLABLE rejections (for funnel page annotation) ─────────────────────
CONTROLLABLE = {"Role cancelled","Compensation mismatch","Communication","No show"}

# ── SIDEBAR ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⬡ Hiring Intelligence")
    st.markdown("---")
    badge_html = '<span class="live-badge">● Live data</span>' if data_source=="live" else '<span class="stale-badge">◌ Demo data</span>'
    st.markdown(badge_html, unsafe_allow_html=True)
    st.caption(f"Last run: {ts}")
    if data_source == "demo" and error:
        st.caption(error)
    if st.button("↻ Refresh"):
        st.cache_data.clear()
        st.rerun()
    st.markdown("---")
    page = st.radio("Navigate", ["Overview","Agent Insights","Pipeline Funnel","Interviewer Load","Evaluation","Cost & Latency"], label_visibility="collapsed")
    st.markdown("---")
    st.caption(f"Timezone: {DISPLAY_TIMEZONE}")
    st.caption("Auto-refreshes every 60s")


# ════════════════════════════════════════════════════════════════════════════
# PAGE: OVERVIEW
# ════════════════════════════════════════════════════════════════════════════
if page == "Overview":
    badge = '<span class="live-badge">● Live</span>' if data_source=="live" else '<span class="stale-badge">◌ Demo</span>'
    st.markdown(f'<div class="page-title">Hiring Intelligence System &nbsp;{badge}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="page-subtitle">Last run: {ts} &nbsp;·&nbsp; {run_summary.get("agents_run",0)} agents &nbsp;·&nbsp; RAG: {run_summary.get("rag_grounding_rate","—")}</div>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    c1,c2,c3,c4,c5 = st.columns(5)
    kpis = [
        ("#7C3AED","Candidates",      ps.get("total",0),    "from Google Sheets"),
        ("#2563EB","Offers Made",     ps.get("offered",0),  f"{ps.get('offer_rate',0)}% offer rate"),
        ("#059669","Accepted",        ps.get("accepted",0), f"{ps.get('accept_rate',0)}% acceptance"),
        ("#DC2626","Rejected",        ps.get("rejected",0), f"{ps.get('reject_rate',0)}% rejection rate"),
        ("#D97706","Active Pipeline", ps.get("active",0),   f"{ps.get('active_rate',0)}% still in process"),
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
        _, tag_cls, label = AGENT_COLOURS[ak]
        conf  = ins.get("confidence_score",0)
        cost  = ins.get("cost_of_insight",{})
        lat   = ins.get("latency_ms")
        rag   = "✦ RAG-grounded" if ins.get("rag_grounded") else "· No RAG context"
        st.markdown(f"""<div class="insight-card">
            <span class="insight-agent-tag {tag_cls}">{label}</span>
            <div class="insight-recommendation">{ins.get('recommendation','')}</div>
            <div class="insight-meta">
                <span>Confidence: {int(conf*100)}%</span>
                <span>Model: {cost.get('model','—')}</span>
                <span>Tokens: {cost.get('total_tokens','—')}</span>
                <span>Cost: ${cost.get('estimated_usd',0):.6f}</span>
                <span>Latency: {f'{lat}ms' if lat else '—'}</span>
                <span style="color:#10B981">{rag}</span>
            </div>
        </div>""", unsafe_allow_html=True)

    st.markdown('<div class="section-header">Run Summary</div>', unsafe_allow_html=True)
    r1,r2,r3,r4 = st.columns(4)
    r1.markdown(f"""<div class="metric-card" style="--accent:#6366F1"><div class="metric-label">Total Cost</div><div class="metric-value">${run_summary.get('total_cost_usd',0):.5f}</div><div class="metric-sub">This run</div></div>""", unsafe_allow_html=True)
    r2.markdown(f"""<div class="metric-card" style="--accent:#6366F1"><div class="metric-label">Total Tokens</div><div class="metric-value">{run_summary.get('total_tokens',0):,}</div><div class="metric-sub">{run_summary.get('prompt_tokens',0):,} prompt · {run_summary.get('completion_tokens',0):,} completion</div></div>""", unsafe_allow_html=True)
    r3.markdown(f"""<div class="metric-card" style="--accent:#6366F1"><div class="metric-label">Avg Latency</div><div class="metric-value">{run_summary.get('avg_latency_ms','—')}ms</div><div class="metric-sub">Slowest: {run_summary.get('slowest_agent','—')}</div></div>""", unsafe_allow_html=True)
    r4.markdown(f"""<div class="metric-card" style="--accent:#059669"><div class="metric-label">Potential Saving</div><div class="metric-value">${run_summary.get('potential_saving_usd',0):.5f}</div><div class="metric-sub">If downgrades applied</div></div>""", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════
# PAGE: AGENT INSIGHTS
# ════════════════════════════════════════════════════════════════════════════
elif page == "Agent Insights":
    st.markdown('<div class="page-title">Agent Insights</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="page-subtitle">Run: {ts}</div>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    labels = [AGENT_COLOURS[agent_key(i.get("agent",""))][2] for i in insights]
    filt   = st.selectbox("Filter", ["All agents"]+labels, label_visibility="collapsed")

    for ins in insights:
        ak = agent_key(ins.get("agent",""))
        _, tag_cls, label = AGENT_COLOURS[ak]
        if filt != "All agents" and label != filt: continue
        conf  = ins.get("confidence_score",0)
        cost  = ins.get("cost_of_insight",{})
        alt   = ins.get("alternative",{})
        ev    = ins.get("eval_scores",{})
        with st.expander(f"**{label}** — {ins.get('recommendation','')[:80]}...", expanded=True):
            st.markdown(f'<span class="insight-agent-tag {tag_cls}">{label}</span>', unsafe_allow_html=True)
            st.info(ins.get("recommendation",""))
            col1,col2 = st.columns(2)
            with col1:
                st.markdown("**Evidence**")
                st.json(ins.get("evidence",{}))
            with col2:
                st.markdown("**Eval Scores**")
                for m,v in ev.items():
                    sc = "score-high" if v>=0.9 else ("score-mid" if v>=0.6 else "score-low")
                    st.markdown(f'<span class="score-pill {sc}">{m}: {v}</span> ', unsafe_allow_html=True)
                st.markdown(f"**Overall:** {ins.get('eval_overall',0):.2f}")
            c1,c2,c3,c4 = st.columns(4)
            c1.metric("Confidence",        f"{int(conf*100)}%")
            c2.metric("Model",             cost.get("model","—"))
            c3.metric("Cost",              f"${cost.get('estimated_usd',0):.6f}")
            c4.metric("Latency",           f"{ins.get('latency_ms','—')}ms")
            c5,c6 = st.columns(2)
            c5.metric("Prompt tokens",     cost.get("prompt_tokens","—"))
            c6.metric("Completion tokens", cost.get("completion_tokens","—"))
            st.markdown(f"**Alternative:** {alt.get('model','—')} — {alt.get('trade_off','')}")


# ════════════════════════════════════════════════════════════════════════════
# PAGE: PIPELINE FUNNEL
# ════════════════════════════════════════════════════════════════════════════
elif page == "Pipeline Funnel":
    st.markdown('<div class="page-title">Pipeline Funnel</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="page-subtitle">Live from n8n run · {ts}</div>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    total     = ps.get("total",0)
    completed = ps.get("completed",0)
    offered   = ps.get("offered",0)
    accepted  = ps.get("accepted",0)

    fig_funnel = go.Figure(go.Funnel(
        y=["Applications","Completed Interviews","Offers Made","Offers Accepted"],
        x=[total, completed, offered, accepted],
        textinfo="value+percent initial",
        marker=dict(color=["#7C3AED","#2563EB","#059669","#10B981"]),
        connector=dict(line=dict(color="#E5E9F0",width=1)),
    ))
    fig_funnel.update_layout(margin=dict(l=20,r=20,t=20,b=20),paper_bgcolor="white",
        plot_bgcolor="white",font=dict(family="IBM Plex Sans",size=13),height=300)
    st.plotly_chart(fig_funnel, use_container_width=True)

    st.markdown('<div class="section-header">Sourcing Channel Performance</div>', unsafe_allow_html=True)
    ch_df = pd.DataFrame(channel_stats)
    if not ch_df.empty:
        col1,col2 = st.columns(2)
        with col1:
            fig = px.bar(ch_df.sort_values("offer_rate"), x="offer_rate", y="channel",
                orientation="h", color="offer_rate",
                color_continuous_scale=["#E0E7FF","#7C3AED"], title="Offer Rate % by Channel",
                labels={"offer_rate":"Offer Rate (%)","channel":"Channel"})
            fig.update_layout(margin=dict(l=10,r=10,t=40,b=10),height=320,paper_bgcolor="white",
                plot_bgcolor="white",coloraxis_showscale=False,font=dict(family="IBM Plex Sans",size=12))
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            fig2 = px.bar(ch_df.sort_values("accept_rate"), x="accept_rate", y="channel",
                orientation="h", color="accept_rate",
                color_continuous_scale=["#D1FAE5","#059669"], title="Acceptance Rate % by Channel",
                labels={"accept_rate":"Acceptance (%)","channel":"Channel"})
            fig2.update_layout(margin=dict(l=10,r=10,t=40,b=10),height=320,paper_bgcolor="white",
                plot_bgcolor="white",coloraxis_showscale=False,font=dict(family="IBM Plex Sans",size=12))
            st.plotly_chart(fig2, use_container_width=True)

    st.markdown('<div class="section-header">Rejection Reasons</div>', unsafe_allow_html=True)
    if rej_reasons:
        rej_df = pd.DataFrame(rej_reasons)
        rej_df["type"] = rej_df["reason"].apply(lambda r: "Process (fixable)" if r in CONTROLLABLE else "Candidate")
        fig3 = px.bar(rej_df.sort_values("count"), x="count", y="reason", orientation="h",
            color="type", color_discrete_map={"Process (fixable)":"#DC2626","Candidate":"#6B7280"},
            title=f"Rejection Reasons — {ps.get('rejected',0)} total rejections",
            labels={"count":"Count","reason":"Reason"})
        fig3.update_layout(margin=dict(l=10,r=10,t=40,b=10),height=380,paper_bgcolor="white",
            plot_bgcolor="white",font=dict(family="IBM Plex Sans",size=12),
            legend=dict(orientation="h",yanchor="bottom",y=1.02))
        st.plotly_chart(fig3, use_container_width=True)


# ════════════════════════════════════════════════════════════════════════════
# PAGE: INTERVIEWER LOAD
# ════════════════════════════════════════════════════════════════════════════
elif page == "Interviewer Load":
    st.markdown('<div class="page-title">Interviewer Load</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="page-subtitle">Live from n8n run · {ts}</div>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    if iv_stats:
        iv_df = pd.DataFrame(iv_stats)
        avg   = avg_iv_load
        fig = px.bar(iv_df.sort_values("panels_this_month"), x="panels_this_month", y="name",
            orientation="h", color="status",
            color_discrete_map={"Overloaded":"#DC2626","At limit":"#D97706","Healthy":"#2563EB","Available":"#059669"},
            title=f"Panel load per interviewer (avg: {avg})",
            labels={"panels_this_month":"Panels","name":"Interviewer"})
        fig.add_vline(x=avg, line_dash="dash", line_color="#6B7280",
            annotation_text=f"Avg {avg}", annotation_position="top right")
        fig.add_vline(x=65, line_dash="dot", line_color="#DC2626",
            annotation_text="Safe max (65)", annotation_position="top left")
        fig.update_layout(margin=dict(l=10,r=10,t=40,b=10),height=360,paper_bgcolor="white",
            plot_bgcolor="white",font=dict(family="IBM Plex Sans",size=12),
            legend=dict(orientation="h",yanchor="bottom",y=1.02))
        st.plotly_chart(fig, use_container_width=True)

    col1,col2 = st.columns(2)
    with col1:
        if resched_dist:
            rs_df = pd.DataFrame(resched_dist)
            fig2 = px.pie(rs_df, values="count", names="reschedules",
                color_discrete_sequence=["#D1FAE5","#A7F3D0","#6EE7B7","#059669"],
                title="Reschedule frequency")
            fig2.update_layout(margin=dict(l=10,r=10,t=40,b=10),height=280,
                paper_bgcolor="white",font=dict(family="IBM Plex Sans",size=12))
            st.plotly_chart(fig2, use_container_width=True)
    with col2:
        st.markdown('<div class="section-header">Rebalancing Actions</div>', unsafe_allow_html=True)
        if iv_stats:
            overloaded = [i["name"] for i in iv_stats if i["status"]=="Overloaded"]
            available  = [i["name"] for i in iv_stats if i["status"]=="Available"]
            if overloaded and available:
                st.markdown(f'<div class="suggestion-item">↗ Move panels from {", ".join(overloaded)} → {", ".join(available)}</div>', unsafe_allow_html=True)
        for a in [
            "Cap any interviewer at 65 panels per hiring cycle",
            "Flag any interviewer exceeding 70% of average load",
            "Require min. 2 interviewers per panel for Senior+ roles",
            "Run calibration sessions every 30 panels per interviewer",
        ]:
            st.markdown(f'<div class="suggestion-item">↗ {a}</div>', unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════
# PAGE: EVALUATION
# ════════════════════════════════════════════════════════════════════════════
elif page == "Evaluation":
    st.markdown('<div class="page-title">Evaluation Agent</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="page-subtitle">Run: {ts}</div>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    dims = ["Actionability","Grounding","Confidence","Schema Valid","RAG Grounded"]
    colours_list = ["#7C3AED","#DC2626","#2563EB","#059669","#D97706"]
    score_rows = []
    for ins in insights:
        ak = agent_key(ins.get("agent",""))
        ev = ins.get("eval_scores",{})
        score_rows.append({"Agent":AGENT_COLOURS[ak][2],"Actionability":ev.get("actionability",0),"Grounding":ev.get("grounding",0),"Confidence":ev.get("confidence",0),"Schema Valid":ev.get("schema_valid",0),"RAG Grounded":ev.get("rag_grounded",0),"Overall":ins.get("eval_overall",0)})

    score_df = pd.DataFrame(score_rows)
    fig = go.Figure()
    for i, row in score_df.iterrows():
        vals = [row[d] for d in dims]+[row[dims[0]]]
        fig.add_trace(go.Scatterpolar(r=vals,theta=dims+[dims[0]],fill='toself',
            name=row["Agent"],line_color=colours_list[i%len(colours_list)],
            fillcolor=colours_list[i%len(colours_list)],opacity=0.15))
    fig.update_layout(polar=dict(radialaxis=dict(visible=True,range=[0,1])),
        margin=dict(l=40,r=40,t=40,b=40),height=400,paper_bgcolor="white",
        font=dict(family="IBM Plex Sans",size=12),legend=dict(orientation="h"))
    st.plotly_chart(fig, use_container_width=True)

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
    st.markdown(f'<div class="page-subtitle">Real token usage from n8n run · {ts}</div>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    cost_df = pd.DataFrame(opt_report.get("cost_by_agent",[]))
    if not cost_df.empty:
        cost_df["Agent"] = cost_df["agent"].apply(lambda a: AGENT_COLOURS[agent_key(a)][2])
        cost_df["Color"] = cost_df["agent"].apply(lambda a: AGENT_COLOURS[agent_key(a)][0])

    k1,k2,k3,k4 = st.columns(4)
    k1.markdown(f"""<div class="metric-card" style="--accent:#6366F1"><div class="metric-label">Total Cost</div><div class="metric-value">${opt_report.get('total_usd',0):.5f}</div><div class="metric-sub">{opt_report.get('total_tokens',0):,} tokens</div></div>""", unsafe_allow_html=True)
    k2.markdown(f"""<div class="metric-card" style="--accent:#2563EB"><div class="metric-label">Avg Latency</div><div class="metric-value">{opt_report.get('avg_latency_ms','—')}ms</div><div class="metric-sub">Max: {opt_report.get('max_latency_ms','—')}ms</div></div>""", unsafe_allow_html=True)
    k3.markdown(f"""<div class="metric-card" style="--accent:#DC2626"><div class="metric-label">Slowest Agent</div><div class="metric-value" style="font-size:18px">{opt_report.get('slowest_agent','—')}</div><div class="metric-sub">{opt_report.get('max_latency_ms','—')}ms</div></div>""", unsafe_allow_html=True)
    k4.markdown(f"""<div class="metric-card" style="--accent:#059669"><div class="metric-label">Potential Saving</div><div class="metric-value">${opt_report.get('potential_saving_usd',0):.5f}</div><div class="metric-sub">If downgrades applied</div></div>""", unsafe_allow_html=True)

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
    gpt4o_agents = [r for r in opt_report.get("cost_by_agent",[]) if r.get("model")=="gpt-4o"]
    if gpt4o_agents:
        rows = []
        for a in gpt4o_agents:
            before = a.get("estimated_usd",0)
            after  = round(before * 0.30, 6)
            rows.append({"Agent":AGENT_COLOURS[agent_key(a["agent"])][2],"Model":"gpt-4o","Before (USD)":before,"After (USD)":after,"Saving":"~70%","Quality Risk":"Low–Medium"})
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        total_before = opt_report.get("total_usd",0)
        saving       = opt_report.get("potential_saving_usd",0)
        total_after  = total_before - saving
        pct          = round(saving/total_before*100) if total_before else 0
        st.markdown(f'<div class="suggestion-item">Run cost: <strong>${total_before:.5f}</strong> → optimized: <strong>${total_after:.5f}</strong> · <strong>{pct}% reduction</strong></div>', unsafe_allow_html=True)

    st.markdown('<div class="section-header">Optimization Suggestions</div>', unsafe_allow_html=True)
    for s in opt_report.get("suggestions",["All agents within targets."]):
        st.markdown(f'<div class="suggestion-item">↗ {s}</div>', unsafe_allow_html=True)

