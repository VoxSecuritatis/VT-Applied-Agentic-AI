# AI-Powered LinkedIn Content Automation

##### VT_AGI: Multi-Agent Ecosystems (II) Module Project | Brock Frary | Published: 2026-06-28 | Updated: 2026-06-30

Automated LinkedIn post pipeline for FinEdge Mumbai. A FastAPI microservice chains three sequential OpenAI agents -- Idea, Draft, and Hashtag -- within a single HTTP call. An n8n workflow handles scheduling, approval gating, Slack review, and CSV logging without human intervention.

![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.138-009688?logo=fastapi&logoColor=white)
![n8n](https://img.shields.io/badge/n8n-self--hosted-EA4B71)
![OpenAI](https://img.shields.io/badge/OpenAI-gpt--4.1--mini-412991?logo=openai&logoColor=white)
![Platform](https://img.shields.io/badge/Platform-Windows%20%2B%20Ubuntu%20WSL2-0078D6?logo=windows&logoColor=white)

---

## Primary Project Artifact

### [Reflection: AI-Powered LinkedIn Content Automation](./reflection-final.pdf)

---

## About This Project

This is the module project for **VT_AGI: Multi-Agent Ecosystems (II)**, part of the *Applied Agentic AI: Systems, Design & Impact* course at Virginia Tech.

The project implements an AutoGen-inspired multi-agent content pipeline, but without the AutoGen SDK. Three discrete OpenAI calls are chained sequentially inside a FastAPI microservice, making the agent hand-offs explicit and easy to inspect.

An n8n workflow running in Ubuntu WSL2 orchestrates the pipeline on a weekday schedule, routes content through a confidence-based approval gate, and logs every run for threshold tuning.

The primary technical challenges were around Windows/WSL2 cross-boundary networking and n8n expression scoping downstream of branch nodes. Both are documented in detail in `reflection-final.pdf` and in the Key Learnings section below.

---

## Architecture

```text
[n8n: Schedule Trigger]  -- Weekdays, 9:00 AM UTC
        |
        v
[n8n: Brand Config]  -- FinEdge Mumbai parameters + dry_run flag
        |
        v
[n8n: HTTP Request]  -- POST http://<windows-host-ip>:8000/linkedin
        |
        v  FastAPI: Three-Agent Chain (single request)
        |    Idea Agent     -> 3 post concepts
        |    Draft Agent    -> draft text + confidence score (0.0-1.0)
        |    Hashtag Agent  -> 5-8 relevant hashtags
        |  Returns structured JSON
        |
        v
[n8n: Compose Final]  -- Set node assembles draft + hashtags; no JavaScript
        |
        v
[n8n: Approval Gate]  -- confidence >= 0.75 AND dry_run == false?
        |                    |
       YES                   NO
        v                    v
  [LinkedIn node]       [Slack node]
  (live publish)        (human review, [DRY RUN] label)
        |                    |
        +--------+-----------+
                 v
        [n8n: Logging node]  -- POST /log -> linkedin_log.csv
```

n8n runs in Ubuntu WSL2. The FastAPI microservice runs on Windows at port `8000`.

The HTTP Request nodes use the WSL2 Windows host IP rather than `localhost` to cross the boundary between the two environments.

---

## How the Agent Chain Works

All three agents run sequentially within a single `POST /linkedin` request. The output of each agent feeds directly into the next.

| Agent | Input | Output |
|---|---|---|
| **Idea Agent** | Brand config + topic | 3 distinct post concepts, returned as a JSON array |
| **Draft Agent** | 3 ideas + brand config | Full post draft, 150-300 words, plus confidence score |
| **Hashtag Agent** | Draft text + industry | 5-8 relevant hashtags, returned as a JSON array |

The confidence score, from `0.0` to `1.0`, is assigned by the Draft Agent based on topical relevance, brand alignment, and post structure quality.

In testing, `gpt-4.1-mini` returned scores consistently above `0.90` for FinEdge Mumbai prompts.

---

## Key Design Decisions

| Decision | Choice | Rationale |
|---|---|---|
| FastAPI vs. AutoGen SDK | FastAPI | No SDK lock-in; the sequential chain pattern is explicit, portable, and easy to debug |
| Standard OpenAI vs. Azure OpenAI | Standard OpenAI API | Azure credentials are sandbox-specific and inaccessible outside the lab VM; same agent logic, different environment variables |
| n8n in WSL2 vs. native Windows | WSL2 | n8n's Node.js dependency runs cleanly in Linux; avoids Windows PATH conflicts with nvm-managed Node |
| CSV logging via FastAPI `/log` | Dedicated endpoint | n8n Code node sandboxes `require('fs')`; Write to File needs binary input; a FastAPI endpoint gives the microservice clean ownership of all file I/O |
| Confidence threshold | `0.75` | Conservative starting point; model consistently returns `0.90+`, so the gate provides a safety margin without blocking quality content |

---

## Key Learnings

### WSL2 / Windows interop

Launching n8n from PowerShell via `wsl bash -c ...` causes Windows PATH entries to shadow the nvm-managed Node.js binary, breaking n8n's startup.

The resolution is to start n8n from an interactive WSL terminal. The interactive terminal sources `.bashrc`, setting the nvm PATH before any Windows entries are appended. Non-interactive shells do not source `.bashrc`.

### n8n expression scoping after branch nodes

When a node sits downstream of an IF, Slack, or HTTP Request node, `$json` resolves to that branch node's output, not the original pipeline data.

This caused `422` errors in the Logging node because `$json.final_post` resolved to the Slack response object.

Named-node expressions fix the issue:

```text
$('Compose Final').item.json.final_post
```

This reaches the correct upstream data regardless of which branch path arrived at the node. The same pattern applies to any n8n workflow with converging branches.

### Slack body formatting

Using JSON mode in the n8n HTTP Request body caused a "bad control character" parse error when the post draft contained newline sequences.

Switching to "Using Fields Below" mode resolved this because n8n handles character escaping internally when values are entered as individual named fields.

---

## Tech Stack

| Layer | Technology | Version / Notes |
|---|---|---|
| Orchestration | n8n, self-hosted in Ubuntu WSL2 | 8-node workflow; no JavaScript |
| Microservice | FastAPI + Uvicorn | FastAPI `0.138`; Uvicorn `0.49.0`; Python `3.12` |
| LLM | OpenAI `gpt-4.1-mini` | 3 sequential calls per run |
| Agent pattern | Sequential chain, AutoGen-inspired | No AutoGen SDK dependency |
| Logging | CSV via FastAPI `/log` endpoint | Written to Windows project root |
| Routing: review | Slack Incoming Webhook | Dry-run and low-confidence posts |
| Routing: publish | LinkedIn OAuth | Mock node during testing |
| Launcher | PowerShell `run.ps1` | Bootstraps `.venv`, installs dependencies, starts Uvicorn |

---

## Prerequisites

| Requirement | Version / Notes |
|---|---|
| Python | `3.12+` on Windows |
| Node.js | `18+` in Ubuntu WSL2, via nvm |
| n8n | Latest self-hosted version |
| OpenAI API key | Standard OpenAI API key |
| OpenAI model | `gpt-4.1-mini` recommended |

---

## Setup

### 1. Install n8n in Ubuntu WSL2

```bash
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
source ~/.bashrc
nvm install 24
npm install -g n8n
n8n start
```

The n8n dashboard will be available at:

```text
http://localhost:5678
```

Always start n8n from an **interactive WSL terminal**, not from PowerShell, to ensure `.bashrc` sets the nvm PATH correctly.

---

### 2. Clone and configure the project

```powershell
git clone https://github.com/VoxSecuritatis/VT-Applied-Agentic-AI.git
cd VT-Applied-Agentic-AI\Multi-Agent-Ecosystems-II
copy .env.example .env
```

Edit `.env` and add your `OPENAI_API_KEY`.

The model is pre-set to:

```text
gpt-4.1-mini
```

---

### 3. Start the FastAPI microservice

```powershell
.\run.ps1
```

`run.ps1` creates `.venv` with Python 3.12 if missing, installs `requirements.txt`, and starts Uvicorn at:

```text
http://0.0.0.0:8000
```

The FastAPI docs are available at:

```text
http://localhost:8000/docs
```

---

### 4. Import the n8n workflow

Open n8n:

```text
http://localhost:5678
```

Then import the workflow:

```text
Workflows -> Import from File -> finedge_linkedin_workflow.json
```

Find your WSL2 Windows host IP:

```bash
ip route show default | awk '/default/ {print $3}'
```

In the workflow, update the two HTTP Request nodes by replacing:

```text
YOUR_WSL2_HOST_IP
```

with the IP returned by the command, for example:

```text
172.x.x.1
```

In the Slack node, replace the placeholder webhook path with your Slack Incoming Webhook URL from your Slack app settings.

---

## Environment Variables

| Variable | Description |
|---|---|
| `OPENAI_API_KEY` | OpenAI API key |
| `OPENAI_MODEL` | Model name; default is `gpt-4.1-mini` |

Never commit `.env`. It is listed in `.gitignore`.

Only `.env.example` is committed.

---

## API Reference

### `POST /linkedin`

Runs the three-agent chain and returns structured content.

#### Request body

```json
{
  "brand": {
    "company": "FinEdge Mumbai",
    "industry": "fintech",
    "tone": "authoritative, professional",
    "audience": "finance professionals, fintech community"
  },
  "context": {
    "topic": "RBI digital lending guidelines update",
    "notes": "optional additional guidance"
  }
}
```

#### Response body

```json
{
  "ideas": ["...", "...", "..."],
  "draft": "Full LinkedIn post text, 150-300 words...",
  "confidence": 0.87,
  "hashtags": ["#fintech", "#FinancialInnovation", "#MumbaiFintech"]
}
```

#### Error codes

| Code | Condition |
|---|---|
| `422` | Malformed or missing required fields |
| `500` | OpenAI call failed or returned unparseable JSON |

---

### `POST /log`

Called by the n8n Logging node after each run.

This endpoint appends one row to:

```text
linkedin_log.csv
```

#### Request body

```json
{
  "final_post": "string",
  "confidence": 0.87,
  "dry_run": false
}
```

#### Response body

```json
{
  "status": "logged"
}
```

The endpoint creates `linkedin_log.csv` with headers if the file does not already exist.

---

## n8n Workflow

### Nodes

| # | Node | Type | Purpose |
|---|---|---|---|
| 1 | Schedule Trigger | Schedule | Fires weekdays at 9:00 AM UTC |
| 2 | Brand Config | Set | FinEdge Mumbai brand parameters plus `dry_run` flag |
| 3 | AutoGen Microservice | HTTP Request | Calls `POST /linkedin` on the FastAPI microservice |
| 4 | Compose Final | Set | Assembles draft plus hashtags; propagates `confidence` and `dry_run` |
| 5 | Approval Gate | IF | Routes on `confidence >= 0.75 AND dry_run == false` |
| 6 | LinkedIn Mock | Set | Live publish path; connect LinkedIn OAuth to activate |
| 7 | Slack | HTTP Request | Sends draft via Incoming Webhook for human review |
| 8 | Logging | HTTP Request | Posts to `POST /log`; appends row to `linkedin_log.csv` |

---

## Dry-run vs. Live Mode

Set `dry_run` in the **Brand Config** node.

| Mode | Behavior |
|---|---|
| `dry_run: true` | Default. All posts route to Slack regardless of confidence. |
| `dry_run: false` | Approval Gate is active. High-confidence posts go to LinkedIn. |

---

## Confidence Threshold

Default threshold:

```text
0.75
```

Adjust this value in the **Approval Gate** node.

The `confidence` column in `linkedin_log.csv` is the primary signal for threshold tuning.

---

## Expression Note

The Logging node sits downstream of both branch nodes. At that position, `$json.*` resolves to the branch output, not the pipeline data.

For that reason, the Logging node uses named-node expressions:

```text
$('Compose Final').item.json.final_post
```

This ensures the Logging node reads the correct upstream data regardless of whether the workflow routed through Slack or LinkedIn.

---

## Log File

`linkedin_log.csv` is created in the project root on the first workflow run.

The file is gitignored.

| Field | Description |
|---|---|
| `timestamp` | ISO 8601 run time |
| `draft` | Post text, truncated to 500 characters |
| `confidence` | Score returned by Draft Agent |
| `routed_to` | `slack` or `linkedin` |
| `dry_run` | `true` or `false` |

---

## Project Structure

```text
.
├── main.py                        # FastAPI microservice: POST /linkedin and POST /log
├── run.ps1                        # Bootstraps .venv and launches microservice
├── requirements.txt               # Pinned direct dependencies: FastAPI, Uvicorn, OpenAI
├── .env.example                   # Variable names template; no secrets
├── finedge_linkedin_workflow.json # Importable n8n workflow
├── README.md                      # Project README
├── PRD.md                         # Product requirements document
├── ROADMAP.md                     # Build plan and stage completion log
└── reflection-final.pdf           # Portfolio document with diagrams, design decisions,
                                   # challenges, build walkthrough, and screenshots
```

---

## Portfolio Document

`reflection-final.pdf` is the full project narrative.

It includes:

- End-to-end workflow flowchart
- Three-lane swimlane architecture diagram
- Design decisions and rationale
- Challenges encountered and how they were resolved
- Trade-offs table
- Personal reflections on the course, WSL2 stack, n8n, and the document tooling built alongside this project
- Build walkthrough with 20 annotated screenshots covering every ROADMAP stage

---

## Copyright

© 2026 Brock Frary. All rights reserved.
