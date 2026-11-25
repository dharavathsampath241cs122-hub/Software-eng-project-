"""Local IEEE 830-1998 SRS Word-document export; this module never calls an LLM."""
from __future__ import annotations

from datetime import datetime
from io import BytesIO

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

from app.schemas import Project, Requirement


def _add_requirement(document: Document, requirement: Requirement) -> None:
    document.add_heading(f"{requirement.id} — {requirement.statement}", level=3)
    document.add_paragraph(f"Priority: {requirement.priority} | Status: {requirement.approval_status} | Risk: {requirement.risk_level}")
    document.add_paragraph(f"Rationale: {requirement.business_justification}")
    if requirement.acceptance_criteria:
        document.add_paragraph("Acceptance criteria:")
        for criterion in requirement.acceptance_criteria:
            document.add_paragraph(criterion, style="List Bullet")
    if requirement.assumptions:
        document.add_paragraph(f"Assumptions: {'; '.join(requirement.assumptions)}")
    if requirement.dependencies:
        document.add_paragraph(f"Dependencies: {'; '.join(requirement.dependencies)}")
    sources = sorted({f"{item.document_name} / {item.chunk_id}" for item in requirement.evidence})
    if sources:
        document.add_paragraph(f"Source traceability: {'; '.join(sources)}")


def _add_group(document: Document, requirements: list[Requirement], empty_message: str) -> None:
    if requirements:
        for requirement in requirements:
            _add_requirement(document, requirement)
    else:
        document.add_paragraph(empty_message)


def _shade(cell, color: str = "F0EFFF") -> None:
    shading = OxmlElement("w:shd")
    shading.set(qn("w:fill"), color)
    cell._tc.get_or_add_tcPr().append(shading)


def _diagram_box(document: Document, label: str, detail: str = "") -> None:
    table = document.add_table(rows=1, cols=1)
    table.style = "Table Grid"
    cell = table.cell(0, 0)
    _shade(cell)
    cell.text = ""
    heading = cell.paragraphs[0]
    heading.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = heading.add_run(label)
    run.bold = True
    run.font.size = Pt(10)
    if detail:
        paragraph = cell.add_paragraph(detail)
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for run in paragraph.runs:
            run.font.size = Pt(9)


def _diagram_connector(document: Document, text: str) -> None:
    paragraph = document.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.paragraph_format.space_after = Pt(3)
    run = paragraph.add_run(text)
    run.bold = True
    run.font.name = "Arial"
    run.font.size = Pt(9)


def _uml_block(document: Document, lines: list[str]) -> None:
    paragraph = document.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.paragraph_format.space_before = Pt(5)
    paragraph.paragraph_format.space_after = Pt(7)
    for index, line in enumerate(lines):
        if index:
            paragraph.add_run().add_break()
        run = paragraph.add_run(line)
        run.font.name = "Consolas"
        run.font.size = Pt(8)


def _add_uml_diagrams(document: Document, project_name: str) -> None:
    """Add five readable, conceptual UML views to the generated SRS."""
    document.add_page_break()
    document.add_heading("4. UML Diagrams", level=1)
    document.add_paragraph(
        "These diagrams are conceptual drafts derived from the submitted project brief and generated requirements. "
        "Confirm actors, domain classes, transitions, and integration details with stakeholders before implementation."
    )

    document.add_heading("4.1 Class Diagram", level=2)
    document.add_paragraph(f"Conceptual information model for {project_name}.")
    _diagram_box(document, "User", "+ user_id: Identifier\n+ role: Role\n+ submitRequest()")
    _diagram_connector(document, "1  -- creates and manages -->  0..*")
    _diagram_box(document, "Project", "+ project_id: Identifier\n+ name: Text\n+ status: ProjectStatus")
    _diagram_connector(document, "1  -- contains -->  1..*")
    _diagram_box(document, "Requirement", "+ requirement_id: Identifier\n+ statement: Text\n+ priority: Priority\n+ reviewStatus: ReviewStatus")
    _diagram_connector(document, "1  -- documented by -->  1")
    _diagram_box(document, "SRS Document", "+ document_id: Identifier\n+ generatedAt: DateTime\n+ format: DocumentFormat")

    document.add_page_break()
    document.add_heading("4.2 Activity Diagram", level=2)
    document.add_paragraph("Single-brief workflow from input through specification delivery.")
    _diagram_box(document, "Initial Node", "Start")
    _diagram_connector(document, "|")
    _diagram_box(document, "Submit Project Brief", "User supplies the project description once")
    _diagram_connector(document, "v")
    _diagram_box(document, "Gather Requirements", "Requirements Gathering Agent extracts draft requirements")
    _diagram_connector(document, "|")
    _diagram_box(document, "Review Requirement Quality", "Record gaps and assumptions for human review")
    _diagram_connector(document, "v")
    _diagram_box(document, "Generate SRS", "SRS Generation Agent creates the Word specification")
    _diagram_connector(document, "|")
    _diagram_box(document, "Deliver SRS", "User downloads the draft document")
    _diagram_connector(document, "v")
    _diagram_box(document, "Final Node", "Complete")

    document.add_page_break()
    document.add_heading("4.3 Use Case Diagram", level=2)
    document.add_paragraph(f"Primary user interactions with {project_name}.")
    _uml_block(document, [
        "+-------------------- Project System --------------------+",
        "|  (Submit project brief)                                 |",
        "|  (Review draft requirements)                            |",
        "|  (Download generated SRS)                               |",
        "|  (Derive requirements)                                  |",
        "|  (Generate SRS document)                                |",
        "+--------------------------------------------------------+",
        " Project User --------> submit / review / download",
        " Requirements Agent --> derive requirements",
        " SRS Generation Agent -> generate SRS document",
    ])
    document.add_paragraph("The boundary and actor associations are conceptual; validate the project's actual user roles during review.")

    document.add_page_break()
    document.add_heading("4.4 Sequence Diagram", level=2)
    document.add_paragraph("Request sequence for creating and delivering the SRS.")
    _uml_block(document, [
        "Project User       System       Requirements Agent       SRS Agent",
        "     |                |                  |                    |",
        "     |-- brief ------>|                  |                    |",
        "     |                |-- gather ------->|                    |",
        "     |                |<-- requirements -|                    |",
        "     |                |-- generate SRS ----------------------->|",
        "     |                |<---------------------- SRS document ---|",
        "     |<-- download ---|                  |                    |",
        "     |                |                  |                    |",
    ])

    document.add_page_break()
    document.add_heading("4.5 State Chart Diagram", level=2)
    document.add_paragraph("Lifecycle states for one generated project specification.")
    _uml_block(document, [
        "[*]",
        " |",
        " v",
        "[Brief Submitted]",
        " |",
        " v",
        "[Requirements Drafted]",
        " |",
        " v",
        "[SRS Generated]",
        " |",
        " v",
        "[Ready for Review] -- approve --> [Approved] --> [*]",
        "       | request changes",
        "       v",
        "[Revision Needed] -- revise --> [Requirements Drafted]",
    ])
    document.add_paragraph("A revision returns to requirements drafting after the brief or approved decisions are updated.")


def create_ieee_830_document(project: Project) -> bytes:
    """Create an IEEE 830-1998-formatted draft from saved, non-rejected requirements."""
    document = Document()
    normal = document.styles["Normal"]
    normal.font.name = "Arial"
    normal.font.size = Pt(10)

    title = document.add_heading("Software Requirements Specification", level=0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    subtitle = document.add_paragraph(project.functionality)
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    subtitle.runs[0].bold = True
    note = document.add_paragraph("IEEE 830-1998 format — Draft for human review")
    note.alignment = WD_ALIGN_PARAGRAPH.CENTER
    document.add_paragraph(f"Generated: {datetime.now().strftime('%d %B %Y')}")

    active = [item for item in project.requirements if item.approval_status != "Rejected"]
    functional = [item for item in active if any(str(category) == "Functional" for category in item.categories)]
    interfaces = [item for item in active if any(str(category) == "Integration" for category in item.categories)]
    performance = [item for item in active if any(str(category) in {"Performance", "Availability / reliability"} for category in item.categories)]
    constraints = [item for item in active if any(str(category) == "Regulatory" for category in item.categories)]
    allocated_ids = {item.id for item in functional + interfaces + performance + constraints}
    attributes = [item for item in active if item.id not in allocated_ids]
    references = sorted({item.document_name for requirement in active for item in requirement.evidence})
    brief_text = " ".join(
        chunk.get("text", "")
        for source in project.documents
        if source.get("id") == "BRIEF-001"
        for chunk in source.get("chunks", [])
    ).strip()

    document.add_heading("1. Introduction", level=1)
    document.add_heading("1.1 Purpose", level=2)
    document.add_paragraph(f"This SRS specifies the recorded requirements for {project.functionality}. It is a generated draft and requires human review before approval.")
    document.add_heading("1.2 Scope", level=2)
    document.add_paragraph(brief_text or f"The scope of this software is {project.functionality}.")
    document.add_heading("1.3 Definitions, Acronyms, and Abbreviations", level=2)
    document.add_paragraph("SRS: Software Requirements Specification. RBI: Reserve Bank of India. KYC: Know Your Customer, where applicable.")
    document.add_heading("1.4 References", level=2)
    _add_group(document, [], "No source references were available.") if not references else [document.add_paragraph(reference, style="List Bullet") for reference in references]
    document.add_heading("1.5 Overview", level=2)
    document.add_paragraph("Section 2 describes the system context. Section 3 provides the specific requirements. Section 4 contains conceptual UML diagrams for the project workflow and information model.")

    document.add_heading("2. Overall Description", level=1)
    document.add_heading("2.1 Product Perspective", level=2)
    document.add_paragraph("The system is defined from the single project brief supplied by the user. The source brief is reproduced in Section 1.2; generated requirements in this document are drafts for review.")
    document.add_heading("2.2 Product Functions", level=2)
    selected_sdlc = project.sdlc.recommended_sdlc if project.sdlc else "Not selected"
    document.add_paragraph(f"The selected SDLC model is {selected_sdlc}. The system functions are specified in Section 3.")
    document.add_heading("2.3 User Characteristics", level=2)
    document.add_paragraph("User roles and characteristics are to be confirmed through stakeholder review.")
    document.add_heading("2.4 Constraints", level=2)
    document.add_paragraph("Regulatory, security, integration, and delivery constraints are documented in the specific requirements.")
    document.add_heading("2.5 Assumptions and Dependencies", level=2)
    document.add_paragraph("Requirement-level assumptions and dependencies are listed with the related requirement in Section 3.")

    document.add_heading("3. Specific Requirements", level=1)
    document.add_heading("3.1 Functional Requirements", level=2)
    _add_group(document, functional, "No functional requirements are currently recorded.")
    document.add_heading("3.2 External Interface Requirements", level=2)
    _add_group(document, interfaces, "No external interface requirements are currently recorded.")
    document.add_heading("3.3 Performance Requirements", level=2)
    _add_group(document, performance, "No performance or reliability requirements are currently recorded.")
    document.add_heading("3.4 Design Constraints", level=2)
    _add_group(document, constraints, "No design constraints are currently recorded.")
    document.add_heading("3.5 Software System Attributes", level=2)
    _add_group(document, attributes, "No additional quality, security, privacy, audit, or operational requirements are currently recorded.")
    _add_uml_diagrams(document, project.functionality)
    document.add_heading("5. Review Notes", level=1)
    document.add_paragraph("Requirements with Draft or Needs review status are not an approved baseline. Review the associated source evidence before approval.")

    output = BytesIO()
    document.save(output)
    return output.getvalue()
