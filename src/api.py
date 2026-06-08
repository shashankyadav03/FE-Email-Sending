import os
import logging
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

_BASE = os.getenv("FUNCTION_BASE", "").rstrip("/")
_KEY  = os.getenv("FUNCTION_KEY",  "")
_TIMEOUT = 90  # seconds


def _url(route: str) -> str:
    return f"{_BASE}/{route}?code={_KEY}"


def health_check() -> dict[str, Any]:
    """GET /health — returns status dict or error dict."""
    try:
        r = requests.get(_url("health"), timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception as exc:
        logger.error("health_check failed: %s", exc)
        return {"status": "error", "error": str(exc)}


def generate_emails(payload: dict) -> dict[str, Any]:
    """
    POST /emails/create
    Expects: { job: {...}, candidates: [...] }
    Returns: { success, job_id, emails: [...] }
    """
    if not _BASE:
        return {"success": False, "error": "FUNCTION_BASE not configured"}
    try:
        r = requests.post(_url("emails/create"), json=payload, timeout=_TIMEOUT)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.Timeout:
        return {"success": False, "error": "Request timed out. The AI generation may still be running."}
    except requests.exceptions.HTTPError as exc:
        try:
            detail = exc.response.json()
        except Exception:
            detail = {"error": str(exc)}
        logger.error("generate_emails HTTP error: %s", detail)
        return {"success": False, **detail}
    except Exception as exc:
        logger.error("generate_emails failed: %s", exc)
        return {"success": False, "error": str(exc)}


def send_emails(payload: dict) -> dict[str, Any]:
    """
    POST /emails/send
    Expects: { job_id, emails: [...with conversation_id...] }
    Returns: { success, sent, saved, emails: [...] }
    """
    if not _BASE:
        return {"success": False, "error": "FUNCTION_BASE not configured"}
    try:
        r = requests.post(_url("emails/send"), json=payload, timeout=_TIMEOUT)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.Timeout:
        return {"success": False, "error": "Request timed out."}
    except requests.exceptions.HTTPError as exc:
        try:
            detail = exc.response.json()
        except Exception:
            detail = {"error": str(exc)}
        logger.error("send_emails HTTP error: %s", detail)
        return {"success": False, **detail}
    except Exception as exc:
        logger.error("send_emails failed: %s", exc)
        return {"success": False, "error": str(exc)}
