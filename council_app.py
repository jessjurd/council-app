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
st.header("📄 Upload PDF (Auto Fill)")

uploaded_file = st.file_uploader("Upload Council Minutes PDF", type=["pdf"])

if uploaded_file and st.button("🔄 Auto Parse PDF"):
    doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
    text = "".join(page.get_text() for page in doc)
    
    report_num = re.search(r'(CC\d+/\d+)', text, re.I)
    title_match = re.search(r'SUBJECT:\s*(.+)', text, re.I)
    rec_match = re.search(r'(?:RECOMMENDATION|MOTION)[:\s]*(.+?)(?=Moved|FOR|CARRIED|$)', text, re.I | re.S)
    conflicts_match = re.search(r'Conflict.*?Interest[:\s]*(.+?)(?=\n{2,}|$)', text, re.I | re.S)
    
    st.success("✅ Parsed! Fields below are pre-filled.")

# ===================== DATA ENTRY =====================
st.header("📝 Data Entry")

col1, col2 = st.columns(2)
with col1:
    report_number = st.text_input("Report Number", placeholder="CC1/2026")
    title = st.text_input("Title")
    meeting_date = st.date_input("Meeting Date", datetime.now().date())

with col2:
    recommendation = st.text_area("Recommendation", height=100)
    outcome = st.selectbox("Outcome", ["Approved", "Carried", "Lost", "Not Approved", "Englobo"])

yes_votes = st.text_input("Who voted YES (comma separated)")
no_votes = st.text_input("Who voted NO (comma separated)")
conflicts = st.text_area("Conflict of Interest (Councillor name + why)")
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

# ===================== SEARCH =====================
st.header("🔍 SEARCH")
search_term = st.text_input("Search by report number, title, councillor, etc.")

if search_term:
    df = pd.read_sql_query("""
        SELECT * FROM reports 
        WHERE report_number LIKE ? OR title LIKE ? OR recommendation LIKE ? 
           OR yes_votes LIKE ? OR no_votes LIKE ? OR conflicts LIKE ?
        ORDER BY meeting_date DESC
    """, conn, params=[f"%{search_term}%"]*6)
else:
    df = pd.read_sql_query("SELECT * FROM reports ORDER BY meeting_date DESC", conn)

# Card View
for _, row in df.iterrows():
    with st.container(border=True):
        st.subheader(f"{row['report_number']} - {row['title']}")
        st.caption(f"📅 {row['meeting_date']}")
        st.write("*Recommendation:*", row['recommendation'][:300] + "..." if len(str(row['recommendation'])) > 300 else row['recommendation'])
        if row['yes_votes']: st.write("*YES:*", row['yes_votes'])
        if row['no_votes']: st.write("*NO:*", row['no_votes'])
        st.write("*Outcome:*", row['outcome'])
        if row['conflicts']: st.warning(f"⚠️ {row['conflicts']}")
        if row['englobo']: st.info("📦 Englobo")

st.dataframe(df, use_container_width=True)

if st.button("Export to CSV"):
    df.to_csv("cessnock_reports.csv", index=False)
    st.success("✅ Exported!")
