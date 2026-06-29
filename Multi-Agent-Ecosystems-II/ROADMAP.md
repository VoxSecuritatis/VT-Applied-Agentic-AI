# **ROADMAP**
## AI-Powered LinkedIn Content Automation -- FinEdge Mumbai

> **Golden source of truth:** `context/1762523953_course_end_project_problem_statement_20260627_001.md`
> All scope decisions trace back to this document. Do not add features not grounded in the rubric.

---

## Stage 0 -- Planning and PRD

- [x] Draft PRD translating the rubric into concrete technical requirements
- [x] Resolve open design decisions (logging destination, confidence threshold, schedule cadence, number of ideas)
- [x] Confirm Azure OpenAI as LLM backend (Microsoft ecosystem)
- [x] Confirm logging destination (Azure Table Storage / Azure SQL / Excel via OneDrive)

**Status:** Complete

---

## Stage 1 -- Environment Setup (Windows + Ubuntu WSL2)

- [x] Verify Node.js version in Ubuntu WSL (`node --version`) [SCREENSHOT REQUIRED]
- [x] Verify Python 3.12 available on local machine (`py -3.12 --version`) [SCREENSHOT REQUIRED]
- [x] Install n8n in Ubuntu WSL (`npm install -g n8n`) [SCREENSHOT REQUIRED]
- [x] Launch n8n in Ubuntu WSL and confirm dashboard loads at `http://localhost:5678` [SCREENSHOT REQUIRED]
- [x] Rebuild Python `.venv` for Windows (original venv was Linux-only, recreated as `.venv`)
- [x] Install FastAPI and dependencies (`uvicorn`, `python-dotenv`, `openai`)
- [x] Create `requirements.txt` with pinned direct dependencies
- [x] Create `run.ps1` -- builds `.venv` if missing, activates, installs deps, launches microservice
- [x] Update `.env` and `.env.example` -- switched from Azure OpenAI to standard OpenAI (`OPENAI_API_KEY`, `OPENAI_MODEL=gpt-4.1-mini`)
- [x] Confirm OpenAI API key is valid (`curl` or quick Python test) [SCREENSHOT REQUIRED]

**Decisions recorded:**
- Switched from Azure OpenAI to standard OpenAI API -- Azure credentials are sandbox-specific and do not work outside the lab VM
- n8n runs in Ubuntu WSL2 (not native Windows); FastAPI microservice runs on Windows via `.venv`

**Verified when:** `node --version` returns 18+ in WSL, n8n dashboard loads at `http://localhost:5678`, `.\run.ps1` starts uvicorn without error, `curl http://localhost:8000/docs` returns FastAPI docs page, `.env` present with all required keys.

**Status:** Complete

---

## Stage 2 -- FastAPI Microservice (`main.py`)

- [x] Implement `POST /linkedin` endpoint
- [x] Accept brand config + context as JSON input
- [x] Implement idea generation (3 ideas)
- [x] Implement draft post generation with confidence score
- [x] Implement hashtag generation
- [x] Return structured JSON response
- [x] Add logging and error handling
- [x] Launch microservice via `.\run.ps1` [SCREENSHOT REQUIRED]
- [x] Test endpoint with `curl` and verify JSON response shape [SCREENSHOT REQUIRED]

**Verified when:** `curl -X POST http://localhost:8000/linkedin -H "Content-Type: application/json" -d '{"brand":{"company":"FinEdge Mumbai","industry":"fintech","tone":"authoritative, professional","audience":"finance professionals"},"context":{"topic":"test"}}' ` returns valid JSON with `ideas` (list, 3 items), `draft` (string), `confidence` (float 0.0-1.0), `hashtags` (list).

**Status:** Complete

---

## Stage 3 -- n8n Workflow

- [x] Create new workflow in n8n dashboard [SCREENSHOT REQUIRED]
- [x] Add Schedule Trigger node (weekdays, 9:00 AM UTC) [SCREENSHOT REQUIRED]
- [x] Add Brand Config node (FinEdge Mumbai brand parameters) [SCREENSHOT REQUIRED]
- [x] Add HTTP Request node -> FastAPI `/linkedin` endpoint [SCREENSHOT REQUIRED]
- [x] Add Set node to compose final post text + hashtags (no JavaScript) [SCREENSHOT REQUIRED]
- [x] Add Approval Gate node (confidence >= 0.75 AND dry_run == false) [SCREENSHOT REQUIRED]
- [x] Add LinkedIn routing branch (live / above threshold) [SCREENSHOT REQUIRED]
- [x] Add Slack routing branch (dry-run or below threshold) [SCREENSHOT REQUIRED]
- [x] Add Logging node (timestamp, draft text, confidence score -> `linkedin_log.csv`) [SCREENSHOT REQUIRED]
- [x] Test each node individually with Execute Node [SCREENSHOT REQUIRED]
- [x] Test full workflow end-to-end [SCREENSHOT REQUIRED]

**Verified when:** Full n8n workflow executes end-to-end without errors. Slack receives a message with `[DRY RUN]` label and confidence score. CSV log file (`linkedin_log.csv`) has a new row appended with timestamp, draft, confidence, and routed_to fields.

**Decisions recorded:**
- Logging node uses named-node expressions `$('Compose Final').item.json.*` -- required because Logging sits downstream of branch nodes (Slack/LinkedIn) whose output does not carry original pipeline fields
- LinkedIn Mock wired to Logging as second input so both branches log their run
- CSV file written to Windows project root via FastAPI `/log` endpoint (n8n Code node blocks `require('fs')`)

**Status:** Complete -- all 8 nodes built and tested; end-to-end run confirmed 2026-06-28; linkedin_log.csv has 2 rows

---

## Stage 4 -- Integration Testing and Debugging

- [x] Test microservice independently with curl [SCREENSHOT REQUIRED] -- completed in Stage 2
- [x] Test each n8n node with Execute Node [SCREENSHOT REQUIRED] -- completed during Stage 3 build
- [x] Run full workflow end-to-end [SCREENSHOT REQUIRED] -- completed 2026-06-28
- [x] Confirm Slack receives message with `[DRY RUN]` label [SCREENSHOT REQUIRED] -- 21-04-Confirm Slack receives message with DRY RUN lab.jpg
- [x] Confirm `linkedin_log.csv` has a new row appended [SCREENSHOT REQUIRED] -- 17-03-Log Sample.jpg; 2 rows confirmed 2026-06-28
- [x] Adjust confidence threshold as needed and document rationale -- model returns 0.9 consistently; 0.75 threshold appropriate; no change needed
- [x] Resolve and document any errors -- all errors resolved during Stage 3 build

**Verified when:** All acceptance criteria in PRD Section 9 pass. Screenshots captured for each major stage. Confidence threshold tuned and documented. No unresolved errors in workflow execution log.

**Status:** Complete -- all items verified 2026-06-28; 21 screenshots captured

---

## Stage 5 -- Deliverables Assembly

- [x] `main.py` -- finalized microservice code; Pylance clean (union return type, `or ""` null guards on message.content)
- [x] `.env.example` -- environment variable template (no secrets)
- [x] Exported n8n workflow JSON -- `finedge_linkedin_workflow.json` in project root
- [x] Screenshots of successful runs -- 20 screenshots in `screenshots_for_project/`; embedded in reflection-FINAL.docx Section 8
- [x] `README.md` -- setup and run instructions; corrected and updated 2026-06-28
- [x] Short reflection -- design decisions, challenges, trade-offs; generated as reflection-FINAL.docx via generate_reflection.py
- [x] Architecture diagrams -- flowchart (Figure A) and swimlane (Figure B) rendered via generate_diagrams.py (maroon theme), embedded in reflection-FINAL.docx Section 2 with explainer text
- [x] Document audit complete -- ASCII-clean, sections 1-8 sequential, figures contiguous (gap at 17 closed by renumbering), 26 images embedded; stamped as reflection-FINAL.docx 2026-06-28
- [x] Document branding -- VT / Simplilearn / Microsoft logo banner header, narrow (0.5in) margins, footer (course / Brock Frary / 2026-06-28 left, page number right)
- [x] generate_reflection.py front matter updated -- inputs list diagrams and logos explicitly; regenerated and stamped as reflection-FINAL.docx 2026-06-28

**Decisions recorded:**
- Reflection, diagrams, and docx extraction are generated programmatically (generate_reflection.py, generate_diagrams.py, decompose_reflection.py) rather than edited by hand, so the deliverable is reproducible
- matplotlib and python-docx are development-only dependencies; intentionally kept out of requirements.txt since the microservice does not need them at runtime
- Diagram theme color set to maroon #861F41 to match reflection.docx headings

**Verified when:** All six submission artifacts present and reviewed: `main.py`, `.env.example`, exported n8n workflow JSON, screenshots, `README.md`, and reflection document. n8n workflow JSON imports cleanly into a fresh n8n instance.

**Status:** Complete -- all six submission artifacts present and reviewed; reflection-FINAL.docx stamped 2026-06-28; export to PDF from Word is the only remaining manual step

---

## Open Design Decisions

| Decision | Choice | Status | Source |
|---|---|---|---|
| Logging destination | Local CSV file on VM (`/home/user/linkedin_log.csv`) | Resolved | PRD Section 8 |
| Confidence threshold | 0.75 | Resolved | PRD Section 8 |
| Schedule cadence | Weekdays (Mon-Fri), 9:00 AM UTC | Resolved | PRD Section 6.2 |
| Number of post ideas | 3 | Resolved | PRD Section 8 |
| LLM backend | Standard OpenAI API (`gpt-4.1-mini`) | Resolved | Stage 1 decision |

---

## Decisions Log

| Date | Decision | Rationale |
|---|---|---|
| 2026-06-27 | FastAPI chosen over AutoGen SDK | Rubric says "AutoGen-inspired/style"; FastAPI satisfies requirement without SDK dependency |
| 2026-06-27 | Microsoft-first ecosystem | Course is Microsoft-first; Azure services preferred for logging and LLM backend |
| 2026-06-27 | Switched LLM backend from Azure OpenAI to standard OpenAI | Azure credentials are sandbox-specific and inaccessible outside the lab VM; standard OpenAI API works locally |
| 2026-06-28 | Screenshots and reflection delivered as PDF from Word document | Simpler to compile and format than markdown; Word allows easy screenshot embedding with captions |
| 2026-06-28 | reflection-FINAL.docx keeps real author identity (byline, screenshot usernames, private IP) | Author intentionally publishes under real name; anonymization rule waived for this named-author portfolio deliverable. Standing rule still applies to any anonymous artifacts |
| 2026-06-28 | Closed Figure 17 gap by renumbering rather than waiting for the CSV sample screenshot | CSV logging is already shown in Figure 16 (Logging node) and both architecture diagrams; a separate sample image is not required |

---

> © 2026 Brock Frary. All rights reserved.
