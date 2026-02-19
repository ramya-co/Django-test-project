import hashlib
import hmac
import json
import logging

import requests
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

logger = logging.getLogger(__name__)


def _verify_sentry_signature(request) -> bool:
    """
    Verify the HMAC-SHA256 signature Sentry attaches to every webhook.
    Sentry signs the raw request body with the integration's client secret
    and sends the hex digest in the 'sentry-hook-signature' header.
    Returns True if the signature is valid or if no client secret is configured
    (allows local testing without a secret).
    """
    client_secret = getattr(settings, "SENTRY_CLIENT_SECRET", "")
    if not client_secret:
        logger.warning(
            "SENTRY_CLIENT_SECRET not set — skipping signature verification"
        )
        return True  # allow through so local curl tests still work

    received_sig = request.META.get("HTTP_SENTRY_HOOK_SIGNATURE", "")
    if not received_sig:
        logger.warning("Request missing sentry-hook-signature header")
        return False

    expected_sig = hmac.new(
        key=client_secret.encode("utf-8"),
        msg=request.body,
        digestmod=hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(received_sig, expected_sig)


@csrf_exempt
@require_POST
def sentry_webhook(request):
    """
    Receives a Sentry webhook payload (issue alert or event alert),
    extracts crash metadata, and forwards it to GitHub's workflow_dispatch
    API to trigger the Copilot triage workflow.
    """
    # ── 1. Verify Sentry signature ────────────────────────────────────────────
    if not _verify_sentry_signature(request):
        logger.warning("Sentry webhook signature verification failed")
        return JsonResponse({"error": "Invalid signature"}, status=403)

    # ── 2. Parse body ─────────────────────────────────────────────────────────
    try:
        payload = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        logger.warning("Sentry webhook received invalid JSON")
        return JsonResponse({"error": "Invalid JSON payload"}, status=400)

    # ── 3. Extract crash fields ───────────────────────────────────────────────
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

    # Only act on newly created issues to avoid duplicate dispatches
    action = payload.get("action", "created")
    if action not in ("created", "triggered"):
        logger.info("Ignoring Sentry webhook action=%s", action)
        return JsonResponse({"status": "ignored", "action": action})

    logger.info(
        "Received Sentry webhook — action=%s level=%s title=%s culprit=%s",
        action, level, title, culprit,
    )

    # ── 4. Validate GitHub settings ──────────────────────────────────────────
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

    # ── 5. Forward to GitHub workflow_dispatch ──────────────────────────────
    workflow_file = "sentry-crash-triage.lock.yml"
    dispatch_url = (
        f"https://api.github.com/repos/{gh_owner}/{gh_repo}"
        f"/actions/workflows/{workflow_file}/dispatches"
    )
    dispatch_payload = {
        "ref": "main",
        "inputs": {
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
