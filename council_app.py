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

# ===================== UPLOAD + AUTO PARSE =====================
st.header("📄 Upload Minutes PDF (Auto Parse)")

uploaded_file = st.file_uploader("Upload Council Minutes PDF", type=["pdf"])

if uploaded_file:
    if st.button("🔄 Parse PDF Automatically"):
        doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        text = "".join(page.get_text() for page in doc)
        
        # Auto extraction
        report_num = re.search(r'(CC\d+/\d+)', text, re.I)
        title = re.search(r'SUBJECT:\s*(.+?)(?=MOTION|RECOMMENDATION|$)', text, re.I | re.S)
        rec = re.search(r'(?:RECOMMENDATION|MOTION)[:\s]*(.+?)(?=Moved|FOR|CARRIED|$)', text, re.I | re.S)
        
        yes = re.search(r'FOR[:\s]*(.+?)(?=AGAINST|Total)', text, re.I | re.S)
        no = re.search(r'AGAINST[:\s]*(.+?)(?=Total|CARRIED)', text, re.I | re.S)
        
        conflicts = re.search(r'Conflict.*?Interest[:\s]*(.+?)(?=\n{2,}|$)', text, re.I | re.S)
        
        st.success("✅ Parsed! Review below and save.")
        
        col1, col2 = st.columns(2)
        with col1:
            report_number = st.text_input("Report Number", value=report_num.group(1) if report_num else "")
            title_input = st.text_input("Title", value=title.group(1).strip() if title else "")
            meeting_date = st.date_input("Meeting Date", datetime.now().date())
        with col2:
            recommendation = st.text_area("Recommendation", value=rec.group(1).strip() if rec else "", height=100)
            outcome = st.selectbox("Outcome", ["Approved", "Carried", "Lost", "Englobo", "Not Approved"])
        
        yes_votes = st.text_input("YES Votes (names)", value=yes.group(1).strip() if yes else "")
        no_votes = st.text_input("NO Votes (names)", value=no.group(1).strip() if no else "")
        conflicts_input = st.text_area("Conflicts of Interest", value=conflicts.group(1).strip() if conflicts else "")
        englobo = st.checkbox("This was Englobo")

        if st.button("💾 Save Parsed Report"):
            c = conn.cursor()
            c.execute("""INSERT INTO reports 
                (report_number, title, meeting_date, recommendation, yes_votes, no_votes, 
                 outcome, conflicts, englobo, entered_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (report_number, title_input, str(meeting_date), recommendation, 
                 yes_votes, no_votes, outcome, conflicts_input, 1 if englobo else 0, 
                 datetime.now().isoformat()))
            conn.commit()
            st.success("Report Saved!")

# ===================== SEARCH & VIEW =====================
st.header("🔍 Search Reports")
search_term = st.text_input("Search by report number, title, councillor, or keyword")

if search_term:
    df = pd.read_sql_query("""
        SELECT * FROM reports 
        WHERE report_number LIKE ? OR title LIKE ? OR recommendation LIKE ? 
        OR yes_votes LIKE ? OR no_votes LIKE ? OR conflicts LIKE ?
        ORDER BY meeting_date DESC
    """, conn, params=[f"%{search_term}%"]*6)
else:
    df = pd.read_sql_query("SELECT * FROM reports ORDER BY meeting_date DESC", conn)

# Card display
for _, row in df.iterrows():
    with st.expander(f"📋 {row['report_number']} - {row['title'][:80]}...", expanded=False):
        st.write(f"*Date:* {row['meeting_date']}")
        st.write(f"*Recommendation:* {row['recommendation']}")
        if row['yes_votes']: st.write(f"*YES:* {row['yes_votes']}")
        if row['no_votes']: st.write(f"*NO:* {row['no_votes']}")
        if row['outcome']: st.write(f"*Outcome:* {row['outcome']}")
        if row['conflicts']: st.warning(f"⚠️ Conflicts: {row['conflicts']}")
        if row['englobo']: st.info("📦 Englobo item")

st.dataframe(df, use_container_width=True)

if st.button("Export All to CSV"):
    df.to_csv("cessnock_council_reports.csv", index=False)
    st.success("✅ Exported!")
