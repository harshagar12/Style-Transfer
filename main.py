import json, uuid, os, re
from typing import List
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import BaseModel
from docx import Document
from docx.shared import Pt, RGBColor, Inches
import tempfile

app = FastAPI()

METADATA_DIR = "template_metadata"
os.makedirs(METADATA_DIR, exist_ok=True)

class Block(BaseModel):
    type: str
    text: str

class GenerateRequest(BaseModel):
    template_id: str
    plain_text: str

def get_run_fmt(run, para, doc):
    # Extract font formatting
    fmt = {}

    try:
        normal_style = doc.styles['Normal']
    except Exception:
        normal_style = None

    doc_defaults = {}
    try:
        rPrDefault = doc.styles.element.xpath('./w:docDefaults/w:rPrDefault/w:rPr')
        if rPrDefault:
            rPr = rPrDefault[0]
            sz = rPr.xpath('./w:sz/@w:val')
            if sz: doc_defaults['size'] = Pt(int(sz[0]) / 2.0)
            rFonts = rPr.xpath('./w:rFonts/@w:ascii')
            if rFonts: doc_defaults['name'] = str(rFonts[0])
            if rPr.xpath('./w:b'): doc_defaults['bold'] = True
            if rPr.xpath('./w:i'): doc_defaults['italic'] = True
            color_el = rPr.xpath('./w:color/@w:val')
            if color_el and color_el[0] != 'auto':
                doc_defaults['color'] = str(color_el[0])
    except Exception:
        pass

    def resolve_prop(prop_name):
        def is_valid(v):
            if prop_name == "color":
                return v is not None and getattr(v, "rgb", None) is not None
            return v is not None

        val = getattr(run.font, prop_name, None)
        if is_valid(val): return val
        if run.style and run.style.font:
            val = getattr(run.style.font, prop_name, None)
            if is_valid(val): return val

        style = para.style
        checked_normal = False
        while style:
            if style.name == 'Normal': checked_normal = True
            if style.font:
                val = getattr(style.font, prop_name, None)
                if is_valid(val): return val
            style = style.base_style

        if not checked_normal and normal_style and normal_style.font:
            val = getattr(normal_style.font, prop_name, None)
            if is_valid(val): return val

        return doc_defaults.get(prop_name, None)

    fmt["font_name"] = resolve_prop("name") or "Calibri"
    size = resolve_prop("size")
    fmt["font_size"] = size.pt if size else 11.0
    fmt["bold"] = resolve_prop("bold") or False
    fmt["italic"] = resolve_prop("italic") or False
    fmt["underline"] = resolve_prop("underline") or False

    color_val = resolve_prop("color")
    if color_val and hasattr(color_val, "rgb") and color_val.rgb:
        fmt["color"] = str(color_val.rgb)
    elif "color" in doc_defaults:
        fmt["color"] = doc_defaults["color"]
    else:
        fmt["color"] = "000000"

    return fmt

# API Endpoint for Uploading a Template File
@app.post("/upload-template")
async def upload_template(file: UploadFile = File(...)):

    # Saving uploaded file temporarily
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".docx")
    tmp.write(await file.read())
    tmp.close()

    doc = Document(tmp.name)
    metadata = {"roles": {}, "layout": {}}

    # Gathering all paragraphs
    para_data = []
    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue
        run = None
        for r in para.runs:
            if r.text.strip():
                run = r
                break
        if not run and para.runs:
            run = para.runs[0]
        if not run:
            continue
        fmt = get_run_fmt(run, para, doc)
        fmt["alignment"] = para.alignment
        pf = para.paragraph_format
        fmt["line_spacing"] = pf.line_spacing
        fmt["space_before"] = pf.space_before
        fmt["space_after"] = pf.space_after
        fmt["first_line_indent"] = pf.first_line_indent
        para_data.append({"text": text, **fmt})

    def copy_fmt(p):
        """Copy formatting dict, excluding the text field."""
        return {k: v for k, v in p.items() if k != "text"}

    roles = metadata["roles"]

    if para_data:

        #Title
        roles["title"] = copy_fmt(para_data[0])

        #Body
        for p in para_data:
            if len(p["text"]) >= 60:
                roles["body"] = copy_fmt(p)
                break
        if "body" not in roles:
            longest = max(para_data, key=lambda x: len(x["text"]))
            roles["body"] = copy_fmt(longest)

        #Heading
        for p in para_data[1:]:
            if len(p["text"]) <= 70 and (p.get("bold") or p.get("italic") or p.get("underline")):
                roles["heading"] = copy_fmt(p)
                break

        #Subheading
        if "heading" in roles:
            h = roles["heading"]
            for p in para_data[1:]:
                if len(p["text"]) <= 70 and (p.get("bold") or p.get("italic") or p.get("underline")):
                    if (p.get("font_size") != h.get("font_size") or
                        p.get("bold") != h.get("bold") or
                        p.get("italic") != h.get("italic") or
                        p.get("underline") != h.get("underline") or
                        p.get("font_name") != h.get("font_name")):
                        roles["subheading"] = copy_fmt(p)
                        break
        if "subheading" not in roles:
            for p in para_data[1:]:
                if len(p["text"]) <= 70 and not p.get("bold"):
                    roles["subheading"] = copy_fmt(p)
                    break

        #List item
        for p in para_data:
            t = p["text"]
            if (t.startswith(("-", "*", "•", "–")) or
                re.match(r"^\d+[\.\)]\s", t)):
                roles["list_item"] = copy_fmt(p)
                break

    # Extracting Table styling if available
    if doc.tables:
        table = doc.tables[0]
        cell = table.cell(0, 0)
        cell_para = cell.paragraphs[0]
        run = cell_para.runs[0] if cell_para.runs else None
        if run:
            table_fmt = get_run_fmt(run, cell_para, doc)
            table_fmt["borders"] = True
        else:
            table_fmt = {"borders": True}
        roles["table"] = table_fmt

    #Layout
    metadata["layout"]["page_size"] = "A4"

    # Saving metadata
    template_id = uuid.uuid4().hex[:8]
    with open(os.path.join(METADATA_DIR, f"{template_id}.json"), "w") as f:
        json.dump(metadata, f, indent=2, default=str)

    os.unlink(tmp.name)
    return {"template_id": template_id, "message": "Template processed", "roles_found": list(roles.keys())}

# API Endpoint for Detecting Structure
def detect_structure(plain_text: str) -> List[Block]:
    lines = plain_text.strip().split("\n")
    blocks = []
    pending_paragraph = []

    def is_table_row(line: str) -> bool:
        return "\t" in line or (line.count("|") >= 2 and not line.strip().startswith("-"))

    def flush_paragraph():
        if pending_paragraph:
            blocks.append(Block(type="body", text=" ".join(pending_paragraph)))
            pending_paragraph.clear()

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            flush_paragraph()
            i += 1
            continue

        # Table detection
        if is_table_row(line):
            flush_paragraph()
            table_lines = [line]
            i += 1
            while i < len(lines) and is_table_row(lines[i].strip()):
                table_lines.append(lines[i].strip())
                i += 1
            for tline in table_lines:
                blocks.append(Block(type="table_row", text=tline))
            continue

        # List detection
        if re.match(r"^(\-|\*|•|–|\d+[\.\)])\s", line):
            flush_paragraph()
            blocks.append(Block(type="list_item", text=line))
            i += 1
            continue

        # Title detectio
        if len(blocks) == 0 and not pending_paragraph:
            blocks.append(Block(type="title", text=line))
            i += 1
            continue

        # Heading detection
        if len(line) <= 70 and not line.endswith("."):
            flush_paragraph()

            # Subheading detection
            if line.startswith("##"):
                blocks.append(Block(type="subheading", text=line.lstrip("#").strip()))
            elif line.startswith("#"):
                blocks.append(Block(type="heading", text=line.lstrip("#").strip()))
            else:
                blocks.append(Block(type="heading", text=line))
            i += 1
            continue

        # Body
        pending_paragraph.append(line)
        i += 1

    flush_paragraph()
    return blocks

# API Endpoint for Generating Document
def apply_run_fmt(run, fmt):

    if fmt.get("font_name"):
        run.font.name = fmt["font_name"]
    if fmt.get("font_size"):
        run.font.size = Pt(float(fmt["font_size"]))
    if fmt.get("bold") is not None:
        run.bold = bool(fmt["bold"])
    if fmt.get("italic") is not None:
        run.italic = bool(fmt["italic"])
    if fmt.get("underline") is not None:
        val = fmt["underline"]
        if isinstance(val, bool):
            run.underline = val
        elif isinstance(val, int) and val > 0:
            run.underline = True
        else:
            run.underline = False
    if fmt.get("color"):
        try:
            run.font.color.rgb = RGBColor.from_string(str(fmt["color"]))
        except Exception:
            pass

def apply_para_fmt(para, fmt):

    if fmt.get("alignment") is not None:
        para.alignment = int(fmt["alignment"])
    pf = para.paragraph_format
    if fmt.get("line_spacing"):
        pf.line_spacing = float(fmt["line_spacing"])
    if fmt.get("space_before"):
        val = fmt["space_before"]
        pf.space_before = Pt(val / 12700) if isinstance(val, (int, float)) and val > 100 else Pt(val) if val else None
    if fmt.get("space_after"):
        val = fmt["space_after"]
        pf.space_after = Pt(val / 12700) if isinstance(val, (int, float)) and val > 100 else Pt(val) if val else None
    if fmt.get("first_line_indent"):
        val = fmt["first_line_indent"]
        pf.first_line_indent = Pt(val / 12700) if isinstance(val, (int, float)) and val > 100 else Pt(val) if val else None

def generate_docx(template_id: str, blocks: List[Block]) -> str:

    # Loading metadata
    meta_path = os.path.join(METADATA_DIR, f"{template_id}.json")
    if not os.path.exists(meta_path):
        raise FileNotFoundError(f"Template '{template_id}' not found")
    with open(meta_path) as f:
        metadata = json.load(f)
    roles = metadata["roles"]

    doc = Document()

    # Applying basic page setup
    section = doc.sections[0]
    section.page_width = Inches(8.27)   # A4
    section.page_height = Inches(11.69)

    # Maping block types
    type_to_role = {
        "title": "title",
        "heading": "heading",
        "subheading": "subheading",
        "body": "body",
        "paragraph": "body",
        "list_item": "list_item",
        "table_row": "table",
    }

    for block in blocks:
        role_key = type_to_role.get(block.type, "body")
        fmt = roles.get(role_key, roles.get("body", {}))

        if block.type == "table_row":
            cells = [c.strip() for c in block.text.split("\t") if c.strip()]
            if not cells:
                cells = [c.strip() for c in block.text.split("|") if c.strip()]
            if not cells:
                continue
            table = doc.add_table(rows=1, cols=len(cells), style="Table Grid")
            for idx, cell_text in enumerate(cells):
                cell = table.cell(0, idx)
                cell.text = cell_text
                for run in cell.paragraphs[0].runs:
                    apply_run_fmt(run, fmt)
            doc.add_paragraph()
        elif block.type == "list_item":
            para = doc.add_paragraph()

            text = re.sub(r"^(\-|\*|•|–|\d+[\.\)])\s*", "", block.text)
            run = para.add_run(f"• {text}")
            apply_run_fmt(run, fmt)
            apply_para_fmt(para, fmt)
        else:
            para = doc.add_paragraph()
            run = para.add_run(block.text)
            apply_run_fmt(run, fmt)
            apply_para_fmt(para, fmt)

    # Saving to temp file and returning
    out_path = tempfile.mktemp(suffix=".docx")
    doc.save(out_path)
    return out_path

# API Endpoint for Generating Document
@app.post("/generate-document")
async def generate_document(req: GenerateRequest):
    try:
        blocks = detect_structure(req.plain_text)
        out_path = generate_docx(req.template_id, blocks)
        return FileResponse(out_path, media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document", filename="generated.docx")
    except FileNotFoundError as e:
        return {"error": str(e)}
