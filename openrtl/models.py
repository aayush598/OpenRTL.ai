from typing import Any, ClassVar

from pydantic import BaseModel, Field

from agno.models.nvidia import Nvidia
from agno.models.response import ModelResponse


class SingleToolCallNvidia(Nvidia):
    """Nvidia model wrapper that limits tool calls to one per response.

    The meta/llama-3.1-8b-instruct model only supports a single tool call
    per assistant turn. This wrapper keeps only the first tool call when
    the model returns multiple.
    """

    retries: int = 3
    delay_between_retries: int = 2
    exponential_backoff: bool = True

    def _parse_provider_response(
        self,
        response: Any,
        response_format: type[BaseModel] | None = None,
    ) -> ModelResponse:
        mr = super()._parse_provider_response(response, response_format=response_format)
        if mr.tool_calls and len(mr.tool_calls) > 1:
            mr.tool_calls = mr.tool_calls[:1]
        return mr


class FolderStructure(BaseModel):
    project_name: str
    directories: list[dict]
    metadata: dict = Field(
        default_factory=lambda: {"generated_by": "OpenRTL", "version": "3.0"}
    )


class RTLModule(BaseModel):
    module_name: str
    file_path: str
    code: str
    language: str = "verilog"


class LintResult(BaseModel):
    file_path: str
    errors: str
    is_clean: bool
    iterations_used: int = 0


class SynthesisResult(BaseModel):
    success_files: list[str]
    error_logs: dict[str, str]


class MetricsResult(BaseModel):
    modules: int = 0
    inputs: int = 0
    outputs: int = 0
    wires: int = 0
    regs: int = 0
    fsm_blocks: int = 0
    always_blocks: int = 0
    design_score: int = 0
    unused_signals: list[str] = []
    module_hierarchy: dict[str, list[str]] = {}
    signal_widths: dict[str, int] = {}


class FPGAProjectPlan(BaseModel):
    project_name: str
    description: str
    architecture_overview: str
    modules: list[dict]
    clock_speed_mhz: int = 100
    target_device: str = "generic"
