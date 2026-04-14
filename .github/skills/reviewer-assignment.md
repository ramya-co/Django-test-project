# Reviewer Assignment Skill

This skill determines the correct label and reviewer for the PR based
on which files were modified in the fix, and requests them through the
workflow's safe-outputs mechanism.

This is an autonomous CI run — no confirmation, no pausing, no skipping.

---

## Step 1: Determine label and reviewer from modified file paths

Inspect the exact list of files you modified during the fix. Use prefix
matching — a file at `tasks/views.py` matches the `tasks/` rule.

If no file matches any specific rule, fall back to `sentry-triage-agent`
and assign `ramyan-hf`.

For this POC, apply this single rule:

| Condition               | Apply label           | Request reviewer |
|-------------------------|-----------------------|------------------|
| Any modified file       | `sentry-triage-agent` | `ramyan-hf`      |

---

## Step 2: Apply the label to the PR

Request the label `sentry-triage-agent` to be added to the PR via the
workflow's `add-labels` safe output.

---

## Step 3: Request the reviewer

Request `ramyan-hf` to be added as a reviewer to the PR via the
workflow's `add-reviewer` safe output.

---

## Rules

- Never skip reviewer assignment under any circumstance.
- Never mark the PR as ready for review — always keep it as a draft.
- GitHub username is exact — do not alter it: `ramyan-hf`
- `sentry-triage-agent` label must always be present on every PR.
- Do not use gh CLI commands or bash to assign labels or reviewers —
  the safe-outputs mechanism handles all writes.
