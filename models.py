from pydantic import BaseModel

class Block(BaseModel):
    type: str
    text: str

class GenerateRequest(BaseModel):
    template_id: str
    plain_text: str

class MarkdownGenerateRequest(BaseModel):
    template_id: str
    prompt: str

class PDFGenerateRequest(BaseModel):
    markdown: str
    template_id: str
    filename: str = "report.pdf"
