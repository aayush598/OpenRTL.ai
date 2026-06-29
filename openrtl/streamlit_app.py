"""Streamlit frontend for OpenRTL.ai.

Run with:  streamlit run openrtl/streamlit_app.py
"""

import json
import os
from pathlib import Path

import streamlit as st

from openrtl.config import config
from openrtl.pipeline import FPGAPipeline
from openrtl.services.database import DatabaseService
from openrtl.services.filesystem import FileSystemService

st.set_page_config(
    page_title="OpenRTL.ai - FPGA Development Pipeline",
    page_icon="⚡",
    layout="wide",
)


def main():
    st.title("⚡ OpenRTL.ai")
    st.caption("FPGA development pipeline from natural-language descriptions")

    if not config.nvidia_api_key:
        st.error("NVIDIA_API_KEY not set. Add it to your `.env` file.")
        st.code("NVIDIA_API_KEY='nvapi-your-key-here'")
        return

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "▶ Generate Project",
        "📂 Saved Projects",
        "🔍 Lint & Review",
        "🔬 RTL Metrics",
        "🧬 Synthesis",
    ])

    # ── Tab 1: Generate ──────────────────────────────────────────────────

    with tab1:
        st.subheader("Describe Your FPGA Project")

        prompt = st.text_area(
            "Project Description",
            placeholder="e.g. 8-bit UART with configurable baud rate, TX, RX",
            height=120,
            key="gen_prompt",
        )

        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            run_btn = st.button("▶ Generate", type="primary", use_container_width=True)
        with col2:
            show_code = st.checkbox("Show code", value=True)

        if run_btn and prompt.strip():
            with st.spinner("Running FPGA development pipeline..."):
                try:
                    pipeline = FPGAPipeline()
                    result = pipeline.run_all(prompt.strip())
                    st.success(f"Pipeline complete in {result.elapsed:.1f}s")

                    for rel_path, content, size in result.files:
                        if rel_path:
                            full = Path(result.project_path) / rel_path
                            with st.expander(f"📄 {rel_path} ({size} bytes)", expanded=show_code):
                                if full.exists():
                                    code = full.read_text()
                                    lang = (
                                        "verilog" if rel_path.endswith((".v", ".sv"))
                                        else "tcl" if rel_path.endswith(".sdc")
                                        else "plaintext"
                                    )
                                    st.code(code, language=lang)
                                else:
                                    st.info(f"{rel_path} — {size} bytes")

                    if result.errors:
                        st.warning(f"Steps with warnings: {len(result.errors)}")
                        for e in result.errors:
                            st.caption(f"⚠ {e[:200]}")

                except Exception as e:
                    st.error(f"Pipeline failed: {e}")

        elif run_btn:
            st.warning("Enter a project description.")

        with st.expander("💡 Examples"):
            examples = [
                "8-bit counter with enable",
                "UART transmitter with configurable baud rate",
                "PWM generator with configurable duty cycle",
                "SPI master-slave with 4 modes",
                "AXI4-Stream FIFO with configurable depth",
            ]
            for ex in examples:
                if st.button(f"  {ex}", use_container_width=True, key=f"ex_{ex}"):
                    st.session_state["gen_prompt"] = ex
                    st.rerun()

    # ── Tab 2: Saved Projects ────────────────────────────────────────────

    with tab2:
        st.subheader("Saved Projects")
        db = DatabaseService()
        projects = db.list_projects()
        if projects:
            selected = st.selectbox("Select a project", projects, key="proj_select")
            if selected:
                data = db.get_project(selected)
                if data:
                    st.json(data)
                proj_path = config.projects_dir / selected
                if proj_path.exists():
                    st.markdown("**Generated files:**")
                    for f in sorted(proj_path.rglob("*")):
                        if f.is_file():
                            rel = f.relative_to(proj_path)
                            st.write(f"📄 `{rel}` ({f.stat().st_size} bytes)")
                            if st.button(f"View {rel}", key=f"view_{rel}"):
                                st.code(f.read_text(), language="verilog" if f.suffix in (".v", ".sv") else "plaintext")
        else:
            st.info("No projects found. Generate one in the Generate tab.")

    # ── Tab 3: Lint ──────────────────────────────────────────────────────

    with tab3:
        st.subheader("Verilator Lint")
        fs = FileSystemService()
        lint_path = st.text_input("File path (relative to projects dir, or absolute)", key="lint_path")

        if st.button("🔍 Run Lint", use_container_width=True) and lint_path:
            try:
                out = fs.run_verilator_lint(lint_path)
                if out:
                    st.error("Lint issues found:")
                    st.code(out, language="plaintext")
                else:
                    st.success("No lint errors!")
            except Exception as e:
                st.info(str(e))

    # ── Tab 4: Metrics ───────────────────────────────────────────────────

    with tab4:
        st.subheader("RTL Metrics Analysis")
        fs = FileSystemService()
        metrics_path = st.text_input("File path (relative to projects dir, or absolute)", key="metrics_path")

        if st.button("📊 Analyze", use_container_width=True) and metrics_path:
            try:
                code = fs.read_file(metrics_path)
                st.markdown(f"**File:** {metrics_path} ({len(code)} chars, {code.count(chr(10)) + 1} lines)")
                result = fs.analyze_metrics(metrics_path)
                if "error" in result:
                    st.info(result["error"])
                else:
                    m = result["metrics"]
                    cols = st.columns(4)
                    cols[0].metric("Modules", m["modules"])
                    cols[1].metric("Inputs", m["inputs"])
                    cols[2].metric("Outputs", m["outputs"])
                    cols[3].metric("Design Score", m["design_score"])
                    cols2 = st.columns(4)
                    cols2[0].metric("Wires", m["wires"])
                    cols2[1].metric("Regs", m["regs"])
                    cols2[2].metric("FSM Blocks", m["fsm_blocks"])
                    cols2[3].metric("Always Blocks", m["always_blocks"])
                    if m.get("unused_signals"):
                        st.warning(f"Unused: {', '.join(m['unused_signals'])}")
                    else:
                        st.success("No unused signals")
                    if result.get("module_hierarchy"):
                        with st.expander("Module Hierarchy"):
                            st.json(result["module_hierarchy"])
            except Exception as e:
                st.info(str(e))

    # ── Tab 5: Synthesis ─────────────────────────────────────────────────

    with tab5:
        st.subheader("Yosys Synthesis")
        fs = FileSystemService()
        synth_proj = st.text_input("Project name", key="synth_proj", placeholder="e.g. 8_bit_counter")

        if st.button("🧬 Run Synthesis", use_container_width=True) and synth_proj:
            try:
                result = fs.run_yosys_synthesis(synth_proj)
                success = result.get("success_files", [])
                errors = result.get("error_logs", {})
                if success:
                    st.success(f"Synthesized {len(success)} modules")
                    for img in success:
                        if Path(img).exists():
                            st.image(img, caption=Path(img).stem)
                if errors:
                    for fname, err in errors.items():
                        st.code(f"{fname}: {err[:300]}")
            except Exception as e:
                st.info(str(e))


if __name__ == "__main__":
    main()
