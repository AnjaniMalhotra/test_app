# 📁 admin_app/admin.py (Modularized)

import streamlit as st
from datetime import datetime
import pandas as pd
import os
import pytz
import sys
from supabase import create_client
from github import Github
from github.GithubException import GithubException
from dotenv import load_dotenv

# ---------- 🌐 Config & Setup ----------
def setup_clients():
    load_dotenv()
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")
    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
    GITHUB_USERNAME = os.getenv("GITHUB_USERNAME")
    GITHUB_REPO = os.getenv("GITHUB_REPO")
    ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")

    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    gh = Github(GITHUB_TOKEN)
    repo = gh.get_user(GITHUB_USERNAME).get_repo(GITHUB_REPO)

    return supabase, repo, ADMIN_USERNAME, ADMIN_PASSWORD

# ---------- ⏲️ Utility ----------
def current_ist_date():
    IST = pytz.timezone("Asia/Kolkata")
    return datetime.now(IST).strftime("%Y-%m-%d")

# ---------- 🔐 Admin Login ----------
def admin_login(admin_user, admin_pass):
    if "admin_logged_in" not in st.session_state:
        st.session_state.admin_logged_in = False

    if not st.session_state.admin_logged_in:
        with st.form("admin_login"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            if st.form_submit_button("🔐 Login"):
                if username == admin_user and password == admin_pass:
                    st.session_state.admin_logged_in = True
                    st.rerun()
                else:
                    st.error("Invalid credentials")
        st.stop()

# ---------- ➕ Sidebar Class Creation + Logout + Delete ----------
def sidebar_controls(supabase):
    with st.sidebar:
        st.markdown("## ➕ Create Class")
        class_input = st.text_input("New Class Name")
        if st.button("➕ Add Class"):
            if class_input.strip():
                exists = supabase.table("classroom_settings").select("*").eq("class_name", class_input).execute().data
                if exists:
                    st.warning("Class already exists.")
                else:
                    supabase.table("classroom_settings").insert({
                        "class_name": class_input,
                        "code": "1234",
                        "daily_limit": 10,
                        "is_open": False
                    }).execute()
                    st.success(f"Class '{class_input}' created.")
                    st.rerun()

        if st.button("🚪 Logout"):
            st.session_state.admin_logged_in = False
            st.rerun()

        st.markdown("## 🗑️ Delete Class")
        delete_target = st.text_input("Enter class to delete")
        if st.button("Delete This Class"):
            if delete_target.strip():
                st.warning("This will permanently delete the class and all data.")
                if st.text_input("Type DELETE to confirm") == "DELETE":
                    supabase.table("attendance").delete().eq("class_name", delete_target).execute()
                    supabase.table("roll_map").delete().eq("class_name", delete_target).execute()
                    supabase.table("classroom_settings").delete().eq("class_name", delete_target).execute()
                    st.success("Class deleted.")
                    st.rerun()

# ---------- 🛠️ Attendance Controls ----------
def class_controls(supabase):
    classes = supabase.table("classroom_settings").select("*").execute().data
    if not classes:
        st.warning("No classes found.")
        st.stop()

    selected_class = st.selectbox("📚 Select a Class", [c["class_name"] for c in classes])
    config = next(c for c in classes if c["class_name"] == selected_class)

    st.markdown(f"**Current Code:** `{config['code']}`")
    st.markdown(f"**Current Limit:** `{config['daily_limit']}`")

    is_open = config["is_open"]
    other_open = [c["class_name"] for c in classes if c["is_open"] and c["class_name"] != selected_class]

    st.subheader("🛠️ Attendance Controls")
    st.info(f"Status: {'OPEN' if is_open else 'CLOSED'}")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Open Attendance"):
            if other_open:
                st.warning(f"Close other open classes: {', '.join(other_open)}")
            else:
                supabase.table("classroom_settings").update({"is_open": True}).eq("class_name", selected_class).execute()
                st.rerun()
    with col2:
        if st.button("❌ Close Attendance"):
            supabase.table("classroom_settings").update({"is_open": False}).eq("class_name", selected_class).execute()
            st.rerun()

    with st.expander("🔄 Update Code & Limit"):
        new_code = st.text_input("New Code", value=config["code"])
        new_limit = st.number_input("New Limit", min_value=1, value=config["daily_limit"], step=1)
        if st.button("📏 Save Settings"):
            supabase.table("classroom_settings").update({"code": new_code, "daily_limit": new_limit}).eq("class_name", selected_class).execute()
            st.success("✅ Settings updated.")
            st.rerun()

    return selected_class

# ---------- 📊 Attendance Matrix + Push ----------
def show_matrix_and_push(supabase, repo, selected_class):
    records = supabase.table("attendance").select("*").eq("class_name", selected_class).order("date", desc=True).execute().data
    if records:
        df = pd.DataFrame(records)
        df["status"] = "P"
        pivot_df = df.pivot_table(index=["roll_number", "name"], columns="date", values="status", aggfunc="first", fill_value="A").reset_index()
        pivot_df["roll_number"] = pd.to_numeric(pivot_df["roll_number"], errors="coerce")
        pivot_df = pivot_df.dropna(subset=["roll_number"])
        pivot_df["roll_number"] = pivot_df["roll_number"].astype(int)

        pivot_df = pivot_df.sort_values("roll_number")


        def highlight(val):
            return "background-color:#d4edda;color:green" if val == "P" else "background-color:#f8d7da;color:red"

        styled = pivot_df.style.map(highlight, subset=pivot_df.columns[2:])
        st.dataframe(styled, use_container_width=True)

        st.download_button("⬇️ Download CSV", pivot_df.to_csv(index=False).encode(), f"{selected_class}_matrix.csv", "text/csv")

        if st.button("🚀 Push to GitHub"):
            filename = f"records/attendance_matrix_{selected_class}_{current_ist_date().replace('-', '')}.csv"
            file_content = pivot_df.to_csv(index=False)
            commit_message = f"Push matrix for {selected_class}"
            branch = "main"

            try:
                existing_file = repo.get_contents(filename, ref=branch)
                repo.update_file(
                    path=filename,
                    message=commit_message,
                    content=file_content,
                    sha=existing_file.sha,
                    branch=branch
                )
                st.success(f"✅ Updated existing file: {filename}")
            except GithubException as e:
                if e.status == 404:
                    repo.create_file(
                        path=filename,
                        message=commit_message,
                        content=file_content,
                        branch=branch
                    )
                    st.success(f"✅ Created new file: {filename}")
                else:
                    st.error(f"GitHub Error: {e.data.get('message', str(e))}")
    else:
        st.info("No attendance data yet.")

# ---------- 👩‍🏫 Main Admin Entry Point ----------
def show_admin_panel():
    st.set_page_config(page_title="Admin Panel", layout="wide", page_icon="👩‍🏫")
    st.markdown("""
        <h1 style='text-align: center; color: #4B8BBE;'>👩‍🏫 Admin Control Panel</h1>
        <hr style='border-top: 1px solid #bbb;' />
    """, unsafe_allow_html=True)

    supabase, repo, admin_user, admin_pass = setup_clients()
    admin_login(admin_user, admin_pass)
    sidebar_controls(supabase)
    selected_class = class_controls(supabase)
    show_matrix_and_push(supabase, repo, selected_class)
