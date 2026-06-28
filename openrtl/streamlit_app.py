import streamlit as st
import json

st.set_page_config(
    page_title="OpenRTL.ai - AI FPGA Development Agent",
    page_icon="",
    layout="wide",
)

from openrtl.config import config
from openrtl.team import fpga_team, run_fpga_team
from openrtl.knowledge import initialize_fpga_knowledge
from openrtl.tools import (
    list_projects_from_db,
    get_project_from_db,
    run_verilator_lint,
    analyze_rtl_metrics,
    run_yosys_synthesis,
    read_file_content,
)


def main():
    st.title("OpenRTL.ai - AI FPGA Development Agent")

    if not config.nvidia_api_key:
        st.error("NVIDIA_API_KEY environment variable not set.")
        st.info("Set it in your environment or create a .env file:")
        st.code("NVIDIA_API_KEY='your-key-here'")
        return

    initialize_fpga_knowledge()

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        " Develop FPGA Project",
        " Lint & Fix",
        " Synthesis",
        " RTL Metrics",
        " Projects",
    ])

    with tab1:
        col1, col2 = st.columns([2, 1])

        with col1:
            st.subheader("Describe Your FPGA Project")
            prompt = st.text_area(
                "Project Description",
                placeholder="e.g., Design a UART module with 8-bit data width, configurable baud rate, with transmitter and receiver. Include a testbench, SDC constraints, and run synthesis.",
                height=150,
            )

            use_workflow = st.checkbox("Enable step-by-step workflow with human review", value=False)

            if st.button(" Generate Project", type="primary", use_container_width=True):
                if prompt.strip():
                    with st.spinner("AI agents are designing your FPGA project..."):
                        try:
                            if use_workflow:
                                from openrtl.workflow import fpga_workflow
                                run_output = fpga_workflow.run(prompt)
                                if run_output.is_paused:
                                    st.warning("Workflow paused for human review.")
                                    for req in run_output.steps_requiring_confirmation:
                                        with st.expander(f"Review: {req.step_name}", expanded=True):
                                            msg = req.confirmation_message or "Approve this step?"
                                            st.info(msg)
                                    stopped = st.warning("Workflow paused. Use CLI for interactive approval.")
                                    st.json(run_output.model_dump() if hasattr(run_output, "model_dump") else {})
                                else:
                                    content = run_output.content if hasattr(run_output, "content") else str(run_output)
                                    st.markdown(content)
                            else:
                                fpga_team.print_response(prompt, stream=True)
                        except Exception as e:
                            st.error(f"Error: {e}")
                else:
                    st.warning("Please enter a project description.")

        with col2:
            st.subheader("Quick Examples")
            examples = [
                "Design an 8-bit UART with configurable baud rate, TX, RX, and status registers. Include testbench.",
                "Create a FIFO with configurable depth and data width, with full/empty flags.",
                "Generate a SPI master-slave system with 4 modes and configurable clock divider.",
                "Design a 32-bit RISC-V CPU with 5-stage pipeline, hazard detection, and forwarding.",
                "Create a PWM generator with configurable duty cycle and frequency.",
                "Design an AXI4-Stream FIFO with configurable depth.",
            ]
            for ex in examples:
                if st.button(f"  {ex[:60]}...", use_container_width=True):
                    st.session_state["prompt"] = ex
                    st.rerun()

    with tab2:
        st.subheader(" Run Verilator Lint & Auto-Fix")
        col1, col2 = st.columns([3, 1])
        with col1:
            lint_path = st.text_input("Verilog File Path", key="lint_path")
        with col2:
            st.markdown("### ")
            if st.button(" Run Lint", use_container_width=True):
                if lint_path:
                    result = run_verilator_lint(lint_path)
                    if result:
                        st.error("Lint Errors Found:")
                        st.code(result, language="plaintext")
                        from openrtl.agents import lint_engineer_agent
                        with st.spinner("AI fixing errors..."):
                            try:
                                code = read_file_content(lint_path)
                                fix_prompt = f"Fix the following Verilog file at {lint_path}. Current lint errors:\n\n{result}\n\nCurrent code:\n\n{code}"
                                lint_engineer_agent.print_response(fix_prompt, stream=True)
                            except Exception as e:
                                st.error(f"Fix failed: {e}")
                    else:
                        st.success("No lint errors found!")
                else:
                    st.warning("Enter a file path.")

    with tab3:
        st.subheader(" Run Yosys Synthesis")
        col1, col2 = st.columns([2, 1])
        with col1:
            synth_src = st.text_input("Source Directory", placeholder="/path/to/project/src", key="synth_dir")
            synth_name = st.text_input("Project Name", placeholder="my_project", key="synth_name")
        with col2:
            st.markdown("### ")
            if st.button(" Run Synthesis", use_container_width=True):
                if synth_src and synth_name:
                    with st.spinner("Running Yosys synthesis..."):
                        result = json.loads(run_yosys_synthesis(synth_src, synth_name))
                        success = result.get("success_files", [])
                        errors = result.get("error_logs", {})
                        if success:
                            st.success(f"Synthesized {len(success)} modules")
                            for img in success:
                                if Path(img).exists():
                                    st.image(img, caption=Path(img).stem)
                        if errors:
                            st.error("Errors:")
                            for fname, err in errors.items():
                                st.code(f"{fname}: {err[:200]}")
                else:
                    st.warning("Enter source directory and project name.")

    with tab4:
        st.subheader(" Analyze RTL Metrics")
        metrics_path = st.text_input("Verilog File Path", key="metrics_path")
        if st.button(" Analyze", use_container_width=True):
            if metrics_path:
                with st.spinner("Analyzing RTL metrics..."):
                    result = json.loads(analyze_rtl_metrics(metrics_path))
                    if "error" in result:
                        st.error(result["error"])
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
                            st.warning(f"Unused Signals: {', '.join(m['unused_signals'])}")
                        else:
                            st.success("No unused signals")
                        if result.get("module_hierarchy"):
                            st.subheader("Module Hierarchy")
                            st.json(result["module_hierarchy"])
            else:
                st.warning("Enter a file path.")

    with tab5:
        st.subheader(" Saved FPGA Projects")
        projects = list_projects_from_db()
        if projects and projects != "No projects found":
            proj_list = [p.strip() for p in projects.split(",")]
            selected = st.selectbox("Select Project", proj_list)
            if selected:
                data = get_project_from_db(selected)
                try:
                    st.json(json.loads(data))
                except json.JSONDecodeError:
                    st.code(data)
        else:
            st.info("No saved projects found. Generate one in the Develop tab.")


if __name__ == "__main__":
    main()
