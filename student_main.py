# student_main.py

import streamlit as st
from Attendence.student import show_student_panel
import pandas as pd
from supabase import create_client
from datetime import datetime
import pytz

# ---------- Setup ----------
st.set_page_config(
    page_title="Student Portal",
    layout="centered",
    page_icon="🎓"
)

# ---------- Supabase Client ----------
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# ---------- Utilities ----------
def current_ist_date():
    return datetime.now(pytz.timezone("Asia/Kolkata")).strftime("%Y-%m-%d")

# ---------- Page Title (Only Once) ----------
st.markdown("""
<h1 style='text-align: center; color: #4B8BBE;'>🎓 Student Attendance Portal</h1>
<hr style='border-top: 1px solid #bbb;' />
""", unsafe_allow_html=True)

# ---------- Tabs ----------
tab1, tab2 = st.tabs(["📥 Mark Attendance", "📅 View My Attendance"])

# ---------- Tab 1: Mark Attendance ----------
with tab1:
    show_student_panel()

# ---------- Tab 2: View Student's Own Records ----------
with tab2:
    st.subheader("📅 Check Your Attendance Record")

    with st.form("view_attendance_form"):
        class_list = [entry["class_name"] for entry in supabase.table("classroom_settings").select("class_name").execute().data]
        selected_class = st.selectbox("Select Your Class", class_list)
        roll_number = st.text_input("Enter Your Roll Number").strip()
        submit = st.form_submit_button("🔍 Show My Attendance")

    if submit:
        if not roll_number:
            st.warning("Please enter your roll number.")
        else:
            records = (
                supabase.table("attendance")
                .select("*")
                .eq("class_name", selected_class)
                .eq("roll_number", roll_number)
                .execute()
                .data
            )

            if not records:
                st.info("No attendance found for this roll number.")
            else:
                df = pd.DataFrame(records)
                df["status"] = "P"

                matrix = df.pivot_table(
                    index=["roll_number", "name"],
                    columns="date",
                    values="status",
                    aggfunc="first",
                    fill_value="A"
                ).reset_index()

                matrix.columns.name = None
                matrix = matrix.sort_values("roll_number")

                st.dataframe(matrix, use_container_width=True)
