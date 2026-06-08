import os
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import streamlit as st
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

_SUPABASE_URL = os.getenv("SUPABASE_URL", "")
_SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")


@st.cache_resource
def _client():
    """Singleton Supabase client (cached for the process lifetime)."""
    if not _SUPABASE_URL or not _SUPABASE_KEY:
        logger.warning("SUPABASE_URL / SUPABASE_KEY not set — DB calls will return empty data.")
        return None
    try:
        from supabase import create_client
        return create_client(_SUPABASE_URL, _SUPABASE_KEY)
    except Exception as exc:
        logger.error("Failed to create Supabase client: %s", exc)
        return None


def _safe(res) -> list[dict]:
    """Extract .data list from a Supabase response; return [] on failure."""
    try:
        return res.data or []
    except Exception:
        return []


def _count(res) -> int:
    try:
        return res.count or 0
    except Exception:
        return 0


# ── Dashboard ──────────────────────────────────────────────────────────────

@st.cache_data(ttl=300)
def get_dashboard_metrics() -> dict[str, Any]:
    sb = _client()
    if not sb:
        return _empty_metrics()
    try:
        today_start = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        ).isoformat()
        week_start = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()

        sent_r        = sb.table("conversation_emails").select("id", count="exact").eq("direction", "outbound").execute()
        recv_r        = sb.table("conversation_emails").select("id", count="exact").eq("direction", "inbound").execute()
        conv_r        = sb.table("conversations").select("id", count="exact").execute()
        opens_r       = sb.table("email_opens").select("id", count="exact").execute()
        inter_r       = sb.table("conversation_status").select("id", count="exact").eq("interest_status", "interested").execute()
        unsub_r       = sb.table("email_unsubscribes").select("id", count="exact").execute()
        sent_today_r  = sb.table("conversation_emails").select("id", count="exact").eq("direction", "outbound").gte("created_at", today_start).execute()
        recv_today_r  = sb.table("conversation_emails").select("id", count="exact").eq("direction", "inbound").gte("created_at", today_start).execute()
        sent_week_r   = sb.table("conversation_emails").select("id", count="exact").eq("direction", "outbound").gte("created_at", week_start).execute()
        recv_week_r   = sb.table("conversation_emails").select("id", count="exact").eq("direction", "inbound").gte("created_at", week_start).execute()

        total_sent    = _count(sent_r)
        total_recv    = _count(recv_r)
        total_convs   = _count(conv_r)
        total_opens   = _count(opens_r)
        total_inter   = _count(inter_r)
        total_unsub   = _count(unsub_r)

        replied_rows = _safe(sb.table("conversation_emails")
                               .select("conversation_id")
                               .eq("direction", "inbound")
                               .execute())
        replied_convs = len({r["conversation_id"] for r in replied_rows if r.get("conversation_id")})

        active_rows = _safe(sb.table("conversations").select("job_id").eq("status", "open").execute())
        active_campaigns = len({r["job_id"] for r in active_rows if r.get("job_id")})

        open_rate     = round(total_opens / total_sent * 100, 1) if total_sent else 0.0
        response_rate = round(replied_convs / total_sent * 100, 1) if total_sent else 0.0

        return {
            "total_sent":        total_sent,
            "total_received":    total_recv,
            "total_convs":       total_convs,
            "total_opens":       total_opens,
            "total_interested":  total_inter,
            "total_unsub":       total_unsub,
            "replied_convs":     replied_convs,
            "open_rate":         open_rate,
            "response_rate":     response_rate,
            "sent_today":        _count(sent_today_r),
            "recv_today":        _count(recv_today_r),
            "sent_week":         _count(sent_week_r),
            "recv_week":         _count(recv_week_r),
            "active_campaigns":  active_campaigns,
        }
    except Exception as exc:
        logger.exception("get_dashboard_metrics failed: %s", exc)
        return _empty_metrics()


def _empty_metrics():
    return {k: 0 for k in [
        "total_sent", "total_received", "total_convs", "total_opens",
        "total_interested", "total_unsub", "replied_convs", "open_rate", "response_rate",
        "sent_today", "recv_today", "sent_week", "recv_week", "active_campaigns",
    ]}


@st.cache_data(ttl=300)
def get_avg_response_time() -> str:
    """Average time between first outbound and first inbound per conversation, human-readable."""
    sb = _client()
    if not sb:
        return "—"
    try:
        rows = _safe(sb.table("conversation_emails")
                       .select("conversation_id, direction, created_at")
                       .order("created_at", desc=False)
                       .execute())
        first_out: dict[str, str] = {}
        first_in:  dict[str, str] = {}
        for r in rows:
            cid = r.get("conversation_id")
            if not cid:
                continue
            if r.get("direction") == "outbound" and cid not in first_out:
                first_out[cid] = r["created_at"]
            elif r.get("direction") == "inbound" and cid not in first_in:
                first_in[cid] = r["created_at"]

        deltas = []
        for cid, out_ts in first_out.items():
            if cid in first_in:
                try:
                    t_out = datetime.fromisoformat(out_ts.replace("Z", "+00:00"))
                    t_in  = datetime.fromisoformat(first_in[cid].replace("Z", "+00:00"))
                    delta = (t_in - t_out).total_seconds()
                    if delta > 0:
                        deltas.append(delta)
                except Exception:
                    pass

        if not deltas:
            return "—"
        avg = sum(deltas) / len(deltas)
        if avg < 3600:
            return f"{int(avg / 60)}m"
        if avg < 86400:
            return f"{avg / 3600:.1f}h"
        return f"{avg / 86400:.1f}d"
    except Exception as exc:
        logger.exception("get_avg_response_time failed: %s", exc)
        return "—"


@st.cache_data(ttl=300)
def get_daily_trend(days: int = 30) -> list[dict]:
    sb = _client()
    if not sb:
        return []
    try:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        rows = _safe(sb.table("conversation_emails")
                       .select("direction, created_at")
                       .gte("created_at", cutoff)
                       .execute())
        if not rows:
            return []

        import pandas as pd
        df = pd.DataFrame(rows)
        df["date"] = pd.to_datetime(df["created_at"], utc=True).dt.date
        pivot = (df.groupby(["date", "direction"])
                   .size()
                   .unstack(fill_value=0)
                   .reset_index())
        pivot.columns.name = None
        for col in ["outbound", "inbound"]:
            if col not in pivot.columns:
                pivot[col] = 0
        return pivot.to_dict("records")
    except Exception as exc:
        logger.exception("get_daily_trend failed: %s", exc)
        return []


@st.cache_data(ttl=300)
def get_job_stats() -> list[dict]:
    """Per-job: outreach count, replies, response rate."""
    sb = _client()
    if not sb:
        return []
    try:
        convs = _safe(sb.table("conversations")
                        .select("id, job_id, jobs(title, company_name)")
                        .execute())
        emails = _safe(sb.table("conversation_emails")
                         .select("conversation_id, direction")
                         .execute())
        statuses = _safe(sb.table("conversation_status")
                           .select("conversation_id, interest_status")
                           .execute())

        # Build lookup tables
        inbound_conv_ids = {e["conversation_id"] for e in emails if e.get("direction") == "inbound" and e.get("conversation_id")}
        interested_conv_ids = {s["conversation_id"] for s in statuses if s.get("interest_status") == "interested"}

        stats: dict[str, dict] = {}
        for c in convs:
            jid = c.get("job_id") or "unknown"
            job = c.get("jobs") or {}
            if jid not in stats:
                stats[jid] = {
                    "job":      job.get("title", "—"),
                    "company":  job.get("company_name") or "—",
                    "total":    0,
                    "replied":  0,
                    "interested": 0,
                }
            stats[jid]["total"] += 1
            cid = c.get("id")
            if cid in inbound_conv_ids:
                stats[jid]["replied"] += 1
            if cid in interested_conv_ids:
                stats[jid]["interested"] += 1

        result = []
        for s in stats.values():
            s["response_rate"] = round(s["replied"] / s["total"] * 100, 1) if s["total"] else 0.0
            result.append(s)

        return sorted(result, key=lambda x: x["total"], reverse=True)[:15]
    except Exception as exc:
        logger.exception("get_job_stats failed: %s", exc)
        return []


@st.cache_data(ttl=60)
def get_recent_activity(limit: int = 12) -> list[dict]:
    sb = _client()
    if not sb:
        return []
    try:
        rows = _safe(sb.table("conversation_emails")
                       .select("direction, subject, body_text, from_email, to_email, created_at, "
                               "conversations(jobs(title), candidates(email))")
                       .order("created_at", desc=True)
                       .limit(limit)
                       .execute())
        result = []
        for r in rows:
            conv  = r.get("conversations") or {}
            job   = conv.get("jobs")        or {}
            cand  = conv.get("candidates")  or {}
            email = cand.get("email") or r.get("to_email") or r.get("from_email") or "—"
            result.append({
                "direction":  r.get("direction", "—"),
                "subject":    r.get("subject",   "—"),
                "body":       r.get("body_text", ""),
                "email":      email,
                "job":        job.get("title", "—"),
                "created_at": r.get("created_at"),
            })
        return result
    except Exception as exc:
        logger.exception("get_recent_activity failed: %s", exc)
        return []


# ── Sent Emails ────────────────────────────────────────────────────────────

@st.cache_data(ttl=120)
def get_sent_emails(search: str = "", job_filter: str = "", days: int = 0) -> list[dict]:
    sb = _client()
    if not sb:
        return []
    try:
        q = (sb.table("conversation_emails")
               .select("id, subject, body_text, to_email, created_at, "
                       "conversation_id, "
                       "conversations(id, status, reference_token, "
                       "  jobs(title, company_name), candidates(email))")
               .eq("direction", "outbound")
               .order("created_at", desc=True))
        if days:
            cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
            q = q.gte("created_at", cutoff)
        rows = _safe(q.execute())

        # Fetch opened conversation IDs
        opened = {r["conversation_id"] for r in _safe(
            sb.table("email_opens").select("conversation_id").execute()
        ) if r.get("conversation_id")}

        result = []
        for r in rows:
            conv    = r.get("conversations") or {}
            job     = conv.get("jobs")        or {}
            cand    = conv.get("candidates")  or {}
            job_t   = job.get("title",       "—")
            company = job.get("company_name") or "—"
            c_email = cand.get("email") or r.get("to_email") or "—"
            conv_id = conv.get("id") or r.get("conversation_id")

            if search:
                haystack = f"{c_email} {job_t} {r.get('subject','')}".lower()
                if search.lower() not in haystack:
                    continue
            if job_filter and job_t != job_filter:
                continue

            result.append({
                "candidate":      c_email,
                "job":            job_t,
                "company":        company,
                "subject":        r.get("subject", "—"),
                "body":           r.get("body_text", ""),
                "sent_at":        r.get("created_at"),
                "conv_status":    conv.get("status", "open"),
                "opened":         conv_id in opened,
                "reference_token": conv.get("reference_token", "—"),
                "conversation_id": conv_id,
            })
        return result
    except Exception as exc:
        logger.exception("get_sent_emails failed: %s", exc)
        return []


# ── Incoming Emails ────────────────────────────────────────────────────────

@st.cache_data(ttl=60)
def get_incoming_emails(search: str = "", days: int = 0) -> list[dict]:
    sb = _client()
    if not sb:
        return []
    try:
        q = (sb.table("conversation_emails")
               .select("id, subject, body_text, from_email, created_at, matched_by, "
                       "conversation_id, "
                       "conversations(id, status, reference_token, "
                       "  jobs(title, company_name), candidates(email))")
               .eq("direction", "inbound")
               .order("created_at", desc=True))
        if days:
            cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
            q = q.gte("created_at", cutoff)
        rows = _safe(q.execute())

        result = []
        for r in rows:
            conv    = r.get("conversations") or {}
            job     = conv.get("jobs")        or {}
            cand    = conv.get("candidates")  or {}
            job_t   = job.get("title", "—")
            preview = (r.get("body_text") or "")[:180].replace("\n", " ")

            if search:
                haystack = f"{r.get('from_email','')} {job_t} {r.get('subject','')} {preview}".lower()
                if search.lower() not in haystack:
                    continue

            result.append({
                "from_email":     r.get("from_email", "—"),
                "job":            job_t,
                "company":        job.get("company_name") or "—",
                "subject":        r.get("subject", "—"),
                "preview":        preview,
                "body":           r.get("body_text", ""),
                "received_at":    r.get("created_at"),
                "matched_by":     r.get("matched_by") or "none",
                "conv_status":    conv.get("status", "—"),
                "conversation_id": conv.get("id") or r.get("conversation_id"),
            })
        return result
    except Exception as exc:
        logger.exception("get_incoming_emails failed: %s", exc)
        return []


# ── Conversation thread ────────────────────────────────────────────────────

@st.cache_data(ttl=60)
def get_conversation_thread(conversation_id: str) -> dict:
    sb = _client()
    if not sb or not conversation_id:
        return {"messages": [], "status": {}}
    try:
        msgs = _safe(sb.table("conversation_emails")
                       .select("direction, subject, body_text, created_at, from_email, to_email")
                       .eq("conversation_id", conversation_id)
                       .order("created_at", desc=False)
                       .execute())

        status_rows = _safe(sb.table("conversation_status")
                              .select("interest_status, availability, jd_confirmation, "
                                      "resume_received, conversation_complete, closed_reason, "
                                      "matching_skills, gaps")
                              .eq("conversation_id", conversation_id)
                              .execute())
        status = status_rows[0] if status_rows else {}
        return {"messages": msgs, "status": status}
    except Exception as exc:
        logger.exception("get_conversation_thread failed: %s", exc)
        return {"messages": [], "status": {}}


# ── Job list (for filters / compose) ──────────────────────────────────────

@st.cache_data(ttl=300)
def get_all_jobs() -> list[dict]:
    sb = _client()
    if not sb:
        return []
    try:
        rows = _safe(sb.table("jobs")
                       .select("id, title, company_name, description, location, contact_email, status")
                       .order("created_at", desc=True)
                       .execute())
        return rows
    except Exception as exc:
        logger.exception("get_all_jobs failed: %s", exc)
        return []


# ── All conversations (for Conversations tab) ──────────────────────────────

@st.cache_data(ttl=60)
def get_all_conversations(search: str = "", job_filter: str = "", replied_only: bool = False) -> list[dict]:
    """All conversations with metadata: candidate, job, message count, last activity."""
    sb = _client()
    if not sb:
        return []
    try:
        convs = _safe(sb.table("conversations")
                        .select("id, status, reference_token, created_at, "
                                "jobs(title, company_name), candidates(email)")
                        .order("created_at", desc=True)
                        .execute())
        emails = _safe(sb.table("conversation_emails")
                         .select("conversation_id, direction, created_at")
                         .execute())

        stats: dict[str, dict] = {}
        for e in emails:
            cid = e.get("conversation_id")
            if not cid:
                continue
            s = stats.setdefault(cid, {"count": 0, "last_at": None, "has_reply": False})
            s["count"] += 1
            if e.get("direction") == "inbound":
                s["has_reply"] = True
            if s["last_at"] is None or (e.get("created_at") or "") > s["last_at"]:
                s["last_at"] = e.get("created_at")

        result = []
        for c in convs:
            job   = c.get("jobs")       or {}
            cand  = c.get("candidates") or {}
            job_t = job.get("title", "—")
            email = cand.get("email", "—")

            if search:
                hay = f"{email} {job_t}".lower()
                if search.lower() not in hay:
                    continue
            if job_filter and job_t != job_filter:
                continue

            cid  = c.get("id")
            stat = stats.get(cid, {})
            if replied_only and not stat.get("has_reply", False):
                continue

            result.append({
                "conversation_id": cid,
                "candidate":       email,
                "job":             job_t,
                "company":         job.get("company_name") or "—",
                "status":          c.get("status", "open"),
                "reference_token": c.get("reference_token", "—"),
                "created_at":      c.get("created_at"),
                "last_activity":   stat.get("last_at") or c.get("created_at"),
                "message_count":   stat.get("count", 0),
                "has_reply":       stat.get("has_reply", False),
            })
        return result
    except Exception as exc:
        logger.exception("get_all_conversations failed: %s", exc)
        return []
