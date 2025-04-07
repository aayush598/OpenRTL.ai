import streamlit as st
from utils.folder_structure_generation import generate_rtl_structure
from utils.folder_setup import create_folders
import json

def display_folder_structure_ui(structure):
    st.subheader("📂 Folder Structure Overview")
    st.markdown(f"**Project Name:** `{structure['project_name']}`")

    directories = structure.get("directories", [])

    def render_directory(directory, indent=0):
        prefix = " " * indent + "📁"  # Unicode em-space for indentation
        with st.expander(f"{prefix} {directory['name']}", expanded=False):
            if directory["files"]:
                st.markdown(f"{' ' * (indent+1)}📄 Files:")
                for file in directory["files"]:
                    st.markdown(f"{' ' * (indent+2)}• `{file}`")

            if directory["subdirectories"]:
                st.markdown(f"{' ' * (indent+1)}📂 Subdirectories:")
                for subdir in directory["subdirectories"]:
                    render_directory(subdir, indent=indent+2)  # Call recursively but avoid nested expanders

    for directory in directories:
        render_directory(directory, indent=0)

    st.markdown("🧠 Metadata:")
    st.json(structure.get("metadata", {}))

def generate_and_display_structure(base_path, project_description):
    """Generates RTL folder structure and displays it."""
    if base_path.strip() and project_description.strip():
        structure_str = generate_rtl_structure(project_description)
        structure = json.loads(structure_str)
        st.success("✅ Folder structure generated successfully!")

        # Automatically create the folder structure in the specified location
        try:
            created_path = create_folders(base_path, structure)
            st.success(f"📁 Folder structure created at: `{created_path}`")
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
