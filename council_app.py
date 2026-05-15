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

st.header("📄 Upload PDF")

uploaded_file = st.file_uploader("Upload full minutes PDF", type=["pdf"])

if uploaded_file and st.button("Auto Parse All Reports"):
    doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
    text = "".join(page.get_text() for page in doc)
    
    reports = re.split(r'(CORPORATE AND COMMUNITY NO\.\s*CC\d+/\d+)', text)
    st.success(f"Found {len(reports)//2} potential reports")

st.header("📝 Data Entry")
col1, col2 = st.columns(2)
with col1:
    rn = st.text_input("Report Number")
    title = st.text_input("Title")
    date = st.date_input("Meeting Date", datetime.now().date())
with col2:
    rec = st.text_area("Recommendation")
    outcome = st.selectbox("Outcome", ["Approved", "Carried", "Lost", "Englobo"])
yes = st.text_input("YES Votes")
no = st.text_input("NO Votes")
conflicts = st.text_area("Conflicts of Interest")
englobo = st.checkbox("Englobo")

if st.button("Save Report"):
    c = conn.cursor()
    c.execute("""INSERT INTO reports 
        (report_number, title, meeting_date, recommendation, yes_votes, no_votes, outcome, conflicts, englobo, entered_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (rn, title, str(date), rec, yes, no, outcome, conflicts, 1 if englobo else 0, datetime.now().isoformat()))
    conn.commit()
    st.success("Saved!")

st.header("🔍 Search")
search = st.text_input("Search")
if search:
    df = pd.read_sql_query("SELECT * FROM reports WHERE report_number LIKE ? OR title LIKE ? ORDER BY meeting_date DESC", conn, params=[f"%{search}%"]*2)
else:
    df = pd.read_sql_query("SELECT * FROM reports ORDER BY meeting_date DESC", conn)

st.dataframe(df, use_container_width=True)
