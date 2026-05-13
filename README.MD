# FastAPI Document Style Transfer & Generator
A comprehensive FastAPI service to extract formatting metadata from documents, generate styled reports, and convert them to PDF with preserved styling.

## What it does

### Phase 1: Template Extraction
- **Template Upload** (`POST /upload-template`)
  - Accepts a `.docx` template file
  - Extracts paragraph/run formatting and structure
  - Identifies sections in order (Title, Introduction, Summary, etc.)
  - Generates table of contents
  - Stores metadata in `template_metadata/<id>.json`

### Phase 2: Report Generation with AI
- **Markdown Generation** (`POST /generate-markdown`)
  - Accepts a template ID and custom prompt
  - Uses Gemini API to generate markdown content
  - Follows the template's structure and styling guidelines
  - Returns formatted markdown ready for PDF conversion

### Phase 3: PDF Generation
- **PDF Conversion** (`POST /generate-pdf`)
  - Converts markdown to PDF using Gotenberg
  - Preserves all styling from the template JSON
  - Applies heading, body, and list item formatting
  - Returns a production-ready PDF file

## Key files
- `main.py`: FastAPI app with all endpoints and business logic
- `requirements.txt`: Python dependencies
- `.env.example`: Environment configuration template

## Quick start

### 1. Create & activate a virtual environment
```powershell
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Setup environment variables
Copy `.env.example` to `.env` and fill in:
```
GEMINI_API_KEY=your_api_key_here
GOTENBERG_URL=http://localhost:3000
```

Get your Gemini API key from: https://makersuite.google.com/app/apikey

### 3. Start Gotenberg (Docker)
```bash
docker run -p 3000:3000 gotenberg/gotenberg:latest
```

### 4. Run the API
```powershell
uvicorn main:app --reload
```

The API is now live at `http://127.0.0.1:8000/docs`

## API Endpoints

### POST /upload-template
Extract and analyze a template document.

**Request:** Form data with `.docx` file
**Response:**
```json
{
  "template_id": "abc123de",
  "message": "Template processed",
  "roles_found": ["title", "heading", "body", "list_item"],
  "table_of_contents": ["Title", "Introduction", "Summary", "Accomplishments"]
}
```

**Example (PowerShell):**
```powershell
$file = "C:\path\to\template.docx"
curl -F "file=@$file" http://127.0.0.1:8000/upload-template
```

### POST /generate-markdown
Generate markdown content using Gemini AI based on template structure.

**Request:**
```json
{
  "template_id": "abc123de",
  "prompt": "Generate a project completion report for a web development project that was completed on time and under budget"
}
```

**Response:**
```json
{
  "template_id": "abc123de",
  "markdown": "# Project Completion Report\n\n## Introduction\nThis report...",
  "message": "Markdown generated successfully"
}
```

**Example (PowerShell):**
```powershell
$body = @{
  template_id = "abc123de"
  prompt = "Generate a quarterly performance review template"
} | ConvertTo-Json

curl -X POST http://127.0.0.1:8000/generate-markdown `
  -H "Content-Type: application/json" `
  -d $body
```

### POST /generate-pdf
Convert markdown to PDF with template styling.

**Request:**
```json
{
  "template_id": "abc123de",
  "markdown": "# Report Title\n\nThis is the content...",
  "filename": "report.pdf"
}
```

**Response:** PDF file

**Example (PowerShell):**
```powershell
$markdown = @"
# Project Report

## Executive Summary
The project was completed successfully.

## Key Achievements
- Goal 1 achieved
- Goal 2 achieved
"@

$body = @{
  template_id = "abc123de"
  markdown = $markdown
  filename = "project_report.pdf"
} | ConvertTo-Json

curl -X POST http://127.0.0.1:8000/generate-pdf `
  -H "Content-Type: application/json" `
  -d $body `
  -o output.pdf
```

### POST /generate-document (Legacy)
Generate a `.docx` document from plain text with template styling.

**Request:**
```json
{
  "template_id": "abc123de",
  "plain_text": "Title\n\nHeading\n\nThis is paragraph text."
}
```

**Response:** Word document (`.docx`)

## Template JSON Structure

The extracted template metadata is stored as:
```json
{
  "roles": {
    "title": { "font_name": "Calibri", "font_size": 16, "bold": true, ... },
    "heading": { "font_name": "Calibri", "font_size": 14, "bold": true, ... },
    "body": { "font_name": "Calibri", "font_size": 11, "bold": false, ... },
    "list_item": { ... },
    "table": { ... }
  },
  "layout": {
    "page_size": "A4"
  },
  "table_of_contents": ["Title", "Introduction", "Summary", "Accomplishments"],
  "sections": [
    {
      "heading": "Introduction",
      "content": ["First paragraph", "Second paragraph"],
      "heading_style": { ... },
      "body_styles": [ ... ]
    },
    ...
  ]
}
```

## Workflow Example

1. **Upload a template:**
   ```powershell
   curl -F "file=@template.docx" http://127.0.0.1:8000/upload-template
   # Returns: template_id = "abc123de"
   ```

2. **Generate markdown with AI:**
   ```powershell
   $body = @{
     template_id = "abc123de"
     prompt = "Create a technical progress report"
   } | ConvertTo-Json
   
   curl -X POST http://127.0.0.1:8000/generate-markdown `
     -H "Content-Type: application/json" `
     -d $body > report.json
   ```

3. **Convert to PDF:**
   ```powershell
   # Extract markdown from previous response
   $markdown = (Get-Content report.json | ConvertFrom-Json).markdown
   
   $body = @{
     template_id = "abc123de"
     markdown = $markdown
     filename = "report.pdf"
   } | ConvertTo-Json
   
   curl -X POST http://127.0.0.1:8000/generate-pdf `
     -H "Content-Type: application/json" `
     -d $body `
     -o final_report.pdf
   ```

## Configuration

### Environment Variables (.env)
- `GEMINI_API_KEY`: Your Google Generative AI API key
- `GOTENBERG_URL`: URL to Gotenberg service (default: http://localhost:3000)

### Supported File Formats
- Input: `.docx` (Word documents)
- Output: `.pdf` (PDF), `.docx` (Word), or `.md` (Markdown)

## Dependencies
- FastAPI - Web framework
- python-docx - Word document handling
- google-generativeai - AI content generation
- requests - HTTP requests to Gotenberg
- python-dotenv - Environment configuration
- uvicorn - ASGI server

## Troubleshooting

### Gotenberg Connection Error
Ensure Gotenberg is running:
```bash
docker run -p 3000:3000 gotenberg/gotenberg:latest
```

### Gemini API Error
- Verify `GEMINI_API_KEY` is set correctly in `.env`
- Check you have enabled the Generative AI API

### Template Not Found
- Verify the template_id is correct
- Check files in `template_metadata/` directory


## How it works
1. **Style extraction**
- First, the upload endpoint attempts to map Word style names (Title, Heading 1, Normal, etc.) to semantic roles.
- If any roles are missing, a set of visual heuristics infers them:
- Title: first line with a font size larger than the body text, or the first paragraph.
- Heading: short (≤ 70 chars), bold, and larger than body text.
- Subheading: similar but smaller than heading, and bold/italic.
- Body: most common font size among long paragraphs (≥ 100 chars).
- All extracted styles are saved in a JSON file named `<template_id>`.json inside `template_metadata/`.

2. **Document generation**
- Loads the metadata JSON for the given `template_id`.
- Creates a new `.docx` and applies the stored font, size, bold/italic/underline, color, alignment, and spacing to each semantic block.
- Tables are recreated using the “Table Grid” style and the stored table font settings.

## Notes
- Metadata files are automatically created in the template_metadata/ directory.
- Temporary files are used during upload and generation; they are cleaned up after use.
- Structure detection relies on simple heuristics; highly unstructured text may require manual adjustments.
