class OpenRTLError(Exception):
    """Base exception for all OpenRTL errors."""


class ConfigError(OpenRTLError):
    """Configuration is missing or invalid."""


class DatabaseError(OpenRTLError):
    """Database operation failed."""


class FileSystemError(OpenRTLError):
    """File or directory operation failed."""


class ToolExecutionError(OpenRTLError):
    """An LLM tool execution failed."""


class AgentError(OpenRTLError):
    """An agent run failed."""


class PipelineError(OpenRTLError):
    """Pipeline step failed."""


class ToolNotFoundError(OpenRTLError):
    """Requested tool is not registered."""


class ExternalToolError(OpenRTLError):
    """An external system tool (yosys, verilator) is not available or failed."""
