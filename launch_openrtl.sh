#!/bin/bash
# OpenRTL.ai Launch Script
# Usage: ./launch_openrtl.sh [--cli|--streamlit|--help]

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

source .venv/bin/activate 2>/dev/null || source .venv/Scripts/activate 2>/dev/null

if [ ! -f .env ]; then
    echo "Creating .env file - please add your NVIDIA_API_KEY"
    echo "# NVIDIA API Key (required)" > .env
    echo "NVIDIA_API_KEY=" >> .env
    echo "# OpenRTL Model ID (optional, default: meta/llama-3.2-1b-instruct)" >> .env
    echo "# Recommended: meta/llama-3.1-8b-instruct for better quality" >> .env
    echo "OPENRTL_MODEL_ID=meta/llama-3.1-8b-instruct" >> .env
fi

case "${1:-}" in
    --cli|-c)
        shift
        python -m openrtl.main --pipeline "$@"
        ;;
    --streamlit|-s)
        echo "Streamlit not installed. Run: pip install streamlit && streamlit run openrtl/streamlit_app.py"
        ;;
    --help|-h)
        echo "OpenRTL.ai - AI-powered FPGA Development Agent"
        echo ""
        echo "Usage:"
        echo "  ./launch_openrtl.sh --cli '<description>'   Run full FPGA development pipeline"
        echo "  ./launch_openrtl.sh --list-projects           List saved projects"
        echo "  ./launch_openrtl.sh --get-project <name>     Get project details"
        echo ""
        echo "Examples:"
        echo "  ./launch_openrtl.sh --cli '8-bit counter with enable'"
        echo "  ./launch_openrtl.sh --cli 'UART with TX and RX'"
        echo "  ./launch_openrtl.sh --list-projects"
        echo "  ./launch_openrtl.sh --get-project counter_with"
        ;;
    --list-projects)
        python -m openrtl.main --list-projects
        ;;
    --get-project)
        shift
        python -m openrtl.main --get-project "$1"
        ;;
    *)
        echo "OpenRTL.ai v2.0"
        echo "Usage: ./launch_openrtl.sh --cli '<project description>'"
        echo "       ./launch_openrtl.sh --list-projects"
        echo "       ./launch_openrtl.sh --get-project <name>"
        ;;
esac
