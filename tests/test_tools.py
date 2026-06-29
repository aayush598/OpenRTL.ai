"""Unit tests for tool layer — no API key required."""

import json
import shutil
from pathlib import Path

import pytest

from openrtl.tools import (
    TOOL_REGISTRY,
    create_folders_on_disk,
    extract_ports_and_clocks,
    generate_folder_structure,
    get_project_from_db,
    list_files_in_dir,
    list_projects_from_db,
    read_file_content,
    save_project_structure_to_db,
    write_rtl_file,
)


class TestToolRegistry:
    def test_all_tools_registered(self):
        expected = {
            "generate_folder_structure",
            "create_folders_on_disk",
            "write_rtl_file",
            "read_file_content",
            "list_files_in_dir",
            "run_verilator_lint",
            "run_yosys_synthesis",
            "analyze_rtl_metrics",
            "extract_ports_and_clocks",
            "save_project_structure_to_db",
            "get_project_from_db",
            "list_projects_from_db",
        }
        assert set(TOOL_REGISTRY.keys()) == expected

    def test_tools_are_callable(self):
        for name, tool in TOOL_REGISTRY.items():
            assert callable(tool), f"{name} is not callable"


class TestProjectTools:
    def test_generate_folder_structure_returns_json(self):
        result = generate_folder_structure("uart transmitter")
        data = json.loads(result)
        assert data["project_name"] == "uart_transmitter"

    def test_create_folders_roundtrip(self, tmp_path, monkeypatch):
        monkeypatch.setattr("openrtl.tools._fs._projects_dir", tmp_path / "projects")
        monkeypatch.setattr("openrtl.tools._db._db_path", str(tmp_path / "test.db"))

        struct = generate_folder_structure("test design")
        path = create_folders_on_disk(struct)
        assert Path(path).exists()

        proj = json.loads(struct)["project_name"]
        p = get_project_from_db(proj)
        assert json.loads(p)["project_name"] == proj

        lp = list_projects_from_db()
        assert proj in lp

    def test_write_rtl_file_relative(self, tmp_path, monkeypatch):
        monkeypatch.setattr("openrtl.tools._fs._projects_dir", tmp_path / "projects")
        result = write_rtl_file("test_mod/src/top.v", "module top; endmodule")
        assert "Written to" in result
        assert (tmp_path / "projects" / "test_mod" / "src" / "top.v").exists()

    def test_write_rtl_file_strips_fences(self, tmp_path, monkeypatch):
        monkeypatch.setattr("openrtl.tools._fs._projects_dir", tmp_path / "projects")
        write_rtl_file("test_mod/src/top.v", "```\nmodule top; endmodule\n```")
        content = (tmp_path / "projects" / "test_mod" / "src" / "top.v").read_text()
        assert "```" not in content


class TestFileTools:
    def test_read_file_content(self, tmp_path, monkeypatch):
        monkeypatch.setattr("openrtl.tools._fs._projects_dir", tmp_path / "projects")
        write_rtl_file("proj/src/test.v", "hello world")
        content = read_file_content("proj/src/test.v")
        assert content == "hello world"

    def test_list_files_filter(self, tmp_path, monkeypatch):
        monkeypatch.setattr("openrtl.tools._fs._projects_dir", tmp_path / "projects")
        write_rtl_file("proj/src/a.v", "")
        write_rtl_file("proj/src/b.sv", "")
        result = list_files_in_dir("proj/src", ".v")
        assert "a.v" in result
        assert "b.sv" not in result


class TestPortExtraction:
    def test_extract_ports(self, tmp_path, monkeypatch):
        monkeypatch.setattr("openrtl.tools._fs._projects_dir", tmp_path / "projects")
        code = """module counter (
    input wire clk,
    input wire rst_n,
    output reg [7:0] count
); endmodule"""
        write_rtl_file("proj/src/counter.v", code)
        result = json.loads(extract_ports_and_clocks("proj/src/counter.v"))
        assert set(result["ports"]) == {"clk", "rst_n", "count"}


class TestErrorHandling:
    def test_generate_empty(self):
        result = generate_folder_structure("")
        data = json.loads(result)
        assert data["project_name"] == "fpga_project"

    def test_create_folders_invalid_json(self):
        result = create_folders_on_disk("not json")
        assert "Error" in result

    def test_read_missing_file(self):
        result = read_file_content("nonexistent/file.v")
        assert "Error" in result or "not found" in result

    def test_list_missing_dir(self):
        result = list_files_in_dir("nonexistent_dir")
        assert "not found" in result or "Error" in result
