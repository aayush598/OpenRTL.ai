import streamlit as st
from utils.homepage import homepage_ui

st.set_page_config(page_title="RTL Project Manager", layout="wide")

# ---- Custom CSS Styling with Larger Font ----
st.markdown("""
    <style>
    .main {
        background-color: #f9f9f9;
    }
    .stTabs [data-baseweb="tab-list"] {
        justify-content: space-around;
        margin-top: 15px;
        margin-bottom: 25px;
        border-bottom: 2px solid #ddd;
    }
    .stTabs [data-baseweb="tab"] {
        font-size: 22px !important;
        padding: 12px 20px;
        margin-right: 10px;
        color: #333;
    }
    .stTabs [aria-selected="true"] {
        border-bottom: 4px solid #007bff;
        color: #007bff;
        font-weight: 700;
    }
    </style>
""", unsafe_allow_html=True)

# ---- Optional Top Banner ----
st.markdown("""
    <div style="text-align: center; padding: 10px 0; background-color: #007bff; color: white; border-radius: 10px;">
        <h2>OpenRTL.ai 🚀</h2>
        <p style="margin-top: -10px;">Design · Analyze · Synthesize · Automate</p>
    </div>
""", unsafe_allow_html=True)

# ---- Enhanced Tabs ----
tabs = st.tabs([
    "🏠 Home",
    "📁 Folder Structure",
    "🗂️ Folder Setup",
    "🧠 Code Generation",
    "🔍 Linting",
    "🧪 Synthesis",
    "📊 RTL Metrics",
    "🤖 AI Error Fixer",
    "💻 IDE",
    "📐 Constraint Generator"
])

with tabs[0]:
    st.header("🏠 Home")
    homepage_ui()