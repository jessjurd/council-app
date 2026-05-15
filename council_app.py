import streamlit as st
import pandas as pd
import sqlite3
import re
import fitz
from datetime import datetime

st.set_page_config(page_title="Cessnock Council", layout="wide")
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
    entered_at TEXT
)''')
conn.commit()

# Upload
st.header("📄 Upload PDF")
uploaded_file = st.file_uploader("Upload full minutes PDF", type=["pdf"])

if uploaded_file and st.button("Auto Parse All Reports"):
    doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
    text = "".join(page.get_text() for page in doc)
    st.success("PDF loaded (" + str(len(text)) + " characters). Basic parsing complete.")
    st.info("Note: Full auto-split coming in next update. Use manual entry for now.")

# Data Entry
st.header("📝 Data Entry")
col1, col2 = st.columns(2)
with col1:
    rn = st.text_input("Report Number", "CC1/2026")
    title = st.text_input("Title")
    date = st.date_input("Meeting Date", datetime.now().date())
with col2:
    rec = st.text_area("Recommendation", height=100)
    outcome = st.selectbox("Outcome", ["Approved", "Carried", "Lost", "Englobo"])

yes = st.text_input("Who voted YES")
no = st.text_input("Who voted NO")
conflicts = st.text_area("Conflicts of Interest")

if st.button("💾 Save Report"):
    c = conn.cursor()
    c.execute("""INSERT INTO reports 
        (report_number, title, meeting_date, recommendation, yes_votes, no_votes, outcome, conflicts, entered_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
   
