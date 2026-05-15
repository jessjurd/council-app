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

# ===================== UPLOAD + AUTO PARSE MULTIPLE REPORTS =====================
st.header("📄 Upload Full Council Minutes PDF")

uploaded_file = st.file_uploader("Upload the full meeting minutes PDF", type=["pdf"])

parsed_reports = []

if uploaded_file and st.button("🔄 Auto Parse ALL Reports"):
    doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
    full_text = "".join(page.get_text() for page in doc)

    # Split into individual reports
    items = re.split(r'(CORPORATE AND COMMUNITY NO\.\s*CC\d+/\d+)', full_text, re.I)
    
    for i in range(1, len(items), 2):
        if i + 1 >= len(items):
            continue
        section = items[i] + items[i + 1]
        
        report_num = re.search(r'NO\.\s*(CC\d+/\d+)', section, re.I)
        if not report_num:
            continue
            
        title = re.search(r'SUBJECT:\s*(.+?)(?=MOTION|AMENDMENT|$)', section, re.I | re.S)
        rec = re.search(r'(?:RECOMMENDATION|MOTION)[:\s]*(.+?)(?=Moved|FOR|The Amendment|CARRIED|$)', section, re.I | re.S)
        
        for_block = re.search(r'FOR\s*(.+?)(?=AGAINST|Total)', section, re.I | re.S)
        against_block = re.search(r'AGAINST\s*(.+?)(?=Total)', section, re.I | re.S)
        
        outcome = re.search(r'(The Amendment was PUT and CARRIED|The Motion was then PUT and CARRIED|CARRIED|LOST)', section, re.I | re.S)
        
        conflicts = re.search(r'Conflict.*?Interest[:\s]*(.+?)(?=\n{2,}|$)', section, re.I | re.S)
        
        parsed_reports.append({
            'report_number': report_num.group(1).upper() if report_num else "",
            'title': title.group(1).strip() if title else "Untitled",
            'recommendation': rec.group(1).strip() if rec else "",
            'yes_votes': for_block.group(1).strip() if for_block else "",
            'no_votes': against_block.group(1).strip() if against_block else "",
            'outcome': outcome.group(0) if outcome else "Approved",
            'conflicts': conflicts.group(1).strip() if conflicts else
