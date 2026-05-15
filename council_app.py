import streamlit as st
import pandas as pd
import sqlite3
import re
import fitz  # PyMuPDF
from datetime import datetime

st.set_page_config(page_title="Council Reports", layout="wide")

conn = sqlite3.connect('council_reports.db', check_same_thread=False)
conn.execute('''CREATE TABLE IF NOT EXISTS reports (
    id INTEGER PRIMARY KEY,
    meeting_date TEXT,
    report_number TEXT,
    title TEXT,
    conflicts TEXT,
    extracted_at TEXT
)''')
conn.commit()

st.title("🗳️ Council Minutes Parser")

uploaded_file = st.file_uploader("Upload Council Minutes PDF", type=["pdf"])

if uploaded_file:
    if st.button("Parse & Save"):
        doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        text = "".join(page.get_text() for page in doc)
        
        meeting_date = datetime.now().strftime("%Y-%m-%d")
        
        report_num = re.search(r'NO\.\s*([A-Z0-9/]+)', text, re.I)
        title = re.search(r'SUBJECT:\s*(.+)', text, re.I)
        conflicts = re.findall(r'Councillor\s+([A-Za-z]+)', text, re.I)
        
        c = conn.cursor()
        c.execute("""INSERT INTO reports (meeting_date, report_number, title, conflicts, extracted_at)
                     VALUES (?, ?, ?, ?, ?)""",
                  (meeting_date, 
                   report_num.group(1) if report_num else "Unknown",
                   title.group(1).strip() if title else "Untitled",
                   str(conflicts),
                   datetime.now().isoformat()))
        conn.commit()
        
        st.success("✅ Saved!")

st.subheader("All Reports")
df = pd.read_sql_query("SELECT * FROM reports ORDER BY meeting_date DESC", conn)
st.dataframe(df, use_container_width=True)
