"""
AI Hiring Intelligence System — Streamlit Dashboard v4
Reads new workflow output: LLM-as-judge eval, golden alignment,
smart cost suggestions, p95 latency, RAG usage rate.
Run: streamlit run dashboard_v4.py
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
DISPLAY_TIMEZONE = "US/Eastern"

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
.score-pill { display: inline-block; padding: 2px 10px; border-radius: 12px; font-size: 11px; font-family: 'IBM Plex Mono', monospace; font-weight: 500; margin-right: 4px; margin-bottom: 4px; }
.score-high { background: #D1FAE5; color: #065F46; }
.score-mid  { background: #FEF3C7; color: #92400E; }
.score-low  { background: #FEE2E2; color: #991B1B; }
.verdict-pass   { background: #D1FAE5; color: #065F46; padding: 3px 10px; border-radius: 4px; font-size: 11px; font-weight: 600; }
.verdict-review { background: #FEF3C7; color: #92400E; padding: 3px 10px; border-radius: 4px; font-size: 11px; font-weight: 600; }
.verdict-fail   { background: #FEE2E2; color: #991B1B; padding: 3px 10px; border-radius: 4px; font-size: 11px; font-weight: 600; }
.suggestion-item { background: #FFFBEB; border-left: 3px solid #F59E0B; padding: 10px 14px; border-radius: 0 6px 6px 0; font-size: 13px; color: #374151; margin-bottom: 8px; }
.suggestion-downgrade { background: #DBEAFE; border-left-color: #2563EB; }
.suggestion-upgrade   { background: #FEE2E2; border-left-color: #DC2626; }
.suggestion-rag       { background: #EDE9FE; border-left-color: #7C3AED; }
.suggestion-latency   { background: #FEF3C7; border-left-color: #D97706; }
.tag-sourcing  { background: #EDE9FE; color: #4C1D95; }
.tag-rejection { background: #FEE2E2; color: #7F1D1D; }
.tag-panel     { background: #DBEAFE; color: #1E3A5F; }
.tag-offer     { background: #D1FAE5; color: #064E3B; }
.tag-pipeline  { background: #FEF3C7; color: #78350F; }
.live-badge  { display:inline-block; padding:2px 10px; background:#D1FAE5; color:#065F46; border-radius:12px; font-size:11px; font-family:'IBM Plex Mono',monospace; font-weight:500; }
.stale-badge { display:inline-block; padding:2px 10px; background:#FEF3C7; color:#92400E; border-radius:12px; font-size:11px; font-family:'IBM Plex Mono',monospace; font-weight:500; }
.judge-quote { background: #F3F4F6; border-left: 3px solid #6B7280; padding: 8px 12px; font-size: 12px; color: #374151; font-style: italic; margin-top: 8px; border-radius: 0 4px 4px 0; }
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
    try:
        dt_utc = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        if dt_utc.tzinfo is None:
            dt_utc = dt_utc.replace(tzinfo=timezone.utc)
        tz       = pytz.timezone(DISPLAY_TIMEZONE)
        dt_local = dt_utc.astimezone(tz)
        return dt_local.strftime("%d %b %Y, %H:%M %Z")
    except Exception:
        return iso_str

def verdict_badge(verdict):
    cls = {"pass":"verdict-pass","review":"verdict-review","fail":"verdict-fail"}.get(verdict, "verdict-review")
    return f'<span class="{cls}">{verdict.upper()}</span>'

# ── GITHUB LOADER ─────────────────────────────────────────────────────────────
@st.cache_data()
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

# ── DEMO DATA (matches new workflow output shape) ────────────────────────────
DEMO = {
    "status": "demo",
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "run_summary": {
        "agents_run": 5,
        "total_cost_usd":      0.01250,
        "insights_cost_usd":   0.00750,
        "eval_cost_usd":       0.00500,
        "total_tokens":        16400,
        "prompt_tokens":       13620,
        "completion_tokens":   2780,
        "avg_latency_ms":      4520,
        "max_latency_ms":      6800,
        "p95_latency_ms":      6500,
        "slowest_agent":       "rejection_pattern",
        "most_expensive_agent": "offer_insights",
        "rag_usage_rate":      1.0,
        "eval_method":         "llm_as_judge_with_golden_dataset",
        "eval_pass_rate":      0.8,
        "eval_avg_score":      0.86,
        "potential_saving_usd": 0.00390,
    },
    "pipeline_stats": {"total":200,"offered":57,"accepted":34,"rejected":114,"active":29,"completed":171,"offer_rate":28.5,"accept_rate":59.6,"reject_rate":57.0,"active_rate":14.5},
    "channel_stats": [
        {"channel":"Referral","total":17,"offers":7,"accepted":4,"offer_rate":41.2,"accept_rate":57.1},
        {"channel":"Recruiter Outreach","total":24,"offers":9,"accepted":5,"offer_rate":37.5,"accept_rate":55.6},
        {"channel":"Hackathon","total":31,"offers":10,"accepted":4,"offer_rate":32.3,"accept_rate":40.0},
        {"channel":"Indeed","total":23,"offers":7,"accepted":4,"offer_rate":30.4,"accept_rate":57.1},
        {"channel":"Glassdoor","total":31,"offers":9,"accepted":7,"offer_rate":29.0,"accept_rate":77.8},
        {"channel":"Company Website","total":31,"offers":7,"accepted":6,"offer_rate":22.6,"accept_rate":85.7},
        {"channel":"AngelList","total":27,"offers":6,"accepted":3,"offer_rate":22.2,"accept_rate":50.0},
        {"channel":"LinkedIn","total":16,"offers":2,"accepted":1,"offer_rate":12.5,"accept_rate":50.0},
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
        {"name":"Sam Rivera","panels_this_month":77,"status":"Overloaded"},
        {"name":"Jamie Osei","panels_this_month":64,"status":"At limit"},
        {"name":"Riley Patel","panels_this_month":61,"status":"Healthy"},
        {"name":"Alex Wang","panels_this_month":61,"status":"Healthy"},
        {"name":"Drew Singh","panels_this_month":61,"status":"Healthy"},
        {"name":"Taylor Brooks","panels_this_month":59,"status":"Healthy"},
        {"name":"Quinn Diaz","panels_this_month":57,"status":"Healthy"},
        {"name":"Jordan Lee","panels_this_month":56,"status":"Healthy"},
        {"name":"Morgan Chen","panels_this_month":55,"status":"Available"},
        {"name":"Casey Kim","panels_this_month":55,"status":"Available"},
    ],
    "avg_interviewer_load": 60.6,
    "insights": [
        {"agent":"sourcing_quality","recommendation":"Increase Referral program investment by 30% — it yields a 41.2% offer rate vs 12.5% for LinkedIn at a fraction of the sourcing cost.","evidence":{"key_insight":"Referral has highest ROI; LinkedIn lowest."},"confidence_score":0.88,"cost_of_insight":{"model":"gpt-4o-mini","prompt_tokens":2240,"completion_tokens":380,"total_tokens":2620,"estimated_usd":0.000564,"llm_calls":2},"rag_used":True,"latency_ms":3800,"total_tokens":2620,"estimated_usd":0.000564,"llm_calls":2,
         "evaluation": {"rubric_scores":{"actionability":1.0,"grounding":1.0,"reasoning_quality":0.9,"schema_validity":1.0,"business_relevance":1.0},"golden_alignment":{"theme_match":1.0,"entity_match":1.0,"anti_theme_avoidance":1.0,"confidence_calibration":1.0},"rubric_overall":0.98,"golden_overall":1.0,"combined_score":0.99,"verdict":"pass","reasoning":"Strong specific recommendation grounded in benchmark data. Mentions both Referral (top) and LinkedIn (bottom) with concrete percentages.","matched_scenario_id":"gold-src-01"}},
        {"agent":"rejection_pattern","recommendation":"Address the 26.3% of rejections from role cancellations and compensation mismatches — these are process failures fixable without changing candidate quality.","evidence":{"key_insight":"Over a quarter of rejections are internally controllable."},"confidence_score":0.91,"cost_of_insight":{"model":"gpt-4o","prompt_tokens":2640,"completion_tokens":480,"total_tokens":3120,"estimated_usd":0.00540,"llm_calls":2},"rag_used":True,"latency_ms":6800,"total_tokens":3120,"estimated_usd":0.00540,"llm_calls":2,
         "evaluation": {"rubric_scores":{"actionability":1.0,"grounding":1.0,"reasoning_quality":1.0,"schema_validity":1.0,"business_relevance":1.0},"golden_alignment":{"theme_match":1.0,"entity_match":1.0,"anti_theme_avoidance":1.0,"confidence_calibration":1.0},"rubric_overall":1.0,"golden_overall":1.0,"combined_score":1.0,"verdict":"pass","reasoning":"Excellent identification of controllable rejections with concrete percentage and actionable fix.","matched_scenario_id":"gold-rej-01"}},
        {"agent":"panel_load_balancer","recommendation":"Redistribute 12 panels from Sam Rivera to Casey Kim and Morgan Chen.","evidence":{"key_insight":"Sam Rivera at 77 panels exceeds safe max."},"confidence_score":0.85,"cost_of_insight":{"model":"gpt-4o-mini","prompt_tokens":1980,"completion_tokens":280,"total_tokens":2260,"estimated_usd":0.000465,"llm_calls":2},"rag_used":True,"latency_ms":3600,"total_tokens":2260,"estimated_usd":0.000465,"llm_calls":2,
         "evaluation": {"rubric_scores":{"actionability":1.0,"grounding":1.0,"reasoning_quality":0.85,"schema_validity":1.0,"business_relevance":1.0},"golden_alignment":{"theme_match":1.0,"entity_match":1.0,"anti_theme_avoidance":1.0,"confidence_calibration":1.0},"rubric_overall":0.97,"golden_overall":1.0,"combined_score":0.98,"verdict":"pass","reasoning":"Specific named-entity recommendation with concrete redistribution count. Could include more rationale.","matched_scenario_id":"gold-pan-01"}},
        {"agent":"offer_insights","recommendation":"Reduce time-to-offer to under 5 days — 39% of declines are speed-related and preventable.","evidence":{"key_insight":"Speed-related declines explain 39% of lost offers."},"confidence_score":0.78,"cost_of_insight":{"model":"gpt-4o","prompt_tokens":3120,"completion_tokens":420,"total_tokens":3540,"estimated_usd":0.00598,"llm_calls":2},"rag_used":True,"latency_ms":6200,"total_tokens":3540,"estimated_usd":0.00598,"llm_calls":2,
         "evaluation": {"rubric_scores":{"actionability":1.0,"grounding":0.9,"reasoning_quality":0.8,"schema_validity":1.0,"business_relevance":1.0},"golden_alignment":{"theme_match":1.0,"entity_match":1.0,"anti_theme_avoidance":1.0,"confidence_calibration":1.0},"rubric_overall":0.94,"golden_overall":1.0,"combined_score":0.97,"verdict":"pass","reasoning":"Identifies speed as primary driver with specific 39% statistic. Strong actionable framing.","matched_scenario_id":"gold-off-01"}},
        {"agent":"pipeline_health","recommendation":"Implement automated SLA alerts at 70% and 85% of target window.","evidence":{"key_insight":"Reschedule rate is the primary SLA breach driver."},"confidence_score":0.55,"cost_of_insight":{"model":"gpt-4o-mini","prompt_tokens":2120,"completion_tokens":320,"total_tokens":2440,"estimated_usd":0.000510,"llm_calls":2},"rag_used":True,"latency_ms":3200,"total_tokens":2440,"estimated_usd":0.000510,"llm_calls":2,
         "evaluation": {"rubric_scores":{"actionability":0.8,"grounding":0.7,"reasoning_quality":0.5,"schema_validity":1.0,"business_relevance":0.7},"golden_alignment":{"theme_match":0.8,"entity_match":0.5,"anti_theme_avoidance":1.0,"confidence_calibration":0.6},"rubric_overall":0.74,"golden_overall":0.73,"combined_score":0.73,"verdict":"review","reasoning":"Reasonable recommendation but lacks specifics on which roles or what alert mechanism. Confidence score (0.55) is correctly low.","matched_scenario_id":"gold-pipe-01"}},
    ],
    "evaluation_summary": {
        "method": "llm_as_judge_with_golden_dataset",
        "judge_model": "gpt-4o",
        "golden_scenarios_count": 18,
        "pass_count": 4, "review_count": 1, "fail_count": 0,
        "pass_rate": 0.8,
        "avg_combined_score": 0.93,
        "eval_cost": {"prompt_tokens":4200,"completion_tokens":680,"total_tokens":4880,"estimated_usd":0.00518,"latency_ms":7200}
    },
    "cost_optimization": {
        "grand_total_usd": 0.01764,
        "grand_total_tokens": 19880,
        "insights_usd": 0.01246,
        "eval_usd": 0.00518,
        "potential_saving_usd": 0.00795,
        "suggestions": [
            {"type":"downgrade","agent":"rejection_pattern","current_model":"gpt-4o","recommended":"gpt-4o-mini","eval_score":1.0,"current_cost":0.00540,"expected_cost":0.00162,"estimated_saving_usd":0.00378,"rationale":"High eval score (1.0) suggests structured task — mini may suffice."},
            {"type":"downgrade","agent":"offer_insights","current_model":"gpt-4o","recommended":"gpt-4o-mini","eval_score":0.97,"current_cost":0.00598,"expected_cost":0.00179,"estimated_saving_usd":0.00419,"rationale":"High eval score (0.97) suggests structured task — mini may suffice."},
        ]
    }
}

# ── LOAD ──────────────────────────────────────────────────────────────────────
github_data, source, error = load_from_github()
data        = github_data if github_data else DEMO
data_source = "live" if github_data else "demo"

# Sanity check — verify live data has expected shape
data_warnings = []
if data_source == "live":
    if not data.get("pipeline_stats"):
        data_warnings.append("pipeline_stats missing — re-import the v104 workflow and run again")
    if not data.get("insights"):
        data_warnings.append("insights array empty — check that 'Aggregate Agent Outputs' fired")
    if not data.get("cost_optimization"):
        data_warnings.append("cost_optimization missing — check that 'Cost & Optimization Agent' ran")
    if not data.get("evaluation_summary"):
        data_warnings.append("evaluation_summary missing — check that 'Eval Output Capture' ran")

insights      = data.get("insights", [])
eval_summary  = data.get("evaluation_summary", {})
cost_opt      = data.get("cost_optimization", {})
run_summary   = data.get("run_summary", {})
ps            = data.get("pipeline_stats", {})
channel_stats = data.get("channel_stats", [])
rej_reasons   = data.get("rejection_reasons", [])
resched_dist  = data.get("reschedule_dist", [])
iv_stats      = data.get("interviewer_stats", [])
avg_iv_load   = data.get("avg_interviewer_load", 0)
ts            = fmt_ts(data.get("generated_at", datetime.now(timezone.utc).isoformat()))

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
    if data_warnings:
        st.warning("⚠ Live data shape issues:")
        for w in data_warnings:
            st.caption(f"• {w}")
    if st.button("↻ Refresh"):
        st.cache_data.clear()
        st.rerun()
    st.markdown("---")
    page = st.radio("Navigate", ["Overview","Agent Insights","Pipeline Funnel","Interviewer Load","Evaluation","Cost & Latency","Optimization"], label_visibility="collapsed")
    st.markdown("---")
    st.caption(f"Timezone: {DISPLAY_TIMEZONE}")
    st.caption("Click ↻ Refresh to load latest run.")


# ════════════════════════════════════════════════════════════════════════════
# PAGE: OVERVIEW
# ════════════════════════════════════════════════════════════════════════════
if page == "Overview":
    badge = '<span class="live-badge">● Live</span>' if data_source=="live" else '<span class="stale-badge">◌ Demo</span>'
    st.markdown(f'<div class="page-title">Hiring Intelligence System &nbsp;{badge}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="page-subtitle">Last run: {ts} &nbsp;·&nbsp; {run_summary.get("agents_run",0)} agents &nbsp;·&nbsp; Eval: {int(run_summary.get("eval_pass_rate",0)*100)}% pass rate &nbsp;·&nbsp; RAG: {int(run_summary.get("rag_usage_rate",0)*100)}% usage</div>', unsafe_allow_html=True)
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
        rag   = "✦ RAG-grounded" if ins.get("rag_used") else "· No RAG used"
        ev    = ins.get("evaluation", {})
        verdict = ev.get("verdict", "—")
        combined = ev.get("combined_score", 0)
        st.markdown(f"""<div class="insight-card">
            <span class="insight-agent-tag {tag_cls}">{label}</span>
            <span style="float:right">{verdict_badge(verdict)}</span>
            <div class="insight-recommendation">{ins.get('recommendation','')}</div>
            <div class="insight-meta">
                <span>Eval: <strong>{combined:.2f}</strong></span>
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
    r1.markdown(f"""<div class="metric-card" style="--accent:#6366F1"><div class="metric-label">Total Cost</div><div class="metric-value">${run_summary.get('total_cost_usd',0):.5f}</div><div class="metric-sub">Insights ${run_summary.get('insights_cost_usd',0):.5f} + Eval ${run_summary.get('eval_cost_usd',0):.5f}</div></div>""", unsafe_allow_html=True)
    r2.markdown(f"""<div class="metric-card" style="--accent:#6366F1"><div class="metric-label">Total Tokens</div><div class="metric-value">{run_summary.get('total_tokens',0):,}</div><div class="metric-sub">{run_summary.get('prompt_tokens',0):,} prompt · {run_summary.get('completion_tokens',0):,} completion</div></div>""", unsafe_allow_html=True)
    r3.markdown(f"""<div class="metric-card" style="--accent:#6366F1"><div class="metric-label">Avg Latency</div><div class="metric-value">{run_summary.get('avg_latency_ms','—')}ms</div><div class="metric-sub">p95: {run_summary.get('p95_latency_ms','—')}ms · max: {run_summary.get('max_latency_ms','—')}ms</div></div>""", unsafe_allow_html=True)
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
        ev    = ins.get("evaluation",{})

        with st.expander(f"**{label}** — {ins.get('recommendation','')[:80]}...", expanded=True):
            st.markdown(f'<span class="insight-agent-tag {tag_cls}">{label}</span>  {verdict_badge(ev.get("verdict","—"))}', unsafe_allow_html=True)
            st.info(ins.get("recommendation",""))

            col1,col2 = st.columns(2)
            with col1:
                st.markdown("**Evidence**")
                st.json(ins.get("evidence",{}))

                if ev.get("reasoning"):
                    st.markdown("**Judge's Reasoning**")
                    st.markdown(f'<div class="judge-quote">{ev["reasoning"]}</div>', unsafe_allow_html=True)
                    if ev.get("matched_scenario_id"):
                        st.caption(f"Matched golden scenario: `{ev['matched_scenario_id']}`")

            with col2:
                st.markdown("**Rubric Scores** (LLM-as-judge)")
                for m,v in ev.get("rubric_scores",{}).items():
                    sc = "score-high" if v>=0.9 else ("score-mid" if v>=0.6 else "score-low")
                    st.markdown(f'<span class="score-pill {sc}">{m}: {v}</span>', unsafe_allow_html=True)

                st.markdown("**Golden Alignment**")
                for m,v in ev.get("golden_alignment",{}).items():
                    sc = "score-high" if v>=0.9 else ("score-mid" if v>=0.6 else "score-low")
                    st.markdown(f'<span class="score-pill {sc}">{m}: {v}</span>', unsafe_allow_html=True)

                st.markdown(f"**Combined Score:** {ev.get('combined_score',0):.2f}")

            c1,c2,c3,c4,c5 = st.columns(5)
            c1.metric("Confidence",     f"{int(conf*100)}%")
            c2.metric("Model",          cost.get("model","—"))
            c3.metric("Cost",           f"${cost.get('estimated_usd',0):.6f}")
            c4.metric("Latency",        f"{ins.get('latency_ms','—')}ms")
            c5.metric("LLM calls",      cost.get("llm_calls",ins.get("llm_calls","—")))

            st.markdown(f"**Alternative model:** {ins.get('alternative',{}).get('model','—')} — {ins.get('alternative',{}).get('trade_off','')}")


# ════════════════════════════════════════════════════════════════════════════
# PAGE: PIPELINE FUNNEL
# ════════════════════════════════════════════════════════════════════════════
elif page == "Pipeline Funnel":
    st.markdown('<div class="page-title">Pipeline Funnel</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="page-subtitle">Live from n8n run · {ts}</div>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    total, completed = ps.get("total",0), ps.get("completed",0)
    offered, accepted = ps.get("offered",0), ps.get("accepted",0)

    fig = go.Figure(go.Funnel(
        y=["Applications","Completed Interviews","Offers Made","Offers Accepted"],
        x=[total, completed, offered, accepted],
        textinfo="value+percent initial",
        marker=dict(color=["#7C3AED","#2563EB","#059669","#10B981"]),
        connector=dict(line=dict(color="#E5E9F0",width=1)),
    ))
    fig.update_layout(margin=dict(l=20,r=20,t=20,b=20),paper_bgcolor="white",plot_bgcolor="white",font=dict(family="IBM Plex Sans",size=13),height=300)
    st.plotly_chart(fig, use_container_width=True)

    st.markdown('<div class="section-header">Sourcing Channel Performance</div>', unsafe_allow_html=True)
    ch_df = pd.DataFrame(channel_stats)
    if not ch_df.empty:
        col1,col2 = st.columns(2)
        with col1:
            fig = px.bar(ch_df.sort_values("offer_rate"), x="offer_rate", y="channel", orientation="h",
                color="offer_rate", color_continuous_scale=["#E0E7FF","#7C3AED"], title="Offer Rate % by Channel",
                labels={"offer_rate":"Offer Rate (%)","channel":"Channel"})
            fig.update_layout(margin=dict(l=10,r=10,t=40,b=10),height=320,paper_bgcolor="white",plot_bgcolor="white",coloraxis_showscale=False,font=dict(family="IBM Plex Sans",size=12))
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            fig2 = px.bar(ch_df.sort_values("accept_rate"), x="accept_rate", y="channel", orientation="h",
                color="accept_rate", color_continuous_scale=["#D1FAE5","#059669"], title="Acceptance Rate % by Channel",
                labels={"accept_rate":"Acceptance (%)","channel":"Channel"})
            fig2.update_layout(margin=dict(l=10,r=10,t=40,b=10),height=320,paper_bgcolor="white",plot_bgcolor="white",coloraxis_showscale=False,font=dict(family="IBM Plex Sans",size=12))
            st.plotly_chart(fig2, use_container_width=True)

    st.markdown('<div class="section-header">Rejection Reasons</div>', unsafe_allow_html=True)
    if rej_reasons:
        rej_df = pd.DataFrame(rej_reasons)
        rej_df["type"] = rej_df["reason"].apply(lambda r: "Process (fixable)" if r in CONTROLLABLE else "Candidate")
        fig3 = px.bar(rej_df.sort_values("count"), x="count", y="reason", orientation="h", color="type",
            color_discrete_map={"Process (fixable)":"#DC2626","Candidate":"#6B7280"},
            title=f"Rejection Reasons — {ps.get('rejected',0)} total rejections")
        fig3.update_layout(margin=dict(l=10,r=10,t=40,b=10),height=380,paper_bgcolor="white",plot_bgcolor="white",font=dict(family="IBM Plex Sans",size=12),legend=dict(orientation="h",yanchor="bottom",y=1.02))
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
        fig = px.bar(iv_df.sort_values("panels_this_month"), x="panels_this_month", y="name", orientation="h",
            color="status", color_discrete_map={"Overloaded":"#DC2626","At limit":"#D97706","Healthy":"#2563EB","Available":"#059669"},
            title=f"Panel load per interviewer (avg: {avg})",
            labels={"panels_this_month":"Panels","name":"Interviewer"})
        fig.add_vline(x=avg, line_dash="dash", line_color="#6B7280", annotation_text=f"Avg {avg}", annotation_position="top right")
        fig.add_vline(x=65, line_dash="dot", line_color="#DC2626", annotation_text="Safe max (65)", annotation_position="top left")
        fig.update_layout(margin=dict(l=10,r=10,t=40,b=10),height=360,paper_bgcolor="white",plot_bgcolor="white",font=dict(family="IBM Plex Sans",size=12),legend=dict(orientation="h",yanchor="bottom",y=1.02))
        st.plotly_chart(fig, use_container_width=True)

    col1,col2 = st.columns(2)
    with col1:
        if resched_dist:
            rs_df = pd.DataFrame(resched_dist)
            fig2 = px.pie(rs_df, values="count", names="reschedules", color_discrete_sequence=["#D1FAE5","#A7F3D0","#6EE7B7","#059669"], title="Reschedule frequency")
            fig2.update_layout(margin=dict(l=10,r=10,t=40,b=10),height=280,paper_bgcolor="white",font=dict(family="IBM Plex Sans",size=12))
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
# PAGE: EVALUATION (rebuilt for LLM-as-judge + golden)
# ════════════════════════════════════════════════════════════════════════════
elif page == "Evaluation":
    st.markdown('<div class="page-title">Evaluation Agent</div>', unsafe_allow_html=True)
    method = eval_summary.get("method","—").replace("_"," ").title()
    judge_model = eval_summary.get("judge_model","—")
    n_scenarios = eval_summary.get("golden_scenarios_count","—")
    st.markdown(f'<div class="page-subtitle">{method} · Judge: {judge_model} · Golden scenarios: {n_scenarios}</div>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    # Summary KPIs
    k1,k2,k3,k4 = st.columns(4)
    k1.markdown(f"""<div class="metric-card" style="--accent:#059669"><div class="metric-label">Pass Rate</div><div class="metric-value">{int(eval_summary.get('pass_rate',0)*100)}%</div><div class="metric-sub">{eval_summary.get('pass_count',0)} pass · {eval_summary.get('review_count',0)} review · {eval_summary.get('fail_count',0)} fail</div></div>""", unsafe_allow_html=True)
    k2.markdown(f"""<div class="metric-card" style="--accent:#2563EB"><div class="metric-label">Avg Combined Score</div><div class="metric-value">{eval_summary.get('avg_combined_score',0):.2f}</div><div class="metric-sub">Across 5 agents</div></div>""", unsafe_allow_html=True)
    eval_cost = eval_summary.get("eval_cost", {})
    k3.markdown(f"""<div class="metric-card" style="--accent:#6366F1"><div class="metric-label">Eval Cost</div><div class="metric-value">${eval_cost.get('estimated_usd',0):.5f}</div><div class="metric-sub">{eval_cost.get('total_tokens',0):,} tokens</div></div>""", unsafe_allow_html=True)
    k4.markdown(f"""<div class="metric-card" style="--accent:#D97706"><div class="metric-label">Eval Latency</div><div class="metric-value">{eval_cost.get('latency_ms','—')}ms</div><div class="metric-sub">Judge run time</div></div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Combined score chart per agent
    rows = []
    for ins in insights:
        ev = ins.get("evaluation", {})
        rows.append({
            "Agent":          AGENT_COLOURS[agent_key(ins.get("agent",""))][2],
            "Rubric":         ev.get("rubric_overall", 0),
            "Golden":         ev.get("golden_overall", 0),
            "Combined":       ev.get("combined_score", 0),
            "Verdict":        ev.get("verdict", "—"),
        })

    if rows:
        df = pd.DataFrame(rows)
        fig = go.Figure()
        fig.add_trace(go.Bar(name="Rubric Score",   x=df["Agent"], y=df["Rubric"],   marker_color="#7C3AED"))
        fig.add_trace(go.Bar(name="Golden Score",   x=df["Agent"], y=df["Golden"],   marker_color="#2563EB"))
        fig.add_trace(go.Bar(name="Combined",       x=df["Agent"], y=df["Combined"], marker_color="#059669"))
        fig.update_layout(barmode='group', margin=dict(l=10,r=10,t=40,b=10),height=360,paper_bgcolor="white",plot_bgcolor="white",font=dict(family="IBM Plex Sans",size=12),title="Evaluation scores per agent", legend=dict(orientation="h", yanchor="bottom", y=1.02))
        fig.update_yaxes(range=[0,1.05])
        st.plotly_chart(fig, use_container_width=True)

    # Detailed table
    st.markdown('<div class="section-header">Per-Agent Detail</div>', unsafe_allow_html=True)
    for ins in insights:
        ak = agent_key(ins.get("agent",""))
        _, tag_cls, label = AGENT_COLOURS[ak]
        ev = ins.get("evaluation", {})

        verdict_text = ev.get("verdict", "—").upper()
        with st.expander(f"**{label}** — [{verdict_text}] · Combined: {ev.get('combined_score',0):.2f}", expanded=False):
            st.markdown(f'<span class="insight-agent-tag {tag_cls}">{label}</span>  {verdict_badge(ev.get("verdict","—"))}', unsafe_allow_html=True)

            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Rubric Scores**")
                for m,v in ev.get("rubric_scores",{}).items():
                    sc = "score-high" if v>=0.9 else ("score-mid" if v>=0.6 else "score-low")
                    st.markdown(f'<span class="score-pill {sc}">{m}: {v}</span>', unsafe_allow_html=True)
                st.markdown(f"&nbsp;<br>**Rubric Overall:** {ev.get('rubric_overall',0):.2f}", unsafe_allow_html=True)
            with col2:
                st.markdown("**Golden Alignment**")
                for m,v in ev.get("golden_alignment",{}).items():
                    sc = "score-high" if v>=0.9 else ("score-mid" if v>=0.6 else "score-low")
                    st.markdown(f'<span class="score-pill {sc}">{m}: {v}</span>', unsafe_allow_html=True)
                st.markdown(f"&nbsp;<br>**Golden Overall:** {ev.get('golden_overall',0):.2f}", unsafe_allow_html=True)
                if ev.get("matched_scenario_id"):
                    st.caption(f"Matched scenario: `{ev['matched_scenario_id']}`")

            st.markdown("**Judge's Reasoning**")
            st.markdown(f'<div class="judge-quote">{ev.get("reasoning","No reasoning available.")}</div>', unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════
# PAGE: COST & LATENCY
# ════════════════════════════════════════════════════════════════════════════
elif page == "Cost & Latency":
    st.markdown('<div class="page-title">Cost & Latency</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="page-subtitle">Real token usage from n8n run · {ts}</div>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    # Cost split: insights vs eval
    k1,k2,k3,k4 = st.columns(4)
    k1.markdown(f"""<div class="metric-card" style="--accent:#6366F1"><div class="metric-label">Grand Total</div><div class="metric-value">${run_summary.get('total_cost_usd',0):.5f}</div><div class="metric-sub">{run_summary.get('total_tokens',0):,} tokens</div></div>""", unsafe_allow_html=True)
    k2.markdown(f"""<div class="metric-card" style="--accent:#7C3AED"><div class="metric-label">Insights Cost</div><div class="metric-value">${run_summary.get('insights_cost_usd',0):.5f}</div><div class="metric-sub">5 agent runs</div></div>""", unsafe_allow_html=True)
    k3.markdown(f"""<div class="metric-card" style="--accent:#DC2626"><div class="metric-label">Eval Cost</div><div class="metric-value">${run_summary.get('eval_cost_usd',0):.5f}</div><div class="metric-sub">LLM-as-judge</div></div>""", unsafe_allow_html=True)
    k4.markdown(f"""<div class="metric-card" style="--accent:#059669"><div class="metric-label">Potential Saving</div><div class="metric-value">${run_summary.get('potential_saving_usd',0):.5f}</div><div class="metric-sub">From suggestions</div></div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Per-agent cost from insights
    cost_data = [{
        "agent":         i.get("agent"),
        "Agent":         AGENT_COLOURS[agent_key(i.get("agent",""))][2],
        "Color":         AGENT_COLOURS[agent_key(i.get("agent",""))][0],
        "model":         i.get("cost_of_insight",{}).get("model","—"),
        "estimated_usd": i.get("estimated_usd",0),
        "total_tokens":  i.get("total_tokens",0),
        "latency_ms":    i.get("latency_ms",0),
        "llm_calls":     i.get("llm_calls",0),
    } for i in insights]
    cost_df = pd.DataFrame(cost_data)

    if not cost_df.empty:
        col1,col2 = st.columns(2)
        with col1:
            fig = px.bar(cost_df.sort_values("estimated_usd"), x="estimated_usd", y="Agent", orientation="h", color="Color",
                color_discrete_map={c:c for c in cost_df["Color"].unique()}, title="Cost (USD) per agent", labels={"estimated_usd":"USD"})
            fig.update_layout(margin=dict(l=10,r=10,t=40,b=10),height=300,paper_bgcolor="white",plot_bgcolor="white",showlegend=False,font=dict(family="IBM Plex Sans",size=12))
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            fig2 = px.bar(cost_df.sort_values("latency_ms"), x="latency_ms", y="Agent", orientation="h", color="Color",
                color_discrete_map={c:c for c in cost_df["Color"].unique()}, title="Latency (ms) per agent", labels={"latency_ms":"ms"})
            fig2.update_layout(margin=dict(l=10,r=10,t=40,b=10),height=300,paper_bgcolor="white",plot_bgcolor="white",showlegend=False,font=dict(family="IBM Plex Sans",size=12))
            st.plotly_chart(fig2, use_container_width=True)

    # Latency stats summary
    st.markdown('<div class="section-header">Latency Distribution</div>', unsafe_allow_html=True)
    l1,l2,l3 = st.columns(3)
    l1.metric("Avg", f"{run_summary.get('avg_latency_ms','—')}ms")
    l2.metric("p95", f"{run_summary.get('p95_latency_ms','—')}ms")
    l3.metric("Max", f"{run_summary.get('max_latency_ms','—')}ms (slowest: {run_summary.get('slowest_agent','—')})")

    # Cost table
    st.markdown('<div class="section-header">Per-agent breakdown</div>', unsafe_allow_html=True)
    show_df = cost_df[["Agent","model","total_tokens","estimated_usd","latency_ms","llm_calls"]].copy()
    show_df.columns = ["Agent","Model","Tokens","Cost (USD)","Latency (ms)","LLM Calls"]
    show_df["Cost (USD)"] = show_df["Cost (USD)"].apply(lambda x: f"${x:.6f}")
    st.dataframe(show_df, use_container_width=True, hide_index=True)


# ════════════════════════════════════════════════════════════════════════════
# PAGE: OPTIMIZATION (NEW)
# ════════════════════════════════════════════════════════════════════════════
elif page == "Optimization":
    st.markdown('<div class="page-title">Optimization Suggestions</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="page-subtitle">Based on real cost + LLM judge eval scores</div>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    k1,k2 = st.columns(2)
    total_before = cost_opt.get("grand_total_usd", 0)
    saving       = cost_opt.get("potential_saving_usd", 0)
    total_after  = max(0, total_before - saving)
    pct          = round(saving/total_before*100) if total_before else 0

    k1.markdown(f"""<div class="metric-card" style="--accent:#DC2626"><div class="metric-label">Current Run Cost</div><div class="metric-value">${total_before:.5f}</div><div class="metric-sub">Insights + Eval</div></div>""", unsafe_allow_html=True)
    k2.markdown(f"""<div class="metric-card" style="--accent:#059669"><div class="metric-label">If Optimized</div><div class="metric-value">${total_after:.5f}</div><div class="metric-sub">{pct}% reduction · ${saving:.5f} saved</div></div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="section-header">Suggestions</div>', unsafe_allow_html=True)

    suggestions = cost_opt.get("suggestions", [])
    if not suggestions:
        st.success("✓ All agents within cost, latency, and quality targets.")
    else:
        type_class = {
            "downgrade":     "suggestion-downgrade",
            "upgrade":       "suggestion-upgrade",
            "rag_grounding": "suggestion-rag",
            "latency":       "suggestion-latency",
            "all_optimal":   "",
        }
        type_label = {
            "downgrade":     "💰 Cost Downgrade",
            "upgrade":       "📈 Quality Upgrade",
            "rag_grounding": "🔗 RAG Grounding",
            "latency":       "⏱ Latency",
            "all_optimal":   "✓ Optimal",
        }
        for s in suggestions:
            t = s.get("type", "all_optimal")
            cls = type_class.get(t, "")
            agent_name = s.get("agent", "")
            if agent_name:
                ak = agent_key(agent_name)
                agent_label = AGENT_COLOURS[ak][2]
            else:
                agent_label = ""

            saving_txt = ""
            if "estimated_saving_usd" in s:
                saving_txt = f" · Saves <strong>${s['estimated_saving_usd']:.5f}</strong>"
            elif "estimated_extra_usd" in s:
                saving_txt = f" · Costs extra <strong>${s['estimated_extra_usd']:.5f}</strong>"

            st.markdown(f"""<div class="suggestion-item {cls}">
                <strong>{type_label.get(t,'•')}</strong>
                {f" — <strong>{agent_label}</strong>" if agent_label else ""}
                {saving_txt}
                <br><span style="color:#6B7280">{s.get('rationale','')}</span>
            </div>""", unsafe_allow_html=True)

    # Downgrade simulation table
    downgrades = [s for s in suggestions if s.get("type") == "downgrade"]
    if downgrades:
        st.markdown('<div class="section-header">Downgrade Impact</div>', unsafe_allow_html=True)
        rows = [{
            "Agent":            AGENT_COLOURS[agent_key(s["agent"])][2],
            "Current Model":    s.get("current_model","—"),
            "Recommended":      s.get("recommended","—"),
            "Eval Score":       f"{s.get('eval_score',0):.2f}",
            "Current Cost":     f"${s.get('current_cost',0):.6f}",
            "Expected Cost":    f"${s.get('expected_cost',0):.6f}",
            "Saving":           f"${s.get('estimated_saving_usd',0):.6f}",
        } for s in downgrades]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
