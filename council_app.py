import streamlit as st
import pandas as pd
import sqlite3
import re
import fitz  # PyMuPDF
from datetime import datetime

st.set_page_config(page_title="Cessnock Council Reports", layout="wide")
st.title("🗳️ Cessnock Council Report Logger")

# Database
conn = sqlite3.connect('cessnock_reports.db', check_same_thread=False)
conn.execute('''CREATE TABLE IF NOT EXISTS reports (
    id INTEGER PRIMARY KEY,
    report_number TEXT,
    title TEXT,
    meeting_date TEXT,
    recommendation TEXT,
    yes_votes TEXT,
    no_votes TEXT,
    outcome TEXT,
    conflicts TEXT,
    englobo INTEGER DEFAULT 0,
    entered_at TEXT
)''')
conn.commit()

# ===================== UPLOAD + AUTO FILL =====================
st.header("📄 Upload PDF (Auto Fill Fields)")

uploaded_file = st.file_uploader("Upload Council Minutes PDF", type=["pdf"])

auto_data = {}
if uploaded_file and st.button("🔄 Auto Parse PDF"):
    doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
    text = "".join(page.get_text() for page in doc)
    
    auto_data['report_number'] = re.search(r'(CC\d+/\d+)', text, re.I)
    auto_data['title'] = re.search(r'SUBJECT:\s*(.+)', text, re.I)
    auto_data['rec'] = re.search(r'(?:RECOMMENDATION|MOTION)[:\s]*(.+?)(?=Moved|FOR|CARRIED|$)', text, re.I | re.S)
    auto_data['conflicts'] = re.search(r'Conflict.*?Interest[:\s]*(.+?)(?=\n{2,}|$)', text, re.I | re.S)

    st.success("✅ Parsed! Fields below are auto-filled. Edit if needed.")

# ===================== DATA ENTRY =====================
st.header("📝 Data Entry")

col1, col2 = st.columns(2)
with col1:
    report_number = st.text_input("Report Number", value=auto_data.get('report_number').group(1) if auto_data.get('report_number') else "")
    title = st.text_input("Title", value=auto_data.get('title').group(1).strip() if auto_data.get('title') else "")
    meeting_date = st.date
