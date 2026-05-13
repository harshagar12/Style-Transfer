import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

METADATA_DIR = "template_metadata"
os.makedirs(METADATA_DIR, exist_ok=True)

# Configure Gemini API
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Gotenberg endpoint
GOTENBERG_URL = os.getenv("GOTENBERG_URL", "http://localhost:3000")
