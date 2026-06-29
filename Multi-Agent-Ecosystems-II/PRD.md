# **Product Requirements Document**
## AI-Powered LinkedIn Content Automation -- FinEdge Mumbai

> **Golden source:** `context/1762523953_course_end_project_problem_statement_20260627_001.md`
> Every requirement below traces directly to that document. Nothing has been added beyond it.

**Date:** 2026-06-27
**Status:** Complete -- all design decisions resolved; project built 2026-06-28

---

## 1. Purpose

Translate the course-end project rubric into concrete, implementable technical requirements so that every build decision can be verified against a single reference before code is written.

---

## 2. Problem Being Solved

FinEdge Mumbai (500+ employees, fintech) spends 15+ hours per week manually drafting LinkedIn posts, posts inconsistently (engagement down 45%), misses trending topics, and lacks a unified executive voice. The solution is an automated AI pipeline with human oversight via an approval gate.

---

## 3. Goals

| # | Goal | Source |
|---|---|---|
| G1 | Build a FastAPI microservice (`POST /linkedin`) that accepts brand config + context and returns ideas, draft, confidence score, and hashtags | Rubric: Tasks, Actions |
| G2 | Deploy microservice on Ubuntu VM lab environment | Rubric: Instructions |
| G3 | Build an n8n workflow with Schedule, Brand Config, HTTP Request, Compose Final, Approval Gate, Slack, LinkedIn, and Logging nodes | Rubric: Tasks, Actions |
| G4 | Route posts to Slack for human review (dry-run or low confidence) or LinkedIn for direct publishing (high confidence, live mode) | Rubric: Actions |
| G5 | Log run details (timestamp, draft, confidence) to a spreadsheet or database for monitoring and threshold tuning | Rubric: Actions |
| G6 | Deliver all required submission artifacts | Rubric: Instructions, Result |

---

## 4. Non-Goals (Out of Scope)

The following are explicitly excluded to prevent scope drift from the rubric:

- Image or media attachment generation for LinkedIn posts
- Multi-language post generation
- Analytics dashboard beyond the logging node
- A/B testing of post variants
- LinkedIn comment or engagement monitoring
- Custom n8n node development
- Full CI/CD pipeline
- User-facing web UI for the microservice

---

## 5. Architecture Overview

```
[n8n: Schedule Trigger]
        |
        v
[n8n: Brand Config] --> brand JSON
        |
        v
[n8n: HTTP Request] --> POST /linkedin (FastAPI microservice)
        |
        v  FastAPI internally chains 3 "agents" (OpenAI API calls):
        |    - Idea Agent    -> 3 post ideas
        |    - Draft Agent   -> draft text + confidence score (0.0 - 1.0)
        |    - Hashtag Agent -> relevant hashtags
        |  Returns structured JSON
        |
        v
[n8n: Compose Final (Set node)] --> assembled final post text + hashtags
        |
        v
[n8n: Approval Gate (IF node)]
   confidence >= 0.75 AND dry_run == false?
        |                    |
       YES                   NO
        |                    |
        v                    v
[LinkedIn node]         [Slack node]
(live publish)         (human review)
        |                    |
        +--------+----------+
                 |
                 v
        [n8n: Logging node]
        (append to local CSV file)
```

**Ecosystem:** Microsoft-first. Standard OpenAI API (gpt-4.1-mini) as LLM backend. n8n self-hosted in Ubuntu WSL2 on Windows.

---

## 6. Component Specifications

### 6.1 FastAPI Microservice

**File:** `main.py`
**Runtime:** Python 3.12 on Windows (launched via `.\run.ps1`, which bootstraps `.venv` and starts Uvicorn)
**Framework:** FastAPI + Uvicorn
**LLM backend:** Standard OpenAI API (`gpt-4.1-mini` recommended for cost; `gpt-4.1` for quality)

#### Endpoints

```
POST /linkedin
Content-Type: application/json
```

Returns `{ ideas, draft, confidence, hashtags }` to the n8n workflow.

```
POST /log
Content-Type: application/json
```

Called by the n8n Logging node. Accepts `{ "final_post": str, "confidence": float, "dry_run": bool }` and appends a row to `linkedin_log.csv` in the project root. Added during build because n8n Code node sandboxes `require('fs')` and Write to File node requires binary input.

#### Internal Agent Chain (AutoGen-style)

Three sequential Azure OpenAI calls, each scoped to one responsibility:

| Agent | Responsibility | Input | Output |
|---|---|---|---|
| Idea Agent | Generate 3 distinct post ideas | brand config + context | `ideas: list[str]` (3 items) |
| Draft Agent | Select best idea, write full LinkedIn draft, assign confidence score | best idea + brand config | `draft: str`, `confidence: float` |
| Hashtag Agent | Generate relevant hashtags for the draft | draft text + industry | `hashtags: list[str]` |

The three agents run sequentially within a single request. Output from each feeds the next. This is the "multi-agent" pattern the rubric requires.

#### Confidence Score

- Range: `0.0` to `1.0`
- Assigned by the Draft Agent based on: topical relevance, brand alignment, post structure quality
- Prompt instructs the LLM to return a numeric score alongside the draft

#### Error Handling

- Return HTTP 422 for malformed input (FastAPI default)
- Return HTTP 500 with `{"error": "<message>"}` if any OpenAI API call fails
- Log all errors to stdout with `[ERROR]` prefix for VM-side debugging

---

### 6.2 n8n Workflow

**Platform:** n8n self-hosted (Ubuntu VM lab environment)
**Export artifact:** workflow JSON file (required deliverable)

#### Node Specifications

##### Node 1 -- Schedule Trigger
- **Type:** Schedule Trigger
- **Cadence:** Weekdays (Mon-Fri), 9:00 AM UTC
- **Rationale:** Suitable cadence for a business-focused LinkedIn presence; aligns with audience active hours

##### Node 2 -- Brand Config
- **Type:** Set node
- **Purpose:** Defines FinEdge Mumbai brand parameters passed to the microservice
- **Fields to set:**

| Field | Value |
|---|---|
| `company` | `FinEdge Mumbai` |
| `industry` | `fintech` |
| `tone` | `authoritative, professional` |
| `audience` | `finance professionals, fintech community` |
| `topic` | `[current week topic -- set manually or from prior node]` |
| `dry_run` | `true` (flip to `false` for live LinkedIn posting) |

##### Node 3 -- AutoGen Microservice (HTTP Request)
- **Type:** HTTP Request node
- **Method:** POST
- **URL:** `http://<windows-host-ip>:8000/linkedin` -- n8n runs in Ubuntu WSL2 and cannot reach the Windows FastAPI microservice via localhost; the Windows host IP (WSL2 virtual adapter) must be used instead
- **Body:** JSON containing brand config fields from Node 2
- **Response format:** JSON

##### Node 4 -- Compose Final (Set node)
- **Type:** Set node
- **Purpose:** Assembles the final post string from microservice response
- **No JavaScript required** (rubric requirement)
- **Fields to set:**
  - `final_post`: `{{ $json.draft }}` + newline + `{{ $json.hashtags.join(' ') }}`
  - `confidence`: `{{ $json.confidence }}`
  - `dry_run`: passed through from Node 2

##### Node 5 -- Approval Gate (IF node)
- **Type:** IF node
- **Condition:** `confidence >= 0.75 AND dry_run == false`
  - `true` branch -> Node 6 (LinkedIn)
  - `false` branch -> Node 7 (Slack)
- **Threshold:** `0.75` (adjustable post-testing)

##### Node 6 -- LinkedIn
- **Type:** LinkedIn node (n8n built-in) or HTTP Request to LinkedIn API
- **Action:** Create a text post with `final_post` content
- **Auth:** OAuth via Google-federated LinkedIn account

##### Node 7 -- Slack
- **Type:** Slack node
- **Method:** Incoming Webhook (preferred for simplicity) or OAuth
- **Message:** Draft post + confidence score + `[DRY RUN]` label
- **Auth:** Incoming webhook URL (configured in Slack app settings)

##### Node 8 -- Logging
- **Type:** HTTP Request node (POST to FastAPI `/log` endpoint)
- **Destination:** `linkedin_log.csv` in Windows project root, written by the FastAPI `/log` endpoint
- **Fields logged:**
  - `timestamp`
  - `draft` (truncated to 500 chars for readability)
  - `confidence`
  - `routed_to` (`slack` or `linkedin`)
  - `dry_run` flag
- **Rationale:** n8n Code node sandboxes `require('fs')`, blocking direct file writes. Write to File node requires binary input. A dedicated FastAPI endpoint cleanly separates concerns -- n8n Logging node is simply an HTTP Request, and all file I/O is owned by the microservice.
- **Note on expressions:** This node sits downstream of both branch nodes (LinkedIn, Slack). `$json.*` resolves to the branch node's output, not the pipeline data. Named-node expressions (`$('Compose Final').item.json.*`) are required to reach the correct upstream fields.

---

## 7. Data Contracts

### 7.1 Request Body (`POST /linkedin`)

```json
{
  "brand": {
    "company": "FinEdge Mumbai",
    "industry": "fintech",
    "tone": "authoritative, professional",
    "audience": "finance professionals, fintech community"
  },
  "context": {
    "topic": "string -- the subject or theme for this post",
    "notes": "string (optional) -- any additional guidance"
  }
}
```

### 7.2 Response Body

```json
{
  "ideas": [
    "Post idea 1",
    "Post idea 2",
    "Post idea 3"
  ],
  "draft": "Full LinkedIn post text (300-500 words recommended for engagement)",
  "confidence": 0.87,
  "hashtags": [
    "#fintech",
    "#FinancialInnovation",
    "#MumbaiFintech"
  ]
}
```

---

## 8. Design Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Microservice framework | FastAPI | Rubric specifies FastAPI explicitly in Actions section |
| Multi-agent pattern | Sequential OpenAI API calls (3 agents) | Satisfies "AutoGen-style multi-agent" without requiring AutoGen SDK; simpler and more debuggable |
| LLM backend | Standard OpenAI API (`gpt-4.1-mini`) | Azure credentials are sandbox-specific and inaccessible outside lab VM; standard OpenAI API works locally with the same agent logic |
| n8n Compose Final | Set node, no JavaScript | Rubric explicitly states "no JavaScript required" |
| Confidence threshold | 0.75 | Starting value; rubric instructs to tune post-testing |
| Slack integration | Incoming Webhook | Simpler than OAuth for a lab; no token refresh management |
| Logging destination | `linkedin_log.csv` on Windows, written by FastAPI `/log` endpoint | n8n Code node blocks `require('fs')`; Write to File needs binary; dedicated endpoint keeps file I/O in the microservice |
| Schedule cadence | Weekdays 9:00 AM UTC | Suitable business cadence per rubric instruction; aligns with LinkedIn B2B peak hours |
| Number of ideas | 3 | Rubric says "multiple"; 3 is concrete, testable, and reasonable for a fintech context |
| dry_run flag location | Set in Brand Config node | Centralizes the flag in one place; easy to flip for live vs. test runs |

---

## 9. Acceptance Criteria

Directly maps to rubric deliverables and graded behaviors. All items verified 2026-06-28.

### Microservice

- [x] `POST /linkedin` returns valid JSON with `ideas` (list, 3 items), `draft` (string), `confidence` (float 0-1), `hashtags` (list)
- [x] Microservice starts successfully on Windows with `.\run.ps1` (bootstraps `.venv`, installs deps, launches Uvicorn)
- [x] Curl test from Windows produces correct structured JSON output (Stage 2 -- Figure 7 in reflection-FINAL.docx)
- [x] `.env.example` contains all required variable names with no actual secrets

### n8n Workflow

- [x] Workflow triggers on schedule without error
- [x] Brand Config node passes correct JSON to HTTP Request node
- [x] HTTP Request node calls `POST /linkedin` and receives a valid response
- [x] Compose Final node assembles `draft + hashtags` string without JavaScript
- [x] Approval Gate routes to Slack when `confidence < 0.75` OR `dry_run == true`
- [x] Approval Gate routes to LinkedIn when `confidence >= 0.75` AND `dry_run == false` (LinkedIn Mock node during testing)
- [x] Slack receives draft post with confidence score and `[DRY RUN]` label (Stage 4 -- Figures 19-20)
- [x] Logging node appends a row to CSV with timestamp, draft, confidence, routed_to (via FastAPI `/log` endpoint)
- [x] Full end-to-end test completes without errors (2026-06-28; linkedin_log.csv has 2 rows)

### Submission Artifacts

- [x] `main.py` -- complete, runnable FastAPI microservice
- [x] `.env.example` -- all required env variable names, no values
- [x] Exported n8n workflow JSON -- `finedge_linkedin_workflow.json` in project root
- [x] Screenshots -- 20 screenshots embedded in `reflection-FINAL.docx` Section 8
- [x] `README.md` -- setup instructions, environment variables, how to run microservice, how to import and run n8n workflow
- [x] Reflection document -- `reflection-FINAL.docx` (design decisions, challenges, trade-offs, architecture diagrams, build walkthrough)

---

## 10. Resolved Design Decisions (formerly Open Questions)

All questions resolved before build began; answers recorded in ROADMAP Decisions Log.

| # | Question | Resolution |
|---|---|---|
| OQ1 | Azure OpenAI or standard OpenAI? | Standard OpenAI API. Azure credentials are sandbox-specific and inaccessible outside the lab VM. `OPENAI_API_KEY` and `OPENAI_MODEL=gpt-4.1-mini` in `.env`. |
| OQ2 | Microsoft 365 / Excel Online for logging? | Local CSV. M365 not used. `linkedin_log.csv` written by FastAPI `/log` endpoint to Windows project root. |
| OQ3 | n8n URL/port? | `http://localhost:5678` in Ubuntu WSL2. Dashboard accessible from Windows browser via WSL2 port forwarding. |
| OQ4 | Slack channel/webhook destination? | Incoming Webhook URL configured in n8n credentials. Dry-run posts route to a personal Slack workspace for human review. |
| OQ5 | Static or dynamic `topic` in Brand Config? | Static -- hardcoded as a weekly FinEdge Mumbai topic in the Brand Config Set node. |

---

> © 2026 Brock Frary. All rights reserved.
