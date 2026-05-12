# FastAPI Document Style Transfer & Generator
A lightweight FastAPI service to extract formatting metadata from a `.docx` template and generate styled `.docx` documents from plain text using that metadata.

## What it does
- **Template Upload**
  Accepts a `.docx` template via `POST /upload-template` and extracts paragraph/run formatting (saved to `template_metadata/<id>.json`).
- **Document Generation**
  Accepts plain text and a `template_id` via `POST /generate-document` and returns a generated `.docx` that applies the extracted styles.

## Key files
- `main.py`: API entrypoint (FastAPI app).
- `requirements.txt`: Python dependencies.

## Quick start
1. **Create & activate a virtual environment**:

```powershell
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2. **Run the API with Uvicorn**:

```powershell
uvicorn main:app --reload
```
The API is now live at `http://127.0.0.1:8000/docs`

## API endpoints
- **POST /upload-template**
	- Request: Form data with the `.docx` file.
	- Response: JSON containing the generated `template_id` and a confirmation message.
	- Example (curl):

```bash
curl -F "file=@template.docx" http://127.0.0.1:8000/upload-template
```

- **POST /generate-document**
	- Request: JSON body with `template_id` and `plain_text`.
	- Response: The generated `.docx` file.
	- Example (curl):

```bash
curl -H "Content-Type: application/json" \
	-d '{"template_id":"abcd1234","plain_text":"Title\n\nHeading\n\nThis is paragraph text."}' \
	http://127.0.0.1:8000/generate-document -o generated.docx
```

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
