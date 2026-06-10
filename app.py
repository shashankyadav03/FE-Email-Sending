import os
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from src.auth import check_password
from src import db, api

load_dotenv()

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="DataFinsight · Recruiter",
    page_icon="📧",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Global CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 1.8rem !important; }

section[data-testid="stSidebar"] {
    background: #0F172A !important;
    border-right: 1px solid #1E293B;
}
section[data-testid="stSidebar"] * { color: #CBD5E1 !important; }
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2 { color: #F8FAFC !important; }
section[data-testid="stSidebar"] hr { border-color: #1E293B !important; }
section[data-testid="stSidebar"] button {
    background: #1E293B !important;
    border: 1px solid #334155 !important;
    color: #CBD5E1 !important;
    border-radius: 8px !important;
}
section[data-testid="stSidebar"] button:hover {
    background: #334155 !important;
    color: #F8FAFC !important;
}

.kpi-card {
    background: #FFFFFF;
    border-radius: 14px;
    padding: 20px 18px 16px;
    border: 1px solid #E2E8F0;
    box-shadow: 0 1px 4px rgba(0,0,0,.06);
    min-height: 120px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
}
.kpi-icon  { font-size: 20px; }
.kpi-value { font-size: 32px; font-weight: 800; color: #1E293B; line-height: 1; }
.kpi-label { font-size: 11.5px; font-weight: 600; color: #64748B; letter-spacing: .4px; text-transform: uppercase; }
.kpi-sub   { font-size: 11px; color: #94A3B8; margin-top: 2px; }

.sec-title { font-size: 19px; font-weight: 700; color: #1E293B; margin-bottom: 2px; }
.sec-sub   { font-size: 13px; color: #64748B; margin-bottom: 18px; }

.badge {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 20px;
    font-size: 11.5px;
    font-weight: 600;
    white-space: nowrap;
}
.badge-open           { background:#DBEAFE; color:#1D4ED8; }
.badge-closed         { background:#F1F5F9; color:#475569; }
.badge-needs          { background:#FEF3C7; color:#92400E; }
.badge-interested     { background:#D1FAE5; color:#065F46; }
.badge-not-interested { background:#FEE2E2; color:#991B1B; }
.badge-token          { background:#D1FAE5; color:#065F46; }
.badge-header         { background:#DBEAFE; color:#1D4ED8; }
.badge-fuzzy          { background:#FEF3C7; color:#92400E; }
.badge-unmatched      { background:#F1F5F9; color:#6B7280; }
.badge-opened         { background:#FEF3C7; color:#92400E; }
.badge-sent           { background:#EFF6FF; color:#3B82F6; }

.bubble-out {
    background: #EFF6FF;
    border-left: 3px solid #3B82F6;
    border-radius: 0 10px 10px 0;
    padding: 12px 16px;
    margin: 6px 0;
}
.bubble-in {
    background: #F0FDF4;
    border-left: 3px solid #22C55E;
    border-radius: 0 10px 10px 0;
    padding: 12px 16px;
    margin: 6px 0;
}
.bubble-label {
    font-size: 11px;
    font-weight: 600;
    letter-spacing: .3px;
    text-transform: uppercase;
    margin-bottom: 4px;
}
.bubble-out .bubble-label { color: #3B82F6; }
.bubble-in  .bubble-label { color: #16A34A; }
.bubble-date { font-size: 11px; color: #94A3B8; float: right; }
.bubble-body { font-size: 13.5px; color: #334155; white-space: pre-wrap; margin-top: 4px; }

.body-preview {
    font-size: 13px;
    color: #64748B;
    font-style: italic;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 100%;
    padding: 3px 0 6px;
}

.divider { border: none; border-top: 1px solid #E2E8F0; margin: 14px 0; }

.status-box {
    background: #F8FAFC;
    border: 1px solid #E2E8F0;
    border-radius: 10px;
    padding: 14px 18px;
    font-size: 13px;
    color: #334155;
    margin-top: 10px;
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
}
.status-box strong { color: #1E293B; }

.conv-token {
    font-size: 11px;
    font-family: monospace;
    color: #7C3AED;
    background: #F5F3FF;
    padding: 2px 7px;
    border-radius: 4px;
    display: inline-block;
}

.compose-notice {
    background: #FFF7ED;
    border: 1px solid #FED7AA;
    border-radius: 10px;
    padding: 12px 16px;
    font-size: 13px;
    color: #92400E;
    margin-bottom: 20px;
}

.page-row {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 12px;
    padding: 10px 0 4px;
    font-size: 13px;
    color: #64748B;
}

@media (max-width: 768px) {
    .block-container { padding: 1rem 0.75rem !important; }
    .kpi-card { min-height: auto !important; padding: 14px 12px !important; }
    .kpi-value { font-size: 26px !important; }
    .kpi-label { font-size: 11px !important; }
    .sec-title { font-size: 16px !important; }
    .bubble-body { font-size: 12.5px !important; }
    div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
        flex: 1 1 45% !important;
        min-width: 45% !important;
    }
}

@media (max-width: 480px) {
    .block-container { padding: 0.75rem 0.5rem !important; }
    .kpi-value { font-size: 22px !important; }
    .kpi-sub { display: none; }
    div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
        flex: 1 1 100% !important;
        min-width: 100% !important;
    }
    .status-box { flex-direction: column; gap: 4px; }
}
</style>
""", unsafe_allow_html=True)


# ── Auth gate ─────────────────────────────────────────────────────────────────
if not check_password():
    st.stop()


# ── Constants ─────────────────────────────────────────────────────────────────
_EMPTY    = "—"
PAGE_SIZE = 25

days_map = {"All time": 0, "Last 7 days": 7, "Last 30 days": 30, "Last 90 days": 90}

_CONV_STATUS = {
    "open":                ("badge-open",           "Open"),
    "closed":              ("badge-closed",          "Closed"),
    "needs_clarification": ("badge-needs",           "Needs Review"),
}
_INTEREST = {
    "interested":          ("badge-interested",      "Interested"),
    "not_interested":      ("badge-not-interested",  "Not Interested"),
    "unsure":              ("badge-needs",            "Unsure"),
}
_MATCH = {
    "subject_token":       ("badge-token",    "Token Match"),
    "in_reply_to":         ("badge-header",   "Header Match"),
    "references":          ("badge-header",   "Ref Match"),
    "sender_fuzzy":        ("badge-fuzzy",    "Fuzzy Match"),
    "none":                ("badge-unmatched","Unmatched"),
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def fmt_dt(iso_str: str, short: bool = False) -> str:
    if not iso_str:
        return _EMPTY
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00")).astimezone(timezone.utc)
        return dt.strftime("%b %d, %Y") if short else dt.strftime("%b %d, %Y  ·  %I:%M %p UTC")
    except Exception:
        return iso_str


def _body_preview(body: str, max_chars: int = 140) -> str:
    """First non-empty line of body, truncated to max_chars."""
    if not body:
        return ""
    for line in body.splitlines():
        stripped = line.strip()
        if stripped:
            return (stripped[:max_chars] + "…") if len(stripped) > max_chars else stripped
    return (body[:max_chars] + "…") if len(body) > max_chars else body


def _after_cutoff(iso_str: str, cutoff) -> bool:
    if not iso_str or cutoff is None:
        return True
    try:
        return datetime.fromisoformat(iso_str.replace("Z", "+00:00")) >= cutoff
    except Exception:
        return True


def _section_header(title: str, sub: str = "") -> None:
    st.markdown(f'<div class="sec-title">{title}</div>', unsafe_allow_html=True)
    if sub:
        st.markdown(f'<div class="sec-sub">{sub}</div>', unsafe_allow_html=True)


def _bubble_html(cls: str, label: str, body: str, ts: str = "") -> str:
    date_span = f'<span class="bubble-date">{ts}</span>' if ts else ""
    return (
        f'<div class="{cls}">'
        f'<div class="bubble-label">{label}{date_span}</div>'
        f'<div class="bubble-body">{body}</div>'
        f'</div>'
    )


def kpi_card(col, icon: str, value, label: str, sub: str = "", color: str = "#2563EB"):
    col.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-icon">{icon}</div>
        <div>
            <div class="kpi-value" style="color:{color}">{value}</div>
            <div class="kpi-label">{label}</div>
            <div class="kpi-sub">{sub}</div>
        </div>
    </div>""", unsafe_allow_html=True)


def badge(cls: str, label: str) -> str:
    return f'<span class="badge {cls}">{label}</span>'


def _make_badge_fn(lookup: dict):
    def fn(status: str) -> str:
        cls, lbl = lookup.get(status, ("badge-open", status or _EMPTY))
        return badge(cls, lbl)
    return fn


conv_badge     = _make_badge_fn(_CONV_STATUS)
interest_badge = _make_badge_fn(_INTEREST)
match_badge    = _make_badge_fn(_MATCH)


def _paginate(items: list, page_key: str, filter_sig: str) -> tuple[list, int, int]:
    """Slice items for current page; reset to page 0 when filters change."""
    if st.session_state.get(f"{page_key}_fsig") != filter_sig:
        st.session_state[f"{page_key}_fsig"] = filter_sig
        st.session_state[page_key] = 0
    total_pages = max(1, (len(items) + PAGE_SIZE - 1) // PAGE_SIZE)
    page = max(0, min(st.session_state.get(page_key, 0), total_pages - 1))
    st.session_state[page_key] = page
    return items[page * PAGE_SIZE : (page + 1) * PAGE_SIZE], page, total_pages


def _pagination_controls(page: int, total_pages: int, page_key: str, total_items: int) -> None:
    if total_pages <= 1:
        return
    p1, p2, p3 = st.columns([1, 4, 1])
    if p1.button("← Prev", key=f"{page_key}_prev", disabled=(page == 0)):
        st.session_state[page_key] = page - 1
        st.rerun()
    start = page * PAGE_SIZE + 1
    end   = min((page + 1) * PAGE_SIZE, total_items)
    p2.markdown(
        f"<div style='text-align:center;padding-top:8px;font-size:13px;color:#64748B'>"
        f"Showing <b>{start}–{end}</b> of <b>{total_items}</b> &nbsp;·&nbsp; "
        f"Page <b>{page + 1}</b> of <b>{total_pages}</b></div>",
        unsafe_allow_html=True,
    )
    if p3.button("Next →", key=f"{page_key}_next", disabled=(page == total_pages - 1)):
        st.session_state[page_key] = page + 1
        st.rerun()


def _render_thread(thread: dict):
    if thread["messages"]:
        st.markdown(
            "<p style='font-size:12px;font-weight:600;color:#64748B;margin-bottom:8px'>CONVERSATION THREAD</p>",
            unsafe_allow_html=True,
        )
        for msg in thread["messages"]:
            is_out   = msg.get("direction") == "outbound"
            cls      = "bubble-out" if is_out else "bubble-in"
            lbl      = "Sent by Recruiter" if is_out else "Candidate Reply"
            body_txt = (msg.get("body_text") or "").strip()
            ts       = fmt_dt(msg.get("created_at"))
            st.markdown(_bubble_html(cls, lbl, body_txt, ts), unsafe_allow_html=True)
    else:
        st.info("No messages in this thread yet.")

    status = thread.get("status", {})
    if status:
        fields = {
            "interest_status":      ("Interest",     interest_badge),
            "availability":          ("Availability", None),
            "jd_confirmation":       ("JD Match",     None),
            "matching_skills":       ("Skills",       None),
            "resume_received":       ("Resume",       None),
            "conversation_complete": ("Complete",     None),
        }
        parts = []
        for key, (label, fmt_fn) in fields.items():
            val = status.get(key)
            if val is None:
                continue
            if key in ("resume_received", "conversation_complete"):
                val = "Yes" if val else "No"
            rendered = fmt_fn(val) if fmt_fn and isinstance(val, str) else f"<b>{val}</b>"
            parts.append(f"<span><span style='color:#94A3B8'>{label}:</span> {rendered}</span>")
        if parts:
            st.markdown(f'<div class="status-box">{"".join(parts)}</div>', unsafe_allow_html=True)


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="padding:16px 4px 8px">
        <div style="font-size:26px">📧</div>
        <h2 style="font-size:20px;font-weight:800;margin:4px 0 2px;color:#F8FAFC!important">
            DataFinsight
        </h2>
        <p style="font-size:12px;color:#64748B!important;margin:0">Recruiter Dashboard · Internal</p>
    </div>
    """, unsafe_allow_html=True)

    st.divider()
    st.markdown(
        f"<p style='font-size:11px;color:#475569!important'>Last refresh: "
        f"{datetime.now(timezone.utc).strftime('%H:%M UTC')}</p>",
        unsafe_allow_html=True,
    )

    if st.button("↺  Refresh data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.divider()

    if st.button("⚡  API Health", use_container_width=True):
        with st.spinner("Checking..."):
            h = api.health_check()
        db_ok  = "🟢" if h.get("database") else "🔴"
        ai_ok  = "🟢" if h.get("openai")   else "🔴"
        sg_ok  = "🟢" if h.get("sendgrid") else "🔴"
        status = h.get("status", "unknown")
        st.markdown(f"""
        <div style="background:#1E293B;border-radius:8px;padding:12px;margin-top:8px;font-size:12px">
            <div style="color:#94A3B8;font-size:11px;margin-bottom:6px">API STATUS</div>
            <div>{db_ok} Database</div><div>{ai_ok} OpenAI</div><div>{sg_ok} SendGrid</div>
            <div style="margin-top:8px;font-weight:600;color:{'#22C55E' if status=='ok' else '#EF4444'}">
                {status.upper()}
            </div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        "<p style='font-size:11px;color:#334155!important;text-align:center'>© DataFinsight · Internal Tool</p>",
        unsafe_allow_html=True,
    )


# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_dash, tab_sent, tab_inbox, tab_convs, tab_compose = st.tabs([
    "📊   Dashboard",
    "📤   Sent Emails",
    "📥   Replies",
    "💬   Conversations",
    "✉️   Compose & Test",
])


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1  ·  DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════════
with tab_dash:
    _section_header("Overview", "Live KPIs from Supabase · auto-refreshes every 5 minutes")

    metrics = db.get_dashboard_metrics()
    avg_rt  = db.get_avg_response_time()

    # ── Row 1: Core KPIs ────────────────────────────────────────────────────
    r1c1, r1c2, r1c3, r1c4, r1c5, r1c6 = st.columns(6)
    kpi_card(r1c1, "📤", metrics["total_sent"],            "Emails Sent",        f"{metrics['total_convs']} conversations",    "#2563EB")
    kpi_card(r1c2, "📥", metrics["total_received"],        "Replies Received",   f"{metrics['replied_convs']} threads replied", "#16A34A")
    kpi_card(r1c3, "💬", f"{metrics['response_rate']}%",  "Reply Rate",         "replies ÷ emails sent",                      "#7C3AED")
    kpi_card(r1c4, "👁️", f"{metrics['open_rate']}%",      "Open Rate",          f"{metrics['total_opens']} tracked opens",    "#EA580C")
    kpi_card(r1c5, "⭐", metrics["total_interested"],      "Interested",         f"{metrics['total_unsub']} unsubscribed",     "#0891B2")
    kpi_card(r1c6, "🗂️", metrics["active_campaigns"],     "Active Campaigns",   "jobs with open conversations",               "#059669")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Row 2: Time-period KPIs ──────────────────────────────────────────────
    r2c1, r2c2, r2c3, r2c4, r2c5 = st.columns(5)
    kpi_card(r2c1, "📅", metrics["sent_today"],   "Sent Today",         "outbound emails",           "#3B82F6")
    kpi_card(r2c2, "💌", metrics["recv_today"],   "Replies Today",      "inbound emails",            "#22C55E")
    kpi_card(r2c3, "📆", metrics["sent_week"],    "Sent This Week",     "last 7 days",               "#6366F1")
    kpi_card(r2c4, "📨", metrics["recv_week"],    "Replies This Week",  "last 7 days",               "#10B981")
    kpi_card(r2c5, "⏱️", avg_rt,                  "Avg Response Time",  "first reply after outreach","#F59E0B")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Row 3: Charts ────────────────────────────────────────────────────────
    col_trend, col_jobs = st.columns([3, 2], gap="large")

    with col_trend:
        st.markdown('<div class="sec-title" style="font-size:15px">Daily Activity (30 days)</div>',
                    unsafe_allow_html=True)
        trend = db.get_daily_trend(30)
        if trend:
            df_t = pd.DataFrame(trend)
            df_t["date"] = pd.to_datetime(df_t["date"])
            fig = go.Figure()
            if "outbound" in df_t.columns:
                fig.add_trace(go.Scatter(
                    x=df_t["date"], y=df_t["outbound"], name="Sent",
                    mode="lines+markers", line=dict(color="#3B82F6", width=2.5),
                    marker=dict(size=5), fill="tozeroy", fillcolor="rgba(59,130,246,0.08)",
                ))
            if "inbound" in df_t.columns:
                fig.add_trace(go.Scatter(
                    x=df_t["date"], y=df_t["inbound"], name="Replies",
                    mode="lines+markers", line=dict(color="#22C55E", width=2.5),
                    marker=dict(size=5), fill="tozeroy", fillcolor="rgba(34,197,94,0.08)",
                ))
            fig.update_layout(
                template="plotly_white", height=260,
                margin=dict(l=0, r=0, t=10, b=0),
                legend=dict(orientation="h", y=1.08, x=0),
                xaxis=dict(showgrid=False, title=None),
                yaxis=dict(showgrid=True, gridcolor="#F1F5F9", title=None),
                plot_bgcolor="white", paper_bgcolor="white",
            )
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        else:
            st.info("No email data in the last 30 days.")

    with col_jobs:
        st.markdown('<div class="sec-title" style="font-size:15px">Top Campaigns by Response Rate</div>',
                    unsafe_allow_html=True)
        jstats = db.get_job_stats()
        if jstats:
            top = sorted(jstats, key=lambda x: x["response_rate"], reverse=True)[:10]
            df_j = pd.DataFrame(top)
            df_j["label"] = df_j["job"].apply(lambda x: (x[:26] + "…") if len(x) > 26 else x)
            df_j["rate_color"] = df_j["response_rate"].apply(
                lambda r: "#16A34A" if r >= 30 else "#EA580C" if r >= 10 else "#94A3B8"
            )
            fig2 = go.Figure()
            fig2.add_trace(go.Bar(
                y=df_j["label"], x=df_j["total"], name="Sent",
                orientation="h", marker_color="#DBEAFE", marker_line_width=0,
            ))
            fig2.add_trace(go.Bar(
                y=df_j["label"], x=df_j["replied"], name="Replied",
                orientation="h", marker_color="#22C55E", marker_line_width=0,
            ))
            fig2.update_layout(
                template="plotly_white", height=260, barmode="overlay",
                margin=dict(l=0, r=0, t=10, b=0),
                legend=dict(orientation="h", y=1.08, x=0),
                xaxis=dict(showgrid=True, gridcolor="#F1F5F9", title=None),
                yaxis=dict(showgrid=False, title=None, tickfont=dict(size=11)),
                plot_bgcolor="white", paper_bgcolor="white",
            )
            st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})
        else:
            st.info("No campaign data yet.")

    # # ── Row 4: Campaign stats table ──────────────────────────────────────────
    # st.markdown("<br>", unsafe_allow_html=True)
    # st.markdown('<div class="sec-title" style="font-size:15px">Campaign Performance Summary</div>',
    #             unsafe_allow_html=True)
    # if jstats:
    #     rows_html = ""
    #     for s in jstats:
    #         rc = "#16A34A" if s["response_rate"] >= 30 else "#EA580C" if s["response_rate"] >= 10 else "#6B7280"
    #         jn = (s["job"][:36] + "…") if len(s["job"]) > 36 else s["job"]
    #         rows_html += f"""<tr>
    #             <td style="padding:9px 12px;font-size:13px;font-weight:600;color:#1E293B">{jn}</td>
    #             <td style="padding:9px 12px;font-size:12px;color:#64748B">{s.get('company', _EMPTY)}</td>
    #             <td style="padding:9px 12px;text-align:center;font-size:13px;font-weight:700;color:#2563EB">{s['total']}</td>
    #             <td style="padding:9px 12px;text-align:center;font-size:13px;color:#16A34A">{s['replied']}</td>
    #             <td style="padding:9px 12px;text-align:center;font-size:13px;font-weight:700;color:{rc}">{s['response_rate']}%</td>
    #             <td style="padding:9px 12px;text-align:center;font-size:12px;color:#7C3AED">{s['interested']}</td>
    #         </tr>"""
    #     st.markdown(f"""
    #     <div style="border:1px solid #E2E8F0;border-radius:12px;overflow:hidden;overflow-x:auto">
    #     <table style="width:100%;border-collapse:collapse;background:white;min-width:420px">
    #         <thead><tr style="background:#F8FAFC;border-bottom:1px solid #E2E8F0">
    #             <th style="padding:10px 12px;text-align:left;font-size:11px;font-weight:700;color:#64748B;letter-spacing:.5px;text-transform:uppercase">Campaign</th>
    #             <th style="padding:10px 12px;text-align:left;font-size:11px;font-weight:700;color:#64748B;letter-spacing:.5px;text-transform:uppercase">Company</th>
    #             <th style="padding:10px 12px;text-align:center;font-size:11px;font-weight:700;color:#64748B;letter-spacing:.5px;text-transform:uppercase">Sent</th>
    #             <th style="padding:10px 12px;text-align:center;font-size:11px;font-weight:700;color:#64748B;letter-spacing:.5px;text-transform:uppercase">Replied</th>
    #             <th style="padding:10px 12px;text-align:center;font-size:11px;font-weight:700;color:#64748B;letter-spacing:.5px;text-transform:uppercase">Reply %</th>
    #             <th style="padding:10px 12px;text-align:center;font-size:11px;font-weight:700;color:#64748B;letter-spacing:.5px;text-transform:uppercase">Interested</th>
    #         </tr></thead>
    #         <tbody>{rows_html}</tbody>
    #     </table></div>""", unsafe_allow_html=True)
    # else:
    #     st.info("No campaign data yet.")


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2  ·  SENT EMAILS  (paginated)
# ═══════════════════════════════════════════════════════════════════════════════
with tab_sent:
    _section_header("Sent Emails", "All outbound recruiter emails · 25 per page · click a row for full details")

    all_sent_raw = db.get_sent_emails()
    all_jobs_s   = sorted({e["job"] for e in all_sent_raw if e["job"] != _EMPTY})

    f1, f2, f3 = st.columns([3, 2, 1])
    search_s   = f1.text_input("Search", placeholder="Recipient, campaign, or subject…",
                                label_visibility="collapsed", key="sent_search")
    job_sel_s  = f2.selectbox("Campaign", ["All Campaigns"] + all_jobs_s,
                               label_visibility="collapsed", key="sent_job")
    days_sel_s = f3.selectbox("Period", list(days_map.keys()),
                               label_visibility="collapsed", key="sent_days")

    days_n = days_map[days_sel_s]
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days_n)) if days_n else None

    sent = [
        e for e in all_sent_raw
        if (not search_s or search_s.lower() in
            f"{e['candidate']} {e['job']} {e.get('subject', '')}".lower())
        and (job_sel_s == "All Campaigns" or e["job"] == job_sel_s)
        and _after_cutoff(e.get("sent_at"), cutoff)
    ]

    filter_sig_s = f"{search_s}|{job_sel_s}|{days_sel_s}"
    page_items_s, page_s, total_pages_s = _paginate(sent, "sent_page", filter_sig_s)

    total_s = len(sent)
    st.markdown(
        f"<p style='font-size:12px;color:#64748B;margin:6px 0 14px'>"
        f"<b>{total_s}</b> email{'s' if total_s != 1 else ''} found</p>",
        unsafe_allow_html=True,
    )

    if not sent:
        st.info("No sent emails match your filters.")
    else:
        for email in page_items_s:
            preview  = _body_preview(email.get("body", ""), max_chars=140)
            date_str = fmt_dt(email["sent_at"], short=True)
            label = f"📤  {email['candidate']}  ·  {date_str}"
            if preview:
                label += f"  —  {preview}"

            with st.expander(label, expanded=False):
                row1, row2 = st.columns([3, 1])
                with row1:
                    opened_b = badge("badge-opened", "Opened") if email["opened"] else badge("badge-sent", "Sent")
                    st.markdown(f"""
                    <div style="margin-bottom:6px">
                        <span style="font-size:12px;color:#64748B">To:</span>
                        <span style="font-size:13px;font-weight:600;color:#1E293B;margin-left:6px">{email['candidate']}</span>
                    </div>
                    <div style="margin-bottom:4px">
                        <span style="font-size:12px;color:#64748B">Campaign:</span>
                        <span style="font-size:13px;color:#334155;margin-left:6px">{email['job']}</span>
                        {(' · ' + email['company']) if email['company'] != _EMPTY else ''}
                    </div>
                    <div>
                        <span style="font-size:12px;color:#64748B">Subject:</span>
                        <span style="font-size:13px;color:#334155;margin-left:6px">{email['subject'] or _EMPTY}</span>
                    </div>
                    """, unsafe_allow_html=True)
                with row2:
                    st.markdown(
                        f"<div style='text-align:right'>{opened_b}&nbsp;&nbsp;{conv_badge(email['conv_status'])}</div>",
                        unsafe_allow_html=True,
                    )
                    st.markdown(
                        f"<p style='text-align:right;font-size:11px;color:#94A3B8'>{fmt_dt(email['sent_at'])}</p>",
                        unsafe_allow_html=True,
                    )

                if email.get("body"):
                    st.markdown('<hr class="divider">', unsafe_allow_html=True)
                    with st.expander("Read full email", expanded=False):
                        st.markdown(
                            _bubble_html("bubble-out", "Sent Message", email["body"]),
                            unsafe_allow_html=True,
                        )

                conv_id = email.get("conversation_id")
                if conv_id:
                    with st.expander("View conversation thread", expanded=False):
                        _render_thread(db.get_conversation_thread(conv_id))

        _pagination_controls(page_s, total_pages_s, "sent_page", total_s)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3  ·  REPLIES / INCOMING  (paginated)
# ═══════════════════════════════════════════════════════════════════════════════
with tab_inbox:
    _section_header("Replies & Incoming", "All inbound candidate replies · 25 per page · click a row to view thread")

    all_inbox_raw = db.get_incoming_emails()

    f1i, f2i = st.columns([4, 1])
    search_i = f1i.text_input("Search replies",
                               placeholder="Sender, subject, or content…",
                               label_visibility="collapsed", key="inbox_search")
    days_i   = f2i.selectbox("Period", list(days_map.keys()),
                              label_visibility="collapsed", key="inbox_days")

    days_ni  = days_map[days_i]
    cutoff_i = (datetime.now(timezone.utc) - timedelta(days=days_ni)) if days_ni else None

    inbox = [
        r for r in all_inbox_raw
        if (not search_i or search_i.lower() in
            f"{r['from_email']} {r['job']} {r.get('subject', '')} {r.get('preview', '')}".lower())
        and _after_cutoff(r.get("received_at"), cutoff_i)
    ]

    filter_sig_i = f"{search_i}|{days_i}"
    page_items_i, page_i, total_pages_i = _paginate(inbox, "inbox_page", filter_sig_i)

    total_i = len(inbox)
    st.markdown(
        f"<p style='font-size:12px;color:#64748B;margin:6px 0 14px'>"
        f"<b>{total_i}</b> repl{'ies' if total_i != 1 else 'y'} found</p>",
        unsafe_allow_html=True,
    )

    if not inbox:
        st.info("No replies match your filters.")
    else:
        for reply in page_items_i:
            preview_text = _body_preview(reply.get("body", "") or reply.get("preview", ""), max_chars=140)
            date_str = fmt_dt(reply["received_at"], short=True)
            label = f"📥  {reply['from_email']}  ·  {date_str}"
            if preview_text:
                label += f"  —  {preview_text}"

            with st.expander(label, expanded=False):
                row1, row2 = st.columns([3, 1])
                with row1:
                    st.markdown(f"""
                    <div style="margin-bottom:6px">
                        <span style="font-size:12px;color:#64748B">From:</span>
                        <span style="font-size:13px;font-weight:600;color:#1E293B;margin-left:6px">{reply['from_email']}</span>
                    </div>
                    <div style="margin-bottom:4px">
                        <span style="font-size:12px;color:#64748B">Campaign:</span>
                        <span style="font-size:13px;color:#334155;margin-left:6px">{reply['job']}</span>
                    </div>
                    <div>
                        <span style="font-size:12px;color:#64748B">Subject:</span>
                        <span style="font-size:13px;color:#334155;margin-left:6px">{reply['subject'] or _EMPTY}</span>
                    </div>
                    """, unsafe_allow_html=True)
                with row2:
                    st.markdown(
                        f"<div style='text-align:right'>"
                        f"{match_badge(reply['matched_by'])}&nbsp;&nbsp;{conv_badge(reply['conv_status'])}"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
                    st.markdown(
                        f"<p style='text-align:right;font-size:11px;color:#94A3B8'>{fmt_dt(reply['received_at'])}</p>",
                        unsafe_allow_html=True,
                    )

                conv_id = reply.get("conversation_id")
                if conv_id:
                    with st.expander("View conversation thread", expanded=False):
                        _render_thread(db.get_conversation_thread(conv_id))
                elif reply.get("body"):
                    with st.expander("View message", expanded=False):
                        st.markdown(
                            _bubble_html("bubble-in", "Candidate Message", reply["body"]),
                            unsafe_allow_html=True,
                        )

        _pagination_controls(page_i, total_pages_i, "inbox_page", total_i)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 4  ·  CONVERSATIONS  (replied-only)
# ═══════════════════════════════════════════════════════════════════════════════
with tab_convs:
    _section_header("Conversations", "Conversations where the candidate has replied · expand to view the full thread")

    all_convs_raw = db.get_all_conversations(replied_only=True)
    all_jobs_c    = sorted({c["job"] for c in all_convs_raw if c["job"] != _EMPTY})

    fc1, fc2 = st.columns([4, 2])
    search_c  = fc1.text_input("Search conversations",
                                placeholder="Candidate email or campaign…",
                                label_visibility="collapsed", key="conv_search")
    job_sel_c = fc2.selectbox("Campaign", ["All Campaigns"] + all_jobs_c,
                               label_visibility="collapsed", key="conv_job")

    convs_list = [
        c for c in all_convs_raw
        if (not search_c or search_c.lower() in f"{c['candidate']} {c['job']}".lower())
        and (job_sel_c == "All Campaigns" or c["job"] == job_sel_c)
    ]

    st.markdown(
        f"<p style='font-size:12px;color:#64748B;margin:6px 0 14px'>"
        f"<b>{len(convs_list)}</b> replied conversation{'s' if len(convs_list) != 1 else ''}</p>",
        unsafe_allow_html=True,
    )

    if not convs_list:
        st.info("No replied conversations found.")
    else:
        for conv in convs_list:
            msg_label = f"{conv['message_count']} msg{'s' if conv['message_count'] != 1 else ''}"
            label = (
                f"💬  {conv['candidate']}  ·  {conv['job']}"
                f"  ·  {msg_label}  ·  {fmt_dt(conv['last_activity'], short=True)}"
            )
            with st.expander(label, expanded=False):
                h1, h2 = st.columns([3, 1])
                with h1:
                    token_html = (
                        f'<span class="conv-token">{conv["reference_token"]}</span>'
                        if conv["reference_token"] != _EMPTY else ""
                    )
                    st.markdown(f"""
                    <div style="margin-bottom:6px">
                        <span style="font-size:12px;color:#64748B">Candidate:</span>
                        <span style="font-size:13px;font-weight:600;color:#1E293B;margin-left:6px">{conv['candidate']}</span>
                    </div>
                    <div style="margin-bottom:4px">
                        <span style="font-size:12px;color:#64748B">Campaign:</span>
                        <span style="font-size:13px;color:#334155;margin-left:6px">{conv['job']}</span>
                        {(' · ' + conv['company']) if conv['company'] != _EMPTY else ''}
                    </div>
                    <div style="margin-top:6px">{token_html}</div>
                    """, unsafe_allow_html=True)
                with h2:
                    st.markdown(
                        f"<div style='text-align:right'>{conv_badge(conv['status'])}</div>",
                        unsafe_allow_html=True,
                    )
                    st.markdown(
                        f"<p style='text-align:right;font-size:11px;color:#94A3B8'>"
                        f"Started {fmt_dt(conv['created_at'], short=True)}<br>"
                        f"Last: {fmt_dt(conv['last_activity'], short=True)}</p>",
                        unsafe_allow_html=True,
                    )

                st.markdown('<hr class="divider">', unsafe_allow_html=True)
                _render_thread(db.get_conversation_thread(conv["conversation_id"]))


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 5  ·  COMPOSE & TEST
# ═══════════════════════════════════════════════════════════════════════════════

_DEFAULT_CANDIDATES = [
    {"name": "Shashank", "email": "shashankyadav4858@gmail.com", "work_experience": "5",
     "summary": "AI Engineer with 5 years of experience in machine learning and data science."},
    {"name": "Shashwat", "email": "shashwat1606@gmail.com",      "work_experience": "5",
     "summary": "Investment banker with 5 years of experience in financial analysis and portfolio management."},
    {"name": "Juhi",     "email": "juhi@atypicaladvantage.in",   "work_experience": "2",
     "summary": "Top recruiter with 3 years of experience in sourcing and hiring top talent."},
]

with tab_compose:
    _section_header("Compose & Test")
    st.markdown("""
    <div class="compose-notice">
        ⚠️  <strong>Testing only</strong> — This tab calls the live AI backend.
        Real campaign emails are sent from the production platform, not here.
    </div>""", unsafe_allow_html=True)

    st.markdown("#### Job / Campaign Details")
    col_a, col_b = st.columns(2)
    job_title     = col_a.text_input("Job Title *",     placeholder="e.g. Data Analyst")
    company       = "Atypical Advantage"
    location      = "Remote"
    contact_email = "hiring@atypicaladvantage.in"
    job_desc      = st.text_area("Job Description *",
                                  placeholder="Paste the full job description here…", height=130)

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown("#### Recipients")
    st.caption("Select pre-configured contacts. Use the counter below to add custom recipients.")

    selected_hardcoded: list[dict] = []
    chk_cols = st.columns(len(_DEFAULT_CANDIDATES))
    for col, c in zip(chk_cols, _DEFAULT_CANDIDATES):
        with col:
            if st.checkbox(
                f"**{c['name']}**",
                value=False,
                key=f"hc_{c['name']}",
                help=f"{c['email']}\n{c['summary']}",
            ):
                selected_hardcoded.append(c)

    st.markdown("<br>", unsafe_allow_html=True)
    n_custom = int(st.number_input(
        "Additional recipients", min_value=0, max_value=7, value=0, step=1,
        key="n_custom", help="Number of extra recipients to add below",
    ))

    custom_candidates: list[dict] = []
    if n_custom > 0:
        hc0, hc1, hc2, hc3 = st.columns([2, 2.5, 1, 4])
        hc0.markdown("**Name**"); hc1.markdown("**Email**")
        hc2.markdown("**Exp**");  hc3.markdown("**Summary**")
        for i in range(n_custom):
            rc0, rc1, rc2, rc3 = st.columns([2, 2.5, 1, 4])
            n_v = rc0.text_input("", key=f"cu_n_{i}", placeholder="Full Name")
            e_v = rc1.text_input("", key=f"cu_e_{i}", placeholder="email@example.com")
            x_v = rc2.text_input("", key=f"cu_x_{i}", placeholder="yrs")
            s_v = rc3.text_input("", key=f"cu_s_{i}", placeholder="Brief background…")
            if n_v.strip() and e_v.strip():
                custom_candidates.append({
                    "name": n_v.strip(), "email": e_v.strip(),
                    "work_experience": x_v.strip() or "0", "summary": s_v.strip(),
                })

    all_recipients = selected_hardcoded + custom_candidates

    st.markdown("<br>", unsafe_allow_html=True)

    if st.button("🤖  Generate AI Emails", type="primary", use_container_width=True):
        errors: list[str] = []
        if not job_title.strip():
            errors.append("Job Title is required.")
        if not job_desc.strip():
            errors.append("Job Description is required.")
        if not all_recipients:
            errors.append("Select at least one recipient.")

        if errors:
            for e in errors:
                st.error(e)
        else:
            payload = {
                "job": {
                    "title":         job_title.strip(),
                    "description":   job_desc.strip(),
                    "company_name":  company,
                    "location":      location,
                    "contact_email": contact_email,
                },
                "candidates": [
                    {
                        "id":                        str(i + 1),
                        "name":                      c["name"],
                        "email":                     c["email"],
                        "work_experience":            c.get("work_experience", "0"),
                        "summary":                   c.get("summary", ""),
                        "location_preference":        location,
                        "disability":                "None",
                        "educational_qualification": "Not specified",
                    }
                    for i, c in enumerate(all_recipients)
                ],
            }

            with st.spinner("Generating personalised emails with AI…"):
                result = api.generate_emails(payload)

            if result.get("success"):
                st.session_state["generated_emails"] = result.get("emails", [])
                st.session_state["generated_job_id"] = result.get("job_id")
                st.success(f"Generated {len(st.session_state['generated_emails'])} email(s).")
            else:
                st.error(f"Generation failed: {result.get('error', 'Unknown error')}")
                if result.get("skipped"):
                    with st.expander("Skipped candidates"):
                        st.json(result["skipped"])

    if st.session_state.get("generated_emails"):
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("#### Review & Edit Emails")
        st.caption("Edit subject or body before sending. Changes are applied in this session only.")

        for i, email in enumerate(st.session_state["generated_emails"]):
            with st.expander(f"✉️  {email.get('email', 'Unknown')}  ·  edit", expanded=True):
                email["subject"] = st.text_input(
                    "Subject", value=email.get("subject", ""), key=f"subj_{i}"
                )
                email["body"] = st.text_area(
                    "Body", value=email.get("body", ""), height=220, key=f"body_{i}"
                )

        st.markdown("<br>", unsafe_allow_html=True)

        if st.button("✅  Send All Emails", type="primary", use_container_width=True):
            payload_send = {
                "job_id": st.session_state.get("generated_job_id"),
                "emails": st.session_state["generated_emails"],
            }
            with st.spinner("Sending via SendGrid…"):
                result = api.send_emails(payload_send)

            if result.get("success"):
                sent_count = result.get("sent", len(st.session_state["generated_emails"]))
                st.success(f"Sent {sent_count} email(s) successfully.")
                details = result.get("emails", [])
                if details:
                    rows = []
                    for d in details:
                        rows.append({
                            "Recipient":   d.get("email", _EMPTY),
                            "Sent":        "✅ Yes" if d.get("sent")  else "❌ No",
                            "Saved to DB": "✅ Yes" if d.get("saved") else "❌ No",
                            "Note":        d.get("error") or d.get("skip_reason") or _EMPTY,
                        })
                    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
                st.session_state["generated_emails"] = []
                st.cache_data.clear()
                st.rerun()
            else:
                st.error(f"Send failed: {result.get('error', 'Unknown error')}")
