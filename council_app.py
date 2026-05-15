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

# ===================== UPLOAD + IMPROVED AUTO PARSE =====================
st.header("📄 Upload PDF (Auto Fill)")

uploaded_file = st.file_uploader("Upload Council Minutes PDF", type=["pdf"])

if uploaded_file and st.button("🔄 Auto Parse PDF"):
    doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
    text = "".join(page.get_text() for page in doc).upper()
    
    # Improved parsing for Cessnock format
    report_num = re.search(r'(CC\d+/\d+)', text)
    title = re.search(r'SUBJECT:\s*(.+?)(?=MOTION|AMENDMENT|$)', text, re.I | re.S)
    rec = re.search(r'(?:RECOMMENDATION|MOTION)[:\s]*(.+?)(?=MOVED|FOR|CARRIED|AMENDMENT|$)', text, re.I | re.S)
    
    # Votes
    for_block = re.search(r'FOR\s*(.+?)(?=AGAINST|TOTAL)', text, re.I | re.S)
    against_block = re.search(r'AGAINST\s*(.+?)(?=TOTAL|CARRIED)', text, re.I | re.S)
    
    # Conflicts
    conflicts = re.search(r'DISCLOSURES? OF INTEREST.*?(.+?)(?=CORPORATE|CC\d+|$)', text, re.I | re.S)
    
    st.success("✅ Parsed! Check and edit the fields below.")

# ===================== DATA ENTRY =====================
st.header("📝 Data Entry")

col1, col2 = st.columns(2)
with col1:
    report_number = st.text_input("Report Number", value=report_num.group(1) if 'report_num' in locals() and report_num else "")
    title = st.text_input("Title", value=title.group(1).strip() if 'title' in locals() and title else "")
    meeting_date = st.date_input("Meeting Date", datetime.now().date())

with col2:
    recommendation = st.text_area("Recommendation", value=rec.group(1).strip() if 'rec' in locals() and rec else "", height=120)
    outcome = st.selectbox("Outcome", ["Approved", "Carried", "Lost", "Not Approved", "Englobo"])

yes_votes = st.text_input("Who voted YES (comma separated)", value=for_block.group(1).strip() if 'for_block' in locals() and for_block else "")
no_votes = st.text_input("Who voted NO (comma separated)", value=against_block.group(1).strip() if 'against_block' in locals() and against_block else "")
conflicts = st.text_area("Conflict of Interest", value=conflicts.group(1).strip() if 'conflicts' in locals() and conflicts else "")

englobo = st.checkbox("This was placed in Englobo")

if st.button("💾 Save Report"):
    c = conn.cursor()
    c.execute("""INSERT INTO reports 
        (report_number, title, meeting_date, recommendation, yes_votes, no_votes, 
         outcome, conflicts, englobo, entered_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (report_number, title, str(meeting_date), recommendation, yes_votes, no_votes,
         outcome, conflicts, 1 if englobo else 0, datetime.now().isoformat()))
    conn.commit()
    st.success("✅ Report Saved!")

# Search and display (same as before)
st.header("🔍 SEARCH")
search_term = st.text_input("Search...")

if search_term:
    df = pd.read_sql_query("SELECT * FROM reports WHERE report_number LIKE ? OR title LIKE ? OR conflicts LIKE ? ORDER BY meeting_date DESC", conn, params=[f"%{search_term}%"]*3)
else:
    df = pd.read_sql_query("SELECT * FROM reports ORDER BY meeting_date DESC", conn)

for _, row in df.iterrows():
    with st.container(border=True):
        st.subheader(f"{row['report_number']} - {row['title']}")
        st.caption(row['meeting_date'])
        st.write("*Recommendation:*", row['recommendation'][:400] + "..." if len(str(row['recommendation'])) > 400 else row['recommendation'])
        if row['yes_votes']: st.write("*YES:*", row['yes_votes'])
        if row['no_votes']: st.write("*NO:*", row['no_votes'])
        if row['outcome']: st.write("*Outcome:*", row['outcome'])
        if row['conflicts']: st.warning(f"⚠️ {row['conflicts']}")
        if row['englobo']: st.info("📦 Englobo")

st.dataframe(df, use_container_width=True)
