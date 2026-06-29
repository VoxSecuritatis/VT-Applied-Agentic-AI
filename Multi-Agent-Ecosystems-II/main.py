# ================================================================
# FastAPI Microservice -- LinkedIn Content Generator
#
# VT_AGI: Multi-Agent Ecosystems (II) Module Project
# Brock Frary guiding Claude Code
# 2026-06-28
# ================================================================
# Objective:
#       Accepts brand config and topic context from n8n, then runs
#       three sequential OpenAI calls (Idea, Draft, Hashtag agents)
#       and returns structured JSON for the n8n workflow to consume.
# Inputs:
#       - POST /linkedin request body: brand config + context
#       - Environment: OPENAI_API_KEY, OPENAI_MODEL
# Outputs:
#       - JSON: ideas (list[str]), draft (str), confidence (float),
#               hashtags (list[str])
# Notes:
#   - Agents run sequentially; output of each feeds the next.
#   - Confidence score (0.0-1.0) is LLM-assigned by the Draft Agent.
#   - Uses standard OpenAI API; Azure credentials not available locally.
# ================================================================

import csv
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from openai import OpenAI
from pydantic import BaseModel

load_dotenv()

app = FastAPI(title="LinkedIn Content Generator", version="1.0.0")
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

# ------------------------------------------------
# Request / Response Models
# ------------------------------------------------

class BrandConfig(BaseModel):
    """Brand identity fields passed from the n8n Brand Config node."""
    company: str
    industry: str
    tone: str
    audience: str


class Context(BaseModel):
    """Topic context for this post run."""
    topic: str
    notes: str = ""


class LinkedInRequest(BaseModel):
    """Full request body for POST /linkedin."""
    brand: BrandConfig
    context: Context


class LinkedInResponse(BaseModel):
    """Structured response returned to n8n."""
    ideas: list[str]
    draft: str
    confidence: float
    hashtags: list[str]


class LogEntry(BaseModel):
    """Log payload posted by the n8n Logging node after each run."""
    final_post: str
    confidence: float
    dry_run: bool


# ================================================================
# Agent Functions
# ================================================================
# Objective:
#       Three sequential LLM calls implementing the multi-agent chain:
#       Idea Agent -> Draft Agent -> Hashtag Agent. Each is a pure
#       function that returns a parsed Python value.
# Inputs:
#       - brand config, context, shared OpenAI client
# Outputs:
#       - ideas: list[str]  (3 items)
#       - draft: str, confidence: float
#       - hashtags: list[str]
# Notes:
#   - Each agent instructs the LLM to return only valid JSON.
#   - json.JSONDecodeError propagates up to the endpoint error handler.
# ================================================================

def run_idea_agent(brand: BrandConfig, context: Context) -> list[str]:
    """Generate 3 distinct LinkedIn post ideas for the given brand and topic."""
    notes_line = f"Additional notes: {context.notes}" if context.notes else ""
    prompt = (
        f"You are a LinkedIn content strategist for {brand.company}, "
        f"a {brand.industry} company.\n"
        f"Tone: {brand.tone}\n"
        f"Audience: {brand.audience}\n"
        f"Topic: {context.topic}\n"
        f"{notes_line}\n\n"
        "Generate exactly 3 distinct LinkedIn post ideas. "
        'Return them as a JSON array of strings: ["idea 1", "idea 2", "idea 3"]\n'
        "Return only the JSON array, no other text."
    )
    response = client.chat.completions.create(
        model=os.environ["OPENAI_MODEL"],
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
    )
    return json.loads((response.choices[0].message.content or "").strip())


def run_draft_agent(ideas: list[str], brand: BrandConfig) -> tuple[str, float]:
    """Select the strongest idea and write a full LinkedIn draft with a confidence score."""
    ideas_block = "\n".join(f"{i + 1}. {idea}" for i, idea in enumerate(ideas))
    prompt = (
        f"You are a LinkedIn ghostwriter for {brand.company}, "
        f"a {brand.industry} company.\n"
        f"Tone: {brand.tone}\n"
        f"Audience: {brand.audience}\n\n"
        f"Post ideas:\n{ideas_block}\n\n"
        "Select the strongest idea and write a full LinkedIn post (150-300 words). "
        "The post must be engaging, professional, and suited to the audience.\n\n"
        "Return your response as JSON with this exact structure:\n"
        '{"draft": "the full post text here", "confidence": 0.85}\n\n'
        "The confidence score (0.0-1.0) reflects topical relevance, brand alignment, "
        "and post quality. Return only the JSON, no other text."
    )
    response = client.chat.completions.create(
        model=os.environ["OPENAI_MODEL"],
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5,
    )
    result = json.loads((response.choices[0].message.content or "").strip())
    draft = result["draft"]
    confidence = max(0.0, min(1.0, float(result["confidence"])))
    return draft, confidence


def run_hashtag_agent(draft: str, industry: str) -> list[str]:
    """Generate 5-8 relevant LinkedIn hashtags for the draft post."""
    prompt = (
        f"Generate relevant LinkedIn hashtags for the following {industry} post.\n\n"
        f"Post:\n{draft}\n\n"
        "Return 5-8 hashtags as a JSON array of strings. Each must start with #.\n"
        'Example: ["#fintech", "#FinancialInnovation", "#MumbaiFintech"]\n'
        "Return only the JSON array, no other text."
    )
    response = client.chat.completions.create(
        model=os.environ["OPENAI_MODEL"],
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )
    return json.loads((response.choices[0].message.content or "").strip())


# ================================================================
# Endpoint
# ================================================================
# Objective:
#       Single POST endpoint that orchestrates the three-agent chain
#       and returns the assembled response to n8n.
# Inputs:
#       - LinkedInRequest body (validated by Pydantic)
# Outputs:
#       - 200: LinkedInResponse JSON
#       - 500: {"error": "<message>"} on any agent failure
# Notes:
#   - FastAPI handles 422 automatically for malformed request bodies.
#   - JSONResponse bypasses response_model validation for error cases.
# ================================================================

@app.post("/linkedin", response_model=LinkedInResponse)
async def generate_linkedin_post(request: LinkedInRequest) -> LinkedInResponse | JSONResponse:
    """Run the three-agent chain and return ideas, draft, confidence, and hashtags."""
    try:
        print(f"[INFO] Idea agent starting -- topic: {request.context.topic}")
        ideas = run_idea_agent(request.brand, request.context)
        print(f"[INFO] Idea agent complete -- {len(ideas)} ideas generated")

        print("[INFO] Draft agent starting")
        draft, confidence = run_draft_agent(ideas, request.brand)
        print(f"[INFO] Draft agent complete -- confidence: {confidence:.2f}")

        print("[INFO] Hashtag agent starting")
        hashtags = run_hashtag_agent(draft, request.brand.industry)
        print(f"[INFO] Hashtag agent complete -- {len(hashtags)} hashtags")

        return LinkedInResponse(
            ideas=ideas,
            draft=draft,
            confidence=confidence,
            hashtags=hashtags,
        )

    except json.JSONDecodeError as exc:
        print(f"[ERROR] LLM returned unparseable JSON: {exc}")
        return JSONResponse(
            status_code=500,
            content={"error": f"LLM returned unparseable JSON: {exc}"},
        )
    except Exception as exc:
        print(f"[ERROR] Agent chain failed: {exc}")
        return JSONResponse(status_code=500, content={"error": str(exc)})


# ================================================================
# Logging Endpoint
# ================================================================
# Objective:
#       Receives run metadata from the n8n Logging node and appends
#       a CSV row to linkedin_log.csv in the project root.
# Inputs:
#       - LogEntry body: final_post, confidence, dry_run
# Outputs:
#       - 200: {"status": "logged"}
#       - 500: {"error": "<message>"} on write failure
# Notes:
#   - routed_to is derived from dry_run; CSV is created if absent.
#   - draft is truncated to 500 chars to keep the CSV readable.
# ================================================================

LOG_FILE = Path(__file__).parent / "linkedin_log.csv"
LOG_HEADERS = ["timestamp", "draft", "confidence", "routed_to", "dry_run"]


@app.post("/log")
async def log_run(entry: LogEntry) -> JSONResponse:
    """Append a CSV row recording the outcome of one workflow run."""
    try:
        routed_to = "slack" if entry.dry_run else "linkedin"
        row = [
            datetime.now(timezone.utc).isoformat(),
            entry.final_post[:500],
            entry.confidence,
            routed_to,
            entry.dry_run,
        ]
        write_header = not LOG_FILE.exists()
        with LOG_FILE.open("a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if write_header:
                writer.writerow(LOG_HEADERS)
            writer.writerow(row)
        print(f"[INFO] Run logged -- confidence: {entry.confidence}, routed_to: {routed_to}")
        return JSONResponse(content={"status": "logged"})
    except Exception as exc:
        print(f"[ERROR] Log write failed: {exc}")
        return JSONResponse(status_code=500, content={"error": str(exc)})

# © 2026 Brock Frary. All rights reserved.
