import streamlit as st
import pandas as pd
import sqlite3
import re
import fitz
from datetime import datetime

st.set_page_config(page_title="Cessnock Council Reports", layout="wide")
st.title("🗳️ Cessnock Council Report Logger")

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

# ===================== UPLOAD + PARSE =====================
st.header("📄 Upload Full Minutes PDF")

uploaded_file = st.file_uploader("Upload the full council minutes PDF", type=["pdf"])

parsed_reports = []

if uploaded_file and st.button("🔄 Auto Parse ALL Reports"):
    doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
    full_text = "".join(page.get_text() for page in doc)

    # Split by report
    items = re.split(r'(CORPORATE AND COMMUNITY NO\.\s*CC\d+/\d+)', full_text, re.I)
    
    for i in range(1, len(items), 2):
        if i + 1 >= len(items):
            continue
        section = items[i] + items[i+1]
        
        report_num = re.search(r'NO\.\s*(CC\d+/\d+)', section, re.I)
        if not report_num:
            continue
            
        title = re.search(r'SUBJECT:\s*(.+?)(?=MOTION|AMENDMENT|$)', section, re.I | re.S)
        rec = re.search(r'(?:RECOMMENDATION|MOTION)[:\s]*(.+?)(?=Moved|FOR|CARRIED|$)', section, re.I | re.S)
        for_block = re.search(r'FOR\s*(.+?)(?=AGAINST|Total)', section, re.I | re.S)
        against_block = re.search(r'AGAINST\s*(.+?)(?=Total)', section, re.I | re.S)
        outcome = re.search(r'(CARRIED|LOST|PUT and CARRIED)', section, re.I)
        conflicts = re.search(r'Conflict.*?Interest[:\s]*(.+?)(?=\n{2,}|$)', section, re.I | re.S)
        
        parsed_reports.append({
            'report_number': report_num.group(1).upper(),
            'title': title.group(1).strip() if title else "Untitled",
            'recommendation': rec.group(1).strip() if rec else "",
            'yes_votes': for_block.group(1).strip() if for_block else "",
            'no_votes': against_block.group(1).strip() if against_block else "",
            'outcome': outcome.group(0) if outcome else "Approved",
            'conflicts': conflicts.group(1).strip() if conflicts else ""
        })

    st.success(f"✅ Found *{len(parsed_reports)} reports*!")

# Show parsed reports
if parsed_reports:
    st.header(f"📋 {len(parsed_reports)} Reports Found")
    for idx, r in enumerate(parsed_reports):
        with st.expander(f"{r['report_number']} - {r['title'][:70]}...", expanded=False):
            col1, col2 = st.columns(2)
            with col1:
                rn = st.text_input("Report Number", r['report_number'], key=f"rn{idx}")
                t = st.text_input("Title", r['title'], key=f"t{idx}")
            with col2:
                rec = st.text_area("Recommendation", r['recommendation'], height=80, key=f"rec{idx}")
                out = st.selectbox("Outcome", ["Approved", "Carried", "Lost", "Englobo"], key=f"out{idx}")
            
            yes = st.text_input("YES Votes", r['yes_votes'], key=f"yes{idx}")
            no = st.text_input("NO Votes", r['no_votes'], key=f"no{idx}")
            conf = st.text_area("Conflicts", r['conflicts'], key=f"conf{idx}")
            eng = st.checkbox("Englobo", key=f"eng{idx}")
            
            if st.button("Save This Report", key=f"save{idx}"):
                c = conn.cursor()
                c.execute("""INSERT INTO reports 
                    (report_number, title, meeting_date, recommendation, yes_votes, no_votes, 
                     outcome, conflicts, englobo, entered_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""
