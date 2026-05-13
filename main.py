import json, uuid, os, re
import tempfile
import requests
import google.generativeai as genai

from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse
from docx import Document

from config import METADATA_DIR, GOTENBERG_URL
from models import GenerateRequest, MarkdownGenerateRequest, PDFGenerateRequest
from utils_extraction import extract_metadata_from_docx
from utils_generation import detect_structure, generate_docx
from utils_markdown import markdown_to_html_with_styling

app = FastAPI()

# API Endpoint for Uploading a Template File
@app.post("/upload-template")
async def upload_template(file: UploadFile = File(...)):

    # Saving uploaded file temporarily
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".docx")
    tmp.write(await file.read())
    tmp.close()

    doc = Document(tmp.name)

    # Extract metadata in the required format
    metadata = extract_metadata_from_docx(doc)

    # Saving metadata
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

# API Endpoint for Generating Markdown with Gemini
@app.post("/generate-markdown")
async def generate_markdown(req: MarkdownGenerateRequest):
    """
    Generate markdown content using Gemini API based on template structure.
    The template JSON includes section structure and styling information.
    """
    try:
        # Load template metadata
        meta_path = os.path.join(METADATA_DIR, f"{req.template_id}.json")
        if not os.path.exists(meta_path):
            return {"error": f"Template '{req.template_id}' not found"}

        with open(meta_path) as f:
            metadata = json.load(f)

        # Extract template structure info for Gemini
        toc = metadata.get("table_of_contents", [])
        sections = metadata.get("sections", [])
        basic_style = metadata.get("basic_style", {})
        title_style = metadata.get("title", {}).get("style", {})
        first_section = sections[0] if sections else {}
        heading_style = first_section.get("heading_style", {}) if isinstance(first_section, dict) else {}
        section_styles = first_section.get("styles", {}) if isinstance(first_section, dict) else {}
        body_style = section_styles.get("paragraph", {}) or basic_style

        title_text = metadata.get("title", {}).get("text", "").strip() or "Generated Report"

        # Build a detailed section schema for Gemini to follow exactly
        section_schema_lines = []
        for sec in sections:
            heading = sec.get("heading", "")
            content_items = sec.get("content", [])
            section_schema_lines.append(f"## {heading}")
            for item in content_items:
                t = item.get("type", "paragraph")
                if t == "subheading":
                    section_schema_lines.append("  ### [subheading here]")
                elif t == "list_item":
                    section_schema_lines.append("  - [list item here]")
                elif t == "table":
                    rows = item.get("rows", 2)
                    cols = item.get("cols", 2)
                    section_schema_lines.append(f"  [table: {rows} rows x {cols} cols]")
                else:
                    section_schema_lines.append("  [paragraph here]")
        section_schema = "\n".join(section_schema_lines)

        # Build context for Gemini about the template structure
        template_context = f"""
Template Structure (follow this EXACTLY — same number of sections, same order, same heading names, same content block types in each section):

{section_schema}

Original Template Title: {title_text} (Please generate a new, relevant title based on the prompt)
"""

        # Create prompt for Gemini
        full_prompt = f"""{template_context}

Generate a professional report in Markdown using this prompt:
{req.prompt}

STRICT INSTRUCTIONS:
1. First line MUST be a level 1 heading ("# <Your Generated Title>") that reflects the prompt's subject.
2. You MUST produce exactly {len(sections)} sections in the SAME ORDER as the schema above.
3. Each section MUST use the EXACT heading text shown in the schema (e.g., "## Introduction" not "## Overview").
4. Inside each section, reproduce the SAME sequence of content blocks:
    - "### subheading" → write a real ### subheading
   - "- list item" → write a real bullet list item
   - "[table: N rows x M cols]" → write a real markdown table with that many rows and columns
   - "[paragraph]" → write a real paragraph of prose
5. Use # only for document title, ## for main sections, and ### for subheadings.
6. Return ONLY the markdown content, no preamble or extra commentary.
"""

        # Call Gemini API
        model = genai.GenerativeModel("gemini-3-flash-preview")
        response = model.generate_content(full_prompt)
        markdown_content = (response.text or "").strip()

        # Safety net: ensure a title is present even if model omits it.
        if not re.search(r"^\s*#\s+", markdown_content, flags=re.MULTILINE):
            markdown_content = f"# Generated Report\n\n{markdown_content}".strip()

        return {
            "template_id": req.template_id,
            "markdown": markdown_content,
            "message": "Markdown generated successfully"
        }
    except Exception as e:
        return {"error": f"Error generating markdown: {str(e)}"}

# API Endpoint for Converting Markdown to PDF via Gotenberg
@app.post("/generate-pdf")
async def generate_pdf(req: PDFGenerateRequest):
    """
    Convert markdown to PDF using Gotenberg, with styling from template.
    """
    try:
        # Load template metadata for styling
        meta_path = os.path.join(METADATA_DIR, f"{req.template_id}.json")
        if not os.path.exists(meta_path):
            return {"error": f"Template '{req.template_id}' not found"}

        with open(meta_path) as f:
            metadata = json.load(f)

        # Build HTML from Markdown with template styling
        html_content = markdown_to_html_with_styling(req.markdown, metadata)

        # Call Gotenberg API
        files = {"files": ("index.html", html_content, "text/html")}
        response = requests.post(
            f"{GOTENBERG_URL}/forms/chromium/convert/html",
            files=files
        )

        if response.status_code == 200:
            # Save PDF temporarily
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
