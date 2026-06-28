import json
import os
import re
import subprocess
from pathlib import Path

from openrtl.config import config
from openrtl.exceptions import ExternalToolError, FileSystemError
from openrtl.logging import get_logger

log = get_logger("filesystem")


class FileSystemService:
    """File and directory operations for FPGA projects."""

    def __init__(self, projects_dir: str | Path | None = None) -> None:
        self._projects_dir = Path(projects_dir or config.projects_dir)

    def _resolve(self, path: str | Path) -> Path:
        p = Path(path)
        return p if p.is_absolute() else (self._projects_dir / p).resolve()

    # ── Project structure ──────────────────────────────────────────────

    def generate_structure(self, description: str) -> dict:
        words = re.findall(r"[a-zA-Z0-9_]+", description.strip().lower()) if description else []
        project_name = "_".join(words[:3]) if words else "fpga_project"

        return {
            "project_name": project_name,
            "directories": [
                {"name": "src", "files": [], "subdirectories": []},
                {"name": "tb", "files": [], "subdirectories": []},
                {"name": "constraints", "files": [], "subdirectories": []},
                {"name": "scripts", "files": [], "subdirectories": []},
                {"name": "docs", "files": [], "subdirectories": []},
                {"name": "results", "files": [], "subdirectories": []},
            ],
            "metadata": {"generated_by": "OpenRTL", "version": "3.0"},
        }

    def create_directories(self, structure: dict) -> Path:
        project_name = structure.get("project_name", "fpga_project")
        project_path = self._projects_dir / project_name
        project_path.mkdir(parents=True, exist_ok=True)
        for entry in structure.get("directories", []):
            (project_path / entry["name"]).mkdir(parents=True, exist_ok=True)
        return project_path

    # ── File I/O ───────────────────────────────────────────────────────

    def write_file(self, path: str | Path, content: str) -> Path:
        full = self._resolve(path)
        full.parent.mkdir(parents=True, exist_ok=True)
        clean = re.sub(r"```[\w]*\n?|```", "", content).strip()
        try:
            full.write_text(clean)
            log.info("Wrote %s (%d chars)", full, len(clean))
            return full
        except OSError as e:
            raise FileSystemError(f"Failed to write {full}: {e}") from e

    def read_file(self, path: str | Path) -> str:
        full = self._resolve(path)
        if not full.exists():
            raise FileSystemError(f"File not found: {full}")
        try:
            return full.read_text()
        except OSError as e:
            raise FileSystemError(f"Failed to read {full}: {e}") from e

    def list_files(self, directory: str | Path, extension: str | None = None) -> list[str]:
        full = self._resolve(directory)
        if not full.is_dir():
            raise FileSystemError(f"Directory not found: {full}")
        files = os.listdir(str(full))
        if extension:
            files = [f for f in files if f.endswith(extension)]
        return sorted(files)

    # ── External tools ─────────────────────────────────────────────────

    def run_verilator_lint(self, path: str | Path) -> str:
        full = self._resolve(path)
        if not full.exists():
            raise FileSystemError(f"File not found: {full}")
        try:
            result = subprocess.run(
                ["verilator", "--lint-only", str(full)],
                capture_output=True, text=True, timeout=30,
            )
            return result.stderr.strip()
        except FileNotFoundError:
            raise ExternalToolError("verilator not installed. Install with: sudo apt install verilator")
        except subprocess.TimeoutExpired:
            raise ExternalToolError("Lint timed out")

    def run_yosys_synthesis(self, project_name: str) -> dict:
        src_dir = self._projects_dir / project_name / "src"
        out_dir = self._projects_dir / project_name / "results"
        out_dir.mkdir(parents=True, exist_ok=True)

        if not src_dir.is_dir():
            return {"success_files": [], "error_logs": {"error": f"src folder not found: {src_dir}"}}

        verilog_files = sorted(src_dir.rglob("*.v")) + sorted(src_dir.rglob("*.sv"))

        if not verilog_files:
            return {"success_files": [], "error_logs": {"warning": "No Verilog files found"}}

        success: list[str] = []
        errors: dict[str, str] = {}

        for vfile in verilog_files:
            base = vfile.stem
            json_out = out_dir / f"{base}.json"
            svg_out = out_dir / f"{base}.svg"
            script = out_dir / f"synth_{base}.ys"

            script.write_text(f"read_verilog {vfile}\nsynth -top {base}\nwrite_json {json_out}\n")

            try:
                result = subprocess.run(
                    ["yosys", "-s", str(script)],
                    capture_output=True, text=True, timeout=config.synthesis_timeout,
                )
            except FileNotFoundError:
                raise ExternalToolError("yosys not installed. Install with: sudo apt install yosys")

            if result.returncode != 0:
                errors[base] = result.stderr
                continue

            try:
                netlist = subprocess.run(
                    ["netlistsvg", str(json_out), "-o", str(svg_out)],
                    capture_output=True, text=True,
                )
                if netlist.returncode == 0:
                    success.append(str(svg_out))
                else:
                    errors[base] = netlist.stderr
            except FileNotFoundError:
                errors[base] = "netlistsvg not installed"

        return {"success_files": success, "error_logs": errors}

    # ── RTL analysis ───────────────────────────────────────────────────

    def extract_ports_and_clocks(self, path: str | Path) -> dict:
        code = self.read_file(path)
        ports: set[str] = set()
        clocks: set[str] = set()

        for match in re.finditer(
            r"(input|output|inout)\s+(\[.*?\]\s+)?([a-zA-Z_][a-zA-Z0-9_]*)",
            code,
        ):
            ports.add(match.group(3))

        for match in re.finditer(r"(?:input|wire|reg)\s+.*?(clk|clock)\b", code, re.IGNORECASE):
            clocks.add(match.group(1))

        return {"ports": sorted(ports), "clocks": sorted(clocks)}

    def analyze_metrics(self, path: str | Path) -> dict:
        full = self._resolve(path)
        if not full.exists():
            return {"error": f"File not found: {full}"}

        try:
            from pyverilog.vparser.ast import (
                Always, CaseStatement, Decl, Input, InstanceList,
                Ioport, ModuleDef, Output, Reg, Wire, Identifier,
            )
            from pyverilog.vparser.parser import parse as pyv_parse
        except ImportError:
            return {"error": "pyverilog not installed. Install with: pip install pyverilog"}

        metrics = {
            "modules": 0, "inputs": 0, "outputs": 0,
            "wires": 0, "regs": 0, "fsm_blocks": 0,
            "always_blocks": 0, "design_score": 0,
            "signal_widths": {}, "unused_signals": [],
            "fan_in_out": {},
        }
        hierarchy: dict[str, list[str]] = {}
        declared: set[str] = set()
        usage: dict[str, int] = {}
        current_module: str | None = None

        def width(node):
            if hasattr(node, "width") and node.width:
                msb = int(node.width.msb.value)
                lsb = int(node.width.lsb.value)
                return abs(msb - lsb) + 1
            return 1

        def is_fsm(node):
            if isinstance(node, Always):
                for stmt in (node.statement.statements if hasattr(node.statement, "statements") else []):
                    if isinstance(stmt, CaseStatement):
                        return True
            return False

        def walk(node, mod=None):
            nonlocal current_module
            if isinstance(node, ModuleDef):
                metrics["modules"] += 1
                current_module = node.name
                hierarchy[current_module] = []
                if node.portlist:
                    for port in node.portlist.ports:
                        if isinstance(port, Ioport):
                            first = port.first
                            w = width(first)
                            if isinstance(first, Input):
                                metrics["inputs"] += 1
                                metrics["signal_widths"][first.name] = w
                                declared.add(first.name)
                            elif isinstance(first, Output):
                                metrics["outputs"] += 1
                                metrics["signal_widths"][first.name] = w
                                declared.add(first.name)
                for item in node.items:
                    walk(item, current_module)
            elif isinstance(node, Decl):
                for decl in node.list:
                    w = width(decl)
                    metrics["signal_widths"][decl.name] = w
                    declared.add(decl.name)
                    if isinstance(decl, Input): metrics["inputs"] += 1
                    elif isinstance(decl, Output): metrics["outputs"] += 1
                    elif isinstance(decl, Wire): metrics["wires"] += 1
                    elif isinstance(decl, Reg): metrics["regs"] += 1
            elif isinstance(node, InstanceList):
                for inst in node.instances:
                    if current_module:
                        hierarchy.setdefault(current_module, []).append(inst.module)
            elif isinstance(node, Always):
                metrics["always_blocks"] += 1
                if is_fsm(node):
                    metrics["fsm_blocks"] += 1
            elif isinstance(node, Identifier):
                usage[node.name] = usage.get(node.name, 0) + 1
            if hasattr(node, "children"):
                for child in node.children():
                    walk(child, mod)

        ast, _ = pyv_parse([str(full)])
        walk(ast)

        metrics["design_score"] = (
            metrics["modules"] * 10 + metrics["inputs"] * 2 + metrics["outputs"] * 2
            + metrics["wires"] * 1 + metrics["regs"] * 2 + metrics["fsm_blocks"] * 5
            + metrics["always_blocks"] * 3
        )
        metrics["unused_signals"] = [s for s in declared if usage.get(s, 0) < 1]

        # Cleanup parser artifacts
        for f in ["parser.out", "parsetab.py", "parsetab.pyc"]:
            Path(f).unlink(missing_ok=True)

        return {"metrics": metrics, "module_hierarchy": hierarchy}
