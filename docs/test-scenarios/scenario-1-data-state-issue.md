# Test Scenario 1 — Data/State Issue (Category A)

**What this tests:** The agent must classify the crash as a *data/state issue*
(Axis 1), skip opening a pull request, apply the correct label, and post a
detailed ops-remediation comment instead.

---

## Simulated GitHub Issue Body

> **How to use:** Open a new GitHub issue in this repository with the title
> below and paste the body below. The issue must be created by `sentry-io[bot]`
> (or a user whose login contains `sentry`) to follow Path A, OR by a human
> using the manual template markers to follow Path B.
>
> For a realistic Path A test, configure the Sentry GitHub integration and let
> it fire. For a quick local test, open the issue manually with Path B markers
> added.

### Issue title (exact)
```
IntegrityError: UNIQUE constraint failed: tasks_task.id
```

### Issue body (paste verbatim)

```markdown
## Overview

**`IntegrityError: UNIQUE constraint failed: tasks_task.id`**

| | |
|--|--|
| **Culprit** | `tasks.views in add_task` |
| **Last seen** | 2026-03-11T08:42:00Z |
| **First seen** | 2026-03-11T08:07:00Z |
| **Times seen** | 14 |
| **Users affected** | 5 |
| **Assigned** | Unassigned |

## Stack Trace

```
File "tasks/views.py", line 56, in add_task
    Task.objects.create(title=label)

  File "django/db/models/manager.py", line 85, in create
    return self.get_queryset().create(**kwargs)

  File "django/db/models/query.py", line 512, in create
    obj.save(force_insert=True, using=self.db)

django.db.utils.IntegrityError: UNIQUE constraint failed: tasks_task.id
```

## Context

Error spike began at 08:07 UTC. All new task creation attempts fail.
Existing task listing, toggling, and deletion still work correctly.
The SQLite database file was replaced with a point-in-time backup earlier
this morning during a disk maintenance operation. The backup predates
approximately 50 recently-created tasks, which means the SQLite
`sqlite_sequence` table still references a `seq` value lower than the
highest `id` that currently exists in the `tasks_task` table. Every new
`INSERT` Django performs tries to use an auto-generated ID that already
exists in the restored data.

Severity: error

https://sentry.io/organizations/demo-org/issues/99001/events/aabbcc112233/
```

---

## Path B equivalent (manual triage template)

If triggering manually without the Sentry bot, create an issue with this body
instead (all three required markers are present):

```markdown
## Issue Type
Type: Data Issue

## Exception / Error
Exception: IntegrityError: UNIQUE constraint failed: tasks_task.id

## Culprit
Culprit: tasks/views.py in add_task

## Severity
Severity: error

## Description
SQLite database was restored from a backup. The sqlite_sequence counter for
tasks_task is now lower than the highest existing id. Every new Task.objects.create()
call fails with IntegrityError because Django auto-generates an id that already
exists in the table.

## Stack Trace (if available)
```
File "tasks/views.py", line 56, in add_task
    Task.objects.create(title=label)
django.db.utils.IntegrityError: UNIQUE constraint failed: tasks_task.id
```
```

---

## Expected Agent Behaviour — Verification Checklist

After the agent runs, verify each item:

### Classification
- [ ] Agent correctly identifies **Axis 1 = Data/state issue** (corrupted SQLite sequence)
- [ ] Agent correctly identifies **Axis 2 = Bad migration/restore data** (sqlite_sequence out of sync)
- [ ] Agent classifies as **Category A — no code PR needed**

### Labels
- [ ] Label `ops-remediation-needed` applied to the issue
- [ ] Label `sentry-triage-code-fix` is **NOT** applied
- [ ] Label `potential-regression` is **NOT** applied

### No PR
- [ ] Agent does **NOT** open a pull request
- [ ] Agent does **NOT** modify any source file

### Impact Analysis comment (posted first)
- [ ] Comment posted with `## Impact Analysis` header
- [ ] Impact level stated as **Low** or **Medium** (task creation broken, read operations unaffected)
- [ ] Affected endpoint listed: `POST /add/` → `add_task`
- [ ] Background tasks: "none"

### Ops Remediation comment (posted after impact analysis)
- [ ] Comment posted with `## Automated Triage Analysis` header
- [ ] Root Cause Axis 1 and Axis 2 clearly stated
- [ ] "No code change required" stated
- [ ] Remediation steps include resetting the SQLite sequence, e.g.:
  ```sql
  UPDATE sqlite_sequence
  SET seq = (SELECT MAX(id) FROM tasks_task)
  WHERE name = 'tasks_task';
  ```
  or equivalent Django shell command:
  ```python
  from django.db import connection
  cursor = connection.cursor()
  cursor.execute("UPDATE sqlite_sequence SET seq = (SELECT MAX(id) FROM tasks_task) WHERE name = 'tasks_task'")
  ```
- [ ] Confidence level stated (should be **High** — all fields present in issue body)

### Not expected
- [ ] No test file created or modified
- [ ] No `tasks/views.py` changes

---

## Why Category A and not Category B?

The `add_task` view code (`Task.objects.create(title=label)`) is **correct**.
Django's ORM correctly delegates ID generation to SQLite's auto-increment
sequence. The crash root cause is that the `sqlite_sequence` table is out of
sync with the actual data — a data integrity problem caused by the backup
restore, not a code defect. Adding a `try/except IntegrityError` would mask
the symptom without fixing the underlying data problem and would silently drop
user-submitted tasks, making the situation worse.
