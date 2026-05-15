import streamlit as st
import pandas as pd
import sqlite3
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

# ===================== DATA ENTRY =====================
st.header("📝 Data Entry")

col1, col2 = st.columns(2)
with col1:
    report_num = st.text_input("Report Number", placeholder="CC1/2026")
    title = st.text_input("Title")
    meeting_date = st.date_input("Meeting Date", datetime.now().date())

with col2:
    recommendation = st.text_area("Recommendation", height=100)
    outcome = st.selectbox("Outcome", ["Approved", "Not Approved", "Carried", "Lost", "Englobo"])

yes_votes = st.text_input("Who voted YES (comma separated names)")
no_votes = st.text_input("Who voted NO (comma separated names)")

conflicts = st.text_area("Conflicts of Interest (Councillor name + reason)")

englobo = st.checkbox("This was placed in Englobo (bulk)")

if st.button("✅ Save Report"):
    c = conn.cursor()
    c.execute("""INSERT INTO reports 
        (report_number, title, meeting_date, recommendation, yes_votes, no_votes, 
         outcome, conflicts, englobo, entered_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (report_num, title, str(meeting_date), recommendation, yes_votes, no_votes,
         outcome, conflicts, 1 if englobo else 0, datetime.now().isoformat()))
    conn.commit()
    st.success("Report Saved!")

# ===================== SEARCH =====================
st.header("🔍 Search Reports")
search = st.text_input("Search by report number, title, councillor name, or keyword")

query = "SELECT * FROM reports WHERE 1=1"
params = []
if search:
    query += """ AND (report_number LIKE ? OR title LIKE ? OR recommendation LIKE ? 
                    OR yes_votes LIKE ? OR no_votes LIKE ? OR conflicts LIKE ?)"""
    params = [f"%{search}%"] * 6

df = pd.read_sql_query(query + " ORDER BY meeting_date DESC", conn, params=params)

# Nice card display
for _, row in df.iterrows():
    with st.container(border=True):
        col1, col2 = st.columns([4,1])
        with col1:
            st.subheader(f"{row['report_number']} - {row['title']}")
            st.caption(f"📅 {row['meeting_date']}")
            st.write(f"*Recommendation:* {row['recommendation'][:300]}...")
        with col2:
            if row['outcome']:
                st.success(row['outcome']) if "Approved" in row['outcome'] else st.error(row['outcome'])
        
        if row['yes_votes']:
            st.write("*YES*", ", ".join(row['yes_votes'].split(",")))
        if row['no_votes']:
            st.write("*NO*", ", ".join(row['no_votes'].split(",")))
        
        if row['conflicts']:
            st.warning(f"⚠️ Conflicts: {row['conflicts']}")
        
        if row['englobo']:
            st.info("📦 This was an Englobo item")

# All reports table
st.header("All Reports")
st.dataframe(df, use_container_width=True)

if st.button("Export to CSV"):
    df.to_csv("cessnock_council_reports.csv", index=False)
    st.success("Downloaded!")
