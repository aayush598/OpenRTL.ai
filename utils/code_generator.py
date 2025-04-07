import os
import sqlite3
import json
import re
from dotenv import load_dotenv
from google import genai

# Load API key from .env file
load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=API_KEY)

# Initialize SQLite connection
def get_db_connection():
    return sqlite3.connect("database/folder_structure.db", check_same_thread=False)

def get_available_projects():
    """Fetch available project names from the database."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT project_name FROM folder_structures")
    projects = [row[0] for row in c.fetchall()]
    conn.close()
    return projects

def get_project_details(project_name):
    """Retrieve project folder structure from the database."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT folder_structure FROM folder_structures WHERE project_name = ?", (project_name,))
    row = c.fetchone()
    conn.close()
    return json.loads(row[0]) if row else {}

def clean_code(response_text):
    """Remove unwanted markdown and language specifiers from Gemini response."""
    return re.sub(r'```[a-zA-Z]*', '', response_text).strip()

def generate_code_for_file(project_name, project_description, folder_structure, file_path):
    """Generate code for a given file using Gemini API."""
    prompt = f'''
    Generate a complete code file based on the following details:
    
    **Project Name:** {project_name}
    **Project Description:** {project_description}
    **Folder Structure:** {json.dumps(folder_structure, indent=4)}
    **File Path:** {file_path}
    
    Provide the full code without explanations or additional text.
    Only provide the code for the file path which is mentioned.
    Do not include the code which will be mentioned in the other files.
    Generate code for only verilog not system verilog or other languages.
    '''
    
    response = client.models.generate_content(model="gemini-2.0-flash-lite", contents=prompt)
    return clean_code(response.text)

def generate_code(project_name, project_location):
    """Generate and overwrite code files in the selected folder structure."""
    folder_structure = get_project_details(project_name)
    project_description = "Provide a detailed description of the project here..."  # Modify as needed
    
    if not folder_structure:
        raise ValueError("No folder structure found for the selected project.")
    
    for directory in folder_structure.get("directories", []):
        dir_path = os.path.join(project_location, directory["name"])
        os.makedirs(dir_path, exist_ok=True)
        
        for file_name in directory.get("files", []):
            file_path = os.path.join(dir_path, file_name)
            code = generate_code_for_file(project_name, project_description, folder_structure, file_path)
            
            with open(file_path, "w") as f:
                f.write(code)
    
    return f"Code generation completed for project: {project_name} at {project_location}"
