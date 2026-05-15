"""
Streamlit app for parsing and searching council minutes PDFs.
Features: PDF upload, text parsing, database storage, and full-text search.
"""

import streamlit as st
import sqlite3
import os
from datetime import datetime
from typing import List, Tuple, Optional
import PyPDF2
from pathlib import Path


# ============================================================================
# DATABASE FUNCTIONS
# ============================================================================

def init_database() -> sqlite3.Connection:
    """Initialize SQLite database for storing council minutes."""
    db_path = "council_minutes.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create tables
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL UNIQUE,
            uploaded_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            file_size INTEGER,
            pages INTEGER
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS minutes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER NOT NULL,
            page_number INTEGER,
            content TEXT,
            FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS searches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query TEXT,
            search_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            results_count INTEGER
        )
    """)
    
    conn.commit()
    return conn


def get_db_connection() -> sqlite3.Connection:
    """Get database connection."""
    conn = sqlite3.connect("council_minutes.db")
    conn.row_factory = sqlite3.Row
    return conn


def save_document(filename: str, file_size: int, pages: int) -> int:
    """Save document metadata to database. Returns document ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO documents (filename, file_size, pages)
            VALUES (?, ?, ?)
        """, (filename, file_size, pages))
        conn.commit()
        doc_id = cursor.lastrowid
        return doc_id
    except sqlite3.IntegrityError:
        st.warning(f"Document '{filename}' already exists in database.")
        cursor.execute("SELECT id FROM documents WHERE filename = ?", (filename,))
        return cursor.fetchone()[0]
    finally:
        conn.close()


def save_minutes(document_id: int, page_number: int, content: str) -> None:
    """Save extracted minutes to database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO minutes (document_id, page_number, content)
        VALUES (?, ?, ?)
    """, (document_id, page_number, content))
    
    conn.commit()
    conn.close()


def get_all_documents() -> List[dict]:
    """Retrieve all documents from database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, filename, uploaded_date, file_size, pages
        FROM documents
        ORDER BY uploaded_date DESC
    """)
    
    documents = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return documents


def get_document_content(document_id: int) -> List[dict]:
    """Retrieve all content for a specific document."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, page_number, content
        FROM minutes
        WHERE document_id = ?
        ORDER BY page_number
    """, (document_id,))
    
    content = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return content


def search_minutes(query: str) -> List[dict]:
    """Search minutes by keyword with full-text capabilities."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Search with LIKE for case-insensitive matching
    search_terms = f"%{query}%"
    
    cursor.execute("""
        SELECT 
            m.id,
            d.filename,
            m.page_number,
            m.content,
            d.id as document_id
        FROM minutes m
        JOIN documents d ON m.document_id = d.id
        WHERE m.content LIKE ?
        ORDER BY d.uploaded_date DESC, m.page_number
    """, (search_terms,))
    
    results = [dict(row) for row in cursor.fetchall()]
    
    # Log search
    cursor.execute("""
        INSERT INTO searches (query, results_count)
        VALUES (?, ?)
    """, (query, len(results)))
    conn.commit()
    conn.close()
    
    return results


def delete_document(document_id: int) -> bool:
    """Delete document and associated content from database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("DELETE FROM documents WHERE id = ?", (document_id,))
        conn.commit()
        return True
    except Exception as e:
        st.error(f"Error deleting document: {e}")
        return False
    finally:
        conn.close()


def get_search_statistics() -> dict:
    """Get search statistics."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) as total_searches FROM searches")
    total_searches = cursor.fetchone()[0]
    
    cursor.execute("""
        SELECT query, COUNT(*) as frequency
        FROM searches
        GROUP BY query
        ORDER BY frequency DESC
        LIMIT 5
    """)
    top_searches = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    return {"total_searches": total_searches, "top_searches": top_searches}


# ============================================================================
# PDF PARSING FUNCTIONS
# ============================================================================

def extract_pdf_text(pdf_file) -> Tuple[str, int]:
    """
    Extract text from uploaded PDF file.
    Returns: (full_text, page_count)
    """
    pdf_reader = PyPDF2.PdfReader(pdf_file)
    pages = []
    
    for page_num, page in enumerate(pdf_reader.pages, 1):
        text = page.extract_text()
        pages.append(f"--- PAGE {page_num} ---\n{text}")
    
    full_text = "\n\n".join(pages)
    return full_text, len(pdf_reader.pages)


def parse_council_minutes(text: str) -> dict:
    """
    Parse council minutes text to extract key sections.
    Returns: dict with parsed sections
    """
    sections = {
        "raw_text": text,
        "attendees": [],
        "agenda_items": [],
        "decisions": [],
        "action_items": []
    }
    
    lines = text.split('\n')
    
    # Simple parsing logic - extract common sections
    current_section = None
    
    for line in lines:
        line_lower = line.lower().strip()
        
        # Detect section headers
        if any(marker in line_lower for marker in ['attendance', 'attendees', 'present']):
            current_section = 'attendees'
        elif any(marker in line_lower for marker in ['agenda', 'items', 'discussion']):
            current_section = 'agenda_items'
        elif any(marker in line_lower for marker in ['decision', 'resolved', 'approved']):
            current_section = 'decisions'
        elif any(marker in line_lower for marker in ['action', 'todo', 'assigned']):
            current_section = 'action_items'
        elif line.strip() == '':
            current_section = None
        
        # Populate sections
        if current_section and line.strip() and not any(m in line_lower for m in ['agenda', 'decision', 'action']):
            sections[current_section].append(line.strip())
    
    return sections


# ============================================================================
# STREAMLIT UI
# ============================================================================

def main():
    st.set_page_config(page_title="Council Minutes Parser", layout="wide")
    
    # Initialize database
    init_database()
    
    # Header
    st.title("📋 Council Minutes Parser")
    st.markdown("Upload, parse, and search council meeting minutes PDFs")
    
    # Sidebar navigation
    page = st.sidebar.radio(
        "Navigation",
        ["Upload & Parse", "Browse Documents", "Search", "Statistics"]
    )
    
    if page == "Upload & Parse":
        upload_and_parse_page()
    elif page == "Browse Documents":
        browse_documents_page()
    elif page == "Search":
        search_page()
    elif page == "Statistics":
        statistics_page()


def upload_and_parse_page():
    """Page for uploading and parsing PDF files."""
    st.header("Upload & Parse Council Minutes")
    
    uploaded_file = st.file_uploader(
        "Select a PDF file",
        type="pdf",
        help="Upload council minutes in PDF format"
    )
    
    if uploaded_file is not None:
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.info(f"📄 File: {uploaded_file.name} ({uploaded_file.size} bytes)")
        
        if st.button("Parse PDF", type="primary"):
            with st.spinner("Parsing PDF..."):
                try:
                    # Extract text
                    text, page_count = extract_pdf_text(uploaded_file)
                    
                    # Save document metadata
                    doc_id = save_document(uploaded_file.name, uploaded_file.size, page_count)
                    
                    # Parse content
                    parsed = parse_council_minutes(text)
                    
                    # Save to database (split by pages)
                    pages = text.split("--- PAGE")
                    for idx, page_content in enumerate(pages[1:], 1):
                        save_minutes(doc_id, idx, page_content.strip())
                    
                    st.success(f"✅ Successfully parsed {page_count} pages!")
                    
                    # Display parsed content
                    st.subheader("Parsed Content Summary")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        if parsed["attendees"]:
                            st.subheader("Attendees")
                            for attendee in parsed["attendees"][:10]:
                                st.write(f"• {attendee}")
                            if len(parsed["attendees"]) > 10:
                                st.caption(f"... and {len(parsed['attendees']) - 10} more")
                    
                    with col2:
                        if parsed["decisions"]:
                            st.subheader("Decisions")
                            for decision in parsed["decisions"][:10]:
                                st.write(f"• {decision}")
                            if len(parsed["decisions"]) > 10:
                                st.caption(f"... and {len(parsed['decisions']) - 10} more")
                    
                    # Agenda items
                    if parsed["agenda_items"]:
                        st.subheader("Agenda Items")
                        for item in parsed["agenda_items"][:10]:
                            st.write(f"• {item}")
                        if len(parsed["agenda_items"]) > 10:
                            st.caption(f"... and {len(parsed['agenda_items']) - 10} more")
                    
                    # Action items
                    if parsed["action_items"]:
                        st.subheader("Action Items")
                        for item in parsed["action_items"][:10]:
                            st.write(f"• {item}")
                        if len(parsed["action_items"]) > 10:
                            st.caption(f"... and {len(parsed['action_items']) - 10} more")
                    
                    # Display raw content
                    with st.expander("📝 View Full Raw Text"):
                        st.text(parsed["raw_text"][:2000])
                        st.caption("(First 2000 characters shown)")
                
                except Exception as e:
                    st.error(f"Error parsing PDF: {e}")


def browse_documents_page():
    """Page for browsing all uploaded documents."""
    st.header("Browse Documents")
    
    documents = get_all_documents()
    
    if not documents:
        st.info("No documents uploaded yet. Go to 'Upload & Parse' to get started.")
        return
    
    # Display documents
    for doc in documents:
        with st.expander(
            f"📄 {doc['filename']} ({doc['pages']} pages) - {doc['uploaded_date']}"
        ):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Pages", doc['pages'])
            with col2:
                st.metric("File Size", f"{doc['file_size'] / 1024:.1f} KB")
            with col3:
                st.metric("Uploaded", doc['uploaded_date'][:10])
            
            # Display content
            content = get_document_content(doc['id'])
            
            for page in content[:3]:  # Show first 3 pages
                st.subheader(f"Page {page['page_number']}")
                st.text(page['content'][:500])
                if len(page['content']) > 500:
                    st.caption("(Truncated)")
            
            if len(content) > 3:
                st.caption(f"... and {len(content) - 3} more pages")
            
            # Delete button
            if st.button("🗑️ Delete Document", key=f"delete_{doc['id']}"):
                if delete_document(doc['id']):
                    st.success("Document deleted successfully!")
                    st.rerun()


def search_page():
    """Page for searching council minutes."""
    st.header("Search Council Minutes")
    
    search_query = st.text_input(
        "Enter search term",
        placeholder="e.g., budget, approval, resolution...",
        help="Search will look for this term in all uploaded documents"
    )
    
    if search_query:
        with st.spinner("Searching..."):
            results = search_minutes(search_query)
        
        st.subheader(f"Search Results ({len(results)} found)")
        
        if results:
            # Group by document
            docs_dict = {}
            for result in results:
                if result['filename'] not in docs_dict:
                    docs_dict[result['filename']] = []
                docs_dict[result['filename']].append(result)
            
            # Display grouped results
            for filename, file_results in docs_dict.items():
                with st.expander(f"📄 {filename} ({len(file_results)} matches)"):
                    for result in file_results:
                        st.subheader(f"Page {result['page_number']}")
                        
                        # Highlight search term
                        content = result['content']
                        highlighted = content.replace(
                            search_query,
                            f":yellow[{search_query}]"
                        )
                        st.markdown(highlighted[:1000])
                        
                        if len(content) > 1000:
                            st.caption("(Truncated)")
                        
                        # Link to document
                        if st.button("View Full Document", key=f"view_{result['id']}"):
                            st.session_state.selected_doc = result['document_id']
        else:
            st.info(f"No results found for '{search_query}'")


def statistics_page():
    """Page for displaying database statistics."""
    st.header("Statistics & Insights")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get statistics
    cursor.execute("SELECT COUNT(*) FROM documents")
    total_docs = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM minutes")
    total_pages = cursor.fetchone()[0]
    
    cursor.execute("SELECT SUM(file_size) FROM documents")
    total_size = cursor.fetchone()[0] or 0
    
    cursor.execute("SELECT COUNT(*) FROM searches")
    total_searches = cursor.fetchone()[0]
    
    conn.close()
    
    # Display metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Documents Uploaded", total_docs)
    with col2:
        st.metric("Total Pages", total_pages)
    with col3:
        st.metric("Total Size", f"{total_size / 1024 / 1024:.1f} MB")
    with col4:
        st.metric("Searches Performed", total_searches)
    
    # Top searches
    stats = get_search_statistics()
    
    if stats["top_searches"]:
        st.subheader("Top Search Queries")
        search_df = []
        for search in stats["top_searches"]:
            search_df.append({
                "Query": search['query'],
                "Times Searched": search['frequency']
            })
        
        if search_df:
            st.bar_chart(
                data=[s["Times Searched"] for s in search_df],
                y_label="Frequency",
                use_container_width=True
            )
            
            st.dataframe(search_df, use_container_width=True)
    
    # Recent documents
    st.subheader("Recent Uploads")
    recent = get_all_documents()[:5]
    
    if recent:
        for doc in recent:
            st.write(f"• **{doc['filename']}** - {doc['pages']} pages ({doc['uploaded_date']})")
    else:
        st.info("No documents uploaded yet.")


if __name__ == "__main__":
    main()
