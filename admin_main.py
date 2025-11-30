# ---------- ✅ main.py (Admin: Supabase + Streamlit + Tabs UI) ----------

import streamlit as st
from Attendence.admin import show_admin_panel
from Attendence.analytics import show_analytics_panel

# ---------- 🎨 Page Config ----------
st.set_page_config(
    page_title="Admin Dashboard - Smart Attendance",
    page_icon="🧠",
    layout="wide"
)

# ---------- 🧠 App Title ----------
st.markdown(
    """
    <h1 style='text-align: center; color: #4B8BBE;'>🧠 Smart Attendance Admin Dashboard</h1>
    <hr style='border-top: 1px solid #bbb;'/>
    """,
    unsafe_allow_html=True
)

# ---------- 🧑‍🏫 Admin Tabs ----------
admin_tab, analytics_tab = st.tabs(["🧑‍🏫 Admin Panel", "📊 Analytics"])

with admin_tab:
    show_admin_panel()

with analytics_tab:
    show_analytics_panel()
