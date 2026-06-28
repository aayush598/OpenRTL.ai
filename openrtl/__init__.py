"""OpenRTL.ai — FPGA development pipeline from natural-language descriptions."""

from openrtl.config import config
from openrtl.pipeline import FPGAPipeline, PipelineResult
from openrtl.cli import main as cli_main
from openrtl.agents import AGENT_REGISTRY
from openrtl.tools import TOOL_REGISTRY

__version__ = "3.0.0"

__all__ = [
    "config",
    "FPGAPipeline",
    "PipelineResult",
    "cli_main",
    "AGENT_REGISTRY",
    "TOOL_REGISTRY",
]
