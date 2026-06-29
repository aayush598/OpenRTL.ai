"""Integration tests for the full pipeline — REQUIRES NVIDIA_API_KEY.

Run all tests:    pytest tests/ -v
Skip slow tests:  pytest tests/ -v -m "not slow"
Only slow tests:  pytest tests/ -v -m slow
"""

import json
import os
import shutil
from pathlib import Path

import pytest

from openrtl.config import config
from openrtl.pipeline import FPGAPipeline

pytestmark = [
    pytest.mark.skipif(
        not os.getenv("NVIDIA_API_KEY"),
        reason="NVIDIA_API_KEY not set",
    ),
    pytest.mark.slow,
]


@pytest.fixture
def pipeline(tmp_path: Path) -> FPGAPipeline:
    original = config.projects_dir
    test_root = tmp_path / "openrtl_test"
    config.projects_dir = test_root
    yield FPGAPipeline()
    config.projects_dir = original
    if test_root.exists():
        shutil.rmtree(test_root)


class TestPipelineIntegration:
    """Full end-to-end pipeline run. Requires NVIDIA API key."""

    def test_full_pipeline_generates_all_files(self, pipeline: FPGAPipeline):
        result = pipeline.run_all("8-bit counter with enable")
        assert result.project_name == "8_bit_counter"
        assert result.project_path
        proj = Path(result.project_path)
        assert (proj / "src" / "counter.v").exists()
        assert (proj / "tb" / "counter_tb.v").exists()
        assert list(proj.rglob("*.sdc"))

    def test_pipeline_result_has_no_errors(self, pipeline: FPGAPipeline):
        result = pipeline.run_all("simple counter")
        pipeline_errors = [
            e for e in result.errors
            if "not installed" not in e.lower()
        ]
        assert not pipeline_errors, f"Pipeline errors: {pipeline_errors}"

    def test_individual_steps(self, pipeline: FPGAPipeline):
        proj = pipeline.step_project_structure("pwm generator")
        assert proj == "pwm_generator"
        rtl = pipeline.step_rtl_code(proj)
        assert Path(rtl).exists()
        tb = pipeline.step_testbench(proj)
        assert Path(tb).exists()
        sdc = pipeline.step_sdc(proj)
        assert Path(sdc).exists()
