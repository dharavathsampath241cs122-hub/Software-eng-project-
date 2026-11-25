from __future__ import annotations

import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.schemas import Project
from app.services.documents import chunk_text, mask_sensitive
from app.services.storage import ProjectStore
from app.services.workflow_agents import (
    RequirementsGatheringAgent,
    SrsGenerationAgent,
    record_agent_run,
)

ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parent
load_dotenv(PROJECT_ROOT / ".env")
# Keep generated projects, documents, and vectors inside Version 2 by default.
os.environ.setdefault("APP_DATA_DIR", str(PROJECT_ROOT / "data"))
os.environ.setdefault("VECTOR_DB_PATH", str(PROJECT_ROOT / "data" / "chroma"))

store = ProjectStore()
requirements_agent = RequirementsGatheringAgent()
srs_agent = SrsGenerationAgent()


class ProjectBrief(BaseModel):
    project_brief: str = Field(min_length=30, max_length=12_000)


@asynccontextmanager
async def lifespan(_: FastAPI):
    print("FinScope Version 2 running at http://127.0.0.1:8000 (Ctrl+C to stop)")
    yield


app = FastAPI(title="FinScope — Single Brief to SRS", version="2.0.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")


@app.get("/")
def home() -> FileResponse:
    return FileResponse(ROOT / "templates" / "index.html")


@app.post("/api/projects")
def create_project(request: ProjectBrief) -> JSONResponse:
    brief = request.project_brief.strip()
    if len(brief) < 30:
        raise HTTPException(422, "Enter a project brief with at least 30 characters.")

    project_id = uuid4().hex[:12]
    safe_brief = mask_sensitive(brief)
    chunks = chunk_text(safe_brief)
    evidence = [
        {
            "id": chunk.id,
            "text": chunk.text,
            "document_id": "BRIEF-001",
            "document_name": "Project brief",
            "relevance": 0.9,
        }
        for chunk in chunks
    ]
    title = next((line.strip() for line in safe_brief.splitlines() if line.strip()), "Project brief")
    if len(title) > 90:
        title = title[:87].rstrip() + "..."
    project = Project(
        id=project_id,
        functionality=title[:180],
        created_at=datetime.now(timezone.utc),
        documents=[{
            "id": "BRIEF-001",
            "name": "Project brief",
            "chunks": [
                {"id": item["id"], "text": item["text"]}
                for item in evidence
            ],
        }],
    )
    requirements, mode = requirements_agent.run(project, evidence)
    record_agent_run(
        project,
        requirements_agent.name,
        requirements_agent.responsibility,
        f"Produced {len(requirements)} draft requirement(s) using {mode}; {len(project.quality_issues)} quality finding(s) recorded.",
    )

    export_path = Path(os.environ["APP_DATA_DIR"]) / "exports" / project.id / "ieee-830-1998-srs.docx"
    srs_agent.run(project, export_path)
    record_agent_run(
        project,
        srs_agent.name,
        srs_agent.responsibility,
        "Generated the SRS Word document from the project brief and draft requirements.",
    )
    project.audit_log.append({
        "at": datetime.now(timezone.utc).isoformat(),
        "action": "srs_generated",
        "detail": "SRS document generated locally for human review.",
    })
    store.save(project)
    return JSONResponse({
        **project.model_dump(mode="json"),
        "project_brief": safe_brief,
        "srs_download_url": f"/api/projects/{project.id}/srs/download",
    })


@app.get("/api/projects/{project_id}/srs/download")
def download_srs(project_id: str) -> FileResponse:
    try:
        store.get(project_id)
    except KeyError as exc:
        raise HTTPException(404, "Project not found.") from exc
    path = Path(os.environ["APP_DATA_DIR"]) / "exports" / project_id / "ieee-830-1998-srs.docx"
    if not path.is_file():
        raise HTTPException(404, "SRS document is not available.")
    return FileResponse(
        path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=f"{project_id}-srs.docx",
    )
