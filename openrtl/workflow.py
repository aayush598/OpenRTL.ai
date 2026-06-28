from agno.workflow import Workflow
from agno.workflow.step import Step
from agno.workflow.types import OnReject
from agno.db.sqlite import SqliteDb

from openrtl.config import config
from openrtl.agents import (
    architect_agent,
    rtl_designer_agent,
    testbench_engineer_agent,
    lint_engineer_agent,
    sdc_engineer_agent,
    synthesis_engineer_agent,
    metrics_analyst_agent,
)

_db = SqliteDb(db_file=str(config.db_path))

fpga_workflow = Workflow(
    name="FPGA Complete Development Pipeline",
    description="End-to-end FPGA development workflow: architecture, RTL design, verification, linting, constraints, synthesis, and quality analysis",
    db=_db,
    steps=[
        Step(
            name="architecture_design",
            agent=architect_agent,
            description="Design the FPGA architecture and generate folder structure. "
                        "Call generate_folder_structure then create_folders_on_disk then save_project_structure_to_db. "
                        "Provide the full architecture overview.",
            requires_confirmation=True,
            confirmation_message="Approve the proposed FPGA architecture to proceed with RTL design.",
            on_reject=OnReject.cancel,
        ),
        Step(
            name="rtl_code_generation",
            agent=rtl_designer_agent,
            description="Generate 8-bit counter Verilog code. "
                        "List files in src/, read existing project structure, "
                        "then write the counter module using write_rtl_file with path 'src/counter.v'. "
                        "The module must have clk, rst_n, enable inputs and an 8-bit count output.",
            requires_confirmation=True,
            confirmation_message="Approve the generated RTL code to proceed with testbenches.",
            on_reject=OnReject.cancel,
        ),
        Step(
            name="testbench_generation",
            agent=testbench_engineer_agent,
            description="Create testbench for the 8-bit counter. "
                        "List src/ files, read counter.v to see its interface, "
                        "then write testbench to 'tb/counter_tb.v'.",
            requires_confirmation=True,
            confirmation_message="Approve testbench coverage to proceed with linting.",
            on_reject=OnReject.skip,
        ),
        Step(
            name="linting_and_fix",
            agent=lint_engineer_agent,
            description="Run lint on src/counter.v and fix all errors. "
                        "If verilator is not installed, just report what would need fixing.",
            requires_confirmation=True,
            confirmation_message="Approve lint results to proceed with SDC generation.",
            on_reject=OnReject.skip,
        ),
        Step(
            name="sdc_generation",
            agent=sdc_engineer_agent,
            description="Generate SDC constraints. "
                        "Extract ports from src/counter.v, then create SDC text with "
                        "create_clock/set_input_delay/set_output_delay and save with save_sdc_file.",
            requires_confirmation=True,
            confirmation_message="Approve SDC constraints to proceed with synthesis.",
            on_reject=OnReject.skip,
        ),
        Step(
            name="synthesis",
            agent=synthesis_engineer_agent,
            description="Run Yosys synthesis. List src/ files then call run_yosys_synthesis.",
            requires_confirmation=True,
            confirmation_message="Approve synthesis results.",
            on_reject=OnReject.skip,
        ),
        Step(
            name="quality_analysis",
            agent=metrics_analyst_agent,
            description="Analyze src/counter.v metrics and generate quality report.",
            requires_confirmation=False,
            on_reject=OnReject.skip,
        ),
    ],
    debug_mode=False,
)


def run_fpga_workflow(prompt: str) -> str:
    run_output = fpga_workflow.run(prompt)

    if run_output.is_paused:
        for req in run_output.steps_requiring_confirmation:
            print(f"\n=== PAUSED: {req.step_name} ===")
            print(f"Message: {req.confirmation_message}")
            response = input("Approve? (y/n): ").strip().lower()
            if response == "y":
                req.confirm()
            else:
                req.reject()
        run_output = fpga_workflow.continue_run(run_output)

    return run_output.content if hasattr(run_output, "content") else str(run_output)
