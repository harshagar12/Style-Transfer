# FastAPI & Streamlit Document Style Transfer & Generator

A comprehensive system featuring a FastAPI backend and a clean, native Streamlit frontend to extract formatting metadata from documents, generate styled reports using Gemini AI, and convert them to PDF with preserved styling and precise layout alignments.

## What it does

### Phase 1: Template Extraction & Parsing
- **Template Upload & Processing** (`POST /upload-template`)
  - Accepts a `.docx` template file.
  - Extracts paragraph/run styling (font names, sizes, colors, weight, italic, underline).
  - Automatically captures **paragraph alignments** (left, center, right, justify) from individual blocks and walks up the style hierarchy if needed.
  - Skips empty heading/title blocks to ensure body-level styles (`subheading`, `paragraph`, `list_item`, `table`) are mapped reliably without bleeding from the title page format.
  - Generates a table of contents and saves a detailed metadata configuration to `template_metadata/<id>.json`.

### Phase 2: Asynchronous AI Report Generation
- **Markdown Generation** (`POST /generate-markdown` + `GET /job/{job_id}`)
  - Accepts a template ID and a custom prompt.
  - Returns a `job_id` **immediately** without waiting for the Gemini API — the generation runs in a background thread.
  - Clients poll `GET /job/{job_id}` to check status (`pending` → `completed` / `failed`) and retrieve the result when ready.
  - The Streamlit frontend handles polling automatically, showing a live elapsed-time counter and notifying the user on completion.

### Phase 3: High-Fidelity PDF Generation
- **PDF Conversion** (`POST /generate-pdf`)
  - Conveys markdown content to styled HTML+CSS and renders it to a print-ready PDF using a Gotenberg container.
  - Maps styles and paragraph alignments precisely back to their original document positions.

### Phase 4: Clean Streamlit Web Frontend
- **Interactive UI** (`app.py`)
  - Built with a wide-layout native Streamlit structure for reading and editing comfort.
  - **Template Upload Tab**: Easy file drops, optional template names, and template ID badge copies.
  - **Markdown Tab**: Submits a generation job, then polls the backend every 2 seconds with a live `Xsec elapsed` counter. Notifies with a `✅` banner when done, and pre-fills the generated markdown into the PDF tab automatically.
  - **PDF Tab**: Pre-fills markdown for instant processing, provides a tall (600px) interactive text editor for customization, and generates download buttons for polished PDF documents on success.

## Key files
- `main.py`: FastAPI backend application exposing all core endpoints.
- `app.py`: Streamlit frontend web app providing an intuitive browser-based interface.
- `utils_extraction.py`: Helper functions to parse DOCX structure and styles, including text alignment extraction.
- `utils_markdown.py`: Markdown parser converting md to high-quality styled HTML using template JSON metadata.
- `requirements.txt`: Python package requirements.
- `.env.example`: Template for local environment variables.

## Quick start

### 1. Create & Activate a Virtual Environment
```powershell
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Setup Environment Variables
Copy `.env.example` to `.env` and fill in your Gemini API key:
```env
GEMINI_API_KEY=your_api_key_here
GOTENBERG_URL=http://localhost:3000
```
Get a Gemini API key from: https://aistudio.google.com/

### 3. Start Gotenberg (Docker)
```bash
docker run -p 3000:3000 gotenberg/gotenberg:latest
```

### 4. Run the FastAPI Backend Server
```powershell
uvicorn main:app --reload
```
The API docs will be live at `http://127.0.0.1:8000/docs`.

### 5. Start the Streamlit Frontend Web App
In a new terminal:
```powershell
streamlit run app.py
```
Open your browser and navigate to `http://localhost:8501`.

---

## Template JSON Structure
Extracted template metadata is parsed and stored inside `template_metadata/`:
```json
{
  "table_of_contents": ["Market Overview", "Financial Performance"],
  "title": {
    "text": "BUSINESS INTELLIGENCE",
    "style": {
      "font_name": "Cambria",
      "font_size": 28.0,
      "bold": true,
      "italic": false,
      "underline": false,
      "color": "7B2D00",
      "alignment": "left"
    }
  },
  "sections": [
    {
      "heading": "Market Overview",
      "heading_style": {
        "font_name": "Cambria",
        "font_size": 20.0,
        "bold": true,
        "color": "7B2D00",
        "alignment": "left"
      },
      "styles": {
        "paragraph": { "font_name": "Calibri", "font_size": 11.0, "color": "2C2C2C", "alignment": "left" },
        "subheading": { "font_name": "Cambria", "font_size": 15.0, "color": "C0392B", "alignment": "left" },
        "list_item": { "font_name": "Calibri", "font_size": 11.0, "color": "2C2C2C", "alignment": "left" },
        "table": { "font_name": "Cambria", "font_size": 11.0, "color": "7B2D00", "alignment": "left" }
      },
      "content": [
        { "type": "paragraph" },
        { "type": "subheading" }
      ]
    }
  ],
  "layout": {
    "page_size": "A4"
  },
  "basic_style": {
    "font_name": "Cambria",
    "font_size": 28.0,
    "bold": true,
    "color": "7B2D00",
    "alignment": "left"
  }
}
```

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/upload-template` | Upload a `.docx` template; returns `template_id` |
| `POST` | `/generate-markdown` | Enqueue a Gemini generation job; returns `job_id` instantly |
| `GET`  | `/job/{job_id}` | Poll for job status (`pending` / `completed` / `failed`) and retrieve markdown |
| `POST` | `/generate-pdf` | Convert markdown to a styled PDF via Gotenberg |
| `POST` | `/generate-document` | _(Legacy)_ Generate a `.docx` from plain text |

### Async markdown flow in detail
```
Client                        FastAPI backend
  │                                │
  │  POST /generate-markdown ──────► enqueue background thread
  │  ◄── {job_id, status:pending}  │  [Gemini API call running...]
  │                                │
  │  GET /job/{job_id} ────────────► {status: "pending"}
  │  (repeat every 2 s)            │  [still running...]
  │                                │
  │  GET /job/{job_id} ────────────► {status: "completed", markdown: "..."}
  │  ◄── display result            │
```

---

## Troubleshooting & Diagnostics

### Gotenberg Connection Error
Ensure the Gotenberg Docker container is actively running on port 3000:
```bash
docker ps
```

### Incorrect Heading Styles or Title Color Bleeding
If your subheadings (`h3`) are appearing too large or using the title page color:
- Ensure the template has properly named headings in the Word document.
- Pre-heading title blocks are skipped during style collection. Re-uploading your `.docx` file will recreate and overwrite the cached JSON in `template_metadata/`.
