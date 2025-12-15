import streamlit as st
import os
import zipfile
import json
import io
import tempfile
import docx2txt
from PyPDF2 import PdfReader
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv

load_dotenv()

os.environ["GOOGLE_API_KEY"] = os.getenv("gemini")

st.set_page_config(page_title="AI WEBSITE CREATOR", page_icon="🤖")
st.title("🌐 AI AUTOMATION WEBSITE")

uploaded_file = st.file_uploader(
    "Upload File",
    type=['docx', 'png', 'jpg', 'jpeg', 'txt', 'pdf', 'json']
)

file_text = ""

if uploaded_file:
    st.success(f"Uploaded: {uploaded_file.name}")
    mime = uploaded_file.type 

    try:
        # ---------- PDF ----------
        if mime == "pdf" or uploaded_file.name.lower().endswith(".pdf"):
            # read bytes and use PdfReader from BytesIO
            uploaded_file.seek(0)
            pdf_bytes = uploaded_file.read()
            try:
                reader = PdfReader(io.BytesIO(pdf_bytes))
                text_pages = []
                for page in reader.pages:
                    t = page.extract_text()
                    if t:
                        text_pages.append(t)
                file_text = "\n".join(text_pages).strip()
            except Exception as e:
                st.warning(f"PdfReader failed: {e}")
                file_text = ""

        # ---------- TXT ----------
        elif mime == "text" or uploaded_file.name.lower().endswith(".txt"):
            uploaded_file.seek(0)
            file_text = uploaded_file.read().decode("utf-8", errors="ignore")

        # ---------- JSON ----------
        elif mime == "json" or uploaded_file.name.lower().endswith(".json"):
            uploaded_file.seek(0)
            data = json.load(uploaded_file)
            file_text = json.dumps(data, indent=2)

        # ---------- DOCX ----------
        elif (mime == "vnd.openxmlformats-officedocument.wordprocessingml.document"
              or uploaded_file.name.lower().endswith(".docx")):
            uploaded_file.seek(0)
            # docx2txt sometimes expects a filename, so save to temp file then process
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
                    tmp.write(uploaded_file.read())
                    tmp_path = tmp.name
                file_text = docx2txt.process(tmp_path) or ""
            finally:
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass

        # ---------- IMAGE ----------
        elif mime.startswith("image/") or uploaded_file.name.lower().endswith((".png", ".jpg", ".jpeg")):
            file_text = ""  # images need OCR to extract text
            st.info("Image uploaded. To extract text from images/scanned PDFs you must enable OCR (pytesseract).")

        else:
            # fallback: try to read as text
            try:
                uploaded_file.seek(0)
                file_text = uploaded_file.read().decode("utf-8", errors="ignore")
            except Exception:
                file_text = ""

    except Exception as e:
        st.error(f"Error while reading file: {e}")
        file_text = ""

prompt = st.text_area("✍️ Write your prompt…", height=150)

if st.button("Generate"):
    # prepare system message
    system_msg = """ You are an expert web developer with deep knowledge of HTML, CSS, JavaScript, UI/UX design, and responsive layouts.
Your task is to generate a complete, production-quality frontend website based on the user prompt.
Follow these rules:

Always generate clean, structured, and well-commented code.

The output must include three sections:

--html--
[html code]
--html--

--css--
[css code]
--css--

--js--
[java script code]
--js--

Use modern UI/UX principles, including responsive navbar, proper spacing, fonts, and color palette.
Smooth animations and transitions.
Code should work independently in a single HTML file.
Use only frontend technologies (no backend).
Do not explain the code unless the user requests an explanation.
"""

    # attach extracted file content to user prompt (if any)
    final_prompt = prompt
    if uploaded_file and file_text:
        final_prompt += "\n\n---\nUse the following extracted content from the uploaded file to fill the portfolio/website:\n\n"
        final_prompt += file_text

    if uploaded_file and not file_text:
        final_prompt += "\n\n---\nNote: A file was uploaded but no selectable text was extracted. If this is a scanned PDF/image, consider enabling OCR or providing a text/DOCX version."

    # combine messages
    messages = [("system", system_msg), ("user", final_prompt)]

    # call model
    model = ChatGoogleGenerativeAI(model="gemini-2.5-flash")
    response = model.invoke(messages)

    # guard: check splits exist before writing
    content = response.content

    required = ["--html--", "--css--", "--js--"]

    if not all(tag in content for tag in required):
        st.error("Invalid AI output format.")
        st.text_area("AI Raw Output", content, height=300)
        st.stop()

    html_part = content.split("--html--")[1].split("--html--")[0]
    css_part = content.split("--css--")[1].split("--css--")[0]
    js_part = content.split("--js--")[1].split("--js--")[0]


    # write files to disk
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_part.strip())

    with open("style.css", "w", encoding="utf-8") as f:
        f.write(css_part.strip())

    with open("script.js", "w", encoding="utf-8") as f:
        f.write(js_part.strip())

    # zip and offer download
    with zipfile.ZipFile("zipfile.zip", "w") as z:
        z.write("index.html")
        z.write("style.css")
        z.write("script.js")

    st.download_button(
        "👉 CLICK HERE TO DOWNLOAD",
        data=open("zipfile.zip", "rb"),
        file_name="website.zip"
    )

    st.success("🎉 success")
