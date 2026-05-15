import streamlit as st
import pandas as pd
import sqlite3
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

# SEARCH AT TOP
st.header("🔍 SEARCH")
search = st.text_input("Search by report number, title or councillor")

# DATA ENTRY - matches your sketch
st.header("📝 Data Entry")

col1, col2 = st.columns(2)
with col1:
    rn = st.text_input("Report Number")
    title = st.text_input("Title")
    date = st.date_input("Meeting Date", datetime.now().date())
with col2:
    rec = st.text_area("Recommendation", height=120)
    yes = st.text_input("Who voted YES")
    no = st.text_input("Who voted NO")
    outcome = st.selectbox("Outcome", ["Approved", "Carried", "Lost", "Englobo"])
    conflicts = st.text_area("Conflicts of Interest")

if st.button("💾 Save This Report"):
    c = conn.cursor()
    c.execute("""INSERT INTO reports 
        (report_number, title, meeting_date, recommendation, yes_votes, no_votes, outcome, conflicts, entered_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (rn, title, str(date), rec, yes, no, outcome, conflicts, datetime.now().isoformat()))
    conn.commit()
    st.success("✅ Saved!")

# DISPLAY AS CARDS
st.header("All Saved Reports")
df = pd.read_sql_query("SELECT * FROM reports ORDER BY entered_at DESC", conn)

for _, row in df.iterrows():
    with st.container(border=True):
        st.subheader(f"{row['report_number']} - {row['title']}")
        st.caption(row['meeting_date'])
        st.write("*Recommendation:*", row['recommendation'][:400] + "..." if len(str(row['recommendation'])) > 400 else row['recommendation'])
        if row['yes_votes']: st.write("*YES:*", row['yes_votes'])
        if row['no_votes']: st.write("*NO:*", row['no_votes'])
        st.write("*Outcome:*", row['outcome'])
        if row['conflicts']: st.warning(f"⚠️ {row['conflicts']}")

if st.button("Export to CSV"):
    df.to_csv("cessnock_reports.csv", index=False)
    st.success("✅ Exported!")

st.dataframe(df, use_container_width=True)
