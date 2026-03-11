# Test Scenario 2 — Code Fix (Category B)

**What this tests:** The agent must classify the crash as a *code defect*
(Axis 1), open a draft PR with the fix, generate regression tests covering the
crash + fix + edge case, post an impact analysis comment, and apply the correct
label. No regression should be detected (the bug was present from the start).

---

## Background — the planted bug

`tasks/views.py` → `index` view:

```python
# Committed as: "bug: use direct dict lookup for sort key — raises KeyError on unexpected ?sort= value"
order_field = sort_map[sort]   # ← KeyError if ?sort= is not in the map
```

Any request to `/?sort=popular` (or any unknown value) produces a 500. The fix
is `sort_map.get(sort, '-created_at')`.

---

## Simulated GitHub Issue Body

### Issue title (exact)
```
KeyError: 'popular'
```

### Issue body (paste verbatim)

```markdown
## Overview

**`KeyError: 'popular'`**

| | |
|--|--|
| **Culprit** | `tasks.views in index` |
| **Last seen** | 2026-03-11T10:22:00Z |
| **First seen** | 2026-03-10T14:05:00Z |
| **Times seen** | 38 |
| **Users affected** | 12 |
| **Assigned** | Unassigned |

## Stack Trace

```
File "tasks/views.py", line 17, in index
    order_field = sort_map[sort]
KeyError: 'popular'
```

## Context

Users sharing URLs with custom ?sort= parameters (e.g., copied from a
different app or clicked from a third-party integration) hit this 500.
Also reproducible by visiting /?sort=popular or /?sort=anything-unknown.
Task listing with default sort (no ?sort= param) is unaffected.

Severity: error

https://sentry.io/organizations/demo-org/issues/99002/events/ddeeff334455/
```

---

## Path B equivalent (manual triage template)

```markdown
## Issue Type
Type: Bug

## Exception / Error
Exception: KeyError: 'popular'

## Culprit
Culprit: tasks/views.py in index

## Severity
Severity: error

## Description
Any request to the index view with an unrecognised ?sort= query parameter
raises a KeyError because the view does a direct dict lookup instead of
using .get() with a safe default. Observed with ?sort=popular shared via
a link, but any unknown value triggers it.

## Stack Trace (if available)
```
File "tasks/views.py", line 17, in index
    order_field = sort_map[sort]
KeyError: 'popular'
```
```

---

## Expected Agent Behaviour — Verification Checklist

After the agent runs, verify each item:

### Classification
- [ ] Agent correctly identifies **Axis 1 = Code defect** (missing `.get()` fallback)
- [ ] Agent classifies as **Category B — code PR needed**
- [ ] Agent does **NOT** classify as data issue

### Labels
- [ ] Label `sentry-triage-code-fix` applied to the issue
- [ ] Label `ops-remediation-needed` is **NOT** applied
- [ ] Label `potential-regression` is **NOT** applied (this was present from the start)

### Regression detection
- [ ] Agent does NOT set `REGRESSION_DETECTED=true`
- [ ] `## Regression Detection` section is **absent** from the PR description

### Impact Analysis comment
- [ ] Comment posted with `## Impact Analysis` header before any code changes
- [ ] Impact level stated as **High** (index view — the main task listing — is broken for any user with a shared URL)
- [ ] Endpoint `GET /` → `index` listed as affected
- [ ] Background tasks: "none"
- [ ] Tests covering this area: agent found `tasks/tests.py` (empty) or reported "none found"

### Code fix (tasks/views.py)
- [ ] `order_field = sort_map[sort]` replaced with `order_field = sort_map.get(sort, '-created_at')`
- [ ] No other lines changed in `tasks/views.py`
- [ ] No other files modified except `tasks/tests.py`

### Draft PR
- [ ] PR opened as a **draft**
- [ ] Branch named `fix/sentry-keyerror-popular-<run_id>` (or similar slug)
- [ ] PR title: `fix: KeyError: 'popular' (Sentry auto-triage)`
- [ ] `Closes #<issue_number>` present in PR body
- [ ] Sentry URL present in PR body
- [ ] `## Tests Added` section present listing the test file

### Test generation (tasks/tests.py)
The agent must add at minimum these three tests to `tasks/tests.py`:

| Test | What it verifies |
|------|-----------------|
| Crash scenario | `GET /?sort=popular` returns 500 **before** the fix (document the bug) |
| Fix scenario | `GET /?sort=popular` returns 200 **after** the fix |
| Edge case | `GET /?sort=` (empty string) returns 200 with default ordering |

Check that:
- [ ] Tests use `django.test.TestCase` (not pytest)
- [ ] Tests use `self.client.get(reverse('index'), {'sort': 'popular'})`
- [ ] Each test has a one-line docstring
- [ ] `assertRedirects` is used where appropriate (not raw status checks for redirects)
- [ ] Tests do NOT test `sort_map` dict contents directly — only HTTP behaviour

---

## Why Category B and not Category A?

The data and the database are fine. The crash happens on every request with an
unknown `?sort=` value, regardless of what tasks exist. It is purely a missing
guard in the Python code — a `.get()` with a safe default would prevent it.
This is a textbook code defect.
