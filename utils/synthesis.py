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
    """Run synthesis using Yosys for all Verilog files, continue on errors."""
    output_folder = os.path.join(folder_path, "synthesized_images")
    os.makedirs(output_folder, exist_ok=True)
    
    folder_structure = get_folder_structure(project_name)
    if not folder_structure:
        return "No folder structure found."
    
    verilog_files = find_verilog_files(folder_structure, folder_path)
    if not verilog_files:
        return "No Verilog files found for synthesis."

    error_logs = {}
    success_files = []

    for vfile in verilog_files:
        base_name = os.path.splitext(os.path.basename(vfile))[0]
        output_image = os.path.join(output_folder, f"{base_name}.svg")  # Netlistsvg outputs SVG

        yosys_script = f"""
        read_verilog {vfile}
        synth -top {base_name}
        write_json {output_folder}/{base_name}.json
        """

        script_path = os.path.join(folder_path, "synthesis.ys")
        with open(script_path, "w") as f:
            f.write(yosys_script)

        result = subprocess.run(["yosys", "-s", script_path], capture_output=True, text=True)

        if result.returncode != 0:
            error_logs[base_name] = result.stderr
            continue  # Skip to the next file

        # Generate SVG using Netlistsvg
        netlistsvg_command = f"netlistsvg {output_folder}/{base_name}.json -o {output_image}"
        netlist_result = subprocess.run(netlistsvg_command.split(), capture_output=True, text=True)

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

