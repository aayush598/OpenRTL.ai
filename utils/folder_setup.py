import os
import json
import sqlite3
from pathlib import Path

DB_NAME = "database/folder_structure.db"

def create_folders(base_path, folder_structure):
    """Recursively create the folder structure."""
    project_root = os.path.join(base_path, folder_structure["project_name"])
    
    if not os.path.exists(project_root):
        os.makedirs(project_root)

    for directory in folder_structure["directories"]:
        dir_path = os.path.join(project_root, directory["name"])
        os.makedirs(dir_path, exist_ok=True)

        for file in directory.get("files", []):
            file_path = os.path.join(dir_path, file)
            open(file_path, 'w').close()  # Create an empty file

        for subdir in directory.get("subdirectories", []):
            subdir_path = os.path.join(dir_path, subdir["name"])
            os.makedirs(subdir_path, exist_ok=True)
    
    return project_root

def get_all_project_names():
    """Fetch all saved project names from the database."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT project_name FROM folder_structures")
    projects = [row[0] for row in c.fetchall()]
    conn.close()
    return projects

def get_project_structure(project_name):
    """Fetch the folder structure of the selected project."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT folder_structure FROM folder_structures WHERE project_name = ?", (project_name,))
    row = c.fetchone()
    conn.close()
    return json.loads(row[0]) if row else {}

# Ensure the database exists with the necessary table
def initialize_database():
    """Create database table if it does not exist."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS folder_structures (
                    project_name TEXT PRIMARY KEY,
                    folder_structure TEXT NOT NULL
                )''')
    conn.commit()
    conn.close()