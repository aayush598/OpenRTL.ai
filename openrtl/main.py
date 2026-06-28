import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from openrtl.config import config
from openrtl.tools import (
    generate_folder_structure,
    create_folders_on_disk,
    save_project_structure_to_db,
    get_project_from_db,
    list_projects_from_db,
    write_rtl_file,
    read_file_content,
    run_verilator_lint,
    run_yosys_synthesis,
    analyze_rtl_metrics,
    extract_ports_and_clocks,
    save_sdc_file,
)
from openrtl.agents import (
    rtl_designer_agent,
    testbench_engineer_agent,
    lint_engineer_agent,
    sdc_engineer_agent,
    synthesis_engineer_agent,
    metrics_analyst_agent,
)


def step(n, label):
    print(f"\n{'='*60}")
    print(f"  STEP {n}: {label}")
    print(f"{'='*60}")


def full_pipeline(project_description: str):
    if not config.nvidia_api_key:
        print("ERROR: NVIDIA_API_KEY not set")
        sys.exit(1)

    print(f"OpenRTL.ai - FPGA Development Pipeline")
    print(f"Model: {config.nvidia_model_id}")
    print(f"Description: {project_description}")

    start = time.time()

    # ---- STEP 1: Project setup (Python - deterministic) ----
    step("1/7", "Creating project structure")
    struct = generate_folder_structure(project_description)
    data = json.loads(struct)
    proj = data["project_name"]
    project_path = create_folders_on_disk(struct)
    save_project_structure_to_db(proj, struct)
    print(f"  Project: {proj}")
    print(f"  Location: {project_path}")

    # ---- STEP 2: RTL code generation (AI generates code, Python writes) ----
    step("2/7", "Generating RTL code")
    r = rtl_designer_agent.run(
        f"Generate Verilog code for an 8-bit counter named 'counter'. "
        f"Ports: clk (input), rst_n (input, active-low), enable (input), "
        f"count (output reg [7:0]). "
        f"Use always_ff @(posedge clk or negedge rst_n) with "
        f"active-low reset and enable-gated increment. "
        f"Output ONLY the Verilog code, no explanations."
    )
    rtl_code = r.content if hasattr(r, "content") else str(r)
    rtl_code = rtl_code.strip()
    if "```" in rtl_code:
        rtl_code = rtl_code.split("```")[1]
        if rtl_code.startswith("verilog"):
            rtl_code = rtl_code[7:].strip()
    # Fallback if model didn't generate proper Verilog
    if not rtl_code.startswith("module"):
        print(f"  Model returned non-code output, using default template")
        rtl_code = """module counter (
    input wire clk,
    input wire rst_n,
    input wire enable,
    output reg [7:0] count
);
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            count <= 8'h00;
        else if (enable)
            count <= count + 1'b1;
    end
endmodule"""
    write_rtl_file(f"{proj}/src/counter.v", rtl_code)
    print(f"  Written: src/counter.v ({len(rtl_code)} chars)")

    # ---- STEP 3: Testbench generation (AI generates, Python writes) ----
    step("3/7", "Generating testbench")
    src_content = read_file_content(f"{proj}/src/counter.v")
    r = testbench_engineer_agent.run(
        f"Generate a self-checking SystemVerilog testbench for this module:\n"
        f"{src_content}\n\n"
        f"Test: reset, enable counting, hold when disabled. "
        f"Use $monitor and $display. Output ONLY the code."
    )
    tb_code = r.content if hasattr(r, "content") else str(r)
    tb_code = tb_code.strip()
    if "```" in tb_code:
        tb_code = tb_code.split("```")[1]
        if tb_code.startswith("verilog") or tb_code.startswith("systemverilog"):
            tb_code = tb_code.split("\n", 1)[1] if "\n" in tb_code else tb_code
    tb_code = tb_code.strip()
    # Fallback if model didn't generate proper testbench code
    if not tb_code.startswith("module") and not tb_code.startswith("//"):
        print(f"  Model returned non-code output, using default template")
        tb_code = """module counter_tb;
    reg clk;
    reg rst_n;
    reg enable;
    wire [7:0] count;

    counter uut (
        .clk(clk),
        .rst_n(rst_n),
        .enable(enable),
        .count(count)
    );

    initial begin
        clk = 0;
        forever #5 clk = ~clk;
    end

    initial begin
        $monitor("time=%0t rst_n=%b enable=%b count=%d", $time, rst_n, enable, count);
        rst_n = 0; enable = 0;
        #20 rst_n = 1;
        #10 enable = 1;
        #100 enable = 0;
        #50;
        $display("Test complete. Final count = %d", count);
        $finish;
    end
endmodule"""
    write_rtl_file(f"{proj}/tb/counter_tb.v", tb_code)
    print(f"  Written: tb/counter_tb.v ({len(tb_code)} chars)")

    # ---- STEP 4: Lint (Python runs tool, AI reviews) ----
    step("4/7", "Running lint")
    lint_output = run_verilator_lint(f"{proj}/src/counter.v")
    if "not installed" in lint_output.lower():
        print(f"  {lint_output}")
        r = lint_engineer_agent.run(
            f"Review this Verilog code for issues:\n{src_content}\n"
            f"List any bugs, style issues, or potential problems."
        )
        print(f"  Review: {(r.content if hasattr(r,'content') else str(r))[:300]}")
    else:
        print(f"  Lint output: {lint_output[:300]}")

    # ---- STEP 5: SDC generation (AI generates, Python writes) ----
    step("5/7", "Generating timing constraints")
    ports_info = extract_ports_and_clocks(f"{proj}/src/counter.v")
    r = sdc_engineer_agent.run(
        f"Generate SDC timing constraints for a 100MHz design. "
        f"Ports: {ports_info}\n"
        f"Output ONLY the SDC commands (create_clock, set_input_delay, set_output_delay)."
    )
    sdc_content = r.content if hasattr(r, "content") else str(r)
    sdc_content = sdc_content.strip()
    if "```" in sdc_content:
        sdc_content = sdc_content.split("```")[1]
        if sdc_content.startswith("tcl") or sdc_content.startswith("sdc"):
            sdc_content = sdc_content[3:].strip()
    if not sdc_content.startswith("create_clock") and not sdc_content.startswith("#"):
        print(f"  Model returned non-SDC output, using default template")
        sdc_content = """create_clock -period 10.000 -name clk [get_ports clk]
set_input_delay -clock clk 2.0 [get_ports enable]
set_output_delay -clock clk 2.0 [get_ports count]"""
    save_sdc_file(sdc_content, project_name=proj)
    print(f"  Written: constraints/{proj}.sdc ({len(sdc_content)} chars)")

    # ---- STEP 6: Synthesis (Python runs tool) ----
    step("6/7", "Running synthesis")
    result = run_yosys_synthesis(proj)
    print(f"  {result[:200]}")

    # ---- STEP 7: Quality analysis (AI analyzes) ----
    step("7/7", "Analyzing RTL quality")
    metrics = analyze_rtl_metrics(f"{proj}/src/counter.v")
    r = metrics_analyst_agent.run(
        f"Analyze these RTL metrics and provide a quality report:\n{metrics}\n"
        f"Rate the design quality (0-100) and suggest improvements."
    )
    print(f"  {(r.content if hasattr(r,'content') else str(r))[:400]}")

    # ---- SUMMARY ----
    elapsed = time.time() - start
    print(f"\n{'='*60}")
    print(f"  PIPELINE COMPLETE ({elapsed:.1f}s)")
    print(f"{'='*60}")
    print(f"  Project: {proj}")
    print(f"  Location: {project_path}")
    print(f"\n  Generated files:")
    import glob
    for f in sorted(glob.glob(f"{project_path}/**/*", recursive=True)):
        p = Path(f)
        if p.is_file():
            print(f"    {p.relative_to(project_path)} ({p.stat().st_size} bytes)")

    return proj


def main():
    parser = argparse.ArgumentParser(description="OpenRTL.ai - FPGA Development Pipeline")
    parser.add_argument("prompt", type=str, nargs="?", default="",
                        help="Project description (e.g. '8-bit counter')")
    parser.add_argument("--pipeline", action="store_true",
                        help="Run the full automated FPGA development pipeline")
    parser.add_argument("--list-projects", action="store_true",
                        help="List saved projects")
    parser.add_argument("--get-project", type=str,
                        help="Get project details by name")

    args = parser.parse_args()

    if not config.nvidia_api_key:
        print("ERROR: NVIDIA_API_KEY not set")
        sys.exit(1)

    if args.list_projects:
        print(list_projects_from_db())
        return

    if args.get_project:
        print(get_project_from_db(args.get_project))
        return

    if args.pipeline:
        if not args.prompt:
            parser.print_help()
            sys.exit(1)
        full_pipeline(args.prompt)
        return

    parser.print_help()


if __name__ == "__main__":
    main()
