"""Integration tests: end-to-end flow tests for all major app functions.

These tests validate module imports, DB function contracts, API flow,
and the shape of data returned by every public DB function.
Supabase and HTTP calls are mocked — no live credentials required.
Run with: python3.11 -m pytest tests/integration_test.py -v
"""
import sys
import os
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ── Mock streamlit before src imports ─────────────────────────────────────────
_st = MagicMock()


def _cache_passthrough(func=None, **kwargs):
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


def _http_response(json_data: dict, status_code: int = 200) -> MagicMock:
    r = MagicMock()
    r.status_code = status_code
    r.json.return_value = json_data
    if status_code >= 400:
        from requests.exceptions import HTTPError
        r.raise_for_status.side_effect = HTTPError(response=r)
    else:
        r.raise_for_status.return_value = None
    return r


# ─────────────────────────────────────────────────────────────────────────────
# 1. Smoke: module imports
# ─────────────────────────────────────────────────────────────────────────────
class TestModuleImports(unittest.TestCase):
    def test_import_db(self):
        import src.db
        self.assertTrue(hasattr(src.db, "get_dashboard_metrics"))
        self.assertTrue(hasattr(src.db, "get_sent_emails"))
        self.assertTrue(hasattr(src.db, "get_incoming_emails"))
        self.assertTrue(hasattr(src.db, "get_all_conversations"))
        self.assertTrue(hasattr(src.db, "get_conversation_thread"))
        self.assertTrue(hasattr(src.db, "get_all_jobs"))

    def test_import_api(self):
        import src.api
        self.assertTrue(hasattr(src.api, "health_check"))
        self.assertTrue(hasattr(src.api, "generate_emails"))
        self.assertTrue(hasattr(src.api, "send_emails"))

    def test_import_auth(self):
        import src.auth
        self.assertTrue(hasattr(src.auth, "check_password"))


# ─────────────────────────────────────────────────────────────────────────────
# 2. DB: client creation — no env vars → returns None gracefully
# ─────────────────────────────────────────────────────────────────────────────
class TestDBClientCreation(unittest.TestCase):
    def test_no_env_vars_returns_none(self):
        # _SUPABASE_URL / _SUPABASE_KEY are module-level constants read at import time;
        # patch them directly rather than via os.environ
        import src.db as _db
        with patch.object(_db, "_SUPABASE_URL", ""), patch.object(_db, "_SUPABASE_KEY", ""):
            _db._client.clear()
            result = _db._client()
        self.assertIsNone(result)


# ─────────────────────────────────────────────────────────────────────────────
# 3. DB: all public functions return safe empty values without a client
# ─────────────────────────────────────────────────────────────────────────────
class TestDBEmptyReturns(unittest.TestCase):
    def setUp(self):
        import src.db as _db
        self._db = _db

    def _clear_all(self):
        for fn in (
            self._db.get_dashboard_metrics,
            self._db.get_daily_trend,
            self._db.get_job_stats,
            self._db.get_recent_activity,
            self._db.get_sent_emails,
            self._db.get_incoming_emails,
            self._db.get_all_jobs,
            self._db.get_all_conversations,
            self._db.get_conversation_thread,
        ):
            fn.clear()

    def test_dashboard_metrics_no_client(self):
        with patch("src.db._client", return_value=None):
            self._clear_all()
            result = self._db.get_dashboard_metrics()
        self.assertIsInstance(result, dict)
        for key in ("total_sent", "total_received", "open_rate", "response_rate"):
            self.assertIn(key, result)

    def test_sent_emails_no_client(self):
        with patch("src.db._client", return_value=None):
            self._clear_all()
            result = self._db.get_sent_emails()
        self.assertEqual(result, [])

    def test_incoming_emails_no_client(self):
        with patch("src.db._client", return_value=None):
            self._clear_all()
            result = self._db.get_incoming_emails()
        self.assertEqual(result, [])

    def test_all_conversations_no_client(self):
        with patch("src.db._client", return_value=None):
            self._clear_all()
            result = self._db.get_all_conversations()
        self.assertEqual(result, [])

    def test_conversation_thread_no_client(self):
        with patch("src.db._client", return_value=None):
            self._clear_all()
            result = self._db.get_conversation_thread("any-id")
        self.assertEqual(result["messages"], [])

    def test_all_jobs_no_client(self):
        with patch("src.db._client", return_value=None):
            self._clear_all()
            result = self._db.get_all_jobs()
        self.assertEqual(result, [])


# ─────────────────────────────────────────────────────────────────────────────
# 4. Dashboard: metrics shape always has all 9 required keys
# ─────────────────────────────────────────────────────────────────────────────
class TestDashboardLoading(unittest.TestCase):
    _REQUIRED_KEYS = {
        "total_sent", "total_received", "total_convs", "total_opens",
        "total_interested", "total_unsub", "replied_convs",
        "open_rate", "response_rate",
    }

    def test_metrics_shape_with_data(self):
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
        self.assertEqual(set(result.keys()), self._REQUIRED_KEYS)

    def test_metrics_shape_empty_db(self):
        with patch("src.db._client", return_value=None):
            from src.db import get_dashboard_metrics
            get_dashboard_metrics.clear()
            result = get_dashboard_metrics()
        self.assertEqual(set(result.keys()), self._REQUIRED_KEYS)


# ─────────────────────────────────────────────────────────────────────────────
# 5. Conversation tab: get_all_conversations() shape and search filter
# ─────────────────────────────────────────────────────────────────────────────
class TestConversationsTab(unittest.TestCase):
    _REQUIRED_KEYS = {
        "conversation_id", "candidate", "job", "company",
        "status", "reference_token", "created_at",
        "last_activity", "message_count", "has_reply",
    }

    def _run(self, search="", job_filter=""):
        sb = _make_sb({
            "conversations": [
                {"id": "c1", "status": "open", "reference_token": "AA-0001", "created_at": "2024-01-01T10:00:00Z",
                 "jobs": {"title": "Engineer", "company_name": "Acme"},
                 "candidates": {"email": "alice@example.com"}},
                {"id": "c2", "status": "closed", "reference_token": "AA-0002", "created_at": "2024-01-02T10:00:00Z",
                 "jobs": {"title": "Designer", "company_name": "Beta"},
                 "candidates": {"email": "bob@example.com"}},
            ],
            "conversation_emails": [
                {"conversation_id": "c1", "direction": "outbound", "created_at": "2024-01-01T10:00:00Z"},
                {"conversation_id": "c1", "direction": "inbound",  "created_at": "2024-01-01T11:00:00Z"},
                {"conversation_id": "c2", "direction": "outbound", "created_at": "2024-01-02T10:00:00Z"},
            ],
        })
        from src.db import get_all_conversations
        with patch("src.db._client", return_value=sb):
            get_all_conversations.clear()
            return get_all_conversations(search=search, job_filter=job_filter)

    def test_returns_list_with_required_keys(self):
        result = self._run()
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)
        for item in result:
            self.assertEqual(set(item.keys()), self._REQUIRED_KEYS)

    def test_message_count_and_has_reply(self):
        result = self._run()
        c1 = next(r for r in result if r["conversation_id"] == "c1")
        self.assertEqual(c1["message_count"], 2)
        self.assertTrue(c1["has_reply"])

    def test_no_reply_flagged_correctly(self):
        result = self._run()
        c2 = next(r for r in result if r["conversation_id"] == "c2")
        self.assertFalse(c2["has_reply"])

    def test_search_filter_by_email(self):
        result = self._run(search="alice")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["candidate"], "alice@example.com")

    def test_search_filter_by_job(self):
        result = self._run(search="designer")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["job"], "Designer")

    def test_job_filter(self):
        result = self._run(job_filter="Engineer")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["job"], "Engineer")

    def test_no_client_returns_empty(self):
        with patch("src.db._client", return_value=None):
            from src.db import get_all_conversations
            get_all_conversations.clear()
            result = get_all_conversations()
        self.assertEqual(result, [])


# ─────────────────────────────────────────────────────────────────────────────
# 6. Email sending flow: generate then send
# ─────────────────────────────────────────────────────────────────────────────
class TestEmailSendingFlow(unittest.TestCase):
    JOB = {"title": "Data Analyst", "description": "Analyze data", "company_name": "Acme",
           "location": "Delhi", "contact_email": "jobs@acme.com"}
    CANDIDATES = [{"id": "1", "name": "Alice", "email": "alice@example.com",
                   "work_experience": "3", "summary": "Data professional",
                   "location_preference": "Delhi", "disability": "None",
                   "educational_qualification": "Masters"}]

    @patch("requests.post")
    def test_generate_success_and_send(self, mock_post):
        gen_response = {"success": True, "job_id": "job-abc", "emails": [
            {"email": "alice@example.com", "subject": "Re: Data Analyst", "body": "Dear Alice…", "conversation_id": "conv-1"}
        ]}
        send_response = {"success": True, "sent": 1, "emails": [
            {"email": "alice@example.com", "sent": True, "saved": True}
        ]}
        mock_post.side_effect = [
            _http_response(gen_response),
            _http_response(send_response),
        ]

        from src import api
        with patch.object(api, "_BASE", "https://fn.example.com/api"):
            gen_result = api.generate_emails({"job": self.JOB, "candidates": self.CANDIDATES})
            self.assertTrue(gen_result["success"])
            self.assertEqual(gen_result["job_id"], "job-abc")
            self.assertEqual(len(gen_result["emails"]), 1)

            send_result = api.send_emails({"job_id": gen_result["job_id"], "emails": gen_result["emails"]})
            self.assertTrue(send_result["success"])
            self.assertEqual(send_result["sent"], 1)

    @patch("requests.post")
    def test_generate_payload_shape(self, mock_post):
        mock_post.return_value = _http_response({"success": True, "job_id": "j1", "emails": []})
        from src import api
        with patch.object(api, "_BASE", "https://fn.example.com/api"):
            api.generate_emails({"job": self.JOB, "candidates": self.CANDIDATES})
        call_kwargs = mock_post.call_args
        sent_json = call_kwargs[1]["json"] if call_kwargs[1] else call_kwargs[0][1]
        self.assertIn("job", sent_json)
        self.assertIn("candidates", sent_json)
        self.assertEqual(sent_json["job"]["title"], "Data Analyst")

    def test_generate_fails_without_base_url(self):
        from src import api
        with patch.object(api, "_BASE", ""):
            result = api.generate_emails({"job": self.JOB, "candidates": self.CANDIDATES})
        self.assertFalse(result["success"])
        self.assertIn("FUNCTION_BASE", result["error"])


# ─────────────────────────────────────────────────────────────────────────────
# 7. Email tracking: open rate and response rate calculation
# ─────────────────────────────────────────────────────────────────────────────
class TestEmailTrackingFlow(unittest.TestCase):
    def test_open_rate_calculated_from_sends_and_opens(self):
        sb = _make_sb({
            "conversation_emails": [
                {"id": "e1", "direction": "outbound", "conversation_id": "c1"},
            ],
            "conversations":       [{"id": "c1"}],
            "email_opens":         [{"id": "o1", "conversation_id": "c1"}],
            "conversation_status": [],
            "email_unsubscribes":  [],
        })
        from src.db import get_dashboard_metrics
        with patch("src.db._client", return_value=sb):
            get_dashboard_metrics.clear()
            metrics = get_dashboard_metrics()
        self.assertEqual(metrics["open_rate"], 100.0)

    def test_response_rate_calculated_from_replies(self):
        # Mock can't filter by direction, so use 1 row only.
        # total_sent (unfiltered count) = 1, replied_convs (unique inbound conv_ids) = 1
        # → response_rate = 1/1 * 100 = 100.0
        sb = _make_sb({
            "conversation_emails": [
                {"id": "e1", "direction": "outbound", "conversation_id": "c1"},
            ],
            "conversations":       [{"id": "c1"}],
            "email_opens":         [],
            "conversation_status": [],
            "email_unsubscribes":  [],
        })
        from src.db import get_dashboard_metrics
        with patch("src.db._client", return_value=sb):
            get_dashboard_metrics.clear()
            metrics = get_dashboard_metrics()
        self.assertEqual(metrics["response_rate"], 100.0)


# ─────────────────────────────────────────────────────────────────────────────
# 8. Conversations tab: replied_only filter
# ─────────────────────────────────────────────────────────────────────────────
class TestConversationsTabRepliedOnly(unittest.TestCase):
    def _setup_sb(self):
        return _make_sb({
            "conversations": [
                {"id": "c1", "status": "open", "reference_token": "AA-0001", "created_at": "2024-01-01T10:00:00Z",
                 "jobs": {"title": "Engineer", "company_name": "Acme"},
                 "candidates": {"email": "alice@example.com"}},
                {"id": "c2", "status": "open", "reference_token": "AA-0002", "created_at": "2024-01-02T10:00:00Z",
                 "jobs": {"title": "Designer", "company_name": "Beta"},
                 "candidates": {"email": "bob@example.com"}},
                {"id": "c3", "status": "open", "reference_token": "AA-0003", "created_at": "2024-01-03T10:00:00Z",
                 "jobs": {"title": "Manager", "company_name": "Gamma"},
                 "candidates": {"email": "carol@example.com"}},
            ],
            "conversation_emails": [
                {"conversation_id": "c1", "direction": "outbound", "created_at": "2024-01-01T10:00:00Z"},
                {"conversation_id": "c1", "direction": "inbound",  "created_at": "2024-01-01T11:00:00Z"},
                {"conversation_id": "c2", "direction": "outbound", "created_at": "2024-01-02T10:00:00Z"},
                {"conversation_id": "c2", "direction": "inbound",  "created_at": "2024-01-02T12:00:00Z"},
                {"conversation_id": "c3", "direction": "outbound", "created_at": "2024-01-03T10:00:00Z"},
                # c3 has no inbound — outbound-only
            ],
        })

    def test_replied_only_filters_outbound_only(self):
        sb = self._setup_sb()
        from src.db import get_all_conversations
        with patch("src.db._client", return_value=sb):
            get_all_conversations.clear()
            result = get_all_conversations(replied_only=True)
        self.assertEqual(len(result), 2)
        ids = {r["conversation_id"] for r in result}
        self.assertIn("c1", ids)
        self.assertIn("c2", ids)
        self.assertNotIn("c3", ids)

    def test_all_returns_all_when_not_replied_only(self):
        sb = self._setup_sb()
        from src.db import get_all_conversations
        with patch("src.db._client", return_value=sb):
            get_all_conversations.clear()
            result = get_all_conversations(replied_only=False)
        self.assertEqual(len(result), 3)

    def test_replied_only_all_have_has_reply_true(self):
        sb = self._setup_sb()
        from src.db import get_all_conversations
        with patch("src.db._client", return_value=sb):
            get_all_conversations.clear()
            result = get_all_conversations(replied_only=True)
        for item in result:
            self.assertTrue(item["has_reply"])

    def test_replied_only_count_matches_inbound_conversations(self):
        # Exactly 2 conversations have inbound emails → replied_only returns exactly 2
        sb = self._setup_sb()
        from src.db import get_all_conversations
        with patch("src.db._client", return_value=sb):
            get_all_conversations.clear()
            result = get_all_conversations(replied_only=True)
        self.assertEqual(len(result), 2)


# ─────────────────────────────────────────────────────────────────────────────
# 9. Shashank: generate then send email flow
# ─────────────────────────────────────────────────────────────────────────────
class TestShashankEmailFlow(unittest.TestCase):
    SHASHANK = {
        "id": "1",
        "name": "Shashank",
        "email": "shashankyadav4858@gmail.com",
        "work_experience": "5",
        "summary": "AI Engineer with 5 years of experience in machine learning and data science.",
        "location_preference": "Delhi",
        "disability": "None",
        "educational_qualification": "Not specified",
    }
    JOB = {
        "title": "Data Engineer",
        "description": "Build data pipelines and ETL workflows.",
        "company_name": "Acme Corp",
        "location": "Delhi",
        "contact_email": "jobs@acme.com",
    }

    @patch("requests.post")
    def test_generate_email_for_shashank(self, mock_post):
        mock_post.return_value = _http_response({
            "success": True,
            "job_id": "job-shashanks",
            "emails": [{"email": "shashankyadav4858@gmail.com",
                        "subject": "Re: Data Engineer at Acme Corp",
                        "body": "Dear Shashank, we reviewed your profile…",
                        "conversation_id": "conv-shashank-1"}],
        })
        from src import api
        with patch.object(api, "_BASE", "https://fn.example.com/api"):
            result = api.generate_emails({"job": self.JOB, "candidates": [self.SHASHANK]})
        self.assertTrue(result["success"])
        self.assertEqual(len(result["emails"]), 1)
        self.assertEqual(result["emails"][0]["email"], "shashankyadav4858@gmail.com")

    @patch("requests.post")
    def test_send_email_to_shashank(self, mock_post):
        mock_post.return_value = _http_response({
            "success": True,
            "sent": 1,
            "emails": [{"email": "shashankyadav4858@gmail.com", "sent": True, "saved": True}],
        })
        from src import api
        with patch.object(api, "_BASE", "https://fn.example.com/api"):
            result = api.send_emails({
                "job_id": "job-shashanks",
                "emails": [{"email": "shashankyadav4858@gmail.com",
                            "subject": "Re: Data Engineer at Acme Corp",
                            "body": "Dear Shashank, we reviewed your profile…",
                            "conversation_id": "conv-shashank-1"}],
            })
        self.assertTrue(result["success"])
        self.assertEqual(result["sent"], 1)
        self.assertEqual(result["emails"][0]["email"], "shashankyadav4858@gmail.com")
        self.assertTrue(result["emails"][0]["sent"])

    @patch("requests.post")
    def test_full_generate_then_send_shashank(self, mock_post):
        gen_response = {
            "success": True,
            "job_id": "job-shashanks",
            "emails": [{"email": "shashankyadav4858@gmail.com",
                        "subject": "Re: Data Engineer at Acme Corp",
                        "body": "Dear Shashank, we reviewed your profile…",
                        "conversation_id": "conv-shashank-1"}],
        }
        send_response = {
            "success": True,
            "sent": 1,
            "emails": [{"email": "shashankyadav4858@gmail.com", "sent": True, "saved": True}],
        }
        mock_post.side_effect = [_http_response(gen_response), _http_response(send_response)]
        from src import api
        with patch.object(api, "_BASE", "https://fn.example.com/api"):
            gen = api.generate_emails({"job": self.JOB, "candidates": [self.SHASHANK]})
            self.assertTrue(gen["success"])
            self.assertEqual(gen["job_id"], "job-shashanks")

            snd = api.send_emails({"job_id": gen["job_id"], "emails": gen["emails"]})
        self.assertTrue(snd["success"])
        self.assertEqual(snd["sent"], 1)
        self.assertEqual(snd["emails"][0]["email"], "shashankyadav4858@gmail.com")

    def test_generate_fails_without_base_url(self):
        from src import api
        with patch.object(api, "_BASE", ""):
            result = api.generate_emails({"job": self.JOB, "candidates": [self.SHASHANK]})
        self.assertFalse(result["success"])
        self.assertIn("FUNCTION_BASE", result["error"])


if __name__ == "__main__":
    unittest.main()
