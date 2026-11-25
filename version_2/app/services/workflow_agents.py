"""Two-agent, single-brief workflow for Version 2."""
from __future__ import annotations

from pathlib import Path

from app.schemas import AgentRun, Project, Requirement
from app.services.generator import generate_evidence_drafts
from app.services.llm import enabled as llm_enabled, generate_requirements
from app.services.quality import analyse
from app.services.srs import create_ieee_830_document


class RequirementsGatheringAgent:
    name = "Requirements Gathering Agent"
    responsibility = "Extracts, classifies, and quality-checks draft requirements from the single project brief."

    def run(self, project: Project, evidence: list[dict]) -> tuple[list[Requirement], str]:
        mode = "evidence-only"
        requirements = []
        if llm_enabled():
            try:
                requirements = generate_requirements(project.functionality, evidence)
                mode = "LLM-assisted"
            except (RuntimeError, ValueError) as exc:
                project.audit_log.append({"action": "llm_fallback", "detail": str(exc)})
        if not requirements:
            requirements = generate_evidence_drafts(project.functionality, evidence)
        project.requirements = requirements
        project.quality_issues = analyse(requirements)
        return requirements, mode


class SrsGenerationAgent:
    name = "SRS Generation Agent"
    responsibility = "Generates a reviewable IEEE 830 style Software Requirements Specification in Word format."

    def run(self, project: Project, output_path: Path) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(create_ieee_830_document(project))


def record_agent_run(project: Project, agent: str, responsibility: str, output: str) -> None:
    from datetime import datetime, timezone

    project.agent_runs.append(AgentRun(
        agent=agent,
        responsibility=responsibility,
        status="Completed",
        output=output,
        at=datetime.now(timezone.utc),
    ))
