"""Unit tests for service layer — no API key required."""

import json
import shutil
from pathlib import Path

import pytest

from openrtl.services.database import DatabaseService
from openrtl.services.filesystem import FileSystemService


@pytest.fixture
def fs(tmp_path: Path) -> FileSystemService:
    return FileSystemService(projects_dir=tmp_path / "projects")


@pytest.fixture
def db(tmp_path: Path) -> DatabaseService:
    return DatabaseService(db_path=tmp_path / "test.db")


class TestFileSystemService:
    def test_generate_structure(self, fs: FileSystemService):
        s = fs.generate_structure("8-bit counter with enable")
        assert s["project_name"] == "8_bit_counter"
        dirs = {d["name"] for d in s["directories"]}
        assert dirs == {"src", "tb", "constraints", "scripts", "docs", "results"}

    def test_create_directories(self, fs: FileSystemService):
        s = fs.generate_structure("test project")
        path = fs.create_directories(s)
        assert path.exists()
        assert (path / "src").is_dir()
        assert (path / "tb").is_dir()

    def test_write_and_read_file(self, fs: FileSystemService):
        s = fs.generate_structure("test")
        fs.create_directories(s)
        written = fs.write_file("test/src/counter.v", "module counter;\nendmodule")
        assert written.exists()
        content = fs.read_file("test/src/counter.v")
        assert "module counter" in content

    def test_write_file_strips_code_fences(self, fs: FileSystemService):
        s = fs.generate_structure("test")
        fs.create_directories(s)
        content = "```verilog\nmodule counter;\nendmodule\n```"
        written = fs.write_file("test/src/counter.v", content)
        result = written.read_text()
        assert "```" not in result

    def test_list_files(self, fs: FileSystemService):
        s = fs.generate_structure("test")
        fs.create_directories(s)
        fs.write_file("test/src/top.v", "module top; endmodule")
        fs.write_file("test/src/top.sv", "module top; endmodule")
        all_files = fs.list_files("test/src")
        assert len(all_files) == 2
        v_files = fs.list_files("test/src", ".v")
        assert v_files == ["top.v"]

    def test_list_files_dir_not_found(self, fs: FileSystemService):
        with pytest.raises(Exception):
            fs.list_files("nonexistent")

    def test_read_missing_file(self, fs: FileSystemService):
        with pytest.raises(Exception):
            fs.read_file("no_such_file.v")

    def test_extract_ports_and_clocks(self, fs: FileSystemService):
        s = fs.generate_structure("test")
        fs.create_directories(s)
        code = """module counter (
    input wire clk,
    input wire rst_n,
    input wire enable,
    output reg [7:0] count
);
endmodule"""
        fs.write_file("test/src/counter.v", code)
        result = fs.extract_ports_and_clocks("test/src/counter.v")
        assert "clk" in result["ports"]
        assert "rst_n" in result["ports"]
        assert "enable" in result["ports"]
        assert "count" in result["ports"]

    def test_generate_structure_empty_description(self, fs: FileSystemService):
        s = fs.generate_structure("")
        assert s["project_name"] == "fpga_project"

    def test_generate_structure_special_chars(self, fs: FileSystemService):
        s = fs.generate_structure("   !!! hello   world!!!   ")
        assert s["project_name"] == "hello_world"


class TestDatabaseService:
    def test_save_and_get_project(self, db: DatabaseService):
        structure = {"project_name": "my_proj", "directories": []}
        db.save_project("my_proj", structure)
        result = db.get_project("my_proj")
        assert result is not None
        assert result["project_name"] == "my_proj"

    def test_get_nonexistent(self, db: DatabaseService):
        assert db.get_project("nonexistent") is None

    def test_list_projects(self, db: DatabaseService):
        db.save_project("a", {"project_name": "a"})
        db.save_project("b", {"project_name": "b"})
        projects = db.list_projects()
        assert "a" in projects
        assert "b" in projects

    def test_delete_project(self, db: DatabaseService):
        db.save_project("to_delete", {"project_name": "to_delete"})
        db.delete_project("to_delete")
        assert db.get_project("to_delete") is None

    def test_update_existing(self, db: DatabaseService):
        db.save_project("proj", {"version": 1})
        db.save_project("proj", {"version": 2})
        result = db.get_project("proj")
        assert result["version"] == 2

    def test_list_empty(self, db: DatabaseService):
        assert db.list_projects() == []
