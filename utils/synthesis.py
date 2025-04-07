import streamlit as st
import os
import sqlite3
import subprocess
import json
from PIL import Image

def get_project_list():
    """Fetch project names from the database."""
    conn = sqlite3.connect("database/folder_structure.db")
    cursor = conn.cursor()
    cursor.execute("SELECT project_name FROM folder_structures")
    projects = [row[0] for row in cursor.fetchall()]
    conn.close()
    return projects

def get_folder_structure(project_name):
    """Fetch folder structure from the database."""
    conn = sqlite3.connect("database/folder_structure.db")
    cursor = conn.cursor()
    cursor.execute("SELECT folder_structure FROM folder_structures WHERE project_name=?", (project_name,))
    result = cursor.fetchone()
    conn.close()
    return json.loads(result[0]) if result else None

def find_verilog_files(folder_structure, root_path):
    """Find all Verilog files based on the stored folder structure."""
    verilog_files = []
    for directory in folder_structure.get("directories", []):
        dir_path = os.path.join(root_path, directory["name"])
        for file in directory["files"]:
            if file.endswith(".v") or file.endswith(".sv"):
                file_path = os.path.join(dir_path, file)
                if os.path.exists(file_path):
                    verilog_files.append(file_path)
    return verilog_files

def run_synthesis(folder_path, project_name):
    """Run synthesis using Yosys for Verilog files in the 'src' folder only."""
    src_folder = os.path.join(folder_path, "src")
    output_folder = os.path.join(folder_path, "synthesized_images")
    os.makedirs(output_folder, exist_ok=True)

    if not os.path.exists(src_folder):
        return [], {"src_folder_missing": "❌ 'src' folder not found in project."}

    folder_structure = get_folder_structure(project_name)
    if not folder_structure:
        return [], {"structure_missing": "❌ Folder structure not found in DB."}

    # ONLY scan src folder
    verilog_files = []
    for root, _, files in os.walk(src_folder):
        for file in files:
            if file.endswith(".v") or file.endswith(".sv"):
                file_path = os.path.join(root, file)
                verilog_files.append(file_path)

    if not verilog_files:
        return [], {"no_verilog": "⚠ No Verilog files found in 'src' folder for synthesis."}

    error_logs = {}
    success_files = []

    for vfile in verilog_files:
        base_name = os.path.splitext(os.path.basename(vfile))[0]
        output_json = os.path.join(output_folder, f"{base_name}.json")
        output_image = os.path.join(output_folder, f"{base_name}.svg")

        yosys_script = f"""
        read_verilog {vfile}
        synth -top {base_name}
        write_json {output_json}
        """

        script_path = os.path.join(output_folder, f"synth_{base_name}.ys")
        with open(script_path, "w") as f:
            f.write(yosys_script)

        result = subprocess.run(["yosys", "-s", script_path], capture_output=True, text=True)

        if result.returncode != 0:
            error_logs[base_name] = result.stderr
            continue

        netlistsvg_cmd = f"netlistsvg {output_json} -o {output_image}"
        netlist_result = subprocess.run(netlistsvg_cmd.split(), capture_output=True, text=True)

        if netlist_result.returncode == 0:
            success_files.append(output_image)
        else:
            error_logs[base_name] = netlist_result.stderr

    return success_files, error_logs

def display_results(success_files, error_logs):
    """Display synthesis results with images and errors."""
    if success_files:
        st.subheader("✅ Successfully Synthesized Images")
        for img_file in success_files:
            if os.path.exists(img_file):
                st.image(img_file, caption=os.path.basename(img_file), use_column_width=True)

    if error_logs:
        st.subheader("⚠ Errors in Synthesis")
        for file, error in error_logs.items():
            st.error(f"Error in {file}.v:\n{error}")

