import os
import json
import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

from pipeline import run_research_pipeline, run_research_pipeline_stream

load_dotenv()

app = FastAPI(title="SynapseAI Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        os.getenv(
            "FRONTEND_URL",
            "https://synapse-ai-green.vercel.app"
        ),
        "*"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ResearchRequest(BaseModel):
    topic: str


@app.get("/")
def home():
    return {"message": "SynapseAI Backend Running"}


@app.post("/api/research")
def research(request: ResearchRequest):
    try:
        if not request.topic.strip():
            raise HTTPException(status_code=400, detail="Topic is required")

        result = run_research_pipeline(request.topic)

        return {
            "success": True,
            "topic": request.topic,
            "data": result
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/research/stream")
def research_stream(topic: str):
    """
    Server-Sent Events (SSE) endpoint for real-time live research streaming progress.
    """
    if not topic or not topic.strip():
        raise HTTPException(status_code=400, detail="Topic is required")

    def event_generator():
        for event in run_research_pipeline_stream(topic.strip()):
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )