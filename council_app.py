import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

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

st.header("📝 Data Entry")
col1, col2 = st.columns(2)
with col1:
    rn = st.text_input("Report Number")
    title = st.text_input("Title")
    date = st.date_input("Meeting Date", datetime.now().date())
with col2:
    rec = st.text_area("Recommendation", height=100)
    outcome = st.selectbox("Outcome", ["Approved", "Carried", "Lost", "Englobo"])

yes = st.text_input("YES Votes")
no = st.text_input("NO Votes")
conflicts = st.text_area("Conflicts of Interest")

if st.button("Save Report"):
    c = conn.cursor()
    c.execute("""INSERT INTO reports 
        (report_number, title, meeting_date, recommendation, yes_votes, no_votes, outcome, conflicts, entered_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (rn, title, str(date), rec, yes, no, outcome, conflicts, datetime.now().isoformat()))
    conn.commit()
    st.success("Saved!")

st.header("🔍 Search")
search = st.text_input("Search")
df = pd.read_sql_query("SELECT * FROM reports ORDER BY entered_at DESC", conn)
st.dataframe(df, use_container_width=True)

if st.button("Export to CSV"):
    df.to_csv("cessnock_reports.csv", index=False)
    st.success("Exported!")
