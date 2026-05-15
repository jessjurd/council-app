import streamlit as st
import pandas as pd
import json
import os
from openai import OpenAI

# Initialize session state for database if it doesn't exist
if "reports_db" not in st.session_state:
    st.session_state.reports_db = []

# Initialize OpenAI client (Ensure your OPENAI_API_KEY environment variable is set)
# To set it in terminal: export OPENAI_API_KEY="your-key-here"
try:
    client = OpenAI()
except Exception:
    client = None

st.set_page_config(layout="wide", page_title="Council Report Tracker")
st.title("🏛️ Council Report Management System")

# ==========================================
# 1. SEARCH BAR & FILTERS
# ==========================================
st.subheader("🔍 Search Reports")
search_query = st.text_input("Search by Report Number, Title, Councillor, or Keywords...", "")

# ==========================================
# 2. UPLOAD & AUTOMATIC AI DATA EXTRACTION
# ==========================================
st.sidebar.header("📥 Data Input Options")
uploaded_file = st.sidebar.file_uploader("Upload Large Council PDF/Text File", type=["txt", "pdf"])

if uploaded_file and st.sidebar.button("🤖 Process and Extract Reports with AI"):
    if not client:
        st.sidebar.error("Please set your OPENAI_API_KEY environment variable first.")
    else:
        with st.spinner("AI is analyzing file, splitting reports, and extracting data..."):
            # Read file content (Assuming text for this lightweight implementation; PDFs require PyPDF2)
            file_content = uploaded_file.read().decode("utf-8", errors="ignore")
            
            # Prompt engineering to force structured JSON output matching exact criteria
            prompt = f"""
            You are an expert data extraction AI. Analyze the following council document text.
            1. Separate each individual report found in the text.
            2. Extract data into the following strict JSON schema structure for each report:
            {{
                "reports": [
                    {{
                        "report_number": "Extract number like PE27/2025",
                        "title": "Extract full report title",
                        "date": "Extract meeting date",
                        "recommendation_motion": "Extract full text of the motion and who moved/seconded it",
                        "voted_yes": "List of councillors who voted yes",
                        "voted_no": "List of councillors who voted no",
                        "outcome": "Outcome of the vote (e.g., Carried, Lost, Resolved)",
                        "conflict_of_interest": "Name of councillor, conflict type, and reason if any",
                        "englob": true/false (Set to true if this report was passed as part of an englob/bulk list block)
                    }}
                ]
            }}
            
            Document Text:
            {file_content[:15000]} 
            """
            # Note: Content is truncated to 15k characters here for safety; production would loop chunked data.

            try:
                response = client.chat.completions.create(
                    model="gpt-4o",
                    response_format={ "type": "json_object" },
                    messages=[{"role": "user", "content": prompt}]
                )
                extracted_data = json.loads(response.choices[0].message.content)
                
                # Append extracted items to our database
                for rep in extracted_data.get("reports", []):
                    st.session_state.reports_db.append(rep)
                st.sidebar.success(f"Successfully extracted {len(extracted_data.get('reports', []))} reports!")
            except Exception as e:
                st.sidebar.error(f"Extraction failed: {str(e)}")

# ==========================================
# 3. MANUAL INPUT OPTION
# ==========================================
with st.sidebar.expander("✍️ Manually Add Report"):
    with st.form("manual_form", clear_on_submit=True):
        m_num = st.text_input("Report Number (e.g., PE27/2025)")
        m_title = st.text_input("Title")
        m_date = st.text_input("Date")
        m_motion = st.text_area("Recommendation / Motion")
        m_yes = st.text_area("Voted Yes (Councillors)")
        m_no = st.text_area("Voted No (Councillors)")
        m_outcome = st.text_input("Outcome of Vote")
        m_conflict = st.text_area("Conflict of Interest (Name, conflict, reason)")
        m_englob = st.checkbox("Englob (Ticked if in bulk list)")
        
        submit_manual = st.form_submit_button("Save Report")
        if submit_manual:
            new_report = {
                "report_number": m_num,
                "title": m_title,
                "date": m_date,
                "recommendation_motion": m_motion,
                "voted_yes": m_yes,
                "voted_no": m_no,
                "outcome": m_outcome,
                "conflict_of_interest": m_conflict,
                "englob": m_englob
            }
            st.session_state.reports_db.append(new_report)
            st.success("Report saved successfully!")

# ==========================================
# FILTER LOGIC FOR SEARCH BAR
# ==========================================
filtered_reports = st.session_state.reports_db
if search_query:
    filtered_reports = [
        r for r in st.session_state.reports_db 
        if search_query.lower() in r['title'].lower() 
        or search_query.lower() in r['report_number'].lower()
        or search_query.lower() in r['recommendation_motion'].lower()
    ]

# ==========================================
# 4 & 5. THUMBNAIL GALLERY & DETAILS DISPLAY
# ==========================================
st.write("---")
st.subheader("📋 Reports Gallery")

if not filtered_reports:
    st.info("No reports found. Upload a file or use manual entry to add data.")
else:
    # Render thumbnails using Streamlit columns
    cols = st.columns(4) # 4 thumbnails per row
    for index, report in enumerate(filtered_reports):
        with cols[index % 4]:
            # Thumbnail visual block
            st.markdown(
                f"""
                <div style="border:1px solid #ddd; border-radius:5px; padding:10px; background-color:#f9f9f9; min-height:120px; margin-bottom:10px;">
                    <span style="color:#007bff; font-weight:bold;">{report['report_number']}</span><br>
                    <small>{report['date']}</small><br>
                    <strong style="font-size:13px;">{report['title'][:50]}...</strong><br>
                    {"📌 <small style='color:green;'>Englob</small>" if report.get('englob') else ""}
                </div>
                """, 
                unsafe_allow_html=True
            )
            
            # Click button to read full details
            if st.button(f"Open Details", key=f"btn_{index}"):
                st.session_state.selected_report = report

# Display full modal-like view when a thumbnail is clicked
if "selected_report" in st.session_state and st.session_state.selected_report:
    rep = st.session_state.selected_report
    st.write("---")
    st.markdown(f"## Detailed View: {rep['report_number']} - {rep['title']}")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"*Date:* {rep['date']}")
        st.markdown(f"*Outcome:* {rep['outcome']}")
        st.markdown(f"*Englob Status:* {'✅ Yes (Part of bulk list)' if rep['englob'] else '❌ No'}")
        st.markdown(f"**Recommendation / Motion:**\n\n{rep['recommendation_motion']}")
        
    with col2:
        st.markdown(f"💚 **Voted YES:**\n{rep['voted_yes']}")
        st.markdown(f"💔 **Voted NO:**\n{rep['voted_no']}")
        st.markdown(f"⚠️ **Conflict of Interest Details:**\n{rep['conflict_of_interest']}")
        
    if st.button("Close Detailed View"):
        st.session_state.selected_report = None
        st.rerun()
