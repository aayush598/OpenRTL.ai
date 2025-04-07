import os
import sqlite3
import json
import streamlit as st
from subprocess import run, PIPE

def init_db():
    """Initialize the SQLite database and create table if not exists."""
    conn = sqlite3.connect("database/folder_structure.db", check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS linting_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_name TEXT,
                    folder_path TEXT,
                    file_name TEXT,
                    linting_output TEXT
                )''')
    conn.commit()
    return conn, c

def get_available_projects(c):
    """Fetch available project names from the database."""
    c.execute("SELECT project_name FROM folder_structures")
    return [row[0] for row in c.fetchall()]

def get_project_details(c, project_name):
    """Retrieve folder structure from the database."""
    c.execute("SELECT folder_structure FROM folder_structures WHERE project_name = ?", (project_name,))
    row = c.fetchone()
    return json.loads(row[0]) if row else {}

def lint_verilog_file(file_path):
    """Runs Verilator linting on a single Verilog file and returns the output."""
    result = run(["verilator", "--lint-only", file_path], stdout=PIPE, stderr=PIPE, text=True)
    return result.stderr  # Verilator prints errors/warnings to stderr

def store_linting_result(c, conn, project_name, folder_path, file_name, linting_output):
    """Stores linting results in the database."""
    c.execute("INSERT INTO linting_results (project_name, folder_path, file_name, linting_output) VALUES (?, ?, ?, ?)",
              (project_name, folder_path, file_name, linting_output))
    conn.commit()

def lint_project(c, conn, project_name, folder_path):
    """Lint all Verilog files in the selected project's folder structure."""
    folder_structure = get_project_details(c, project_name)
    
    if not folder_structure:
        return "No folder structure found for the selected project."
    
    results = []
    for directory in folder_structure.get("directories", []):
        dir_path = os.path.join(folder_path, directory["name"])
        
        for file_name in directory.get("files", []):
            if file_name.endswith((".v", ".sv")):
                file_path = os.path.join(dir_path, file_name)
                
                lint_output = lint_verilog_file(file_path)
                store_linting_result(c, conn, project_name, folder_path, file_name, lint_output)
                
                results.append((file_name, lint_output))
    
    return results

def run_linting(project_name, project_folder):
    """Wrapper function to run linting from app.py."""
    conn, c = init_db()
    return lint_project(c, conn, project_name, project_folder)

def linting_ui():
    """Streamlit UI for linting Verilog files."""
    st.title("🔍 Verilog Linting with Verilator")
    st.markdown("Lint your Verilog files to identify syntax or logic issues.")
    
    conn, c = init_db()
    
    st.sidebar.header("Project Selection")
    project_folder = st.sidebar.text_input("Enter Folder Path", placeholder="/path/to/project")
    available_projects = get_available_projects(c)
    project_name = st.sidebar.selectbox("Select Project", available_projects)
    
    if st.sidebar.button("Start Linting"):
        if project_folder and project_name:
            st.sidebar.success(f"Linting started for **{project_name}** in **{project_folder}**...")
            results = lint_project(c, conn, project_name, project_folder)
            
            if isinstance(results, str):
                st.error(results)
            else:
                st.subheader("Linting Results")
                for file_name, lint_output in results:
                    if lint_output:
                        st.error(f"⚠ Issues in {file_name}")
                        st.code(lint_output, language="plaintext")
                    else:
                        st.success(f"✅ No issues found in {file_name}")
            
            st.sidebar.success("✅ Linting process completed.")
        else:
            st.sidebar.error("Please provide a folder path and select a project.")