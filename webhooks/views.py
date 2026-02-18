import json
import logging

import requests
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

logger = logging.getLogger(__name__)


@csrf_exempt
@require_POST
def sentry_webhook(request):
    """
    Receives a Sentry webhook payload (issue alert or event alert),
    extracts crash metadata, and forwards it to GitHub's repository_dispatch
    API as a 'sentry-crash' event to trigger the Copilot triage workflow.
    """
    # ── 1. Parse body ────────────────────────────────────────────────────────
    try:
        payload = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        logger.warning("Sentry webhook received invalid JSON")
        return JsonResponse({"error": "Invalid JSON payload"}, status=400)

    # ── 2. Extract crash fields ───────────────────────────────────────────────
    # Sentry issue-alert payloads nest data under data.issue;
    # event-alert payloads nest data under data.event.
    data = payload.get("data", {})
    issue_data = data.get("issue") or data.get("event") or {}

    title = (
        issue_data.get("title")
        or payload.get("message")
        or "Unknown error"
    )
    culprit = issue_data.get("culprit") or "unknown"
    level = issue_data.get("level") or "error"
    url = (
        issue_data.get("web_url")
        or issue_data.get("permalink")
        or payload.get("url", "")
    )

    logger.info(
        "Received Sentry webhook — level=%s title=%s culprit=%s",
        level, title, culprit,
    )

    # ── 3. Validate GitHub settings ──────────────────────────────────────────
    gh_pat = getattr(settings, "GH_PAT", "")
    gh_owner = getattr(settings, "GH_OWNER", "")
    gh_repo = getattr(settings, "GH_REPO", "")

    if not all([gh_pat, gh_owner, gh_repo]):
        logger.error(
            "GitHub env vars not fully configured — "
            "set GH_PAT, GH_OWNER, and GH_REPO"
        )
        return JsonResponse(
            {
                "error": (
                    "GitHub integration not configured. "
                    "Ensure GH_PAT, GH_OWNER, and GH_REPO are set."
                )
            },
            status=500,
        )

    # ── 4. Forward to GitHub repository_dispatch ─────────────────────────────
    dispatch_url = (
        f"https://api.github.com/repos/{gh_owner}/{gh_repo}/dispatches"
    )
    dispatch_payload = {
        "event_type": "sentry-crash",
        "client_payload": {
            "title": title,
            "culprit": culprit,
            "level": level,
            "url": url,
        },
    }

    try:
        response = requests.post(
            dispatch_url,
            json=dispatch_payload,
            headers={
                "Authorization": f"Bearer {gh_pat}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=10,
        )
        response.raise_for_status()
    except requests.exceptions.HTTPError:
        logger.error(
            "GitHub API error %s: %s",
            response.status_code,
            response.text,
        )
        return JsonResponse(
            {
                "error": f"GitHub API returned {response.status_code}",
                "detail": response.text,
            },
            status=502,
        )
    except requests.exceptions.RequestException as exc:
        logger.error("Network error calling GitHub API: %s", exc)
        return JsonResponse({"error": f"Network error: {exc}"}, status=502)

    logger.info(
        "Dispatched sentry-crash event to GitHub — title=%s culprit=%s",
        title, culprit,
    )
    return JsonResponse(
        {
            "status": "dispatched",
            "title": title,
            "culprit": culprit,
            "level": level,
        }
    )
