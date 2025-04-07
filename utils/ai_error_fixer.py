import os
import re
import sqlite3
import json
import streamlit as st
from subprocess import run, PIPE
from dotenv import load_dotenv
from google import genai

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY)

def init_db():
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

def lint_verilog_file(file_path):
    result = run(["verilator", "--lint-only", file_path], stdout=PIPE, stderr=PIPE, text=True)
    return result.stderr

def clean_gemini_response(response):
    return re.sub(r"```[\w]*\n|```", "", response).strip()

def fix_errors_with_gemini(verilog_code, linting_errors):
    prompt = f"""
You are a Verilog expert. The following Verilog code has linting errors.
Please fix these errors. Provide only the corrected Verilog code, no explanations or markdown.

### Linting Errors:
{linting_errors}

### Verilog Code:
{verilog_code}
"""
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash-lite",
            contents=prompt
        )
        return clean_gemini_response(response.text)
    except Exception as e:
        return f"Gemini error: {e}"

def ai_fix_verilog_ui():
    st.title("🔧 Auto-Fix Verilog Linting Errors with Gemini AI")
    file_path = st.text_input("📁 Enter full Verilog file path (.v or .sv)")

    if st.button("🧠 Auto Fix Errors"):
        if not os.path.exists(file_path):
            st.error("❌ File does not exist.")
            return
        if not file_path.endswith((".v", ".sv")):
            st.warning("⚠ Please provide a valid Verilog file (.v or .sv)")
            return

        try:
            with open(file_path, "r") as f:
                code = f.read()

            st.subheader("📜 Status Log")
            log_area = st.empty()
            full_log = ""

            iteration = 1
            while True:
                lint_output = lint_verilog_file(file_path)

                full_log += f"\n--- Iteration {iteration} ---\n"
                full_log += f"🔍 Linting Output:\n{lint_output or 'No errors found.'}\n"

                if not lint_output:
                    full_log += f"✅ All errors resolved in {iteration} iteration(s).\n"
                    log_area.text_area("🔧 Fixing Process Log", full_log, height=400)
                    st.success("✅ Verilog code is clean and ready!")
                    with open(file_path, "r") as final_code:
                        st.code(final_code.read(), language="verilog")
                    break
                else:
                    full_log += f"⚠ Errors detected. Sending to Gemini...\n"
                    log_area.text_area("🔧 Fixing Process Log", full_log, height=400)

                    fixed_code = fix_errors_with_gemini(code, lint_output)

                    if fixed_code.startswith("Gemini error:"):
                        full_log += f"{fixed_code}\n❌ Gemini failed to fix the code.\n"
                        log_area.text_area("🔧 Fixing Process Log", full_log, height=400)
                        st.error(fixed_code)
                        break

                    with open(file_path, "w") as f:
                        f.write(fixed_code)

                    full_log += "✅ Gemini response applied. Retesting...\n"
                    log_area.text_area("🔧 Fixing Process Log", full_log, height=400)

                    code = fixed_code
                    iteration += 1

        except Exception as e:
            st.error(f"Unexpected error: {e}")
