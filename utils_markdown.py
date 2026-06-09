import re
from typing import Dict, Any, List, Optional

def _normalize_heading(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", str(text).lower())).strip()


# ── Public entry point ────────────────────────────────────────────────────────

def markdown_to_html_with_styling(markdown: str, metadata: Dict[str, Any]) -> str:
    toc            = metadata.get("table_of_contents") or []
    sections_meta  = metadata.get("sections") or []
    raw_default    = metadata.get("default_style") or {}
    raw_title      = (metadata.get("title") or {}).get("style") or {}

    # ── 1. Body baseline ──────────────────────────────────────────────────────
    # Alignment for body text is ALWAYS "left" – override whatever the template says.
    _HARDCODED = {
        "font_name": "Calibri", "font_size": 11, "bold": False,
        "italic": False, "underline": False, "color": "000000",
        "alignment": "left",
    }
    body_base = {**_HARDCODED, **raw_default}
    body_base["alignment"] = "left"   # force: body text is never centred

    # ── 2. Title style ────────────────────────────────────────────────────────
    # Title MAY have its own alignment (e.g. centred); default to "left".
    title_style = {**body_base, **raw_title}
    title_style.setdefault("alignment", "left")

    # ── 3. Build the section → element-type → style lookup dictionary ─────────
    #
    # Shape:
    #   {
    #     "introduction": {
    #         "heading":    { ...style with alignment from template... },
    #         "subheading": { ...style with alignment from template... },
    #         "paragraph":  { ...style with alignment FORCED to "left"... },
    #         "list_item":  { ...style with alignment FORCED to "left"... },
    #         "table":      { ...style with alignment FORCED to "left"... },
    #     },
    #     ...
    #   }
    #
    # Alignment is baked in here once so the renderer never has to think about it.

    def _style(override: Optional[dict], force_left: bool) -> dict:
        """Merge override onto body_base. If force_left, alignment is always 'left'."""
        result = {**body_base, **(override or {})}
        if force_left:
            result["alignment"] = "left"
        else:
            result.setdefault("alignment", "left")
        return result

    section_styles: Dict[str, Dict[str, Any]] = {}
    for idx, heading_text in enumerate(toc):
        sec = sections_meta[idx] if idx < len(sections_meta) else {}
        es  = sec.get("element_styles") or {}
        key = _normalize_heading(heading_text)
        section_styles[key] = {
            # Headings & subheadings: use template alignment (or "left")
            "heading":    _style(sec.get("heading_style"), force_left=False),
            "subheading": _style(es.get("subheading"),     force_left=False),
            # Body elements: alignment is ALWAYS "left"
            "paragraph":  _style(es.get("paragraph"),  force_left=True),
            "list_item":  _style(es.get("list_item"),   force_left=True),
            "table":      _style(es.get("table"),       force_left=True),
        }

    # ── 4. CSS helpers ────────────────────────────────────────────────────────
    _VALID_ALIGNS = {"left", "center", "right", "justify"}

    def css_color(s: dict) -> str:
        return str(s.get("color", "000000") or "000000").lstrip("#")

    def css_align(s: dict) -> str:
        a = str(s.get("alignment", "left") or "left").strip().lower()
        return a if a in _VALID_ALIGNS else "left"

    def inline_style(s: dict, include_spacing: bool = False) -> str:
        """
        Build an inline CSS string for element s.
        s['alignment'] is read directly – it was baked correctly during dict build.
        No fallback chains, no inheritance possible.
        """
        parts = [
            f"font-family: '{s.get('font_name', 'Calibri')}', Arial, sans-serif",
            f"font-size: {s.get('font_size', 11)}pt",
            f"font-weight: {'bold' if s.get('bold') else 'normal'}",
            f"font-style: {'italic' if s.get('italic') else 'normal'}",
            f"text-decoration: {'underline' if s.get('underline') else 'none'}",
            f"color: #{css_color(s)}",
            # !important ensures Chromium's UA print stylesheet cannot override
            # the alignment we explicitly set per element.
            f"text-align: {css_align(s)} !important",
        ]
        if include_spacing and s.get("line_spacing") is not None:
            parts.append(f"line-height: {s.get('line_spacing')}")
        return "; ".join(parts)

    # ── 5. Global CSS ─────────────────────────────────────────────────────────
    css = f"""
    <style>
        /* @page sets the PRINT page margins – this is what Chromium/Gotenberg
           actually respects when rendering to PDF. body margin is ignored in
           print mode by most Chromium-based renderers. */
        @page {{
            size: Letter;
            margin: 1in;
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: '{body_base.get('font_name', 'Calibri')}', Arial, sans-serif;
            font-size: {body_base.get('font_size', 11)}pt;
            line-height: {body_base.get('line_spacing', 1.15)};
            color: #{css_color(body_base)};
            /* text-align default – each element overrides via inline style */
            text-align: left;
        }}
        /* Hard left-align baseline; each element's inline style !important
           overrides this where a different alignment is needed (e.g. title). */
        h1, h2, h3, h4, h5, h6, p, li, td, th {{ text-align: left; }}
        ul, ol {{ display: block !important; margin: 6pt 0 8pt 0 !important;
                  padding-left: 24pt !important; clear: both !important; }}
        h1, h2, h3, h4, h5, h6, p, table {{
            clear: both !important; margin-left: 0 !important; padding-left: 0 !important;
        }}
        table {{ border-collapse: collapse; width: 100%; margin: 12pt 0; }}
        th, td {{ border: 1px solid #ccc; padding: 6pt 8pt; }}
        th {{ background-color: #f0f0f0; font-weight: bold; }}
        pre, code {{ font-family: 'Courier New', monospace; font-size: 10pt;
                     background: #f5f5f5; padding: 2pt 4pt; }}
        pre {{ padding: 8pt; margin: 8pt 0; overflow-x: auto; }}
        p {{ margin: 6pt 0 !important; }}
        li {{ margin: 2pt 0 !important; }}
    </style>
    """

    html_body = _render_markdown(
        markdown, section_styles, title_style, body_base, inline_style
    )

    return f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="UTF-8">{css}</head>
    <body>{html_body}</body>
    </html>
    """


# ── Renderer ──────────────────────────────────────────────────────────────────

def _render_markdown(
    markdown: str,
    section_styles: Dict[str, Dict[str, Any]],
    title_style: Dict[str, Any],
    body_base: Dict[str, Any],
    inline_style_fn,        # fn(style_dict: dict, include_spacing: bool) -> str
) -> str:
    """
    Iterate the markdown line by line.

    Alignment strategy
    ------------------
    * When a '## Section Heading' is encountered, look it up in section_styles
      and set current_sec to that section's style dict.
    * Every element rendered (p, li, h2, h3, table cell) calls inline_style_fn
      with its own style dict, which already has the correct 'text-align' baked in.
    * No element can inherit another's alignment – each carries its own inline style.
    """
    # Default section: all elements use body_base (alignment = "left")
    _default_sec: Dict[str, Any] = {k: body_base for k in
                                     ("heading", "subheading", "paragraph", "list_item", "table")}
    current_sec: Dict[str, Any] = (
        next(iter(section_styles.values()), _default_sec)
        if section_styles else _default_sec
    )

    html_lines: List[str] = []
    in_code_block = False
    in_list       = False
    list_tag      = "ul"
    in_table      = False

    def cur(kind: str) -> dict:
        """Return the style dict for element-type `kind` in the current section."""
        return current_sec.get(kind, body_base)

    def close_list():
        nonlocal in_list, list_tag
        if in_list:
            html_lines.append(f"</{list_tag}>")
            html_lines.append(
                '<div style="clear:both;margin:0;padding:0;line-height:0;height:0;font-size:0;"></div>'
            )
            in_list  = False
            list_tag = "ul"

    def close_table():
        nonlocal in_table
        if in_table:
            html_lines.append("</tbody></table>")
            in_table = False

    for line in markdown.split("\n"):

        # ── Code fence ────────────────────────────────────────────────────────
        if line.strip().startswith("```"):
            close_list(); close_table()
            if in_code_block:
                html_lines.append("</code></pre>")
                in_code_block = False
            else:
                lang = line.strip()[3:].strip()
                html_lines.append(f'<pre><code class="language-{lang}">')
                in_code_block = True
            continue

        if in_code_block:
            html_lines.append(
                line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            )
            continue

        # ── Blank line ────────────────────────────────────────────────────────
        if not line.strip():
            close_list(); close_table()
            html_lines.append('<div style="margin:0;padding:0;height:6pt;"></div>')
            continue

        stripped = line.strip()

        # ── Table rows ────────────────────────────────────────────────────────
        if stripped.startswith("|") and stripped.endswith("|"):
            close_list()
            if re.match(r"^\|[\s\-\|:]+\|$", stripped):
                continue                          # separator row
            cells    = [c.strip() for c in stripped.strip("|").split("|")]
            t_style  = inline_style_fn(cur("table"), False)
            if not in_table:
                html_lines.append(f'<table style="{t_style}"><thead><tr>')
                for c in cells:
                    html_lines.append(f'<th style="{t_style}">{format_inline_markdown(c)}</th>')
                html_lines.append("</tr></thead><tbody>")
                in_table = True
            else:
                html_lines.append("<tr>")
                for c in cells:
                    html_lines.append(f'<td style="{t_style}">{format_inline_markdown(c)}</td>')
                html_lines.append("</tr>")
            continue

        close_table()

        # ── Headings ──────────────────────────────────────────────────────────
        hm = re.match(r"^(#{1,6})\s+(.*)", stripped)
        if hm:
            close_list()
            level = len(hm.group(1))
            text  = hm.group(2).strip()

            if level == 1:
                # Document title – uses title_style (may be centred)
                html_lines.append(
                    f'<h1 style="{inline_style_fn(title_style, True)};'
                    f' margin-top: 14pt; margin-bottom: 6pt;'
                    f' border-bottom: 2px solid #333; padding-bottom: 4pt;">'
                    f'{format_inline_markdown(text)}</h1>'
                )

            elif level == 2:
                # Section heading: switch current section, then render with its heading style
                key = _normalize_heading(text)
                if key in section_styles:
                    current_sec = section_styles[key]
                html_lines.append(
                    f'<h2 style="{inline_style_fn(cur("heading"), True)};'
                    f' margin-top: 10pt; margin-bottom: 4pt;">'
                    f'{format_inline_markdown(text)}</h2>'
                )

            elif level == 3:
                html_lines.append(
                    f'<h3 style="{inline_style_fn(cur("subheading"), True)};'
                    f' margin-top: 8pt; margin-bottom: 4pt;">'
                    f'{format_inline_markdown(text)}</h3>'
                )

            else:
                html_lines.append(f"<h{level}>{format_inline_markdown(text)}</h{level}>")
            continue

        # ── Unordered list ────────────────────────────────────────────────────
        ul_m = re.match(r"^[-*+]\s+(.*)", stripped)
        if ul_m:
            if in_list and list_tag == "ol":
                close_list()
            if not in_list:
                html_lines.append("<ul>")
                in_list  = True
                list_tag = "ul"
            html_lines.append(
                f'<li style="{inline_style_fn(cur("list_item"), False)}">'
                f'{format_inline_markdown(ul_m.group(1))}</li>'
            )
            continue

        # ── Ordered list ──────────────────────────────────────────────────────
        ol_m = re.match(r"^\d+[.)]\s+(.*)", stripped)
        if ol_m:
            if in_list and list_tag == "ul":
                close_list()
            if not in_list:
                html_lines.append("<ol>")
                in_list  = True
                list_tag = "ol"
            html_lines.append(
                f'<li style="{inline_style_fn(cur("list_item"), False)}">'
                f'{format_inline_markdown(ol_m.group(1))}</li>'
            )
            continue

        # ── Paragraph ─────────────────────────────────────────────────────────
        close_list()
        html_lines.append(
            f'<p style="{inline_style_fn(cur("paragraph"), True)}">'
            f'{format_inline_markdown(stripped)}</p>'
        )

    close_list()
    close_table()
    if in_code_block:
        html_lines.append("</code></pre>")

    return "\n".join(html_lines)


# ── Inline markdown formatting ────────────────────────────────────────────────

def format_inline_markdown(text: str) -> str:
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'__(.+?)__',     r'<strong>\1</strong>', text)
    text = re.sub(r'\*(.+?)\*',     r'<em>\1</em>',         text)
    text = re.sub(r'_(.+?)_',       r'<em>\1</em>',         text)
    text = re.sub(r'`(.+?)`',       r'<code>\1</code>',     text)
    return text
