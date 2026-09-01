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
    nocache: bool = False


class ChatRequest(BaseModel):
    topic: str
    report: str = ""
    evidence: list = []
    question: str
    history: str = ""


@app.get("/")
def home():
    return {"message": "SynapseAI Backend Running"}


@app.post("/api/research")
def research(request: ResearchRequest):
    try:
        if not request.topic.strip():
            raise HTTPException(status_code=400, detail="Topic is required")

        result = run_research_pipeline(request.topic, nocache=request.nocache)

        return {
            "success": True,
            "topic": request.topic,
            "data": result
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/research/chat")
def research_chat(request: ChatRequest):
    """
    Grounded follow-up chat endpoint ("Ask Synapse").
    """
    try:
        if not request.question.strip():
            raise HTTPException(status_code=400, detail="Question is required")

        from agents import qa_chat_prompt, execute_prompt_with_fallback
        from pipeline_validators import extract_text_from_llm_output

        evidence_str = json.dumps(request.evidence, indent=2) if isinstance(request.evidence, list) else str(request.evidence)

        response = execute_prompt_with_fallback(
            qa_chat_prompt,
            {
                "topic": request.topic,
                "report": request.report[:10000],
                "evidence": evidence_str[:5000],
                "history": request.history[:2000],
                "question": request.question
            }
        )

        answer = extract_text_from_llm_output(response)

        return {
            "success": True,
            "answer": answer
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/research/stream")
def research_stream(topic: str, nocache: bool = False):
    """
    Server-Sent Events (SSE) endpoint for real-time live research streaming progress.
    """
    if not topic or not topic.strip():
        raise HTTPException(status_code=400, detail="Topic is required")

    def event_generator():
        for event in run_research_pipeline_stream(topic.strip(), nocache=nocache):
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)