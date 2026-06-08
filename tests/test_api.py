"""Tests for src/api.py — all HTTP calls are mocked."""
import sys
import os
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def _make_response(json_data: dict, status_code: int = 200) -> MagicMock:
    r = MagicMock()
    r.status_code = status_code
    r.json.return_value = json_data
    if status_code >= 400:
        from requests.exceptions import HTTPError
        r.raise_for_status.side_effect = HTTPError(response=r)
    else:
        r.raise_for_status.return_value = None
    return r


class TestHealthCheck(unittest.TestCase):
    @patch("requests.get")
    def test_success(self, mock_get):
        mock_get.return_value = _make_response({"status": "ok"})
        from src import api
        result = api.health_check()
        self.assertEqual(result["status"], "ok")

    @patch("requests.get", side_effect=Exception("connection refused"))
    def test_network_error(self, _):
        from src import api
        result = api.health_check()
        self.assertEqual(result["status"], "error")
        self.assertIn("connection refused", result["error"])


class TestGenerateEmails(unittest.TestCase):
    PAYLOAD = {"job": {"title": "Engineer"}, "candidates": [{"email": "a@b.com"}]}

    @patch("requests.post")
    def test_success(self, mock_post):
        mock_post.return_value = _make_response({"success": True, "emails": []})
        from src import api
        result = api.generate_emails(self.PAYLOAD)
        self.assertTrue(result["success"])

    def test_missing_base_url(self):
        from src import api
        with patch.object(api, "_BASE", ""):
            result = api.generate_emails(self.PAYLOAD)
        self.assertFalse(result["success"])
        self.assertIn("FUNCTION_BASE", result["error"])

    @patch("requests.post")
    def test_http_error_with_json(self, mock_post):
        mock_post.return_value = _make_response({"error": "invalid payload"}, status_code=422)
        from src import api
        result = api.generate_emails(self.PAYLOAD)
        self.assertFalse(result["success"])
        self.assertEqual(result.get("error"), "invalid payload")

    @patch("requests.post")
    def test_timeout(self, mock_post):
        from requests.exceptions import Timeout
        mock_post.side_effect = Timeout()
        from src import api
        result = api.generate_emails(self.PAYLOAD)
        self.assertFalse(result["success"])
        self.assertIn("timed out", result["error"].lower())


class TestSendEmails(unittest.TestCase):
    PAYLOAD = {"job_id": "job-123", "emails": [{"conversation_id": "conv-1"}]}

    @patch("requests.post")
    def test_success(self, mock_post):
        mock_post.return_value = _make_response({"success": True, "sent": 1})
        from src import api
        result = api.send_emails(self.PAYLOAD)
        self.assertTrue(result["success"])

    def test_missing_base_url(self):
        from src import api
        with patch.object(api, "_BASE", ""):
            result = api.send_emails(self.PAYLOAD)
        self.assertFalse(result["success"])

    @patch("requests.post")
    def test_timeout(self, mock_post):
        from requests.exceptions import Timeout
        mock_post.side_effect = Timeout()
        from src import api
        result = api.send_emails(self.PAYLOAD)
        self.assertFalse(result["success"])
        self.assertIn("timed out", result["error"].lower())


if __name__ == "__main__":
    unittest.main()
