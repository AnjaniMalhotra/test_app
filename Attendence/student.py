# ---------- ✅ student.py (no time column) ----------

from datetime import datetime
import pytz
from supabase import create_client, Client
import streamlit as st

def show_student_panel():
    # ---------- 🧠 Config ----------
    IST = pytz.timezone("Asia/Kolkata")
    def current_ist_date():
        return datetime.now(IST).strftime("%Y-%m-%d")

    # ---------- 🔐 Supabase Setup ----------
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(url, key)

    # ---------- 🎓 Student Portal ----------
    st.title("🎓 Student Attendance Portal")

    # 🔍 Get only OPEN classrooms
    open_classes_response = supabase.table("classroom_settings").select("class_name").eq("is_open", True).execute()
    class_list = [entry["class_name"] for entry in open_classes_response.data]

    if not class_list:
        st.warning("🚫 No classrooms are currently open for attendance.")
        st.stop()

    selected_class = st.selectbox("Select Your Class", class_list)

    # 🧩 Fetch settings for selected class
    settings_response = supabase.table("classroom_settings").select("code", "daily_limit").eq("class_name", selected_class).execute()
    settings = settings_response.data[0]
    required_code = settings["code"]
    daily_limit = settings["daily_limit"]

    # 🧠 Roll number input
    roll_number = st.text_input("Roll Number").strip()

    # 🔒 Fetch locked name for roll number (if exists)
    roll_map_response = supabase.table("roll_map").select("name").eq("class_name", selected_class).eq("roll_number", roll_number).execute()

    if roll_map_response.data:
        locked_name = roll_map_response.data[0]["name"]
        st.info(f"🔒 Name auto-filled for Roll {roll_number}: **{locked_name}**")
        name = locked_name
    else:
        name = st.text_input("Name (Will be locked after first time)").strip()

    code_input = st.text_input("Attendance Code")

    if st.button("✅ Submit Attendance"):
        today = current_ist_date()

        # 🔐 Check code
        if code_input != required_code:
            st.error("❌ Incorrect attendance code.")
            st.stop()

        # 🔁 Check if already submitted today
        existing_response = (
            supabase.table("attendance")
            .select("*")
            .eq("class_name", selected_class)
            .eq("roll_number", roll_number)
            .eq("date", today)
            .execute()
        )
        if existing_response.data:
            st.error("❌ Attendance already marked today.")
            st.stop()

        # 🔁 Check daily limit
        attendance_today_response = (
            supabase.table("attendance")
            .select("*", count="exact")
            .eq("class_name", selected_class)
            .eq("date", today)
            .execute()
        )

        attendance_count = attendance_today_response.count or 0

        if attendance_count >= daily_limit:
            st.warning("⚠️ Attendance limit for today has been reached.")
            st.stop()

        # 🔒 Lock roll_number to name if new
        if not roll_map_response.data:
            supabase.table("roll_map").insert({
                "class_name": selected_class,
                "roll_number": roll_number,
                "name": name
            }).execute()
        else:
            if roll_map_response.data[0]["name"] != name:
                st.error("❌ Roll number already locked to a different name.")
                st.stop()

        # ✅ Submit Attendance
        supabase.table("attendance").insert({
            "class_name": selected_class,
            "roll_number": roll_number,
            "name": name,
            "date": today
        }).execute()

        st.success("✅ Attendance submitted successfully!")
