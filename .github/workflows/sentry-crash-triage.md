---
name: Sentry Crash Triage Agent
description: >
  When a Sentry crash is detected, read .github/triage-instructions.md,
  find the root cause in the codebase, apply a minimal fix, and open a
  draft PR for human review. Never auto-merge. Never open an issue as output.
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
| `culprit` | File + function responsible (e.g. `tasks.views in delete_task`) |
| `level` | Severity: `fatal` · `error` · `warning` |
| `url` | Direct link to the Sentry issue for full stack trace |

## Output contract

**Always and only:** open a **draft Pull Request** with the fix.  
**Never:** open a GitHub Issue, post analysis-only comments, or auto-merge.  
The human reviewer will mark the PR ready, approve it, and merge it.

---

## Agent Instructions

> **Before writing any code, read `.github/triage-instructions.md` in full.**
> That file contains the project map, code-style guide, culprit-parsing rules,
> investigation checklist, and the mandatory PR description template.

### 1 · Locate the culprit

- Parse `client_payload.culprit` using the rules in `triage-instructions.md §2`.
- Read the full culprit file and find the exact function.

### 2 · Understand the crash

Answer before touching code:
- What operation is failing?
- What exception / failure mode is triggered?
- What guard or assumption is missing?

### 3 · Check git history

```bash
git log --oneline -20 -- <culprit_file>
```

Identify any recent commit that may have introduced the regression.

### 4 · Check for duplicates

Search open PRs and issues for the crash title and culprit module keywords.  
If an open PR already covers this crash, add a comment there and stop.

### 5 · Apply the fix

Follow the fix guidelines in `triage-instructions.md §3–§4`:
- Minimal, targeted change only.
- Match existing code style exactly.
- No unrelated edits.

### 6 · Open a draft PR

Follow `triage-instructions.md §5` exactly:

| Requirement | Detail |
|-------------|--------|
| Branch | `fix/sentry-<slug>` from `main` |
| PR state | **draft** — never mark ready |
| Title | `fix: <crash title> (Sentry auto-triage)` |
| Description | Use the full template from `triage-instructions.md §5` |
| Issue ref | `Closes #<triggering issue number>` |
| Sentry URL | Must appear in the PR description |

---

## Hard rules

- ❌ Do not auto-merge.
- ❌ Do not open an issue as your output.
- ❌ Do not modify unrelated files.
- ✅ PR must reference the Sentry URL from `client_payload.url`.
- ✅ PR must be a draft until a human approves it.

