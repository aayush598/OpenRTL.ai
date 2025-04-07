import os
import platform

def launch_streamlit():
    app_file = "app.py"

    os.system(f"streamlit run {app_file}")

if __name__ == "__main__":
    print("🚀 Launching RTL Project Manager UI...")
    launch_streamlit()
