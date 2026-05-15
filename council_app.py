import streamlit as st
import pandas as pd
import sqlite3
import re
import fitz  # PyMuPDF
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

# ===================== UPLOAD + MULTI-REPORT AUTO PARSE =====================
st.header("📄 Upload Full Council Minutes PDF")

uploaded_file = st.file_uploader("Upload the full meeting minutes PDF", type=["pdf"])

parsed_reports = []

if uploaded_file and st.button("🔄 Auto Parse ALL Reports"):
    doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
    full_text = "".join(page.get_text() for page in doc)

    # First extract conflicts section
    conflicts_dict = {}
    disc_section = re.search(r'DISCLOSURES? OF INTEREST.*?((?=CORPORATE AND COMMUNITY NO\.)|(?=\Z))', full_text, re.I | re.S)
    if disc_section:
        for match in re.finditer(r'(CC\d+/\d+).*?Councillor\s+([A-Za-z]+).*?for the reason that(.*?)(?=CC\d+/\d+|$)', disc_section.group(0), re.I | re.S):
            report_num = match.group(1).strip().upper()
            councillor = match.group(2).strip()
            reason = match.group(3).strip()
            if report_num not in conflicts_dict:
                conflicts_dict[report_num] = []
            conflicts_dict[report_num].append(f"{councillor}: {reason}")

    # Split into individual reports
    items = re.split(r'(CORPORATE AND COMMUNITY NO\.\s*CC\d+/\d+)', full_text, re.I)
    
    for i in range(1, len(items), 2):
        if i+1 >= len(items):
            continue
        section = items[i] + items[i+1]
        
        report_num_match = re.search(r'NO\.\s*(CC\d+/\d+)', section, re.I)
        if not report_num_match:
            continue
        report_num = report_num_match.group(1).upper()
        
        title_match = re.search(r'SUBJECT:\s*(.+?)(?=MOTION|AMENDMENT|$)', section, re.I | re.S)
        rec_match = re.search(r'(?:RECOMMENDATION|MOTION)[:\s]*(.+?)(?=Moved|FOR|The Amendment|CARRIED|$)', section, re.I | re.S)
        
        for_block = re.search(r'FOR\s*(.+?)(?=AGAINST|Total)', section, re.I | re.S)
        against_block = re.search(r'AGAINST\s*(.+?)(?=Total)', section, re.I | re.S)
        
        outcome_match = re.search(r'(The Amendment was PUT and CARRIED|The Motion was then PUT and CARRIED|CARRIED|LOST)', section, re.I | re.S)
        
        conflicts = "\n".join(conflicts_dict.get(report_num, []))

        parsed_reports.append({
            'report_number': report_num,
            'title': title_match.group(1).strip() if title_match else "Untitled",
            'recommendation': rec_match.group(1).strip() if rec_match else "",
            'yes_votes': for_block.group(1).strip() if for_block else "",
            'no_votes': against_block.group(1).strip() if against_block else "",
            'outcome': outcome_match.group(0) if outcome_match else "Approved",
            'conflicts': conflicts
        })

    st.success(f"✅ Found and parsed *{len(parsed_reports)} individual reports*!")

# ===================== SHOW PARSED REPORTS =====================
if parsed_reports:
    st.header(f"📋 {len(parsed_reports)} Reports Parsed – Review & Save")
    
    for i, report in enumerate(parsed_reports):
        with st.expander(f"Report {report['report_number']} - {report['title'][:80]}...", expanded=False):
            col1, col2 = st.columns(2)
            with col1:
                st.text_input("Report Number", report['report_number'], key=f"num_{i}")
                st.text_input("Title", report['title'], key=f"title_{i}")
            with col2:
                st.text_area("Recommendation", report['recommendation'], height=100, key=f"rec_{i}")
                outcome = st.selectbox("Outcome", ["Approved", "Carried", "Lost", "Not Approved", "Englobo"], key=f"out_{i}")
            
            yes = st.text_input("YES Votes", report['yes_votes'], key=f"yes_{i}")
            no = st.text_input("NO Votes", report['no_votes'], key=f"no_{i}")
            conflicts = st.text_area("Conflicts of Interest", report['conflicts'], key=f"conf_{i}")
            englobo = st.checkbox("Englobo", key=f"eng_{i}")
            
            if st.button("💾 Save This Report", key=f"save_{i}"):
                c = conn.cursor()
                c.execute("""INSERT INTO reports 
                    (report_number, title, meeting_date, recommendation, yes_votes, no_votes, 
                     outcome, conflicts, englobo, entered_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (report['report_number'], report['title'], datetime.now().strftime("%Y-%m-%d"),
                     report['recommendation'], yes, no, outcome, conflicts, 
                     1 if englobo else 0, datetime.now().isoformat()))
                conn.commit()
                st.success(f"Saved {report['report_number']}!")

# ===================== SEARCH & ALL REPORTS =====================
st.header("🔍 Search All Saved
