import streamlit as st

def homepage_ui():
    st.title("🛠️ RTL Project Manager Dashboard")
    
    st.markdown("""
    <style>
    .big-font {
        font-size:20px !important;
    }
    .section-title {
        font-size:24px !important;
        font-weight: bold;
        color: #4A90E2;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<p class="big-font">Welcome to the <strong>RTL Project Manager</strong> — your complete solution for managing RTL (Register Transfer Level) design projects with efficiency, automation, and AI-powered tools.</p>', unsafe_allow_html=True)
    
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/e/e1/RTL_Design.svg/1024px-RTL_Design.svg.png", use_column_width=True, caption="RTL Design Workflow")

    st.markdown('<p class="section-title">🚀 Platform Highlights</p>', unsafe_allow_html=True)
    st.markdown("""
    - 📁 **Folder Structure Generator**  
      Define your RTL project in simple natural language and let the system generate a complete folder structure tailored to your needs.
    
    - 🗂️ **Folder Setup Assistant**  
      Automatically create physical folders for your RTL design based on the logical structure you've defined.

    - 🧠 **Verilog Code Generator**  
      Translate project descriptions into Verilog code using AI — ideal for accelerating initial development phases.

    - 🔍 **Linting Tool**  
      Catch syntax issues, coding violations, and ensure your RTL code follows best practices.

    - 🧪 **Synthesis Engine**  
      Run synthesis on your Verilog code to validate designs and review successful and failed compilations.

    - 📊 **RTL Metrics Analyzer**  
      Visualize module hierarchy, detect deep nesting, and evaluate RTL code complexity.

    - 🤖 **AI-Powered Error Fixer**  
      Automatically fix Verilog errors using large language models. Just paste your code and fix with one click.

    - 💻 **Built-in IDE Environment**  
      Experience a web-based RTL development environment tailored for productivity and clarity.

    - 📐 **Constraint File Generator (AI)**  
      Use natural language prompts to generate `.sdc` constraint files needed for FPGA synthesis.
    """)

    st.markdown('<p class="section-title">🔧 Getting Started</p>', unsafe_allow_html=True)
    st.markdown("""
    - Use the **navigation sidebar** to access different modules.
    - Start with **Folder Structure Generation** to define your project.
    - Proceed step-by-step: Setup → Code Generation → Linting → Synthesis → Analysis.
    - Optional tools like AI Error Fixer and Constraint Generator can be used any time.

    > 💡 *Pro Tip:* Keep your Verilog files organized in their respective folders and regularly run synthesis/linting for clean and robust designs.
    """)

    st.markdown('<p class="section-title">👨‍💻 About This Project</p>', unsafe_allow_html=True)
    st.markdown("""
    - 🧑‍💻 **Developer**: Aayush Gid  
    - 📅 **Internship Start Date**: February 15, 2025  
    - 🛠 **Technologies Used**: Python, Streamlit, Gemini AI API, Verilog, RTL Synthesis Tools  
    - 📁 **Modules**: 9 interconnected tools for complete RTL project lifecycle management  
    """)

    st.info("👉 Get started by selecting a tool from the left sidebar!")

    st.markdown("---")
    st.caption("© 2025 RTL Project Manager · Made with ❤️ by Aayush Gid")
