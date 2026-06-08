"""Tests for src/db.py — Supabase client and streamlit are mocked throughout."""
import sys
import os
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ── Mock streamlit before src.db is imported ───────────────────────────────────
_st = MagicMock()


def _cache_passthrough(func=None, **kwargs):
    """Replaces st.cache_data / st.cache_resource: passes the function through
    unchanged but adds a no-op .clear() method so tests can call fn.clear()."""
    if func is not None:
        func.clear = MagicMock()
        return func

    def decorator(f):
        f.clear = MagicMock()
        return f

    return decorator


_st.cache_data = _cache_passthrough
_st.cache_resource = _cache_passthrough
sys.modules["streamlit"] = _st
# ──────────────────────────────────────────────────────────────────────────────


def _mock_response(data: list, count: int = 0) -> MagicMock:
    r = MagicMock()
    r.data = data
    r.count = count
    return r


def _make_chain(rows: list) -> MagicMock:
    """A query chain mock where any call returns itself and .execute() → rows."""
    chain = MagicMock()
    terminal = _mock_response(rows, len(rows))
    for method in ("select", "eq", "gte", "order", "limit"):
        getattr(chain, method).return_value = chain
    chain.execute.return_value = terminal
    return chain


def _make_sb(table_data: dict | None = None) -> MagicMock:
    table_data = table_data or {}
    sb = MagicMock()
    sb.table.side_effect = lambda name: _make_chain(table_data.get(name, []))
    return sb


class TestSafe(unittest.TestCase):
    def test_returns_data(self):
        from src.db import _safe
        r = _mock_response([{"id": 1}])
        self.assertEqual(_safe(r), [{"id": 1}])

    def test_returns_empty_on_none(self):
        from src.db import _safe
        self.assertEqual(_safe(None), [])


class TestCount(unittest.TestCase):
    def test_returns_count(self):
        from src.db import _count
        r = _mock_response([], count=7)
        self.assertEqual(_count(r), 7)

    def test_returns_zero_on_none(self):
        from src.db import _count
        self.assertEqual(_count(None), 0)


class TestGetDashboardMetrics(unittest.TestCase):
    def test_no_client_returns_zeros(self):
        from src.db import get_dashboard_metrics
        with patch("src.db._client", return_value=None):
            get_dashboard_metrics.clear()
            result = get_dashboard_metrics()
        self.assertEqual(result["total_sent"], 0)
        self.assertEqual(result["open_rate"], 0)

    def test_computes_open_and_response_rates(self):
        # 1 row in conversation_emails (unfiltered count = 1 for all direction queries),
        # 1 open, 1 inbound with conversation_id "c1"
        # open_rate = 1/1 * 100 = 100.0, response_rate = 1 unique / 1 = 100.0
        sb = _make_sb({
            "conversation_emails": [{"id": "e1", "direction": "outbound", "conversation_id": "c1"}],
            "conversations":       [{"id": "c1"}],
            "email_opens":         [{"id": "o1"}],
            "conversation_status": [{"id": "s1", "interest_status": "interested"}],
            "email_unsubscribes":  [],
        })
        from src.db import get_dashboard_metrics
        with patch("src.db._client", return_value=sb):
            get_dashboard_metrics.clear()
            result = get_dashboard_metrics()
        self.assertEqual(result["open_rate"], 100.0)
        self.assertEqual(result["response_rate"], 100.0)
        self.assertGreaterEqual(result["total_sent"], 1)


class TestGetAllJobs(unittest.TestCase):
    def test_returns_jobs(self):
        jobs = [{"id": "j1", "title": "Engineer", "company_name": "Acme"}]
        sb = _make_sb({"jobs": jobs})
        from src.db import get_all_jobs
        with patch("src.db._client", return_value=sb):
            get_all_jobs.clear()
            result = get_all_jobs()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["title"], "Engineer")

    def test_no_client_returns_empty(self):
        from src.db import get_all_jobs
        with patch("src.db._client", return_value=None):
            get_all_jobs.clear()
            result = get_all_jobs()
        self.assertEqual(result, [])


class TestGetConversationThread(unittest.TestCase):
    def test_empty_id_returns_empty(self):
        from src.db import get_conversation_thread
        with patch("src.db._client", return_value=MagicMock()):
            get_conversation_thread.clear()
            result = get_conversation_thread("")
        self.assertEqual(result["messages"], [])

    def test_no_client_returns_empty(self):
        from src.db import get_conversation_thread
        with patch("src.db._client", return_value=None):
            get_conversation_thread.clear()
            result = get_conversation_thread("conv-123")
        self.assertEqual(result["messages"], [])

    def test_returns_messages_and_status(self):
        msgs = [{"direction": "outbound", "subject": "Hello", "body_text": "Hi"}]
        statuses = [{"interest_status": "interested"}]
        sb = _make_sb({
            "conversation_emails": msgs,
            "conversation_status": statuses,
        })
        from src.db import get_conversation_thread
        with patch("src.db._client", return_value=sb):
            get_conversation_thread.clear()
            result = get_conversation_thread("conv-123")
        self.assertEqual(len(result["messages"]), 1)
        self.assertEqual(result["status"]["interest_status"], "interested")


class TestGetAvgResponseTime(unittest.TestCase):
    def test_no_client_returns_dash(self):
        from src.db import get_avg_response_time
        with patch("src.db._client", return_value=None):
            get_avg_response_time.clear()
            result = get_avg_response_time()
        self.assertEqual(result, "—")

    def test_no_replies_returns_dash(self):
        sb = _make_sb({
            "conversation_emails": [
                {"conversation_id": "c1", "direction": "outbound", "created_at": "2024-01-01T10:00:00Z"},
            ],
        })
        from src.db import get_avg_response_time
        with patch("src.db._client", return_value=sb):
            get_avg_response_time.clear()
            result = get_avg_response_time()
        self.assertEqual(result, "—")

    def test_returns_formatted_minutes(self):
        sb = _make_sb({
            "conversation_emails": [
                {"conversation_id": "c1", "direction": "outbound", "created_at": "2024-01-01T10:00:00+00:00"},
                {"conversation_id": "c1", "direction": "inbound",  "created_at": "2024-01-01T10:30:00+00:00"},
            ],
        })
        from src.db import get_avg_response_time
        with patch("src.db._client", return_value=sb):
            get_avg_response_time.clear()
            result = get_avg_response_time()
        self.assertRegex(result, r"^\d+m$")


if __name__ == "__main__":
    unittest.main()
