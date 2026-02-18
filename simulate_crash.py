#!/usr/bin/env python3
"""
simulate_crash.py — End-to-end pipeline tester

Simulates a Sentry webhook POST to your local Django server.
Signs the payload with your SENTRY_CLIENT_SECRET so the
signature verification passes, exactly like a real Sentry event.

Usage:
    # Make sure Django is running in another terminal first:
    #   venv/bin/python manage.py runserver
    
    venv/bin/python simulate_crash.py

    # Override the target URL (e.g. point at ngrok):
    WEBHOOK_URL=https://3610-14-99-67-22.ngrok-free.app/webhooks/sentry/ \
        venv/bin/python simulate_crash.py
"""

import hashlib
import hmac
import json
import os
import sys
import time

# Load .env so SENTRY_CLIENT_SECRET is available without manual export
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not needed if vars are already in environment

try:
    import requests
except ImportError:
    print("❌  'requests' not installed. Run: venv/bin/pip install requests")
    sys.exit(1)

# ── Config ────────────────────────────────────────────────────────────────────
WEBHOOK_URL       = os.getenv("WEBHOOK_URL", "http://127.0.0.1:8000/webhooks/sentry/")
CLIENT_SECRET     = os.getenv("SENTRY_CLIENT_SECRET", "")

# ── Fake Sentry issue-created payload ─────────────────────────────────────────
# This mirrors exactly what Sentry sends when a new issue is created.
FAKE_PAYLOAD = {
    "action": "created",
    "data": {
        "issue": {
            "id": "fake-issue-001",
            "title": "ZeroDivisionError: division by zero",
            "culprit": "tasks.views in trigger_test_crash",
            "level": "error",
            "status": "unresolved",
            "web_url": "https://demo.sentry.io/issues/fake-001/",
            "permalink": "https://demo.sentry.io/issues/fake-001/",
        }
    },
    "installation": {"uuid": "simulate-crash-test"},
}

# ── Build request ─────────────────────────────────────────────────────────────
body = json.dumps(FAKE_PAYLOAD).encode("utf-8")

if CLIENT_SECRET:
    signature = hmac.new(
        key=CLIENT_SECRET.encode("utf-8"),
        msg=body,
        digestmod=hashlib.sha256,
    ).hexdigest()
else:
    print("⚠️  SENTRY_CLIENT_SECRET not set — sending without a valid signature.")
    print("   The webhook view will warn but still proceed (dev mode).")
    signature = "no-secret"

headers = {
    "Content-Type":            "application/json",
    "sentry-hook-signature":   signature,
    "sentry-hook-resource":    "issue",
    "sentry-hook-timestamp":   str(int(time.time())),
}

# ── Fire ──────────────────────────────────────────────────────────────────────
print(f"\n{'='*60}")
print("  Sentry Crash Pipeline Simulator")
print(f"{'='*60}")
print(f"  Target  : {WEBHOOK_URL}")
print(f"  Title   : {FAKE_PAYLOAD['data']['issue']['title']}")
print(f"  Culprit : {FAKE_PAYLOAD['data']['issue']['culprit']}")
print(f"  Signed  : {'yes' if CLIENT_SECRET else 'no (missing secret)'}")
print(f"{'='*60}\n")

try:
    resp = requests.post(WEBHOOK_URL, data=body, headers=headers, timeout=15)
    print(f"✅  HTTP {resp.status_code}")
    try:
        print(f"    Response: {json.dumps(resp.json(), indent=4)}")
    except Exception:
        print(f"    Response: {resp.text}")

    if resp.status_code == 200:
        print("\n🚀  Pipeline triggered!")
        print("    1. Check GitHub Actions:  https://github.com/ramya-co/Django-test-project/actions")
        print("    2. A new issue will appear in:  https://github.com/ramya-co/Django-test-project/issues")
        print("    3. Copilot will be auto-assigned and will open a draft PR shortly.")
        print("    4. Review the PR, approve it, and merge when satisfied.")
    elif resp.status_code == 403:
        print("\n❌  Signature mismatch — check SENTRY_CLIENT_SECRET in your .env")
    else:
        print(f"\n⚠️  Unexpected status {resp.status_code}")

except requests.exceptions.ConnectionError:
    print(f"❌  Could not connect to {WEBHOOK_URL}")
    print("    Is the Django dev server running?  →  venv/bin/python manage.py runserver")
    sys.exit(1)
except requests.exceptions.Timeout:
    print("❌  Request timed out after 15 s")
    sys.exit(1)
