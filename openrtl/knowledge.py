from openrtl.config import config

FPGA_KNOWLEDGE_DOCS = {
    "verilog_coding_standards": """Verilog Coding Standards for Production FPGA Designs:
1. Use always_ff for sequential logic, always_comb for combinational logic
2. Use non-blocking (<=) assignments in sequential always blocks
3. Use blocking (=) assignments in combinational always blocks
4. Always include default assignments to avoid inferred latches
5. Use parameters for configurable module widths and depths
6. Use active-low reset (rst_n) by convention
7. Use case statements with 'default' to avoid latches
8. Register all outputs to break combinational paths
9. Avoid mixed-edge clocking in a single module
10. Limit FSM state encoding: binary for few states, one-hot for many""",

    "sdc_constraints_guide": """SDC Constraint Generation Guide:
1. create_clock - Define all clocks: create_clock -name clk -period 10.0 [get_ports clk]
2. create_generated_clock - For divided clocks from PLLs/MMCMs
3. set_input_delay / set_output_delay - Constrain I/O ports relative to clock
4. set_false_path - Disable timing for async crossings
5. set_multicycle_path - For multi-cycle paths
6. set_clock_uncertainty - Add jitter margin
7. Typical 100MHz clock has 10ns period, use 60-70% for logic""",

    "yosys_synthesis_guide": """Yosys Synthesis Flow:
1. Basic: yosys -s script.ys
2. read_verilog file.v - Read Verilog files
3. synth -top module_name - Set top module and synthesize
4. write_json output.json - Write netlist as JSON
5. netlistsvg input.json -o output.svg - Visualize netlist
6. stat -top module_name - Check statistics
7. Common: hierarchy, proc, opt, memory, fsm, techmap, abc""",

    "verilator_lint_guide": """Verilator Lint Guide:
1. Basic: verilator --lint-only file.v
2. Common errors: WIDTH, CASEINCOMPLETE, BLKSEQ, INCABSP, UNOPTFLAT, UNUSED
3. Fixes: Add 'reg' type, complete sensitivity lists, add 'default' in case,
   match widths, use proper assignment types (blocking vs non-blocking)""",

    "fpga_design_best_practices": """FPGA Design Best Practices:
1. Use dedicated clock resources (BUFG, PLL, MMCM). Never gate clocks internally.
2. Use synchronous resets preferrably.
3. Use double-flop synchronizers for all async inputs.
4. Use vendor-specific FIFO primitives.
5. Infer DSP blocks with proper coding style (pipeline registers).
6. Infer block RAM with synchronous read/write patterns.
7. Add pipeline registers to break long combinational paths.
8. Register all I/O signals at the boundary.
9. Simulate before synthesis, verify after implementation.""",
}


def initialize_fpga_knowledge():
    pass


def get_knowledge_context(topic: str) -> str:
    topic = topic.lower().replace(" ", "_")
    for key in FPGA_KNOWLEDGE_DOCS:
        if topic in key or key in topic:
            return FPGA_KNOWLEDGE_DOCS[key]
    return ""
