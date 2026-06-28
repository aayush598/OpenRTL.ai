"""Tool definitions for LLM agent use.

Each tool is a plain function with a docstring that serves as the LLM's
description of the tool's purpose and parameters.

Tools delegate to service层的 actual implementations,
keeping agent-contract documentation clean and consistent.
"""

import json
from typing import Any

from openrtl.exceptions import (
    ExternalToolError,
    FileSystemError,
    ToolExecutionError,
)
from openrtl.logging import get_logger
from openrtl.services.database import DatabaseService
from openrtl.services.filesystem import FileSystemService

log = get_logger("tools")

_db = DatabaseService()
_fs = FileSystemService()


# ── Project structure tools ──────────────────────────────────────────


def generate_folder_structure(project_description: str) -> str:
    """Generate a hierarchical folder structure for an RTL/FPGA project.

    Args:
        project_description: Natural language description of the FPGA project.

    Returns:
        JSON string with project_name, directories list, and metadata.
    """
    try:
        structure = _fs.generate_structure(project_description)
        log.info("Generated structure for: %s", structure["project_name"])
        return json.dumps(structure, indent=2)
    except Exception as e:
        log.error("generate_folder_structure failed: %s", e)
        return json.dumps({"error": str(e)})


def create_folders_on_disk(folder_structure_json: str) -> str:
    """Create project directories on disk from a JSON folder structure.

    Args:
        folder_structure_json: JSON string from generate_folder_structure.

    Returns:
        Absolute path to the created project directory.
    """
    try:
        data = json.loads(folder_structure_json)
        path = _fs.create_directories(data)
        project_name = data.get("project_name", "fpga_project")
        _db.save_project(project_name, data)
        log.info("Created project at: %s", path)
        return str(path)
    except (json.JSONDecodeError, KeyError) as e:
        return f"Error: {e}"


# ── File I/O tools ───────────────────────────────────────────────────


def write_rtl_file(file_path: str, content: str) -> str:
    """Write RTL code to a file on disk.

    Use relative paths like 'src/counter.v' — they resolve inside the
    projects directory. Absolute paths are used as-is.

    Args:
        file_path: Path to the file (relative or absolute).
        content: File content (markdown code fences are stripped automatically).

    Returns:
        Confirmation message with the absolute path written to.
    """
    try:
        full = _fs.write_file(file_path, content)
        return f"Written to {full}"
    except (FileSystemError, Exception) as e:
        log.error("write_rtl_file failed: %s", e)
        return f"Error: {e}"


def read_file_content(file_path: str) -> str:
    """Read the content of a file from disk.

    Args:
        file_path: Path relative to projects directory, or absolute path.

    Returns:
        Full file content as a string.
    """
    try:
        return _fs.read_file(file_path)
    except FileSystemError as e:
        return f"Error: {e}"


def list_files_in_dir(directory: str, extension: str | None = None) -> str:
    """List files in a directory, optionally filtered by extension.

    Args:
        directory: Directory path (relative to projects dir, or absolute).
        extension: Optional filter like '.v', '.sv', '.sdc'.

    Returns:
        Comma-separated list of filenames, or a message if none found.
    """
    try:
        files = _fs.list_files(directory, extension=extension)
        return ", ".join(files) if files else "No files found"
    except FileSystemError as e:
        return str(e)


# ── Lint / synthesis tools ───────────────────────────────────────────


def run_verilator_lint(file_path: str) -> str:
    """Run Verilator linting on a Verilog/SystemVerilog file.

    Args:
        file_path: Path to a .v or .sv file (relative to projects dir).

    Returns:
        Lint output (stderr). Empty string if no errors.
    """
    try:
        return _fs.run_verilator_lint(file_path)
    except (ExternalToolError, FileSystemError) as e:
        return str(e)


def run_yosys_synthesis(project_name: str) -> str:
    """Run Yosys RTL synthesis on all Verilog files in the project.

    Args:
        project_name: Name of the project folder under projects/.

    Returns:
        JSON with "success_files" list and "error_logs" dict.
    """
    try:
        result = _fs.run_yosys_synthesis(project_name)
        return json.dumps(result, indent=2)
    except (ExternalToolError, Exception) as e:
        return json.dumps({"success_files": [], "error_logs": {"error": str(e)}})


# ── Analysis tools ───────────────────────────────────────────────────


def analyze_rtl_metrics(file_path: str) -> str:
    """Analyze RTL quality metrics of a Verilog file via pyverilog.

    Returns module count, I/O ports, signals, FSM blocks, design score,
    unused signals, and module hierarchy.

    Args:
        file_path: Path to a .v file (relative to projects dir).

    Returns:
        JSON with "metrics" dict and "module_hierarchy" dict.
    """
    try:
        result = _fs.analyze_metrics(file_path)
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


def extract_ports_and_clocks(file_path: str) -> str:
    """Extract port names and clock signals from a Verilog file.

    Args:
        file_path: Path to a .v file (relative to projects dir).

    Returns:
        JSON with "ports" list and "clocks" list.
    """
    try:
        result = _fs.extract_ports_and_clocks(file_path)
        return json.dumps(result, indent=2)
    except (FileSystemError, Exception) as e:
        return json.dumps({"error": str(e)})


# ── Database tools ───────────────────────────────────────────────────


def save_project_structure_to_db(project_name: str, structure_json: str) -> str:
    """Save a project's folder structure to the database.

    Args:
        project_name: Unique project name.
        structure_json: JSON string of the folder structure.

    Returns:
        Confirmation message.
    """
    try:
        data = json.loads(structure_json)
        _db.save_project(project_name, data)
        return f"Project '{project_name}' saved to database"
    except (json.JSONDecodeError, Exception) as e:
        return f"Error: {e}"


def get_project_from_db(project_name: str) -> str:
    """Retrieve a project's folder structure from the database.

    Args:
        project_name: Name of the project.

    Returns:
        JSON string of the folder structure, or "{}" if not found.
    """
    try:
        data = _db.get_project(project_name)
        return json.dumps(data, indent=2) if data else "{}"
    except Exception as e:
        return json.dumps({"error": str(e)})


def list_projects_from_db() -> str:
    """List all project names stored in the database.

    Returns:
        Comma-separated list of project names, or a message if none.
    """
    try:
        projects = _db.list_projects()
        return ", ".join(projects) if projects else "No projects found"
    except Exception as e:
        return f"Error: {e}"


# ── Tool registry ────────────────────────────────────────────────────

TOOL_REGISTRY: dict[str, Any] = {
    "generate_folder_structure": generate_folder_structure,
    "create_folders_on_disk": create_folders_on_disk,
    "write_rtl_file": write_rtl_file,
    "read_file_content": read_file_content,
    "list_files_in_dir": list_files_in_dir,
    "run_verilator_lint": run_verilator_lint,
    "run_yosys_synthesis": run_yosys_synthesis,
    "analyze_rtl_metrics": analyze_rtl_metrics,
    "extract_ports_and_clocks": extract_ports_and_clocks,
    "save_project_structure_to_db": save_project_structure_to_db,
    "get_project_from_db": get_project_from_db,
    "list_projects_from_db": list_projects_from_db,
}
