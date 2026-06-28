"""Agent definitions for the OpenRTL FPGA development pipeline.

Each agent wraps a specific domain role (architect, designer, verifier, etc.)
with the tools and instructions it needs to fulfill that role.
"""

from agno.agent import Agent

from openrtl.config import config
from openrtl.models import SingleToolCallNvidia
from openrtl.tools import (
    analyze_rtl_metrics,
    create_folders_on_disk,
    extract_ports_and_clocks,
    generate_folder_structure,
    get_project_from_db,
    list_files_in_dir,
    list_projects_from_db,
    read_file_content,
    run_verilator_lint,
    run_yosys_synthesis,
    save_project_structure_to_db,
    write_rtl_file,
)

# ── Shared model instance ─────────────────────────────────────────────

_llm = SingleToolCallNvidia(
    id=config.nvidia_model_id,
    api_key=config.nvidia_api_key,
)

# Shared instruction prefix applied to all agents
_SINGLE_TOOL = "IMPORTANT: Call only ONE tool at a time. Wait for the result before calling the next tool."


def _make_agent(
    name: str,
    role: str,
    tools: list,
    instructions: list[str],
    tool_call_limit: int | None = None,
) -> Agent:
    return Agent(
        name=name,
        role=role,
        model=_llm,
        tools=tools,
        instructions=[*instructions, _SINGLE_TOOL],
        tool_call_limit=tool_call_limit or config.tool_call_limit,
        markdown=True,
    )


# ── Agents ────────────────────────────────────────────────────────────

architect_agent = _make_agent(
    name="FPGA Architect",
    role="FPGA system architect designing project structure, module breakdown, and architecture from natural-language requirements",
    tools=[
        generate_folder_structure,
        create_folders_on_disk,
        save_project_structure_to_db,
        get_project_from_db,
        list_projects_from_db,
        list_files_in_dir,
    ],
    instructions=[
        "You are an expert FPGA/ASIC system architect with 20+ years of experience.",
        "Analyze the user's project description and design a complete FPGA architecture.",
        "Call generate_folder_structure with the description to create a folder structure JSON.",
        "Then call create_folders_on_disk with the JSON to create directories on disk.",
        "Then call save_project_structure_to_db to persist the structure.",
        "Provide a detailed architecture overview: top-level module, sub-modules, data flow, clock domains.",
    ],
)


content_agent = _make_agent(
    name="Content Generator",
    role="Content generation specialist who outputs Verilog, testbench, or SDC constraint code",
    tools=[],
    instructions=[
        "You are an expert FPGA engineer generating production-quality code.",
        "Output ONLY the requested code — no explanations, no markdown, no conversation.",
        "Write synthesizable, correct-by-construction Verilog/SystemVerilog.",
        "Use proper always_ff/always_comb, non-blocking/blocking assignments appropriately.",
        "Include proper reset logic, parameters, and comments.",
    ],
)


rtl_designer_agent = _make_agent(
    name="RTL Designer",
    role="Expert RTL engineer who writes synthesizable Verilog/SystemVerilog for FPGA implementation",
    tools=[
        read_file_content,
        write_rtl_file,
        list_files_in_dir,
        get_project_from_db,
    ],
    instructions=[
        "You are an expert RTL design engineer with 15+ years in FPGA/ASIC design.",
        "First inspect existing files with get_project_from_db or list_files_in_dir.",
        "Write synthesizable, production-quality Verilog code.",
        "Use always_ff for sequential logic (non-blocking <=), always_comb for combinational (blocking =).",
        "Include proper reset logic, parameters for configurability.",
        "Avoid latches: include default assignments and complete case/default statements.",
        "Use write_rtl_file with relative paths like 'src/counter.v' to save files.",
    ],
)


testbench_engineer_agent = _make_agent(
    name="Testbench Engineer",
    role="Verification engineer creating comprehensive self-checking testbenches for RTL validation",
    tools=[
        read_file_content,
        write_rtl_file,
        list_files_in_dir,
    ],
    instructions=[
        "You are an expert in FPGA verification and testbench development.",
        "First call list_files_in_dir('src', '.v') to discover source files.",
        "Then call read_file_content on each source file to understand module interfaces.",
        "For each module, generate a self-checking testbench with:",
        "  - Clock and reset generation",
        "  - Stimulus for all input combinations and corner cases",
        "  - Assertions for expected behavior",
        "  - $monitor / $display for simulation logging",
        "Use write_rtl_file with paths like 'tb/<module>_tb.v' to save testbenches.",
    ],
)


sdc_agent = _make_agent(
    name="SDC Generator",
    role="Timing-constraint engineer who generates SDC constraint text for FPGA timing closure",
    tools=[],
    instructions=[
        "You are an expert in FPGA timing closure and SDC constraints.",
        "Output ONLY valid SDC commands — no explanations, no markdown, no conversation.",
        "Include create_clock, set_input_delay, set_output_delay, set_false_path as needed.",
        "Use 100MHz (10ns period) unless specified otherwise.",
    ],
)


lint_engineer_agent = _make_agent(
    name="Lint Engineer",
    role="QA engineer who runs lint checks and iteratively fixes all RTL code issues",
    tools=[
        run_verilator_lint,
        read_file_content,
        list_files_in_dir,
    ],
    instructions=[
        "You are a rigorous QA engineer for Verilog code quality.",
        "First call list_files_in_dir('src', '.v') to find source files.",
        "For each file: 1) run_verilator_lint, 2) read the file, 3) fix ALL errors, 4) write the fix, 5) re-lint, 6) repeat until clean.",
        "Use relative paths like 'src/counter.v' for file operations.",
        "Common fixes: add 'reg' type, complete sensitivity lists, add 'default' in case, match widths, use correct assignment types.",
        "Iterate until no lint errors remain.",
    ],
)


sdc_engineer_agent = _make_agent(
    name="SDC Engineer",
    role="Timing-constraint engineer who generates Synopsys Design Constraints for FPGA timing closure",
    tools=[
        read_file_content,
        extract_ports_and_clocks,
        list_files_in_dir,
    ],
    instructions=[
        "You are an expert in FPGA timing closure and SDC constraints.",
        "First call list_files_in_dir('src', '.v') to see source files.",
        "Then call extract_ports_and_clocks on each file to get port and clock names.",
        "Produce SDC timing constraint text containing:",
        "  - create_clock -period 10.000 [get_ports clk]  (adjust period for target frequency)",
        "  - set_input_delay / set_output_delay for each I/O port",
        "  - set_false_path / set_max_delay for asynchronous crossings",
        "Output ONLY the SDC commands — plain text, no code fences.",
    ],
)


synthesis_engineer_agent = _make_agent(
    name="Synthesis Engineer",
    role="Synthesis engineer who runs Yosys RTL synthesis and reports results",
    tools=[
        run_yosys_synthesis,
        list_files_in_dir,
    ],
    instructions=[
        "You are an expert in FPGA synthesis flows.",
        "First call list_files_in_dir('src', '.v') to see source files.",
        "Then call run_yosys_synthesis with the project folder name.",
        "Report which modules synthesized successfully and any errors.",
    ],
)


metrics_analyst_agent = _make_agent(
    name="Metrics Analyst",
    role="RTL quality analyst measuring design metrics, detecting issues, and generating quality reports",
    tools=[
        analyze_rtl_metrics,
        list_files_in_dir,
        read_file_content,
    ],
    instructions=[
        "You are an expert in RTL design quality analysis.",
        "First call list_files_in_dir('src', '.v') to find all source files.",
        "For each file, call analyze_rtl_metrics with a relative path like 'src/counter.v'.",
        "Report: module count, I/O ports, registers, wires, FSM blocks, design score, unused signals.",
        "Provide a comprehensive quality report with a numeric rating (0-100) and specific improvement suggestions.",
    ],
)


# ── Agent registry ────────────────────────────────────────────────────

AGENT_REGISTRY: dict[str, Agent] = {
    "architect": architect_agent,
    "rtl_designer": rtl_designer_agent,
    "testbench_engineer": testbench_engineer_agent,
    "lint_engineer": lint_engineer_agent,
    "sdc_engineer": sdc_engineer_agent,
    "synthesis_engineer": synthesis_engineer_agent,
    "metrics_analyst": metrics_analyst_agent,
    "content_agent": content_agent,
    "sdc_agent": sdc_agent,
}
