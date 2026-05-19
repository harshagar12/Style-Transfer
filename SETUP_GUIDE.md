# Setup & Getting Started Guide

This guide describes how to configure and run the full report generation pipeline, including the FastAPI backend server and the simple wide-layout Streamlit frontend.

---

## Prerequisites

- Windows/Linux/Mac with Python 3.8+
- Docker installed and running (required for Gotenberg PDF conversion)
- A Google Generative AI API key (from Gemini)

---

## Step-by-Step Setup

### 1. Clone/Navigate to the Project Folder
Open your terminal and navigate to the project directory:
```powershell
cd "d:\Programs\Tecore Labs Internship\Style Transfer"
```

### 2. Create a Virtual Environment
```powershell
python -m venv venv
venv\Scripts\Activate.ps1
```

### 3. Install Dependencies
This will install all backend and frontend packages, including FastAPI, `python-docx`, `google-generativeai`, and `streamlit`:
```powershell
pip install -r requirements.txt
```

### 4. Get a Gemini API Key
1. Visit [Google AI Studio](https://aistudio.google.com/).
2. Sign in with your Google account.
3. Click "Create API Key".
4. Copy the generated key.

### 5. Configure your Environment variables
Create a `.env` file in the root directory:
```env
GEMINI_API_KEY=your_api_key_here
GOTENBERG_URL=http://localhost:3000
```
**Or do this via PowerShell:**
```powershell
@"
GEMINI_API_KEY=your_api_key_here
GOTENBERG_URL=http://localhost:3000
"@ | Out-File .env
```

### 6. Start the Gotenberg Service (Docker)
Gotenberg converts the parsed HTML reports into styled, print-ready PDFs.
Make sure Docker Desktop is running, then start the container:
```bash
docker run -p 3000:3000 gotenberg/gotenberg:latest
```
This runs in the foreground. Keep this terminal window open.

---

## Running the Application

To run the full suite, you need to launch both the **FastAPI Backend** and the **Streamlit Frontend**:

### Terminal 1: Gotenberg (Docker Container)
Keep the Gotenberg docker terminal open and running.

### Terminal 2: FastAPI Backend Server
Open a new PowerShell terminal, activate the environment, and start uvicorn:
```powershell
venv\Scripts\Activate.ps1
uvicorn main:app --reload
```
You should see:
```text
Uvicorn running on http://127.0.0.1:8000
```
*   **Interactive API Docs**: http://127.0.0.1:8000/docs

### Terminal 3: Streamlit Frontend Web App
Open another PowerShell terminal, activate the environment, and start Streamlit:
```powershell
venv\Scripts\Activate.ps1
streamlit run app.py
```
*   **Web App URL**: http://localhost:8501
*   Streamlit will open a clean, simple, wide-layout user interface in your default browser.

---

## Project Structure

```text
.
├── main.py                      # FastAPI backend application
├── app.py                       # Streamlit web application
├── utils_extraction.py          # Extractor for DOCX font, color, and alignment properties
├── utils_markdown.py          # Markdown-to-HTML parser with custom template CSS mapping
├── requirements.txt             # Python package dependencies
├── .env                        # Local environment configuration variables
├── README.MD                   # Project overview & documentation
├── SETUP_GUIDE.md              # This setup guide
└── template_metadata/          # Folder storing parsed template JSON configurations
```

---

## First Usage Web Workflow

1.  **Prepare a Template Document**:
    Create a `.docx` file in Microsoft Word. Try giving it a centered Title (large, bold), some body text, a few bold headings, subheadings, and lists.
2.  **Upload the Template**:
    *   Open `http://localhost:8501` in your browser.
    *   Navigate to the **Template Upload** tab.
    *   Drag and drop your `.docx` file, enter an optional custom name, and click **Upload Template**.
    *   Copy the generated **Template ID** shown on screen.
3.  **Generate Markdown with AI**:
    *   Go to the **Markdown Generation** tab.
    *   Select your uploaded template from the dropdown.
    *   In the tall 300px text area, type a prompt describing your report.
    *   Click **Generate Markdown**. The Gemini API will generate structured content following your template's layout.
4.  **Export to Polished PDF**:
    *   Go to the **PDF Generation** tab.
    *   The generated markdown from the previous tab will be pre-filled automatically inside the large 600px editor.
    *   Adjust the output filename if desired, verify the template dropdown selection, and click **Generate PDF**.
    *   Click **Download PDF** to save the polished document (retaining your original template's font faces, colors, and centered/justified text alignments).

---

## Setup & Running Troubleshooting

### Gotenberg Connection Error
Make sure Docker Desktop is open and run:
```bash
docker ps
```
If you see no active containers, start Gotenberg again:
```bash
docker run -p 3000:3000 gotenberg/gotenberg:latest
```

### Module Not Found / Streamlit Command Not Found
Ensure your virtual environment is properly activated in your active terminal:
```powershell
venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Headings styling looks incorrect
If the body subheadings or lists are using Title formatting:
*   Pre-headings (unnamed header metadata) are skipped during merging to prevent title style leakage.
*   Make sure headings in your original `.docx` are using explicit paragraph heading styles.
*   Simply re-upload your template inside the web app to overwrite the metadata configuration instantly.

---

## Common Commands Cheat Sheet

```powershell
# Activate the virtual environment
venv\Scripts\Activate.ps1

# Run the Gotenberg service (Docker)
docker run -p 3000:3000 gotenberg/gotenberg:latest

# Run the backend API server
uvicorn main:app --reload

# Run the Streamlit web interface
streamlit run app.py

# Check existing parsed templates
Get-ChildItem template_metadata/
```
