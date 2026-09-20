import streamlit as st
import pandas as pd
import sqlite3
from datetime import date

DB_FILE = "job_applications.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS applications(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company TEXT NOT NULL,
            role TEXT NOT NULL,
            date_applied DATE NOT NULL,
            status TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def add_application(company, role, date_applied, status):

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO applications(company, role, date_applied, status) VALUES (?, ?, ?, ?)",
        (company, role, str(date_applied), status)
    )

    conn.commit()
    conn.close()

def get_all_applications():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("SELECT id, company, role, date_applied , status FROM applications ORDER BY date_applied DESC")
    
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_stats():

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM applications"
    )
    total = cursor.fetchone()[0]

    stats = {"Total": total}

    for status in  ["Applied", "Interview", "Offer", "Rejected"]:
        cursor.execute("SELECT COUNT(*) FROM applications WHERE status = ?",(status,))
        stats[status] = cursor.fetchone()[0]

    conn.close()
    return stats

def delete_application(app_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM applications WHERE id= ?", (app_id,)
    )

    conn.commit()
    conn.close()

st.set_page_config(page_title="Job & Internships applications Tracker", layout="wide")
init_db()

st.title("Job & Internships application tracker")

with st.sidebar:
    st.header("Job & Internships Application Tracker")

    with st.form("add_form", clear_on_submit=True):
        company = st.text_input("Company")
        role = st.text_input("role")
        date_applied = st.date_input("Date Applied", value= date.today())
        status = st.selectbox("Status", ["Applied", "Interview", "Offer", "Rejected"])
        submitted = st.form_submit_button("Add Application")

    if submitted:
        if company and role:
            add_application(company, role, date_applied, status)
            st.success(f"Added {role} at {company}!")
        else:
            st.error("Please fill in both Company and Role")


stats = get_stats()
col1, col2, col3, col4, col5 = st.columns(5)

col1.metric("Total", stats["Total"])
col2.metric("Applied", stats["Applied"])
col3.metric("Interview", stats["Interview"])
col4.metric("Offer", stats["Offer"])
col5.metric("Rejected", stats["Rejected"])

st.divider()

st.subheader("All Applications")
data = get_all_applications()

if data:
    df = pd.DataFrame(data, columns=["ID", "Company", "Role", "Date Applied", "Status"])
    st.dataframe(df, use_container_width=True, hide_index= True)

    with st.expander("Delete an application"):
        del_id = st.number_input("Enter ID to delete", min_value=1, step=1)

        if st.button("Delete"):
            delete_application(del_id)
            st.success(f"Deleted application {del_id}")
            st.rerun()
else:
    st.info("No applications yet. Add one from the sidebar!")
