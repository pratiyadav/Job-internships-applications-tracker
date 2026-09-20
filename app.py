import streamlit as st
import sqlite3
import pandas as pd
from datetime import date

DB_FILE = "job_applications.db"


# ----------------------------------------------------------------------
# CUTE MASCOT ARTWORK
# These are hand-drawn SVGs stored as plain text -- no image files needed,
# so nothing to misplace. st.markdown renders raw SVG directly when we
# pass unsafe_allow_html=True.
# ----------------------------------------------------------------------

PANDA_SVG = """
<svg width="110" height="110" viewBox="0 0 130 130" xmlns="http://www.w3.org/2000/svg">
  <circle cx="30" cy="28" r="17" fill="#2D2640"/>
  <circle cx="100" cy="28" r="17" fill="#2D2640"/>
  <circle cx="65" cy="68" r="50" fill="#FFF7FA"/>
  <ellipse cx="42" cy="70" rx="15" ry="19" fill="#2D2640"/>
  <ellipse cx="88" cy="70" rx="15" ry="19" fill="#2D2640"/>
  <circle cx="44" cy="72" r="6" fill="#FFFFFF"/>
  <circle cx="86" cy="72" r="6" fill="#FFFFFF"/>
  <circle cx="46" cy="74" r="3" fill="#2D2640"/>
  <circle cx="84" cy="74" r="3" fill="#2D2640"/>
  <ellipse cx="30" cy="90" rx="8" ry="5" fill="#FF8FAB" opacity="0.6"/>
  <ellipse cx="100" cy="90" rx="8" ry="5" fill="#FF8FAB" opacity="0.6"/>
  <ellipse cx="65" cy="88" rx="5" ry="4" fill="#2D2640"/>
  <path d="M 65 92 Q 65 100 58 100" stroke="#2D2640" stroke-width="2.5" fill="none" stroke-linecap="round"/>
  <path d="M 65 92 Q 65 100 72 100" stroke="#2D2640" stroke-width="2.5" fill="none" stroke-linecap="round"/>
</svg>
"""

SLEEPY_CAT_SVG = """
<svg width="160" height="140" viewBox="0 0 160 140" xmlns="http://www.w3.org/2000/svg">
  <path d="M 130 100 Q 155 95 150 70 Q 148 60 138 62" stroke="#B8B0C8" stroke-width="10" fill="none" stroke-linecap="round"/>
  <ellipse cx="80" cy="100" rx="45" ry="30" fill="#D8D0E8"/>
  <circle cx="80" cy="55" r="34" fill="#D8D0E8"/>
  <path d="M 55 35 L 48 12 L 68 28 Z" fill="#D8D0E8"/>
  <path d="M 105 35 L 112 12 L 92 28 Z" fill="#D8D0E8"/>
  <path d="M 57 30 L 53 18 L 65 27 Z" fill="#FF8FAB" opacity="0.5"/>
  <path d="M 103 30 L 107 18 L 95 27 Z" fill="#FF8FAB" opacity="0.5"/>
  <path d="M 62 55 Q 68 60 74 55" stroke="#2D2640" stroke-width="2.5" fill="none" stroke-linecap="round"/>
  <path d="M 86 55 Q 92 60 98 55" stroke="#2D2640" stroke-width="2.5" fill="none" stroke-linecap="round"/>
  <ellipse cx="58" cy="66" rx="7" ry="4" fill="#FF8FAB" opacity="0.5"/>
  <ellipse cx="102" cy="66" rx="7" ry="4" fill="#FF8FAB" opacity="0.5"/>
  <path d="M 76 65 L 84 65 L 80 70 Z" fill="#FF8FAB"/>
  <path d="M 80 70 Q 80 74 75 75" stroke="#2D2640" stroke-width="2" fill="none" stroke-linecap="round"/>
  <path d="M 80 70 Q 80 74 85 75" stroke="#2D2640" stroke-width="2" fill="none" stroke-linecap="round"/>
  <text x="115" y="35" font-size="16" fill="#B8B0C8" font-family="sans-serif">z</text>
  <text x="125" y="25" font-size="12" fill="#B8B0C8" font-family="sans-serif">z</text>
</svg>
"""


# ----------------------------------------------------------------------
# DATABASE FUNCTIONS
# Each function opens its own connection, does one job, then closes it.
# This is the simplest pattern to learn with SQLite -- no shared state
# to worry about, and each function is easy to test on its own.
# ----------------------------------------------------------------------

def init_db():
    """
    Creates the 'applications' table if it doesn't already exist.
    Runs every time the app starts -- CREATE TABLE IF NOT EXISTS makes
    this safe to call repeatedly without wiping existing data.
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company TEXT NOT NULL,
            role TEXT NOT NULL,
            date_applied TEXT NOT NULL,
            status TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def add_application(company, role, date_applied, status):
    """
    Inserts one new row into the applications table.
    The '?' placeholders are parameterized queries -- always use these
    instead of pasting values directly into the SQL string. It stops
    SQL injection and also correctly handles quotes/special characters.
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO applications (company, role, date_applied, status) VALUES (?, ?, ?, ?)",
        (company, role, str(date_applied), status)
    )
    conn.commit()
    conn.close()


def get_all_applications():
    """
    Fetches every row, most recent date first.
    Returns a plain list of tuples -- one tuple per row -- which we turn
    into a pandas DataFrame later for display.
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, company, role, date_applied, status FROM applications ORDER BY date_applied DESC"
    )
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_stats():
    """
    Computes the numbers shown on the dashboard: total applications,
    plus a count for each status. Runs a small COUNT(*) query per
    status -- fine for a personal tracker with a modest number of rows.
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM applications")
    total = cursor.fetchone()[0]

    stats = {"Total": total}
    for status in ["Applied", "Interview", "Offer", "Rejected"]:
        cursor.execute("SELECT COUNT(*) FROM applications WHERE status = ?", (status,))
        stats[status] = cursor.fetchone()[0]

    conn.close()
    return stats


def delete_application(app_id):
    """Removes one row by its id. Used by the 'Delete' expander below."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM applications WHERE id = ?", (app_id,))
    conn.commit()
    conn.close()


# ----------------------------------------------------------------------
# STREAMLIT UI
# Streamlit re-runs this whole script top-to-bottom every time the user
# interacts with a widget (clicks a button, types in a box, etc). That's
# why init_db() is safe to call on every run, and why we re-fetch the
# stats/table fresh each time instead of trying to update them in place.
# ----------------------------------------------------------------------

st.set_page_config(page_title="Job & Internship Tracker", layout="wide")
init_db()

st.title("🐼 Job & Internship Tracker")

# --- Sidebar: form to add a new application ---
with st.sidebar:
    # centered panda mascot above the form
    st.markdown(f"<div style='text-align:center'>{PANDA_SVG}</div>", unsafe_allow_html=True)
    st.header("🎀 Add New Application")
    st.caption("Track job or internship applications here. ✨")
    # st.form batches all the inputs inside it so nothing is submitted
    # until the button is clicked -- without it, Streamlit would re-run
    # the script (and lose your half-typed input) on every keystroke.
    with st.form("add_form", clear_on_submit=True):
        company = st.text_input("Company")
        role = st.text_input("Role")
        date_applied = st.date_input("Date Applied", value=date.today())
        status = st.selectbox("Status", ["Applied", "Interview", "Offer", "Rejected"])
        submitted = st.form_submit_button("Add Application")

        if submitted:
            if company and role:
                add_application(company, role, date_applied, status)
                st.success(f"Added {role} at {company}!")
                if status == "Offer":
                    st.balloons()  # little celebration for good news 🎉
            else:
                st.error("Please fill in both Company and Role.")

# --- Dashboard: key stats as metric cards ---
stats = get_stats()
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Total", stats["Total"])
col2.metric("Applied", stats["Applied"])
col3.metric("Interview", stats["Interview"])
col4.metric("Offer", stats["Offer"])
col5.metric("Rejected", stats["Rejected"])

st.divider()

# --- Table of all applications ---
st.subheader("📋 All Applications")
data = get_all_applications()

# A small emoji per status, purely cosmetic, makes the table easier to
# scan at a glance without changing what's actually stored in the database.
STATUS_EMOJI = {
    "Applied": "📝",
    "Interview": "💬",
    "Offer": "🎉",
    "Rejected": "💔",
}

if data:
    df = pd.DataFrame(data, columns=["ID", "Company", "Role", "Date Applied", "Status"])

    # Export button: uses the plain (no-emoji) data so the CSV stays clean
    # and easy to reopen in Excel/Sheets. Built before we add emoji below.
    csv_data = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="⬇️ Export as CSV",
        data=csv_data,
        file_name="job_applications_backup.csv",
        mime="text/csv"
    )

    df["Status"] = df["Status"].apply(lambda s: f"{STATUS_EMOJI.get(s, '')} {s}")
    st.dataframe(df, use_container_width=True, hide_index=True)

    with st.expander("🗑️ Delete an application"):
        del_id = st.number_input("Enter ID to delete", min_value=1, step=1)
        if st.button("Delete"):
            delete_application(del_id)
            st.success(f"Deleted application {del_id}")
            st.rerun()  # re-runs the script so the table refreshes immediately
else:
    # sleepy cat illustration instead of a plain text message
    st.markdown(
        f"<div style='text-align:center; padding-top:1rem'>{SLEEPY_CAT_SVG}"
        f"<p style='color:#8A8296'>No applications yet. Add one from the sidebar!</p></div>",
        unsafe_allow_html=True
    )