import re
from typing import Dict, Any

def markdown_to_html_with_styling(markdown: str, metadata: Dict[str, Any]) -> str:
    """
    Convert markdown to HTML with styling from extracted template metadata.
    Applies styles across ALL sections (not just the first), keyed by heading name.
    """
    sections = metadata.get("sections", [])
    basic_style = metadata.get("basic_style", {})
    title_style = metadata.get("title", {}).get("style", {})

    # Merge styles across all sections: later sections fill in gaps
    merged_heading_style = {}
    merged_subheading_style = {}
    merged_body_style = {}
    merged_list_style = {}
    merged_table_style = {}

    for sec in sections:
        sec_styles = sec.get("styles", {}) if isinstance(sec, dict) else {}
        hs = sec.get("heading_style", {}) if isinstance(sec, dict) else {}
        if hs and not merged_heading_style:
            merged_heading_style = hs
        for key, target in [
            ("subheading", merged_subheading_style),
            ("paragraph",  merged_body_style),
            ("list_item",  merged_list_style),
            ("table",      merged_table_style),
        ]:
            src = sec_styles.get(key, {})
            if src and not target:
                # mutate in-place so the variable we captured is updated
                target.update(src)

    # Fallbacks
    if not merged_heading_style:
        merged_heading_style = basic_style
    if not title_style:
        title_style = merged_heading_style or basic_style
    if not merged_body_style:
        merged_body_style = basic_style or {"font_name": "Calibri", "font_size": 11, "bold": False, "italic": False, "underline": False, "color": "000000"}
    if not merged_subheading_style:
        merged_subheading_style = merged_heading_style
    if not merged_list_style:
        merged_list_style = merged_body_style
    if not merged_table_style:
        merged_table_style = merged_body_style

    h1_size = title_style.get("font_size", 18)
    h2_size = merged_heading_style.get("font_size", max(float(h1_size) - 2, 14))
    h3_size = merged_subheading_style.get("font_size", max(float(h2_size) - 2, 12))

    def _css_color(style_dict, fallback="000000"):
        c = style_dict.get("color", fallback) or fallback
        return c.lstrip("#")

    css_styles = f"""
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: '{merged_body_style.get('font_name', 'Calibri')}', Arial, sans-serif;
            font-size: {merged_body_style.get('font_size', 11)}pt;
            line-height: {merged_body_style.get('line_spacing', 1.15)};
            color: #{_css_color(merged_body_style)};
            margin: 1in;
        }}
        h1 {{
            font-family: '{title_style.get('font_name', 'Calibri')}', Arial, sans-serif;
            font-size: {h1_size}pt;
            font-weight: {'bold' if title_style.get('bold') else 'normal'};
            font-style: {'italic' if title_style.get('italic') else 'normal'};
            text-decoration: {'underline' if title_style.get('underline') else 'none'};
            color: #{_css_color(title_style)};
            margin-top: 14pt;
            margin-bottom: 6pt;
            border-bottom: 2px solid #333;
            padding-bottom: 4pt;
        }}
        h2 {{
            font-family: '{merged_heading_style.get('font_name', 'Calibri')}', Arial, sans-serif;
            font-size: {h2_size}pt;
            font-weight: {'bold' if merged_heading_style.get('bold') else 'normal'};
            font-style: {'italic' if merged_heading_style.get('italic') else 'normal'};
            text-decoration: {'underline' if merged_heading_style.get('underline') else 'none'};
            color: #{_css_color(merged_heading_style)};
            margin-top: 10pt;
            margin-bottom: 4pt;
        }}
        h3, h4, h5, h6 {{
            font-family: '{merged_subheading_style.get('font_name', 'Calibri')}', Arial, sans-serif;
            font-size: {h3_size}pt;
            font-weight: bold;
            color: #{_css_color(merged_subheading_style)};
            margin-top: 8pt;
            margin-bottom: 4pt;
        }}
        p {{
            font-family: '{merged_body_style.get('font_name', 'Calibri')}', Arial, sans-serif;
            font-size: {merged_body_style.get('font_size', 11)}pt;
            font-weight: {'bold' if merged_body_style.get('bold') else 'normal'};
            font-style: {'italic' if merged_body_style.get('italic') else 'normal'};
            text-decoration: {'underline' if merged_body_style.get('underline') else 'none'};
            color: #{_css_color(merged_body_style)};
            margin: 6pt 0 !important;
            text-align: justify;
        }}
        ul, ol {{
            display: block !important;
            margin: 6pt 0 8pt 0 !important;
            padding-left: 24pt !important;
            clear: both !important;
        }}
        li {{
            display: list-item !important;
            margin: 2pt 0 !important;
            padding-left: 0 !important;
            font-family: '{merged_list_style.get('font_name', merged_body_style.get('font_name', 'Calibri'))}', Arial, sans-serif;
            font-size: {merged_list_style.get('font_size', merged_body_style.get('font_size', 11))}pt;
            font-weight: {'bold' if merged_list_style.get('bold') else 'normal'};
            font-style: {'italic' if merged_list_style.get('italic') else 'normal'};
            color: #{_css_color(merged_list_style, _css_color(merged_body_style))};
        }}
        h1, h2, h3, h4, h5, h6, p, table {{
            clear: both !important;
            margin-left: 0 !important;
            padding-left: 0 !important;
        }}
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 12pt 0;
        }}
        th, td {{
            border: 1px solid #ccc;
            padding: 6pt 8pt;
            text-align: left;
            font-family: '{merged_table_style.get('font_name', merged_body_style.get('font_name', 'Calibri'))}', Arial, sans-serif;
            font-size: {merged_table_style.get('font_size', merged_body_style.get('font_size', 11))}pt;
            color: #{_css_color(merged_table_style, _css_color(merged_body_style))};
        }}
        th {{
            background-color: #f0f0f0;
            font-weight: bold;
        }}
        pre, code {{
            font-family: 'Courier New', monospace;
            font-size: 10pt;
            background: #f5f5f5;
            padding: 2pt 4pt;
        }}
        pre {{
            padding: 8pt;
            margin: 8pt 0;
            overflow-x: auto;
        }}
    </style>
    """

    # Basic markdown to HTML conversion
    html_content = markdown_to_basic_html(markdown)

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        {css_styles}
    </head>
    <body>
        {html_content}
    </body>
    </html>
    """

def markdown_to_basic_html(markdown: str) -> str:
    """
    Basic markdown to HTML conversion.
    Supports headers, paragraphs, bold, italic, lists, tables, and code blocks.
    """
    lines = markdown.split("\n")
    html_lines = []
    in_code_block = False
    in_list = False          # True when inside a list
    list_tag = "ul"          # tracks whether current open list is ul or ol
    in_table = False

    def close_list():
        nonlocal in_list, list_tag
        if in_list:
            html_lines.append(f"</{list_tag}>")
            # Hard reset: explicit block-level div flushes all float/indent state
            html_lines.append('<div style="clear:both;margin:0;padding:0;line-height:0;height:0;font-size:0;"></div>')
            in_list = False
            list_tag = "ul"

    def close_table():
        nonlocal in_table
        if in_table:
            html_lines.append("</tbody></table>")
            in_table = False

    for line in lines:
        # ── Code blocks ──────────────────────────────────────────────────────
        if line.strip().startswith("```"):
            close_list()
            close_table()
            if in_code_block:
                html_lines.append("</code></pre>")
                in_code_block = False
            else:
                lang = line.strip()[3:].strip()
                html_lines.append(f'<pre><code class="language-{lang}">')
                in_code_block = True
            continue

        if in_code_block:
            # Escape HTML entities so code renders literally
            html_lines.append(line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))
            continue

        # ── Empty lines ───────────────────────────────────────────────────────
        if not line.strip():
            close_list()
            close_table()
            # Use a zero-height block, NOT <br>, so no extra gap accumulates
            html_lines.append('<div style="margin:0;padding:0;height:6pt;"></div>')
            continue

        stripped = line.strip()

        # ── Markdown table rows (| col | col |) ──────────────────────────────
        if stripped.startswith("|") and stripped.endswith("|"):
            close_list()
            # Skip separator rows like |---|---|
            if re.match(r"^\|[\s\-\|:]+\|$", stripped):
                continue
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            if not in_table:
                html_lines.append('<table><thead><tr>')
                for c in cells:
                    html_lines.append(f"<th>{format_inline_markdown(c)}</th>")
                html_lines.append("</tr></thead><tbody>")
                in_table = True
            else:
                html_lines.append("<tr>")
                for c in cells:
                    html_lines.append(f"<td>{format_inline_markdown(c)}</td>")
                html_lines.append("</tr>")
            continue

        # Any non-table line closes an open table
        close_table()

        # ── Headers ───────────────────────────────────────────────────────────
        # Use re.match to strip exactly the right number of # chars
        header_match = re.match(r"^(#{1,6})\s+(.*)", stripped)
        if header_match:
            close_list()
            level = len(header_match.group(1))
            text = format_inline_markdown(header_match.group(2).strip())
            html_lines.append(f"<h{level}>{text}</h{level}>")
            continue

        # ── Unordered lists ───────────────────────────────────────────────────
        ul_match = re.match(r"^[-*+]\s+(.*)", stripped)
        if ul_match:
            if in_list and list_tag == "ol":
                close_list()
            if not in_list:
                html_lines.append("<ul>")
                in_list = True
                list_tag = "ul"
            html_lines.append(f"<li>{format_inline_markdown(ul_match.group(1))}</li>")
            continue

        # ── Ordered lists ─────────────────────────────────────────────────────
        ol_match = re.match(r"^\d+[.)]\s+(.*)", stripped)
        if ol_match:
            if in_list and list_tag == "ul":
                close_list()
            if not in_list:
                html_lines.append("<ol>")
                in_list = True
                list_tag = "ol"
            html_lines.append(f"<li>{format_inline_markdown(ol_match.group(1))}</li>")
            continue

        # ── Paragraphs ────────────────────────────────────────────────────────
        close_list()
        html_lines.append(f"<p>{format_inline_markdown(stripped)}</p>")

    # Close any unclosed blocks at EOF
    close_list()
    close_table()
    if in_code_block:
        html_lines.append("</code></pre>")

    return "\n".join(html_lines)

def format_inline_markdown(text: str) -> str:
    """Format inline markdown elements (bold, italic, code)."""
    # Bold
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'__(.+?)__', r'<strong>\1</strong>', text)
    # Italic
    text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
    text = re.sub(r'_(.+?)_', r'<em>\1</em>', text)
    # Code
    text = re.sub(r'`(.+?)`', r'<code>\1</code>', text)
    return text
