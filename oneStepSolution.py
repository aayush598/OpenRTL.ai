import streamlit as st
from utils.folder_structure_generation import generate_rtl_structure
from utils.folder_setup import create_folders
from utils.code_generator import generate_code, get_db_connection
from utils.linting import run_linting
from utils.ai_error_fixer import lint_verilog_file, fix_errors_with_gemini
from utils.synthesis import run_synthesis, display_results
from utils.rtl_metrics import analyze_verilog_file, visualize_rtl_metrics
from utils.sdc_generator import extract_ports_and_clocks, generate_sdc_using_gemini, save_sdc_file  # 🔥 NEW
import json
import os

def display_folder_structure_ui(structure):
    st.subheader("📂 Folder Structure Overview")
    st.markdown(f"**Project Name:** `{structure['project_name']}`")

    directories = structure.get("directories", [])

    def render_directory(directory, indent=0):
        prefix = " " * indent + "📁"
        with st.expander(f"{prefix} {directory['name']}", expanded=False):
            if directory["files"]:
                st.markdown(f"{' ' * (indent+1)}📄 Files:")
                for file in directory["files"]:
                    st.markdown(f"{' ' * (indent+2)}• `{file}`")

            if directory["subdirectories"]:
                st.markdown(f"{' ' * (indent+1)}📂 Subdirectories:")
                for subdir in directory["subdirectories"]:
                    render_directory(subdir, indent=indent+2)

    for directory in directories:
        render_directory(directory, indent=0)

    st.markdown("🧠 Metadata:")
    st.json(structure.get("metadata", {}))

def save_structure_to_db(project_name, structure):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO folder_structures (project_name, folder_structure) VALUES (?, ?)",
              (project_name, json.dumps(structure)))
    conn.commit()
    conn.close()

def perform_linting_and_fix(project_name, base_path):
    src_path = os.path.join(base_path, "src")
    if not os.path.exists(src_path):
        st.error("❌ 'src' folder not found in the given path.")
        return

    st.spinner("🔍 Running Verilator linting...")
    all_files = []
    for root, _, files in os.walk(src_path):
        for file in files:
            if file.endswith((".v", ".sv")):
                all_files.append(os.path.join(root, file))

    if not all_files:
        st.warning("⚠ No Verilog files found in the 'src' folder.")
        return

    st.subheader("🧪 Linting & Auto-Fix Results")
    for file_path in all_files:
        iteration = 0
        with open(file_path, "r") as f:
            code = f.read()

        while iteration < 5:
            lint_output = lint_verilog_file(file_path)

            if not lint_output:
                st.success(f"✅ No issues in {os.path.basename(file_path)} (after {iteration} fix(es))")
                break
            else:
                if iteration == 0:
                    st.warning(f"⚠ Initial issues in {os.path.basename(file_path)}")
                    st.code(lint_output, language="plaintext")

                st.info(f"🤖 Attempting Gemini fix: Iteration {iteration + 1}")
                fixed_code = fix_errors_with_gemini(code, lint_output)

                if fixed_code.startswith("Gemini error:"):
                    st.error(f"❌ Gemini failed: {fixed_code}")
                    break

                with open(file_path, "w") as f:
                    f.write(fixed_code)

                code = fixed_code
                iteration += 1

        if iteration == 5:
            final_errors = lint_verilog_file(file_path)
            if final_errors:
                st.error(f"❌ Errors still exist in {os.path.basename(file_path)} after 5 attempts.")
                st.code(final_errors, language="plaintext")

def perform_synthesis(project_name, base_path):
    st.subheader("🔧 RTL Synthesis")
    with st.spinner("🏗 Running Yosys and Netlistsvg synthesis..."):
        success_files, error_logs = run_synthesis(base_path, project_name)
        display_results(success_files, error_logs)

def perform_rtl_metrics_analysis(project_name, base_path):
    st.subheader("📊 RTL Metrics Analysis")
    src_path = f"{base_path}/{project_name}/src" 
    if not os.path.exists(src_path):
        st.error(f"❌ 'src' folder not found in the given path.")
        return

    verilog_files = []
    for root, _, files in os.walk(src_path):
        for file in files:
            if file.endswith((".v", ".sv")):
                verilog_files.append(os.path.join(root, file))

    if not verilog_files:
        st.warning("⚠ No Verilog files found for RTL metrics analysis.")
        return

    for vfile in verilog_files:
        st.markdown("---")
        try:
            metrics, hierarchy = analyze_verilog_file(vfile)
            visualize_rtl_metrics(os.path.basename(vfile), metrics, hierarchy)
        except Exception as e:
            st.error(f"❌ Failed to analyze `{os.path.basename(vfile)}`: {e}")

def generate_sdc_for_top_module(project_name, base_path):
    st.subheader("⏱️ .SDC Constraint File Generation")
    src_path = os.path.join(base_path, project_name, "src")
    if not os.path.exists(src_path):
        st.error("❌ 'src' folder not found.")
        return

    # Heuristic: assume first .v file as top module
    top_file = None
    for file in os.listdir(src_path):
        if file.endswith(".v") or file.endswith(".sv"):
            top_file = os.path.join(src_path, file)
            break

    if not top_file:
        st.warning("⚠ No Verilog file found to generate .SDC.")
        return

    try:
        with open(top_file, "r") as f:
            top_code = f.read()

        ports, clocks = extract_ports_and_clocks(top_code)

        with st.spinner("⚙ Generating .SDC using Gemini..."):
            sdc_content = generate_sdc_using_gemini(top_code, ports, clocks)

        sdc_file_name = os.path.splitext(os.path.basename(top_file))[0] + ".sdc"
        sdc_path = save_sdc_file(sdc_content, sdc_file_name)

        st.success(f"✅ .SDC file generated: `{sdc_path}`")
        st.download_button("📥 Download .SDC File", sdc_content, file_name=sdc_file_name)
        st.code(sdc_content, language="tcl")

    except Exception as e:
        st.error(f"❌ Failed to generate .SDC file: {e}")

def generate_and_display_structure(base_path, project_description):
    if base_path.strip() and project_description.strip():
        structure_str = generate_rtl_structure(project_description)
        structure = json.loads(structure_str)
        project_name = structure["project_name"]
        st.success("✅ Folder structure generated successfully!")

        try:
            created_path = create_folders(base_path, structure)
            st.success(f"📁 Folder structure created at: `{created_path}`")

            save_structure_to_db(project_name, structure)
            st.success("💾 Folder structure saved to the database!")

            with st.spinner("🤖 Generating Verilog code using Gemini..."):
                result = generate_code(project_name, created_path)
                st.success(result)

            perform_linting_and_fix(project_name, created_path)
            perform_synthesis(project_name, created_path)
            perform_rtl_metrics_analysis(project_name, base_path)
            generate_sdc_for_top_module(project_name, base_path)  # 🔥 .SDC Integration

        except Exception as e:
            st.error(f"❌ Failed to create folder structure: {str(e)}")

        display_folder_structure_ui(structure)
    else:
        st.warning("⚠️ Please enter both base path and project description.")

def one_step_input_fields():
    st.title("🛠️ One-Step RTL Project Setup")

    base_path = st.text_input("📁 Enter the base folder path:")
    project_description = st.text_area("📝 Describe your RTL project:")

    if st.button("Generate Project Structure"):
        generate_and_display_structure(base_path, project_description)

    return base_path, project_description
