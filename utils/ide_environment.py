import os
import streamlit as st

def list_files_in_directory(directory):
    """Recursively list all files and folders."""
    file_structure = []

    for root, dirs, files in os.walk(directory):
        rel_root = os.path.relpath(root, directory)
        rel_root = "" if rel_root == "." else rel_root

        for d in dirs:
            file_structure.append({
                "type": "folder",
                "path": os.path.join(rel_root, d)
            })

        for f in files:
            file_structure.append({
                "type": "file",
                "path": os.path.join(rel_root, f)
            })

    return sorted(file_structure, key=lambda x: x["path"])

def ide_environment_ui():
    st.title("🧠 IDE Environment")
    st.markdown("Simulate a VS Code-style IDE to browse and edit project files.")

    # Base Folder Input
    base_folder = st.text_input("📁 Enter base project folder path", placeholder="/path/to/project")

    if not base_folder or not os.path.exists(base_folder):
        st.warning("Please enter a valid base project folder path.")
        return

    # Project File Explorer
    st.subheader("📂 Project Explorer")
    files = list_files_in_directory(base_folder)

    if "selected_file" not in st.session_state:
        st.session_state.selected_file = None

    for item in files:
        full_path = os.path.join(base_folder, item["path"])
        display_path = item["path"]

        if item["type"] == "folder":
            st.markdown(f"📁 `{display_path}`")
        else:
            if st.button(f"📝 {display_path}", key=f"open_{display_path}"):
                st.session_state.selected_file = full_path

    st.markdown("---")
    st.subheader("➕ Create New")

    new_file_name = st.text_input("New File Name (with extension)", key="new_file_name")
    new_file_content = st.text_area("File Content", height=200, key="new_file_content")
    create_path = st.text_input("Folder to create in (relative to base)", value="", key="create_path")

    if st.button("Create File"):
        new_full_path = os.path.join(base_folder, create_path, new_file_name)
        os.makedirs(os.path.dirname(new_full_path), exist_ok=True)
        with open(new_full_path, "w") as f:
            f.write(new_file_content)
        st.success(f"File created: {new_full_path}")

    # Editor: Load + Save + Delete
    if st.session_state.selected_file and os.path.isfile(st.session_state.selected_file):
        selected_file = st.session_state.selected_file
        rel_path = os.path.relpath(selected_file, base_folder)
        st.markdown("---")
        st.subheader(f"📝 Editing: `{rel_path}`")

        # Use a dynamic key for text_area so it holds state
        if f"{selected_file}_content" not in st.session_state:
            with open(selected_file, "r") as f:
                st.session_state[f"{selected_file}_content"] = f.read()

        new_content = st.text_area("Edit File", value=st.session_state[f"{selected_file}_content"], height=300, key=f"{selected_file}_editor")

        col1, col2 = st.columns(2)

        with col1:
            if st.button("💾 Save Changes", key=f"{selected_file}_save"):
                with open(selected_file, "w") as f:
                    f.write(new_content)
                st.success("File saved successfully.")
                st.session_state[f"{selected_file}_content"] = new_content  # Update state

        with col2:
            if st.button("🗑 Delete File", key=f"{selected_file}_delete"):
                os.remove(selected_file)
                st.success("File deleted.")
                del st.session_state[f"{selected_file}_content"]
                st.session_state.selected_file = None
