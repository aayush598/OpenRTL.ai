import streamlit as st
import os
import re
from google import genai
from dotenv import load_dotenv

# Load API key from .env
load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

def extract_ports_and_clocks(verilog_code):
    ports = []
    clocks = []

    port_matches = re.findall(r'(input|output|inout)\s+(\[.*?\]\s+)?([a-zA-Z_][a-zA-Z0-9_]*)', verilog_code)
    for port in port_matches:
        ports.append(port[2])

    clock_patterns = [r'input\s+.*clk', r'input\s+.*clock']
    for pattern in clock_patterns:
        clocks.extend(re.findall(pattern, verilog_code))

    return list(set(ports)), list(set(clocks))

def clean_sdc_output(raw_content):
    # Remove code block markers and language tags like ```sdc, ```json, ```python, etc.
    cleaned = re.sub(r'```\w*', '', raw_content)
    cleaned = re.sub(r'```', '', cleaned)
    return cleaned.strip()

def generate_sdc_using_gemini(top_module_code, ports, clocks):
    prompt = f"""
    Given the following Verilog top module code:

    {top_module_code}

    Generate an advanced .SDC (Synopsys Design Constraints) file with the following requirements:
    - Include create_clock constraints for all clock ports.
    - Define input and output delays.
    - Include set_input_transition and set_output_load for all ports.
    - Add constraints for set_false_path and set_max_delay if applicable.
    - Ensure constraints are realistic for a 100 MHz FPGA-based design.
    - Add any advanced industry-grade constraints.

    Output only the content of the .sdc file.
    """
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt
    )
    return clean_sdc_output(response.text)

def save_sdc_file(content, file_name, save_dir="projects/sdc_outputs"):
    os.makedirs(save_dir, exist_ok=True)
    file_path = os.path.join(save_dir, file_name)
    with open(file_path, 'w') as f:
        f.write(content)
    return file_path

def sdc_ui():
    st.title("🧠 AI-Powered .SDC Constraint File Generator")

    file_path = st.text_input("📂 Enter path to your Top Module Verilog File (.v or .sv)")

    if st.button("📎 Generate Constraint File"):
        if not os.path.exists(file_path):
            st.error("❌ File not found. Please enter a valid path.")
            return

        try:
            with open(file_path, 'r') as f:
                top_module_code = f.read()

            ports, clocks = extract_ports_and_clocks(top_module_code)

            st.info("🔍 Extracted Ports and Clocks")
            st.code(f"Ports: {ports}\nClocks: {clocks}", language="text")

            with st.spinner("⏳ Generating .SDC using Gemini..."):
                sdc_output = generate_sdc_using_gemini(top_module_code, ports, clocks)

            sdc_file_name = os.path.splitext(os.path.basename(file_path))[0] + ".sdc"
            saved_path = save_sdc_file(sdc_output, sdc_file_name)

            st.success(f"✅ .SDC file generated and saved at: {saved_path}")
            st.download_button("📥 Download .SDC File", sdc_output, file_name=sdc_file_name)

            st.subheader("📝 Generated .SDC Content")
            st.code(sdc_output, language="tcl")

        except Exception as e:
            st.error(f"⚠ Error: {e}")