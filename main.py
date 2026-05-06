import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

from pipeline import run_research_pipeline

load_dotenv()

app = FastAPI(title="SynapseAI Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_URL", "http://localhost:5173")],
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