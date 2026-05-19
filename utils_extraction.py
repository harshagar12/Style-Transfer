import re
from typing import Dict, Any
from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

def extract_metadata_from_docx(doc) -> Dict[str, Any]:
    metadata = {
        "table_of_contents": [],
        "title": {},
        "sections": [],
        "layout": {"page_size": "A4"},
        "basic_style": {}
    }

    def first_text_run(para: Paragraph):
        for r in para.runs:
            if r.text and r.text.strip():
                return r
        return para.runs[0] if para.runs else None

    def para_style_name(para: Paragraph) -> str:
        try:
            return (para.style.name or "").strip().lower()
        except Exception:
            return ""

    def is_list_paragraph(para: Paragraph, text: str) -> bool:
        style_name = para_style_name(para)
        if "list" in style_name or "bullet" in style_name or "number" in style_name:
            return True
        return bool(re.match(r"^(?:[-*•–]|\d+[\.)])\s+", text))

    def heading_level(para: Paragraph, text: str, fmt: Dict[str, Any], base_font: float) -> int:
        style_name = para_style_name(para)

        m = re.match(r"heading\s*(\d+)", style_name)
        if m:
            level = int(m.group(1))
            if level <= 2:
                return level
            return 2

        if text.startswith("##"):
            return 2
        if text.startswith("#"):
            return 1

        if len(text) > 90:
            return 0
        if re.search(r"[\.!?]$", text):
            return 0

        size = float(fmt.get("font_size", 0) or 0)
        bold = bool(fmt.get("bold"))
        underline = bool(fmt.get("underline"))
        italic = bool(fmt.get("italic"))

        strong_heading = size >= (base_font + 4.0) or (bold and underline)
        soft_heading = size >= (base_font + 2.0) or bold or (underline and not italic)

        if strong_heading:
            return 1
        if soft_heading:
            return 2
        return 0

    def new_section(heading_text: str = "", heading_style: Dict[str, Any] = None) -> Dict[str, Any]:
        return {
            "heading": heading_text,
            "heading_style": heading_style or {},
            "styles": {
                "paragraph": {},
                "subheading": {},
                "list_item": {},
                "table": {}
            },
            "content": []
        }

    def table_style_from_table(table: Table) -> Dict[str, Any]:
        for row in table.rows:
            for cell in row.cells:
                for para in cell.paragraphs:
                    text = para.text.strip()
                    if not text:
                        continue
                    run = first_text_run(para)
                    if run:
                        return get_run_fmt(run, para, doc)
        return {}

    def iter_block_items(document: Document):
        for child in document.element.body.iterchildren():
            if isinstance(child, CT_P):
                yield "paragraph", Paragraph(child, document)
            elif isinstance(child, CT_Tbl):
                yield "table", Table(child, document)

    base_font_size = 11.0
    for kind, block in iter_block_items(doc):
        if kind != "paragraph":
            continue
        text = block.text.strip()
        if not text:
            continue
        run = first_text_run(block)
        title_style = get_run_fmt(run, block, doc) if run else {}
        metadata["title"] = {"text": text, "style": title_style}
        metadata["basic_style"] = title_style or {"font_name": "Calibri", "font_size": 11.0, "bold": False, "italic": False, "underline": False, "color": "000000"}
        base_font_size = float(metadata["basic_style"].get("font_size", 11.0) or 11.0)
        break

    current_section = None
    toc = []

    for kind, block in iter_block_items(doc):
        if kind == "paragraph":
            para = block
            text = para.text.strip()
            if not text:
                continue

            run = first_text_run(para)
            if not run:
                continue

            fmt = get_run_fmt(run, para, doc)

            if metadata.get("title", {}).get("text") == text and not current_section and not metadata["sections"]:
                continue

            level = heading_level(para, text, fmt, base_font_size)
            is_list = is_list_paragraph(para, text)

            if level == 1 and not is_list:
                if current_section and (current_section["heading"] or current_section["content"]):
                    metadata["sections"].append(current_section)
                current_section = new_section(text, fmt)
                toc.append(text)
                continue

            if current_section is None:
                current_section = new_section()

            if level == 2 and not is_list:
                if not current_section["styles"]["subheading"]:
                    current_section["styles"]["subheading"] = fmt
                current_section["content"].append({"type": "subheading"})
            elif is_list:
                if not current_section["styles"]["list_item"]:
                    current_section["styles"]["list_item"] = fmt
                current_section["content"].append({"type": "list_item"})
            else:
                if not current_section["styles"]["paragraph"]:
                    current_section["styles"]["paragraph"] = fmt
                current_section["content"].append({"type": "paragraph"})

        else:  
            table = block
            if current_section is None:
                current_section = new_section()

            row_count = len(table.rows)
            col_count = len(table.columns) if table.rows else 0

            tbl_style = table_style_from_table(table)
            if not current_section["styles"]["table"]:
                current_section["styles"]["table"] = tbl_style
            current_section["content"].append({"type": "table", "rows": row_count, "cols": col_count})

    if current_section and (current_section["heading"] or current_section["content"]):
        metadata["sections"].append(current_section)

    metadata["table_of_contents"] = toc
    return metadata

# Function to extract font formatting
def get_run_fmt(run, para, doc):
    
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

    _ALIGN_MAP = {
        WD_ALIGN_PARAGRAPH.CENTER:  "center",
        WD_ALIGN_PARAGRAPH.RIGHT:   "right",
        WD_ALIGN_PARAGRAPH.JUSTIFY: "justify",
        WD_ALIGN_PARAGRAPH.DISTRIBUTE: "justify",
    }
    align = None
    try:
        align = para.alignment
    except Exception:
        pass
    if align is None:
        try:
            style = para.style
            while style and align is None:
                align = style.paragraph_format.alignment
                style = style.base_style
        except Exception:
            pass
    fmt["alignment"] = _ALIGN_MAP.get(align, "left")

    return fmt
