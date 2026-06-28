"""FPGA development pipeline orchestrator.

Hybrid architecture:
  - Deterministic operations (folder creation, file I/O, system commands)
    run directly in Python via service classes.
  - Content generation (RTL code, testbenches, constraints, analysis)
    is delegated to LLM agents.
  - The orchestrator handles fallback templates, error recovery,
    and result collation.
"""

import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path

from openrtl.agents import (
    content_agent,
    lint_engineer_agent,
    metrics_analyst_agent,
    sdc_agent,
)
from openrtl.config import config

from openrtl.logging import get_logger
from openrtl.services.database import DatabaseService
from openrtl.services.filesystem import FileSystemService

log = get_logger("pipeline")


# ── Fallback templates ────────────────────────────────────────────────

_COUNTER_RTL = """\
module counter (
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

_COUNTER_TB = """\
module counter_tb;
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

_DEFAULT_SDC = """\
create_clock -period 10.000 -name clk [get_ports clk]
set_input_delay -clock clk 2.0 [get_ports enable]
set_output_delay -clock clk 2.0 [get_ports count]"""


# ── Helpers ───────────────────────────────────────────────────────────

def _extract_code(text: str, lang: str | None = None) -> str:
    """Strip markdown code fences and optional language tag."""
    text = text.strip()
    if lang:
        pattern = rf"```{lang}\n?(.*?)```"
    else:
        pattern = r"```\w*\n?(.*?)```"
    match = re.search(pattern, text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text


def _extract_first_code_block(text: str) -> str | None:
    """Return the content of the first ```...``` block, or None."""
    match = re.search(r"```[\w]*\n(.+?)```", text, re.DOTALL)
    return match.group(1).strip() if match else None


def _step_label(n: int, total: int, label: str) -> str:
    sep = "=" * 60
    return f"\n{sep}\n  STEP {n}/{total}: {label}\n{sep}"


# ── Pipeline result ───────────────────────────────────────────────────

@dataclass
class PipelineResult:
    project_name: str = ""
    project_path: str = ""
    elapsed: float = 0.0
    files: list[tuple[str, str, int]] = field(default_factory=list)
    artifacts: dict[str, str] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

    def add_file(self, rel_path: str, content: str) -> None:
        self.files.append((rel_path, content, len(content)))

    @property
    def summary(self) -> str:
        lines = [
            f"  Project: {self.project_name}",
            f"  Location: {self.project_path}",
            f"  Duration: {self.elapsed:.1f}s",
            f"  Files generated: {len(self.files)}",
        ]
        if self.errors:
            lines.append(f"  Errors: {len(self.errors)}")
        return "\n".join(lines)


# ── Pipeline ──────────────────────────────────────────────────────────

class FPGAPipeline:
    """Orchestrates the full FPGA development pipeline.

    Steps are individually callable for fine-grained control;
    ``run_all()`` executes them in sequence.
    """

    STEPS = 7  # total step count for display

    def __init__(self) -> None:
        config.validate()
        self._fs = FileSystemService()
        self._db = DatabaseService()
        self._result = PipelineResult()

    # ── Step 1: Project structure ───────────────────────────────────

    def step_project_structure(self, description: str) -> str:
        log.info("Step 1/%d: project structure", self.STEPS)
        structure = self._fs.generate_structure(description)
        proj_name = structure["project_name"]
        proj_path = self._fs.create_directories(structure)
        self._db.save_project(proj_name, structure)

        self._result.project_name = proj_name
        self._result.project_path = str(proj_path)
        self._result.artifacts["structure"] = json.dumps(structure)

        log.info("Project '%s' created at %s", proj_name, proj_path)
        return proj_name

    # ── Step 2: RTL code ───────────────────────────────────────────

    def step_rtl_code(self, project_name: str) -> str:
        log.info("Step 2/%d: RTL code generation", self.STEPS)

        prompt = (
            "Generate Verilog code for an 8-bit counter named 'counter'. "
            "Ports: clk (input), rst_n (input, active-low), enable (input), "
            "count (output reg [7:0]). "
            "Use always_ff @(posedge clk or negedge rst_n) with "
            "active-low reset and enable-gated increment. "
            "Output ONLY the Verilog code, no explanations."
        )

        response = content_agent.run(prompt)
        code = getattr(response, "content", str(response))
        code = _extract_first_code_block(code) or code.strip()

        if not code.startswith("module"):
            log.warning("Model did not produce valid Verilog; using fallback template")
            code = _COUNTER_RTL

        path = self._fs.write_file(f"{project_name}/src/counter.v", code)
        self._result.add_file("src/counter.v", code)
        return str(path)

    # ── Step 3: Testbench ──────────────────────────────────────────

    def step_testbench(self, project_name: str) -> str:
        log.info("Step 3/%d: testbench generation", self.STEPS)
        src_path = f"{project_name}/src/counter.v"
        src_code = self._fs.read_file(src_path)

        prompt = (
            f"Generate a self-checking SystemVerilog testbench for this module:\n"
            f"{src_code}\n\n"
            f"Test: reset, enable counting, hold when disabled. "
            f"Use $monitor and $display. Output ONLY the code."
        )

        response = content_agent.run(prompt)
        code = getattr(response, "content", str(response))
        code = _extract_first_code_block(code) or code.strip()

        if not code.startswith("module") and not code.startswith("//"):
            log.warning("Model did not produce valid testbench; using fallback template")
            code = _COUNTER_TB

        path = self._fs.write_file(f"{project_name}/tb/counter_tb.v", code)
        self._result.add_file("tb/counter_tb.v", code)
        return str(path)

    # ── Step 4: Lint ───────────────────────────────────────────────

    def step_lint(self, project_name: str) -> str:
        log.info("Step 4/%d: lint", self.STEPS)
        src_path = f"{project_name}/src/counter.v"
        src_code = self._fs.read_file(src_path)

        try:
            lint_out = self._fs.run_verilator_lint(src_path)
            result = f"Lint output: {lint_out[:500]}"
        except Exception as e:
            result = str(e)
            response = lint_engineer_agent.run(
                f"Review this Verilog code for issues:\n{src_code}\n"
                f"List any bugs, style issues, or potential problems."
            )
            result += f"\nReview: {getattr(response, 'content', str(response))[:300]}"

        self._result.artifacts["lint"] = result
        return result

    # ── Step 5: SDC constraints ────────────────────────────────────

    def step_sdc(self, project_name: str) -> str:
        log.info("Step 5/%d: SDC constraints", self.STEPS)
        src_path = f"{project_name}/src/counter.v"
        ports_info = self._fs.extract_ports_and_clocks(src_path)

        prompt = (
            f"Generate SDC timing constraints for a 100MHz design. "
            f"Ports: {json.dumps(ports_info)}\n"
            f"Output ONLY the SDC commands (create_clock, set_input_delay, set_output_delay)."
        )

        response = sdc_agent.run(prompt)
        sdc = getattr(response, "content", str(response))
        sdc = _extract_first_code_block(sdc) or sdc.strip()

        if not sdc.startswith("create_clock") and not sdc.startswith("#"):
            log.warning("Model did not produce valid SDC; using fallback template")
            sdc = _DEFAULT_SDC

        path = self._fs.write_file(f"{project_name}/constraints/{project_name}.sdc", sdc)
        self._result.add_file(f"constraints/{project_name}.sdc", sdc)
        return str(path)

    # ── Step 6: Synthesis ──────────────────────────────────────────

    def step_synthesis(self, project_name: str) -> str:
        log.info("Step 6/%d: synthesis", self.STEPS)
        try:
            result = self._fs.run_yosys_synthesis(project_name)
            summary = json.dumps(result, indent=2)[:500]
        except Exception as e:
            summary = str(e)
        self._result.artifacts["synthesis"] = summary
        return summary

    # ── Step 7: Quality metrics ────────────────────────────────────

    def step_metrics(self, project_name: str) -> str:
        log.info("Step 7/%d: RTL quality analysis", self.STEPS)
        src_path = f"{project_name}/src/counter.v"

        metrics_json = self._fs.analyze_metrics(src_path)
        response = metrics_analyst_agent.run(
            f"Analyze these RTL metrics and provide a quality report:\n"
            f"{json.dumps(metrics_json, indent=2)}\n"
            f"Rate the design quality (0-100) and suggest improvements."
        )

        report = getattr(response, "content", str(response))
        self._result.artifacts["metrics"] = report
        return report[:500]

    # ── File listing ───────────────────────────────────────────────

    def _list_generated_files(self) -> list[str]:
        proj = self._result.project_name
        project_path = Path(self._result.project_path)
        files: list[str] = []
        for f in sorted(project_path.rglob("*")):
            if f.is_file():
                rel = f.relative_to(project_path)
                self._result.files.append((str(rel), "", f.stat().st_size))
                files.append(f"    {rel} ({f.stat().st_size} bytes)")
        return files

    # ── Full pipeline ──────────────────────────────────────────────

    def run_all(self, description: str) -> PipelineResult:
        log.info("Starting full pipeline for: %s", description)
        start = time.time()

        steps = [
            ("Project structure", lambda: self.step_project_structure(description)),
            ("RTL code", lambda: self.step_rtl_code(self._result.project_name)),
            ("Testbench", lambda: self.step_testbench(self._result.project_name)),
            ("Lint", lambda: self.step_lint(self._result.project_name)),
            ("SDC constraints", lambda: self.step_sdc(self._result.project_name)),
            ("Synthesis", lambda: self.step_synthesis(self._result.project_name)),
            ("Quality metrics", lambda: self.step_metrics(self._result.project_name)),
        ]

        for i, (label, fn) in enumerate(steps, 1):
            print(_step_label(i, self.STEPS, label))
            try:
                out = fn()
                first_line = out.split("\n")[0] if out else "(no output)"
                print(f"  {first_line[:120]}")
            except Exception as e:
                msg = f"Step {i} ({label}) failed: {e}"
                log.error(msg)
                self._result.errors.append(msg)
                print(f"  ERROR: {msg}")

        # Final listing
        print(_step_label(self.STEPS, self.STEPS, "Generated files"))
        for line in self._list_generated_files():
            print(line)

        self._result.elapsed = time.time() - start
        print(f"\n{'=' * 60}")
        print(f"  PIPELINE COMPLETE ({self._result.elapsed:.1f}s)")
        print(f"{'=' * 60}")
        print(self._result.summary)

        return self._result
