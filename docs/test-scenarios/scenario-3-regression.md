# Test Scenario 3 — Regression (Category B + Regression Detection)

**What this tests:** The agent must classify the crash as a *code defect*
introduced by a specific recent commit, set `REGRESSION_DETECTED=true`, include
the `## Regression Detection` section in the PR description, apply label
`potential-regression`, request review from the regression author *in addition
to* `ramya-co/ops-team`, generate tests, and post an impact analysis comment.

---

## Background — the planted regression

Commit `1f1d6090bad1eb055d2f35a8eee6d5604f7072c0` on `main`:

```
feat: add completion rate summary row to CSV export
```

Changed `export_tasks_csv` in `tasks/views.py`:

```python
# Line added by the regression commit — crashes when Task table is empty
total = Task.objects.count()
completed_count = Task.objects.filter(completed=True).count()
completion_rate = round(completed_count / total * 100, 1)  # ZeroDivisionError when total == 0
writer.writerow(['', f'Completion rate: {completion_rate}%', '', ''])
```

`GET /export/` on a fresh or empty database raises:
```
ZeroDivisionError: division by zero
```

It also crashes in production after all tasks are deleted (an uncommon but
valid state). Prior to the commit, `/export/` returned an empty CSV safely.

---

## Simulated GitHub Issue Body

### Issue title (exact)
```
ZeroDivisionError: division by zero
```

### Issue body (paste verbatim)

```markdown
## Overview

**`ZeroDivisionError: division by zero`**

| | |
|--|--|
| **Culprit** | `tasks.views in export_tasks_csv` |
| **Last seen** | 2026-03-11T11:55:00Z |
| **First seen** | 2026-03-11T11:30:00Z |
| **Times seen** | 9 |
| **Users affected** | 4 |
| **Assigned** | Unassigned |

## Stack Trace

```
File "tasks/views.py", line 105, in export_tasks_csv
    completion_rate = round(completed_count / total * 100, 1)
ZeroDivisionError: division by zero
```

## Context

CSV export was working fine until yesterday. The crash started appearing
approximately 25 minutes after the latest deployment. Only affects the
/export/ endpoint. Task listing, creation, and deletion are unaffected.
The crash is 100% reproducible on a fresh database instance or after
all tasks have been deleted.

Severity: error

https://sentry.io/organizations/demo-org/issues/99003/events/ffee99887766/
```

---

## Path B equivalent (manual triage template)

```markdown
## Issue Type
Type: Crash

## Exception / Error
Exception: ZeroDivisionError: division by zero

## Culprit
Culprit: tasks/views.py in export_tasks_csv

## Severity
Severity: error

## Description
The /export/ endpoint crashes with ZeroDivisionError since the latest
deployment. Worked correctly before. The crash occurs when total task
count is 0 — the new completion rate calculation divides by total without
guarding against zero. Started after commit that added completion rate row.

## Stack Trace (if available)
```
File "tasks/views.py", line 105, in export_tasks_csv
    completion_rate = round(completed_count / total * 100, 1)
ZeroDivisionError: division by zero
```
```

---

## Expected Agent Behaviour — Verification Checklist

After the agent runs, verify each item:

### Classification
- [ ] Agent correctly identifies **Axis 1 = Code defect** (division without zero-guard)
- [ ] Agent classifies as **Category B — code PR needed**

### Regression detection
- [ ] Agent runs `git log --oneline -15 -- tasks/views.py` and finds the introducing commit
- [ ] Agent runs `git show 1f1d6090bad1eb055d2f35a8eee6d5604f7072c0 -- tasks/views.py` and identifies the added division
- [ ] Agent sets `REGRESSION_DETECTED=true`
- [ ] Label `potential-regression` applied to the issue
- [ ] Label `sentry-triage-code-fix` also applied

### Labels
- [ ] `sentry-triage-code-fix` ✅
- [ ] `potential-regression` ✅
- [ ] `ops-remediation-needed` — NOT applied ✅

### Impact Analysis comment
- [ ] Comment posted with `## Impact Analysis` header
- [ ] Impact level stated as **Medium** (secondary view affected; core task CRUD unaffected)
- [ ] Affected endpoint: `GET /export/` → `export_tasks_csv`
- [ ] Background tasks: "none"
- [ ] Note about recently introduced commit is included if the agent detected it during dedup check (Step 3c)

### Code fix (tasks/views.py)
The fix must guard against `total == 0`. Any of these approaches is acceptable:

```python
# Option A — conditional
completion_rate = round(completed_count / total * 100, 1) if total > 0 else 0.0

# Option B — or-default
completion_rate = round(completed_count / total * 100, 1) if total else 0.0
```

- [ ] Division guarded against zero
- [ ] Docstring updated to mention completion rate summary (optional but nice)
- [ ] No other unrelated lines changed

### Draft PR
- [ ] PR opened as a **draft**
- [ ] Branch named `fix/sentry-zerodivisionerror-division-by-zero-<run_id>`
- [ ] PR title: `fix: ZeroDivisionError: division by zero (Sentry auto-triage)`
- [ ] `Closes #<issue_number>` in PR body
- [ ] Sentry URL in PR body

### Regression Detection section in PR description
- [ ] `## Regression Detection` section present
- [ ] Introducing commit: `1f1d6090bad1eb055d2f35a8eee6d5604f7072c0`
- [ ] Commit message: `feat: add completion rate summary row to CSV export`
- [ ] `git revert 1f1d6090bad1eb055d2f35a8eee6d5604f7072c0` rollback command shown
- [ ] Recommendation states "Fix forward" (the feature is desirable; only the zero-guard is missing)

### Reviewer assignment
- [ ] Review requested from `ramya-co/ops-team` (always)
- [ ] Review also requested from the regression commit author (Github username derived from commit email)

### Test generation (tasks/tests.py)
The agent must add at minimum these three tests:

| Test | What it verifies |
|------|-----------------|
| Crash scenario | `GET /export/` with empty DB returns 500 **before** the fix |
| Fix scenario | `GET /export/` with empty DB returns 200 **after** the fix |
| Edge case | `GET /export/` with tasks present returns 200 and CSV contains the completion rate row |

Check that:
- [ ] Tests use `django.test.TestCase` (not pytest)
- [ ] Crash scenario uses an empty database (no `setUpTestData`) or deletes all tasks in `setUp`
- [ ] Fix scenario asserts `response.status_code == 200`
- [ ] Edge case asserts that `b'Completion rate'` appears in `response.content`
- [ ] Each test has a one-line docstring

---

## Why Fix Forward and not Rollback?

The completion rate feature is useful and the commit author's intent was
correct. The only defect is the missing zero guard. Reverting removes the
feature entirely. A one-line fix preserves the value of the change while
eliminating the crash. Rollback is appropriate when the entire change was
wrong; here, only one arithmetic expression needs guarding.
