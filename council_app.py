import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

st.title("🗳️ Cessnock Council Report Logger")

conn = sqlite3.connect('cessnock_reports.db')
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

st.header("📝 Data Entry")
rn = st.text_input("Report Number")
title = st.text_input("Title")
date = st.date_input("Meeting Date", datetime.now().date())
rec = st.text_area("Recommendation")
yes = st.text_input("YES Votes")
no = st.text_input("NO Votes")
outcome = st.selectbox("Outcome", ["Approved", "Carried", "Lost"])
conflicts = st.text_area("Conflicts")

if st.button("Save Report"):
    c = conn.cursor()
    c.execute("""INSERT INTO reports 
        (report_number, title, meeting_date, recommendation, yes_votes, no_votes, outcome, conflicts, entered_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (rn, title, str(date), rec, yes, no, outcome, conflicts, datetime.now().isoformat()))
    conn.commit()
    st.success("Saved!")

st.header("Search")
search = st.text_input("Search")
df = pd.read_sql_query("SELECT * FROM reports ORDER BY entered_at DESC", conn)
st.dataframe(df, use_container_width=True)
