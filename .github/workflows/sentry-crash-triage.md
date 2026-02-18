---
name: Sentry Crash Triage Agent
description: >
  When a Sentry crash is detected, analyze the culprit code, check git
  history, search for related issues, then either open a draft PR with a
  targeted fix or open a detailed triage issue for human review.
on:
  repository_dispatch:
    types: [sentry-crash]
engine: copilot
permissions:
  contents: write
  issues: write
  pull-requests: write
---

# Sentry Crash Triage — Copilot Agent

## Overview

This agentic workflow fires on every `sentry-crash` repository-dispatch event.
The `client_payload` carries four fields extracted from Sentry:

| Field | Description |
|-------|-------------|
| `title` | Human-readable crash title |
| `culprit` | File + function responsible (e.g. `tasks/views.py in delete_task`) |
| `level` | Severity: `fatal` · `error` · `warning` |
| `url` | Direct link to the Sentry issue for full stack trace |

---

## Agent Instructions

Complete **every** step below in order before taking any action.

### 1 · Find the culprit file

Parse `client_payload.culprit`. Sentry uses the format `module/path in function_name`.

- Map the module path to the actual file in this repository.
- Read the full file and locate the function/method named in the culprit.

### 2 · Understand the crash

With the culprit code in hand:

- Identify what operation is being attempted at the crash site.
- Determine what exception type or failure mode is most plausible.
- Note any assumptions, missing guards, or unchecked return values.

### 3 · Check git history

Run:

```bash
git log --oneline -15 -- <culprit_file>
```

- Surface any commits in the last 15 entries that touched the crash site.
- Flag commits that look like potential regressions (refactors, dependency bumps, logic changes).

### 4 · Search existing issues

Search open GitHub Issues for keywords taken from `title` and `culprit`.

- If a duplicate issue is found → add a comment with the new `url` value and
  **stop here** (do not create another issue or PR).

### 5 · Take action

Choose **one** of the two paths below:

---

#### Path A — Simple fix → Draft PR

Use this path when the fix is a single, obvious, targeted change
(null-check, missing guard clause, off-by-one, unhandled edge case).

1. Create branch `fix/sentry-crash` from `main`.
2. Apply the minimal fix — no unrelated changes.
3. Open a **draft Pull Request**:
   - **Title**: `fix: <crash title>`
   - **Body** must include:
     - Root cause (one paragraph)
     - The specific lines changed and why
     - A link back to the Sentry URL from `client_payload.url`
     - Reference to this dispatch event

---

#### Path B — Complex issue → Triage analysis

Use this path when the fix requires architectural decisions, deep context,
or investigation beyond a single file.

Open a **GitHub Issue** with:

- **Title**: `[Crash Triage] <crash title>`
- **Body** structured as:

```markdown
## Root Cause
<file path and line numbers where the crash originates>

## Affected Code
```<language>
<relevant snippet with line numbers>
```

## Inferred Reproduction Steps
1. …

## Recommended Fix
<approach, pros/cons, effort estimate>

## Related Areas
<any other files or modules that may be affected>

## Sentry Reference
<url from client_payload>
```

---

## Notes for the Agent

- **Never** modify unrelated files.
- **Never** force-push or rebase existing branches.
- If the culprit path cannot be resolved in this repository, open a
  triage issue (Path B) and explain that the file was not found.
- Keep all commit messages prefixed with `fix:` and under 72 characters.
