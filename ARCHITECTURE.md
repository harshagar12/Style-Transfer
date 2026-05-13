# System Architecture & Data Flow

## Overall Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Server                           │
│                    (main.py)                                │
└─────────────────────────────────────────────────────────────┘
         │                    │                    │
         ↓                    ↓                    ↓
    ┌──────────┐         ┌─────────┐         ┌──────────┐
    │Upload    │         │Generate │         │Generate  │
    │Template  │         │Markdown │         │PDF       │
    │Endpoint  │         │(Gemini) │         │(Gotenberg)
    └──────────┘         └─────────┘         └──────────┘
         │                    │                    │
         ↓                    ↓                    ↓
    ┌──────────────────────────────────────────────────┐
    │    External Services                             │
    ├──────────────────────────────────────────────────┤
    │ - Python-docx (Local)                            │
    │ - Google Generative AI (Cloud)                   │
    │ - Gotenberg (Docker Container)                   │
    └──────────────────────────────────────────────────┘
         ↓
    ┌──────────────────────────────────────────────────┐
    │    Storage                                       │
    ├──────────────────────────────────────────────────┤
    │ - template_metadata/ (JSON files)                │
    │ - Temporary files (OS temp directory)            │
    └──────────────────────────────────────────────────┘
```

---

## Phase 1: Template Extraction

### Input
- `.docx` file (Word document with formatting)

### Processing Steps

```
1. Receive .docx file
        ↓
2. Parse document with python-docx
        ↓
3. Extract paragraphs
        ├─ Detect headings (short text, formatting)
        ├─ Detect body text (longer paragraphs)
        ├─ Detect lists (bullet/numbered items)
        └─ Detect tables
        ↓
4. Extract formatting for each role:
        ├─ Font name, size, color
        ├─ Bold, italic, underline
        ├─ Alignment, spacing
        └─ Indentation
        ↓
5. Identify sections:
        ├─ Read paragraphs in order
        ├─ Headings mark section starts
        └─ Group content under headings
        ↓
6. Build Table of Contents
        ├─ Extract all heading texts
        └─ Maintain order
        ↓
7. Create JSON metadata
        ├─ roles (formatting for each element type)
        ├─ sections (structure with styling)
        ├─ table_of_contents (TOC list)
        └─ layout (page configuration)
        ↓
8. Save to template_metadata/{template_id}.json
        ↓
9. Return template_id
```

### Output
- **template_metadata/{template_id}.json** containing:
  ```json
  {
    "roles": {
      "title": { styling info },
      "heading": { styling info },
      "body": { styling info },
      "list_item": { styling info },
      "table": { styling info }
    },
    "sections": [ section objects ],
    "table_of_contents": [ heading strings ],
    "layout": { page configuration }
  }
  ```

### Code Flow
```python
@app.post("/upload-template")
├─ Save file temporarily
├─ Parse with Document()
├─ extract_sections_from_docx()
│  ├─ Iterate paragraphs
│  ├─ Identify headings
│  └─ Group into sections
├─ extract_table_of_contents()
├─ Extract formatting for each role
├─ Save JSON
└─ Return template_id
```

---

## Phase 2: Markdown Generation with AI

### Input
- `template_id` (identifier for template)
- `prompt` (description of desired report)

### Processing Steps

```
1. Receive request
        ↓
2. Load template metadata JSON
        ├─ Get table_of_contents
        ├─ Get sections structure
        ├─ Get roles (styling info)
        └─ Get layout
        ↓
3. Build context for Gemini:
        ├─ Describe template structure
        ├─ List expected sections
        ├─ Indicate styling (fonts, sizes, etc.)
        └─ Set professional tone requirements
        ↓
4. Create full prompt:
        ├─ Template context
        ├─ User's custom prompt
        ├─ Instructions (markdown format, section structure)
        └─ Tone & style guidelines
        ↓
5. Call Gemini API:
        └─ generativeai.GenerativeModel().generate_content()
        ↓
6. Receive markdown output:
        ├─ Headers (# ## ###)
        ├─ Body text
        ├─ Lists
        └─ Sections in order
        ↓
7. Return markdown
```

### Output
- Markdown text following template structure:
  ```markdown
  # Title
  
  ## Introduction
  Introduction content...
  
  ## Summary
  Summary content...
  
  ## Accomplishments
  - Item 1
  - Item 2
  ```

### Code Flow
```python
@app.post("/generate-markdown")
├─ Load template metadata
├─ Extract structure info
├─ Build context string
├─ Create full prompt
├─ Call genai.GenerativeModel().generate_content()
├─ Extract response text
└─ Return markdown
```

### Example Prompts to Gemini

```
Template Structure Information:
- Table of Contents: Introduction, Summary, Accomplishments
- Heading Style: Font 'Calibri', Size 14pt, Bold
- Body Style: Font 'Calibri', Size 11pt

Based on the template structure above, please generate a professional 
report in Markdown format for: [USER PROMPT]

Instructions:
1. Structure using template sections
2. Use markdown heading levels appropriately
3. Maintain professional style
4. Include all relevant sections
5. Return ONLY the markdown content
```

---

## Phase 3: PDF Generation

### Input
- `template_id` (for template styling)
- `markdown` (content from Phase 2)
- `filename` (output PDF name)

### Processing Steps

```
1. Receive request
        ↓
2. Load template metadata JSON
        ├─ Get roles (styling information)
        ├─ Get layout (page size, margins)
        └─ Extract heading & body styles
        ↓
3. Convert markdown to HTML:
        └─ markdown_to_html_with_styling()
           ├─ Create CSS from template styles
           ├─ Apply font names, sizes, colors
           ├─ Parse markdown syntax
           │  ├─ # → <h1>
           │  ├─ ## → <h2>
           │  ├─ Bold, italic, code formatting
           │  ├─ Lists → <ul>/<ol>
           │  └─ Paragraphs → <p>
           └─ Embed styling in HTML
        ↓
4. Create full HTML document:
        ├─ HTML5 structure
        ├─ Meta charset (UTF-8)
        ├─ Embedded CSS styles
        └─ Body content
        ↓
5. Send to Gotenberg:
        ├─ HTTP POST to /forms/chromium/convert/html
        ├─ Multipart form with HTML file
        └─ Gotenberg renders & converts to PDF
        ↓
6. Receive PDF binary
        ↓
7. Save to temporary file
        ↓
8. Return as file download
```

### Output
- PDF file with:
  - Template styling applied
  - Professional formatting preserved
  - All content from markdown

### Code Flow
```python
@app.post("/generate-pdf")
├─ Load template metadata
├─ Extract styling roles
├─ Call markdown_to_html_with_styling()
│  ├─ Build CSS from roles
│  ├─ Call markdown_to_basic_html()
│  │  ├─ Parse markdown syntax
│  │  └─ Generate HTML elements
│  └─ Embed in complete HTML doc
├─ POST HTML to Gotenberg
├─ Receive PDF response
├─ Save to temp file
└─ Return FileResponse
```

### Markdown to HTML Example

```
Input Markdown:
# Title
## Section
Body text with **bold** and *italic*.
- List item 1
- List item 2

↓

Generated HTML:
<h1>Title</h1>
<h2>Section</h2>
<p>Body text with <strong>bold</strong> and <em>italic</em>.</p>
<ul>
  <li>List item 1</li>
  <li>List item 2</li>
</ul>

↓ (with CSS styling)

<html>
<head>
  <style>
    h1 { font-size: 16pt; font-weight: bold; ... }
    body { font-size: 11pt; font-family: Calibri; ... }
  </style>
</head>
<body>
  [HTML content]
</body>
</html>

↓ (sent to Gotenberg)

PDF Output ✓
```

---

## Data Structures

### Template Metadata (JSON)

```json
{
  "roles": {
    "role_name": {
      "font_name": "string",
      "font_size": "number",
      "bold": "boolean",
      "italic": "boolean",
      "underline": "boolean",
      "color": "hex string",
      "alignment": "number",
      "line_spacing": "number",
      "space_before": "number",
      "space_after": "number"
    }
  },
  "sections": [
    {
      "heading": "string",
      "content": ["string", "string"],
      "heading_style": { styling object },
      "body_styles": [{ styling object }]
    }
  ],
  "table_of_contents": ["string"],
  "layout": {
    "page_size": "string"
  }
}
```

### Request/Response Models

```python
# Upload Template
Response: {
  template_id: string,
  table_of_contents: [string],
  roles_found: [string],
  message: string
}

# Generate Markdown
Request: {
  template_id: string,
  prompt: string
}
Response: {
  template_id: string,
  markdown: string,
  message: string
}

# Generate PDF
Request: {
  template_id: string,
  markdown: string,
  filename: string
}
Response: PDF binary file

# Generate Document (Legacy)
Request: {
  template_id: string,
  plain_text: string
}
Response: DOCX binary file
```

---

## Storage Structure

```
d:\Programs\Tecore Labs Internship\Style Transfer\
├── main.py                          (FastAPI application)
├── requirements.txt                 (Python dependencies)
├── .env                            (Configuration - create from .env.example)
├── .env.example                    (Configuration template)
├── README.MD                       (Main documentation)
├── IMPLEMENTATION_GUIDE.md         (Detailed usage guide)
├── API_QUICK_REFERENCE.md          (Quick API reference)
├── ARCHITECTURE.md                 (This file)
└── template_metadata/              (Template storage)
    ├── abc123de.json              (Template 1)
    ├── xyz789ab.json              (Template 2)
    └── ...
```

---

## External Service Integrations

### 1. Python-docx
- **Purpose**: Parse and extract formatting from .docx files
- **Used in**: Phase 1 (Template Extraction)
- **Installation**: `pip install python-docx`

### 2. Google Generative AI (Gemini)
- **Purpose**: Generate report content based on template structure
- **Used in**: Phase 2 (Markdown Generation)
- **Installation**: `pip install google-generativeai`
- **Configuration**: `GEMINI_API_KEY` in .env

### 3. Gotenberg
- **Purpose**: Convert HTML to PDF with professional rendering
- **Used in**: Phase 3 (PDF Generation)
- **Installation**: Docker image `gotenberg/gotenberg:latest`
- **Configuration**: `GOTENBERG_URL` in .env (default: http://localhost:3000)

---

## Error Handling

```
Phase 1 - Template Upload
├─ File not found → HTTP 400
├─ Invalid .docx → Exception handling
└─ JSON save error → HTTP 500

Phase 2 - Markdown Generation
├─ Template not found → HTTP 404
├─ Gemini API error → HTTP 500
├─ Invalid prompt → Return error message
└─ Rate limit → Gemini handles

Phase 3 - PDF Generation
├─ Template not found → HTTP 404
├─ Invalid markdown → HTML parsing attempts recovery
├─ Gotenberg connection error → HTTP 500
├─ Rendering error → HTTP 500
└─ File save error → HTTP 500
```

---

## Performance Considerations

1. **Template Extraction** (Phase 1)
   - One-time per template
   - Fast (< 1 second for typical documents)
   - Store template_id for reuse

2. **Markdown Generation** (Phase 2)
   - Depends on Gemini API response time
   - Typical: 5-30 seconds
   - Can generate multiple reports with same template

3. **PDF Generation** (Phase 3)
   - Depends on content length and Gotenberg performance
   - Typical: 2-10 seconds
   - Can be parallelized

## Scalability Notes

- **Single Server**: ✓ Handles sequential requests
- **Multiple Servers**: ✓ Share `template_metadata/` directory
- **High Volume**: Consider:
  - Caching template metadata in memory
  - Using async task queue (Celery)
  - Load balancing across multiple API instances
  - Using cloud storage for templates
