# POC: Sentry Crash Auto-Triage Pipeline

**Project:** Django-test-project  
**Repository:** github.com/ramya-co/Django-test-project  
**Date:** February 2026  
**Status:** Validated and operational  

---

## 1. Objective

Demonstrate an end-to-end automated crash-triage pipeline where:

- A production exception is captured by **Sentry**.
- Sentry fires a webhook to the Django application.
- The Django webhook bridge forwards crash metadata to **GitHub** via `repository_dispatch`.
- A **GitHub Agentic Workflow** (gh-aw) triggers, running the **Copilot CLI** agent with the **Claude Sonnet 4.5** model.
- The agent reads the crash details, locates the faulty code, applies a minimal fix, and opens a **draft Pull Request** for human review.

No human intervention is required between the crash occurring and the draft PR appearing. The human engineer reviews and merges at their discretion.

---

## 2. Architecture Overview

```
+-------------------+        HTTPS POST         +---------------------------+
|   Sentry Cloud    | ───────────────────────>   |  Django App (webhooks/)   |
| (error monitoring)|   signed webhook payload   |  sentry_webhook view      |
+-------------------+                            +---------------------------+
                                                           |
                                                           | POST /repos/{owner}/{repo}/dispatches
                                                           | event_type: "sentry-crash"
                                                           v
                                                 +---------------------------+
                                                 |    GitHub API             |
                                                 |    repository_dispatch    |
                                                 +---------------------------+
                                                           |
                                                           | triggers workflow
                                                           v
                                                 +---------------------------+
                                                 | GitHub Actions            |
                                                 | sentry-crash-triage       |
                                                 | (gh-aw compiled workflow) |
                                                 +---------------------------+
                                                           |
                                                           | Copilot CLI + Claude Sonnet 4.5
                                                           v
                                                 +---------------------------+
                                                 |  Draft Pull Request       |
                                                 |  with fix + explanation   |
                                                 +---------------------------+
```

---

## 3. Technology Stack

| Layer                | Technology                   | Version       |
|----------------------|------------------------------|---------------|
| Web framework        | Django                       | 6.x           |
| Database             | SQLite                       | (bundled)     |
| Error monitoring     | Sentry SDK for Django        | 2.19.2        |
| Workflow framework   | GitHub Agentic Workflows     | v0.46.0       |
| AI coding agent      | GitHub Copilot CLI           | 0.0.410       |
| AI model             | Claude Sonnet 4.5 (Anthropic)| GA            |
| Sandbox / firewall   | Agent Workflow Firewall (AWF)| v0.20.0       |
| MCP gateway          | gh-aw MCP Gateway            | v0.1.4        |
| GitHub MCP server    | github-mcp-server            | v0.30.3       |
| Language             | Python                       | 3.x           |

---

## 4. Repository Structure

```
Django-test-project/
  manage.py
  requirements.txt
  simulate_crash.py                          <-- manual pipeline tester
  .env                                       <-- local secrets (git-ignored)
  .env.example                               <-- template for new contributors

  todoproject/                               <-- Django project config
    settings.py                              <-- loads GH_PAT, GH_OWNER, GH_REPO,
                                                  SENTRY_DSN, SENTRY_CLIENT_SECRET
    urls.py                                  <-- routes: admin/, tasks/, webhooks/
    wsgi.py
    asgi.py

  tasks/                                     <-- the To-Do list application
    models.py                                <-- Task(title, completed, created_at)
    views.py                                 <-- index, add_task, toggle_task,
                                                  delete_task, trigger_test_crash
    urls.py
    templates/tasks/
      base.html
      index.html
    migrations/

  webhooks/                                  <-- Sentry-to-GitHub bridge
    views.py                                 <-- sentry_webhook: receives Sentry
                                                  payload, dispatches to GitHub
    urls.py                                  <-- /webhooks/sentry/

  .github/
    triage-instructions.md                   <-- agent playbook (project map,
                                                  coding style, PR template)
    aw/
      actions-lock.json                      <-- pinned action SHAs
    agents/
      agentic-workflows.agent.md             <-- Copilot agent descriptor
    workflows/
      sentry-crash-triage.md                 <-- workflow source (markdown)
      sentry-crash-triage.lock.yml           <-- compiled workflow (auto-generated)
      copilot-setup-steps.yml                <-- Copilot agent environment setup
```

---

## 5. Secrets and Tokens Required

Every secret or variable below is necessary for the pipeline to function. They are organized by where they are consumed.

### 5.1 Local Django Application (.env file)

| Variable               | Purpose                                                        | Where to obtain                                                                                                   |
|------------------------|----------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------|
| `GH_PAT`              | GitHub Personal Access Token. Used by the webhook bridge to call the GitHub `repository_dispatch` API. | GitHub > Settings > Developer settings > Fine-grained PAT. Scopes: contents (r/w), issues (r/w), pull-requests (r/w), workflows (r/w). |
| `GH_OWNER`            | GitHub account or organization that owns the repo.             | Plain string, e.g. `ramya-co`.                                                                                    |
| `GH_REPO`             | Repository name (without owner prefix).                        | Plain string, e.g. `Django-test-project`.                                                                         |
| `SENTRY_DSN`          | Sentry Data Source Name. Configures the Sentry SDK to report errors from the Django app. | Sentry > Settings > Projects > [project] > Client Keys (DSN).                                                     |
| `SENTRY_CLIENT_SECRET`| Sentry internal integration client secret. Used to verify HMAC-SHA256 signatures on incoming webhooks. | Sentry > Settings > Developer Settings > [integration] > Credentials > Client Secret.                             |

### 5.2 GitHub Repository Secrets (Settings > Secrets and variables > Actions > Secrets)

| Secret                          | Purpose                                                        | Where to obtain                                                                                                   |
|---------------------------------|----------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------|
| `COPILOT_GITHUB_TOKEN`         | Authenticates the Copilot CLI agent during the GitHub Actions workflow. This is the primary token the AI agent uses. | GitHub > Settings > Developer settings > Fine-grained PAT with the `copilot-requests` scope. Must be created under your personal account with "Public repositories" access selected (required for the Copilot Requests permission to appear). |
| `GH_AW_GITHUB_TOKEN` (optional)| Used by the conclusion and safe-outputs jobs for creating PRs, posting comments, and other write operations. Falls back to the built-in `GITHUB_TOKEN` if not set. | Same type of PAT as above, or omit to use the default `GITHUB_TOKEN`.                                             |

### 5.3 GitHub Repository Variables (Settings > Secrets and variables > Actions > Variables)

| Variable                       | Purpose                                                        | Value set in this POC |
|--------------------------------|----------------------------------------------------------------|-----------------------|
| `GH_AW_MODEL_AGENT_COPILOT`   | Specifies which AI model the Copilot CLI agent uses. Passed as `--model` to the CLI. If empty, the Copilot default model is used. | `claude-sonnet-4.5`  |
| `GH_AW_MODEL_DETECTION_COPILOT` (optional) | Specifies the model for the threat-detection pass (a second, lighter agent run that validates the output). If empty, the Copilot default is used. | (not set -- uses default) |

### 5.4 Token Flow Summary

```
Sentry Cloud
  |
  | webhook POST with HMAC signature (signed using SENTRY_CLIENT_SECRET)
  v
Django webhooks/views.py
  |  verifies signature using SENTRY_CLIENT_SECRET
  |  calls GitHub API using GH_PAT
  v
GitHub API (repository_dispatch)
  |
  | triggers sentry-crash-triage workflow
  v
GitHub Actions
  |  pre_activation job: uses GITHUB_TOKEN to check team membership
  |  agent job: uses COPILOT_GITHUB_TOKEN to run Copilot CLI
  |  agent job: uses GH_AW_GITHUB_TOKEN (or GITHUB_TOKEN) for MCP server
  |  agent job: reads vars.GH_AW_MODEL_AGENT_COPILOT to select the model
  |  safe_outputs job: uses GH_AW_GITHUB_TOKEN (or GITHUB_TOKEN) to create the PR
  v
Draft Pull Request
```

---

## 6. Workflow Execution Pipeline (Job by Job)

The compiled workflow `sentry-crash-triage.lock.yml` defines six jobs that run in sequence with dependencies:

### 6.1 pre_activation

- **Runner:** ubuntu-slim
- **Purpose:** Checks whether the actor who triggered the event has sufficient repository permissions (admin, maintainer, or write).
- **Output:** `activated` (true/false). All downstream jobs are skipped if false.

### 6.2 activation

- **Depends on:** pre_activation
- **Runner:** ubuntu-slim
- **Purpose:** Builds the prompt for the AI agent. Checks out `.github/` and `.agents/` directories, imports the workflow markdown (`sentry-crash-triage.md`), interpolates GitHub context variables (actor, repository, run ID, event payload), and uploads the final prompt as an artifact.
- **Key detail:** The prompt includes the full text of `sentry-crash-triage.md`, which instructs the agent to read `triage-instructions.md` for the project map and coding style.

### 6.3 agent

- **Depends on:** activation
- **Runner:** ubuntu-latest
- **Purpose:** Executes the Copilot CLI agent inside the AWF sandbox.
- **Steps of note:**
  1. Checks out the full repository.
  2. Configures git credentials for the actions bot.
  3. Validates the `COPILOT_GITHUB_TOKEN` secret.
  4. Installs Copilot CLI (v0.0.410) and AWF binary (v0.20.0).
  5. Downloads Docker images for the firewall, MCP gateway, GitHub MCP server, and Safe Outputs server.
  6. Starts the Safe Outputs MCP server (provides structured tools for creating PRs).
  7. Starts the MCP Gateway (proxies between Copilot CLI and MCP servers).
  8. Downloads the prompt artifact from the activation job.
  9. **Executes the Copilot CLI** inside the AWF firewall with `--model claude-sonnet-4.5` (from the repository variable). The agent reads the crash payload from the prompt, follows the triage instructions, edits source files, and calls the `create_pull_request` safe-output tool.
  10. Collects outputs (safe-output JSONL, patches, logs).
- **Model selection line:**
  ```
  ${GH_AW_MODEL_AGENT_COPILOT:+ --model "$GH_AW_MODEL_AGENT_COPILOT"}
  ```
  The variable `GH_AW_MODEL_AGENT_COPILOT` is read from `vars.GH_AW_MODEL_AGENT_COPILOT || ''`. When set to `claude-sonnet-4.5`, the Copilot CLI routes inference to Anthropic's Claude Sonnet 4.5 model through GitHub's model gateway.

### 6.4 detection

- **Depends on:** agent
- **Runner:** ubuntu-latest
- **Purpose:** Threat detection. Runs a second Copilot CLI pass (with restricted tools: only cat, grep, head, jq, ls, tail, wc) to review the agent's output for suspicious or harmful content.
- **Gate:** The safe_outputs job only proceeds if detection passes (`success == 'true'`).

### 6.5 safe_outputs

- **Depends on:** activation, agent, detection
- **Runner:** ubuntu-slim
- **Purpose:** Processes the agent's safe-output tool calls. If the agent called `create_pull_request`, this job applies the patch to a new branch and creates the draft PR via the GitHub API.
- **Permissions:** contents: write, issues: write, pull-requests: write.

### 6.6 conclusion

- **Depends on:** activation, agent, detection, safe_outputs
- **Runner:** ubuntu-slim
- **Purpose:** Handles edge cases: logs no-op messages if the agent found nothing to fix, records missing-tool reports, handles agent failures, and reports PR creation errors.

---

## 7. Agent Behavior (What the AI Does)

When triggered, the Claude Sonnet 4.5 agent follows these steps, as defined in `sentry-crash-triage.md` and `triage-instructions.md`:

1. **Read the project map** from `.github/triage-instructions.md`.
2. **Parse the culprit** from `github.event.client_payload.culprit`. Convert Sentry's dot-notation module path to a file path (e.g. `tasks.views in trigger_test_crash` becomes `tasks/views.py`, function `trigger_test_crash`).
3. **Read the culprit file** and locate the exact function.
4. **Analyze the crash**: identify the operation, exception type, and missing guard.
5. **Check git history** (`git log --oneline -20 -- <file>`) for recent changes that may have introduced the bug.
6. **Check for duplicate issues/PRs** to avoid redundant work.
7. **Apply the smallest correct fix** matching the existing code style.
8. **Open a draft PR** with a structured description including: crash title, culprit, severity, Sentry URL, root cause analysis, fix summary, before/after code, and risk assessment.

The agent is explicitly forbidden from:
- Auto-merging the PR.
- Opening a GitHub Issue as output.
- Modifying unrelated files.
- Touching `webhooks/` or `migrations/` unless the crash originates there.

---

## 8. Model Configuration

### Available Claude Models in GitHub Copilot (as of February 2026)

| Model              | Status         | Premium Multiplier | Plan Availability              |
|--------------------|----------------|--------------------|--------------------------------|
| Claude Haiku 4.5   | GA             | 0.33x              | All plans                      |
| Claude Sonnet 4    | GA             | 1x                 | Pro, Pro+, Business, Enterprise|
| Claude Sonnet 4.5  | GA             | 1x                 | Pro, Pro+, Business, Enterprise|
| Claude Sonnet 4.6  | GA             | 1x                 | Pro, Pro+, Business, Enterprise|
| Claude Opus 4.5    | GA             | 3x                 | Pro, Pro+, Business, Enterprise|
| Claude Opus 4.6    | GA             | 3x                 | Pro, Pro+, Business, Enterprise|

### Model Selected for This POC

**Claude Sonnet 4.5** -- chosen for the balance of quality and cost. At a 1x premium multiplier, it consumes the same quota as GPT-based defaults while providing strong code-reasoning capabilities from Anthropic.

### How to Change the Model

Set the `GH_AW_MODEL_AGENT_COPILOT` repository variable to any supported model identifier:

```bash
# via GitHub CLI
gh variable set GH_AW_MODEL_AGENT_COPILOT --body "claude-sonnet-4.6"
```

Or via the GitHub UI: Settings > Secrets and variables > Actions > Variables tab > edit `GH_AW_MODEL_AGENT_COPILOT`.

Valid identifiers include: `claude-sonnet-4`, `claude-sonnet-4.5`, `claude-sonnet-4.6`, `claude-opus-4.5`, `gpt-5.1`, `gemini-2.5-pro`, among others.

### Alternative: Claude Code as a Standalone Engine

The gh-aw framework also supports Anthropic's Claude Code as a separate engine (not routed through Copilot). This requires changing the workflow frontmatter to `engine: claude` and providing an `ANTHROPIC_API_KEY` secret instead of `COPILOT_GITHUB_TOKEN`. This approach was not used in this POC.

---

## 9. Triggering the Pipeline

There are three methods to trigger the pipeline, from production to manual testing:

### 9.1 Production Path (Sentry Webhook)

1. An unhandled exception occurs in the Django app.
2. The Sentry SDK captures it and creates an issue.
3. Sentry's webhook integration POSTs to `https://<your-domain>/webhooks/sentry/`.
4. The Django `sentry_webhook` view verifies the HMAC signature, extracts crash metadata, and calls the GitHub `repository_dispatch` API.
5. The workflow triggers automatically.

### 9.2 Local Simulation (simulate_crash.py)

Run the Django dev server, then execute `simulate_crash.py` which constructs a properly signed Sentry webhook payload and POSTs it to the local server:

```bash
python manage.py runserver          # terminal 1
python simulate_crash.py            # terminal 2
```

The Django server receives the webhook, verifies the signature, and forwards it to GitHub.

### 9.3 Direct GitHub API (Bypass Django)

Send a `repository_dispatch` event directly to GitHub, bypassing the Django webhook bridge entirely:

```bash
curl -s -X POST \
  -H "Authorization: Bearer $GH_PAT" \
  -H "Accept: application/vnd.github+json" \
  -H "X-GitHub-Api-Version: 2022-11-28" \
  "https://api.github.com/repos/ramya-co/Django-test-project/dispatches" \
  -d '{
    "event_type": "sentry-crash",
    "client_payload": {
      "title": "ZeroDivisionError: division by zero",
      "culprit": "tasks.views in trigger_test_crash",
      "level": "error",
      "url": "https://demo.sentry.io/issues/fake-001/"
    }
  }'
```

A successful dispatch returns HTTP 204 with no body.

---

## 10. The Test Crash Endpoint

For POC validation, a deliberate crash endpoint was added:

**File:** `tasks/views.py`  
**Function:** `trigger_test_crash`  
**URL:** `/debug-crash/`

```python
def trigger_test_crash(request):
    task_count = Task.objects.filter(completed=False).count()
    result = 1 / 0  # intentional ZeroDivisionError
    return redirect('index')
```

When visited, this raises a `ZeroDivisionError` that Sentry captures and reports. The resulting Sentry webhook (or manual dispatch) presents the agent with a clear crash to triage.

This endpoint should be removed after POC validation is complete.

---

## 11. Webhook Signature Verification

The Sentry webhook handler implements HMAC-SHA256 signature verification:

1. Sentry signs the raw request body using the integration's client secret.
2. The signature is sent in the `sentry-hook-signature` HTTP header.
3. The Django view (`webhooks/views.py` > `_verify_sentry_signature`) recomputes the HMAC using `SENTRY_CLIENT_SECRET` from settings and compares using `hmac.compare_digest` (constant-time comparison to prevent timing attacks).
4. If `SENTRY_CLIENT_SECRET` is not configured, the view logs a warning but allows the request through (development convenience).

---

## 12. Validation Results

The following steps were executed to validate the pipeline:

1. Set repository variable `GH_AW_MODEL_AGENT_COPILOT` to `claude-sonnet-4.5` via the GitHub UI (Settings > Secrets and variables > Actions > Variables).
2. Triggered a `repository_dispatch` event via direct GitHub API call with a `ZeroDivisionError` crash payload targeting `tasks.views in trigger_test_crash`.
3. Confirmed HTTP 204 response (dispatch accepted).
4. Verified the "Sentry Crash Auto-Triage" workflow appeared in the Actions tab.
5. Confirmed all workflow jobs completed: pre_activation, activation, agent (running Claude Sonnet 4.5), detection, safe_outputs, conclusion.
6. Confirmed a draft Pull Request was created with the fix and structured description.

---

## 13. Security Considerations

| Concern                        | Mitigation                                                                                       |
|--------------------------------|--------------------------------------------------------------------------------------------------|
| Webhook forgery                | HMAC-SHA256 signature verification using `SENTRY_CLIENT_SECRET`.                                 |
| Token exposure                 | All secrets stored in GitHub encrypted secrets. The `.env` file is git-ignored. `.env.example` contains only placeholders. |
| Agent sandbox escape           | The Copilot CLI runs inside the Agent Workflow Firewall (AWF) with an explicit domain allowlist. Only approved domains are reachable. |
| Malicious agent output         | The detection job runs a second AI pass to scan for suspicious content before the safe_outputs job creates any GitHub resources. |
| PR auto-merge                  | Explicitly forbidden in the agent instructions. PRs are always created as drafts.                |
| Minimal permissions            | The workflow declares `permissions: {}` at the top level. Each job declares only the permissions it needs. |
| Secret redaction in logs       | A dedicated step scans all log files and redacts any leaked secret values before artifact upload. |

---

## 14. Cost Implications

Claude Sonnet 4.5 has a premium request multiplier of **1x**, meaning each agent invocation consumes one premium request from the Copilot plan quota. This is the same cost as GPT-5, Gemini 2.5 Pro, and other 1x models.

The detection job uses the Copilot default model (not Claude Sonnet) unless `GH_AW_MODEL_DETECTION_COPILOT` is explicitly set, keeping the secondary pass at default cost.

---

## 15. Known Limitations

1. The agent cannot run the Django test suite inside the Actions runner (no database setup step). Verification is done via code analysis only.
2. The `trigger_test_crash` endpoint is a synthetic test case. Real production crashes may involve more complex root causes that the agent cannot fully resolve.
3. The pipeline assumes the crash is reproducible from the code. Data-dependent crashes (corrupt database rows, missing environment variables at runtime) may not be fixable by code changes alone.
4. Rate limits on the GitHub API and Copilot premium requests apply.
5. The webhook bridge (`webhooks/views.py`) contains duplicated dead code after the first `return` statement. This is a pre-existing issue unrelated to the pipeline functionality.
