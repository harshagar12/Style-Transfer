# Setup & Getting Started Guide

## Prerequisites

- Windows/Linux/Mac with Python 3.8+
- Docker (for Gotenberg)
- A Google Generative AI API key (free tier available)

## Step-by-Step Setup

### 1. Clone/Navigate to Project

```powershell
cd "d:\Programs\Tecore Labs Internship\Style Transfer"
```

### 2. Create Virtual Environment

```powershell
python -m venv venv
venv\Scripts\Activate.ps1
```

### 3. Install Dependencies

```powershell
pip install -r requirements.txt
```

### 4. Get Gemini API Key

1. Visit: https://makersuite.google.com/app/apikey
2. Sign in with Google account
3. Click "Create API key"
4. Copy the key

### 5. Configure Environment

Create `.env` file in project root:

```bash
GEMINI_API_KEY=your_api_key_from_step_4
GOTENBERG_URL=http://localhost:3000
```

**Or use PowerShell:**
```powershell
@"
GEMINI_API_KEY=your_api_key_here
GOTENBERG_URL=http://localhost:3000
"@ | Out-File .env
```

### 6. Start Gotenberg (Docker)

**First time only - install Docker:**
- Download from https://www.docker.com/products/docker-desktop

**Start Gotenberg:**
```bash
docker run -p 3000:3000 gotenberg/gotenberg:latest
```

This will run in the foreground. Keep this terminal open.

### 7. Start the FastAPI Server

In a new PowerShell terminal:

```powershell
# Activate venv if not already done
venv\Scripts\Activate.ps1

# Start the server
uvicorn main:app --reload
```

You should see:
```
Uvicorn running on http://127.0.0.1:8000
```

### 8. Access the API

- **API Documentation**: http://127.0.0.1:8000/docs
- **Alternative Docs**: http://127.0.0.1:8000/redoc

## Verify Installation

Test the API with a simple request:

```powershell
# Test that API is running
curl http://127.0.0.1:8000/docs
# Should return HTML documentation page
```

## Project Structure

```
.
├── main.py                      # Main API application
├── requirements.txt             # Python packages
├── .env                        # Environment variables (create this)
├── .env.example                # Template for .env
├── README.MD                   # Project overview
├── IMPLEMENTATION_GUIDE.md     # Detailed usage guide
├── API_QUICK_REFERENCE.md      # Quick API reference
├── ARCHITECTURE.md             # System architecture
├── SETUP_GUIDE.md              # This file
└── template_metadata/          # Stores extracted templates
    └── (JSON files generated after uploading templates)
```

## First Usage Example

### 1. Prepare a Template Document

Create a simple `.docx` file named `template.docx` with:
- Title: "Quarterly Report" (large, bold)
- Heading 1: "Executive Summary" (bold, smaller than title)
- Some body text (regular formatting)
- Heading 2: "Key Metrics"
- More body text
- Heading 3: "Action Items"

### 2. Upload Template

```powershell
$file = "C:\path\to\template.docx"
$response = curl -F "file=@$file" http://127.0.0.1:8000/upload-template | ConvertFrom-Json
$template_id = $response.template_id

Write-Host "Template ID: $template_id"
Write-Host "Sections: $($response.table_of_contents -join ', ')"
```

Save the `template_id` - you'll use it for next steps.

### 3. Generate Markdown

```powershell
$body = @{
  template_id = $template_id
  prompt = "Generate a Q4 2024 quarterly report with sales metrics, achievements, and goals"
} | ConvertTo-Json

$response = curl -X POST http://127.0.0.1:8000/generate-markdown `
  -H "Content-Type: application/json" `
  -d $body | ConvertFrom-Json

$markdown = $response.markdown
Write-Host "Markdown generated!"
```

### 4. Generate PDF

```powershell
$body = @{
  template_id = $template_id
  markdown = $markdown
  filename = "quarterly_report.pdf"
} | ConvertTo-Json

curl -X POST http://127.0.0.1:8000/generate-pdf `
  -H "Content-Type: application/json" `
  -d $body `
  -o quarterly_report.pdf

Write-Host "PDF generated: quarterly_report.pdf"
```

Done! Open `quarterly_report.pdf` to see the result.

## Running the System

### Development Mode

```powershell
# Terminal 1: Start Gotenberg
docker run -p 3000:3000 gotenberg/gotenberg:latest

# Terminal 2: Start FastAPI with auto-reload
venv\Scripts\Activate.ps1
uvicorn main:app --reload
```

### Production Mode

```powershell
# Terminal 1: Start Gotenberg (background)
docker run -d -p 3000:3000 gotenberg/gotenberg:latest

# Terminal 2: Start FastAPI (production)
venv\Scripts\Activate.ps1
uvicorn main:app --host 0.0.0.0 --port 8000
```

## Troubleshooting Setup

### "Module not found" Error
```powershell
# Make sure venv is activated
venv\Scripts\Activate.ps1

# Reinstall packages
pip install -r requirements.txt --force-reinstall
```

### Gemini API Key Error
- Verify key is copied correctly (no extra spaces)
- Check `.env` file has no typos
- Restart the API server after updating `.env`

### Gotenberg Connection Error
```powershell
# Check if Docker is running
docker ps

# If not, start Docker Desktop and run:
docker run -p 3000:3000 gotenberg/gotenberg:latest
```

### Port Already in Use
```powershell
# FastAPI on different port:
uvicorn main:app --port 8001

# Or find and kill process using port 8000:
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

## Tips

1. **Keep Terminal Windows Organized**
   - Use Windows Terminal or ConEmu to manage multiple PowerShell tabs
   - Terminal 1: Gotenberg (keep running)
   - Terminal 2: FastAPI (keep running)
   - Terminal 3: Run test commands

2. **Test API Interactively**
   - Use Swagger UI: http://127.0.0.1:8000/docs
   - Click "Try it out" on each endpoint
   - Great for learning the API

3. **Save Template IDs**
   ```powershell
   # Create a templates.txt file
   @"
   sales_report_template = abc123de
   progress_report_template = xyz789ab
   performance_review_template = def456gh
   "@ | Out-File templates.txt
   ```

4. **Reuse Templates**
   - Upload a template once
   - Generate unlimited reports with same template_id
   - Saves time and maintains consistency

## Next Steps

- Read [IMPLEMENTATION_GUIDE.md](IMPLEMENTATION_GUIDE.md) for detailed workflows
- Check [API_QUICK_REFERENCE.md](API_QUICK_REFERENCE.md) for API syntax
- See [ARCHITECTURE.md](ARCHITECTURE.md) for technical details
- Explore API docs at http://127.0.0.1:8000/docs

## Common Commands Cheat Sheet

```powershell
# Activate virtual environment
venv\Scripts\Activate.ps1

# Install/update packages
pip install -r requirements.txt
pip install -r requirements.txt --upgrade

# Start Gotenberg (Docker)
docker run -p 3000:3000 gotenberg/gotenberg:latest

# Start FastAPI
uvicorn main:app --reload

# Test API availability
curl http://127.0.0.1:8000/docs

# List templates
Get-ChildItem template_metadata/

# Create .env from example
Copy-Item .env.example .env
```

## Support & Help

- **API Documentation**: http://127.0.0.1:8000/docs
- **Gemini Docs**: https://ai.google.dev/
- **Gotenberg Docs**: https://gotenberg.dev/
- **FastAPI Docs**: https://fastapi.tiangolo.com/

---

**Ready to use! 🚀**

For the first time, follow steps 1-8 above. After that, just:
1. Ensure Gotenberg is running (Terminal 1)
2. Ensure FastAPI is running (Terminal 2)
3. Use the API!
