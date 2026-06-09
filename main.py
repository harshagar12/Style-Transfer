import json, uuid, os, re
import tempfile
import threading
import requests
import google.generativeai as genai

from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import FileResponse
from docx import Document

from config import METADATA_DIR, GOTENBERG_URL
from models import GenerateRequest, MarkdownGenerateRequest, PDFGenerateRequest
from utils_extraction import extract_metadata_from_docx, extract_metadata_from_pdf
from utils_generation import detect_structure, generate_docx
from utils_markdown import markdown_to_html_with_styling

app = FastAPI()

_jobs: dict[str, dict] = {}
_jobs_lock = threading.Lock()

# API Endpoint for Uploading a Template File
@app.post("/upload-template")
async def upload_template(
    file: UploadFile = File(...),
    template_name: str = Form(None)
):

    filename = file.filename or ""
    is_pdf = filename.lower().endswith(".pdf")
    suffix = ".pdf" if is_pdf else ".docx"

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp.write(await file.read())
    tmp.close()

    if is_pdf:
        metadata = extract_metadata_from_pdf(tmp.name)
    else:
        doc = Document(tmp.name)
        metadata = extract_metadata_from_docx(doc)

    if template_name and template_name.strip():
        if "title" not in metadata or not isinstance(metadata["title"], dict):
            metadata["title"] = {}
        metadata["title"]["text"] = template_name.strip()

    template_id = uuid.uuid4().hex[:8]
    with open(os.path.join(METADATA_DIR, f"{template_id}.json"), "w") as f:
        json.dump(metadata, f, indent=2, default=str)

    os.unlink(tmp.name)
    return {
        "template_id": template_id,
        "message": "Template processed",
        "title": metadata.get("title", {}),
        "table_of_contents": metadata.get("table_of_contents", []),
        "sections_count": len(metadata.get("sections", []))
    }

# API Endpoint for Generating Document
@app.post("/generate-document")
async def generate_document(req: GenerateRequest):
    try:
        blocks = detect_structure(req.plain_text)
        out_path = generate_docx(req.template_id, blocks)
        return FileResponse(out_path, media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document", filename="generated.docx")
    except FileNotFoundError as e:
        return {"error": str(e)}

def _run_markdown_job(job_id: str, req: MarkdownGenerateRequest):
    """Executed in a background thread; writes result into _jobs."""
    try:
        meta_path = os.path.join(METADATA_DIR, f"{req.template_id}.json")
        if not os.path.exists(meta_path):
            raise FileNotFoundError(f"Template '{req.template_id}' not found")

        with open(meta_path) as f:
            metadata = json.load(f)

        toc       = metadata.get("table_of_contents", [])
        sections  = metadata.get("sections", [])
        title_text = metadata.get("title", {}).get("text", "").strip() or "Generated Report"

        section_schema_lines = []
        for index, heading in enumerate(toc):
            sec        = sections[index] if index < len(sections) else {}
            components = sec.get("components", [])
            section_schema_lines.append(f"## {heading}")
            if components:
                section_schema_lines.append(f"  Elements: {', '.join(components)}")
        section_schema = "\n".join(section_schema_lines)

        template_context = f"""
Template Structure (follow this EXACTLY — same number of sections, same order, same heading names, same section elements):

{section_schema}

Original Template Title: {title_text} (Please generate a new, relevant title based on the prompt)
"""

        full_prompt = f"""{template_context}
Generate a professional report in Markdown using this prompt:
{req.prompt}

STRICT INSTRUCTIONS:
1. First line MUST be a level 1 heading ("# <Your Generated Title>") that reflects the prompt's subject.
2. You MUST produce exactly {len(toc)} sections in the SAME ORDER as the schema above.
3. Each section MUST use the EXACT heading text shown in the schema.
4. Inside each section, include the following types of content blocks (order is flexible, but each listed type should appear at least once):
   - "### subheading" → write a real ### subheading
   - "- list item" → write a real bullet list item
   - "[table: N rows x M cols]" → write a real markdown table with that many rows and columns
   - "[paragraph]" → write a real paragraph of prose
5. Use # only for document title, ## for main sections, and ### for subheadings.
6. Return ONLY the markdown content, no preamble or extra commentary.
"""

        model = genai.GenerativeModel("gemini-3-flash-preview")
        response = model.generate_content(full_prompt)
        markdown_content = (response.text or "").strip()

        if not re.search(r"^\s*#\s+", markdown_content, flags=re.MULTILINE):
            markdown_content = f"# Generated Report\n\n{markdown_content}".strip()

        with _jobs_lock:
            _jobs[job_id] = {"status": "completed", "markdown": markdown_content, "error": None}

    except Exception as exc:
        with _jobs_lock:
            _jobs[job_id] = {"status": "failed", "markdown": None, "error": str(exc)}


# API Endpoint for Generating Markdown with Gemini (async / fire-and-forget)
@app.post("/generate-markdown")
async def generate_markdown(req: MarkdownGenerateRequest, background_tasks: BackgroundTasks):
    """
    Enqueues a Gemini markdown generation job and returns a job_id immediately.
    Poll GET /job/{job_id} to check status and retrieve the result.
    """
    job_id = uuid.uuid4().hex[:12]
    with _jobs_lock:
        _jobs[job_id] = {"status": "pending", "markdown": None, "error": None}
    background_tasks.add_task(_run_markdown_job, job_id, req)
    return {"job_id": job_id, "status": "pending"}


# API Endpoint for polling job status
@app.get("/job/{job_id}")
async def get_job_status(job_id: str):
    """Returns the current status and result (if ready) of a background job."""
    with _jobs_lock:
        job = _jobs.get(job_id)
    if job is None:
        return {"error": f"Job '{job_id}' not found"}
    return {
        "job_id": job_id,
        "status": job["status"],
        "markdown": job["markdown"],
        "error": job["error"],
    }

# API Endpoint for Previewing generated HTML (debug)
@app.post("/preview-html")
async def preview_html(req: PDFGenerateRequest):
    """Return the HTML that would be sent to Gotenberg, as plain text for debugging."""
    from fastapi.responses import PlainTextResponse
    try:
        meta_path = os.path.join(METADATA_DIR, f"{req.template_id}.json")
        if not os.path.exists(meta_path):
            return PlainTextResponse(f"Template '{req.template_id}' not found", status_code=404)
        with open(meta_path) as f:
            metadata = json.load(f)
        html_content = markdown_to_html_with_styling(req.markdown, metadata)
        return PlainTextResponse(html_content)
    except Exception as e:
        return PlainTextResponse(f"Error: {e}", status_code=500)

# API Endpoint for Converting Markdown to PDF via Gotenberg
@app.post("/generate-pdf")
async def generate_pdf(req: PDFGenerateRequest):
    """
    Convert markdown to PDF using Gotenberg, with styling from template.
    """
    try:
        meta_path = os.path.join(METADATA_DIR, f"{req.template_id}.json")
        if not os.path.exists(meta_path):
            return {"error": f"Template '{req.template_id}' not found"}

        with open(meta_path) as f:
            metadata = json.load(f)

        html_content = markdown_to_html_with_styling(req.markdown, metadata)

        # Pass margins=0 to Gotenberg so our @page CSS rule is the
        # single source of truth for page margins and sizing.
        files = {"files": ("index.html", html_content, "text/html")}
        data  = {
            "marginTop":        "0",
            "marginBottom":     "0",
            "marginLeft":       "0",
            "marginRight":      "0",
            "preferCssPageSize": "true",
            "printBackground":   "true",
        }
        response = requests.post(
            f"{GOTENBERG_URL}/forms/chromium/convert/html",
            files=files,
            data=data,
        )

        if response.status_code == 200:
            pdf_path = tempfile.mktemp(suffix=".pdf")
            with open(pdf_path, "wb") as f:
                f.write(response.content)

            return FileResponse(
                pdf_path,
                media_type="application/pdf",
                filename=req.filename
            )
        else:
            return {"error": f"Gotenberg error: {response.status_code} - {response.text}"}
    except Exception as e:
        return {"error": f"Error generating PDF: {str(e)}"}
