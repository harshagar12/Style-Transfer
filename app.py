import os
import json
import streamlit as st
import requests

BACKEND_URL = "http://127.0.0.1:8000"

st.set_page_config(
    page_title="Report Generator",
    page_icon="📄",
    layout="wide",
)

st.title("📄 Report Generator")

@st.cache_data(ttl=30)
def fetch_templates() -> dict[str, str]:
    """
    Returns {display_name -> template_id} by scanning the local
    template_metadata directory.
    """
    meta_dir = os.path.join(os.path.dirname(__file__), "template_metadata")
    templates: dict[str, str] = {}
    if os.path.isdir(meta_dir):
        for fname in os.listdir(meta_dir):
            if fname.endswith(".json"):
                tid = fname[:-5]
                try:
                    with open(os.path.join(meta_dir, fname)) as f:
                        meta = json.load(f)
                    title = meta.get("title", {})
                    display = (
                        title.get("text", "").strip()
                        if isinstance(title, dict)
                        else str(title).strip()
                    )
                    display = display or tid
                except Exception:
                    display = tid
                templates[f"{display}  [{tid}]"] = tid
    return templates


def get_template_options() -> dict[str, str]:
    fetch_templates.clear()
    return fetch_templates()


tab1, tab2, tab3 = st.tabs(["📁 Template Upload", "✍️ Markdown Generation", "🖨️ PDF Generation"])

with tab1:
    st.subheader("Upload a Template")

    uploaded_file = st.file_uploader(
        "Select a .docx file",
        type=["docx"],
        help="Only Word (.docx) files are accepted.",
    )
    template_name = st.text_input(
        "Custom template name (optional)",
        placeholder="e.g. Quarterly Financial Report",
    )

    if st.button("Upload Template", key="upload_btn"):
        if uploaded_file is None:
            st.error("Please select a .docx file before uploading.")
        else:
            with st.spinner("Uploading and processing template…"):
                try:
                    files = {
                        "file": (
                            uploaded_file.name,
                            uploaded_file.getvalue(),
                            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        )
                    }
                    payload = {}
                    if template_name and template_name.strip():
                        payload["template_name"] = template_name.strip()

                    resp = requests.post(
                        f"{BACKEND_URL}/upload-template",
                        files=files,
                        data=payload,
                        timeout=60,
                    )
                    resp.raise_for_status()
                    data = resp.json()

                    if "error" in data:
                        st.error(f"Backend error: {data['error']}")
                    else:
                        tid = data.get("template_id", "—")
                        sec_count = data.get("sections_count", "?")
                        st.success(
                            f"Template processed successfully — {sec_count} sections detected."
                        )
                        st.write("**Template ID**")
                        st.code(tid)
                        st.info(
                            "Copy this ID and use it in the Markdown Generation or PDF Generation tabs."
                        )

                except requests.exceptions.ConnectionError:
                    st.error(
                        f"Could not reach the backend. Make sure the FastAPI server is running on {BACKEND_URL}."
                    )
                except requests.exceptions.Timeout:
                    st.error("The request timed out. The server may be busy — please try again.")
                except Exception as exc:
                    st.error(f"Unexpected error: {exc}")


with tab2:
    st.subheader("Generate Markdown")

    templates_md = get_template_options()

    if templates_md:
        selected_label_md = st.selectbox(
            "Select a template",
            options=list(templates_md.keys()),
            key="template_select_md",
        )
        selected_tid_md = templates_md[selected_label_md]
    else:
        st.warning("No templates found. Upload one in the Template Upload tab first.")
        selected_tid_md = st.text_input(
            "Or enter Template ID manually",
            placeholder="e.g. a1b2c3d4",
            key="manual_tid_md",
        )

    prompt_text = st.text_area(
        "Prompt",
        height=300,
        placeholder="e.g. Write a Q3 performance report for an e-commerce platform.",
        key="prompt_area",
    )

    if st.button("Generate Markdown", key="gen_md_btn"):
        tid = selected_tid_md if isinstance(selected_tid_md, str) else ""
        if not tid:
            st.error("Please select or enter a Template ID.")
        elif not prompt_text.strip():
            st.error("Please enter a prompt before generating.")
        else:
            with st.spinner("Calling Gemini AI — this may take a few seconds…"):
                try:
                    payload = {"template_id": tid, "prompt": prompt_text.strip()}
                    resp = requests.post(
                        f"{BACKEND_URL}/generate-markdown", json=payload, timeout=120
                    )
                    resp.raise_for_status()
                    data = resp.json()

                    if "error" in data:
                        st.error(f"Backend error: {data['error']}")
                    else:
                        md_output = data.get("markdown", "")
                        st.success("Markdown generated successfully!")
                        st.session_state["last_markdown"] = md_output

                        st.write("**Generated Markdown**")
                        st.code(md_output, language="markdown")

                        st.download_button(
                            label="Download as .md file",
                            data=md_output,
                            file_name="report.md",
                            mime="text/markdown",
                            key="download_md_file",
                        )

                except requests.exceptions.ConnectionError:
                    st.error(
                        f"Could not reach the backend. Make sure the FastAPI server is running on {BACKEND_URL}."
                    )
                except requests.exceptions.Timeout:
                    st.error("The request timed out. Gemini generation can take a while — please try again.")
                except Exception as exc:
                    st.error(f"Unexpected error: {exc}")


with tab3:
    st.subheader("Generate PDF")

    templates_pdf = get_template_options()

    if templates_pdf:
        selected_label_pdf = st.selectbox(
            "Select a template (for styling)",
            options=list(templates_pdf.keys()),
            key="template_select_pdf",
        )
        selected_tid_pdf = templates_pdf[selected_label_pdf]
    else:
        st.warning("No templates found. Upload one in the Template Upload tab first.")
        selected_tid_pdf = st.text_input(
            "Or enter Template ID manually",
            placeholder="e.g. a1b2c3d4",
            key="manual_tid_pdf",
        )

    pdf_filename = st.text_input(
        "Output file name",
        value="report.pdf",
        placeholder="report.pdf",
        key="pdf_filename",
    )

    prefill_md = st.session_state.get("last_markdown", "")
    markdown_input = st.text_area(
        "Markdown content",
        value=prefill_md,
        height=600,
        placeholder="Paste or type your markdown here…",
        key="pdf_markdown_area",
    )
    if prefill_md:
        st.caption("Markdown from the Markdown Generation tab was pre-filled. You can edit it freely.")

    if st.button("Generate PDF", key="gen_pdf_btn"):
        tid = selected_tid_pdf if isinstance(selected_tid_pdf, str) else ""
        fname = pdf_filename.strip() or "report.pdf"
        if not fname.endswith(".pdf"):
            fname += ".pdf"

        if not tid:
            st.error("Please select or enter a Template ID.")
        elif not markdown_input.strip():
            st.error("Please enter some markdown content before generating.")
        else:
            with st.spinner("Generating PDF via Gotenberg…"):
                try:
                    payload = {
                        "template_id": tid,
                        "markdown": markdown_input.strip(),
                        "filename": fname,
                    }
                    resp = requests.post(
                        f"{BACKEND_URL}/generate-pdf",
                        json=payload,
                        timeout=120,
                    )
                    resp.raise_for_status()

                    content_type = resp.headers.get("content-type", "")
                    if "application/pdf" in content_type or resp.content[:4] == b"%PDF":
                        st.success("PDF generated successfully!")
                        st.download_button(
                            label=f"Download {fname}",
                            data=resp.content,
                            file_name=fname,
                            mime="application/pdf",
                            key="download_pdf_btn",
                        )
                    else:
                        try:
                            data = resp.json()
                            st.error(f"Backend error: {data.get('error', resp.text)}")
                        except Exception:
                            st.error(f"Unexpected response from backend: {resp.text[:400]}")

                except requests.exceptions.ConnectionError:
                    st.error(
                        f"Could not reach the backend. Make sure the FastAPI server is running on {BACKEND_URL}."
                    )
                except requests.exceptions.Timeout:
                    st.error("The request timed out. PDF generation can take a while — please try again.")
                except Exception as exc:
                    st.error(f"Unexpected error: {exc}")
