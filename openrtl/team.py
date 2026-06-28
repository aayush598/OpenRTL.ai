from agno.team import Team
from agno.team.mode import TeamMode
from agno.db.sqlite import SqliteDb

from openrtl.config import config
from openrtl.models import SingleToolCallNvidia
from openrtl.agents import (
    architect_agent,
    rtl_designer_agent,
    testbench_engineer_agent,
    lint_engineer_agent,
    sdc_engineer_agent,
    synthesis_engineer_agent,
    metrics_analyst_agent,
)
from openrtl.tools import list_projects_from_db, get_project_from_db

_model = SingleToolCallNvidia(
    id=config.nvidia_model_id,
    api_key=config.nvidia_api_key,
)

_db = SqliteDb(db_file=str(config.db_path))

fpga_team = Team(
    name="OpenRTL.ai FPGA Development Team",
    mode=TeamMode.coordinate,
    model=_model,
    members=[
        architect_agent,
        rtl_designer_agent,
        testbench_engineer_agent,
        lint_engineer_agent,
        sdc_engineer_agent,
        synthesis_engineer_agent,
        metrics_analyst_agent,
    ],
    instructions=[
        "You are the lead project manager for a professional FPGA development team.",
        "Your team consists of specialized engineers who handle different aspects of FPGA design.",
        "For each user request, follow this process:",
        "1. UNDERSTAND: Analyze the user's requirements carefully.",
        "2. ARCHITECT: Delegate to the FPGA Architect to design the system architecture and folder structure.",
        "3. DESIGN RTL: Delegate to the RTL Designer to generate all Verilog/SystemVerilog code.",
        "4. VERIFY: Delegate to the Testbench Engineer to create comprehensive testbenches.",
        "5. LINT: Delegate to the Lint Engineer to run linting and fix all errors iteratively.",
        "6. CONSTRAINTS: Delegate to the SDC Engineer to generate timing constraints.",
        "7. SYNTHESIZE: Delegate to the Synthesis Engineer to run Yosys synthesis.",
        "8. ANALYZE: Delegate to the Metrics Analyst for quality analysis.",
        "9. REPORT: Synthesize all results into a comprehensive final report.",
        "Always provide a comprehensive final summary with links to all generated files.",
    ],
    tools=[list_projects_from_db, get_project_from_db],
    db=_db if config.enable_memory else None,
    add_history_to_context=True,
    num_history_runs=3,
    markdown=True,
    debug_mode=False,
)


def run_fpga_team(prompt: str, stream: bool = True):
    if stream:
        fpga_team.print_response(prompt, stream=True)
        return ""
    response = fpga_team.run(prompt)
    return response.content if hasattr(response, "content") else str(response)
