"""Tests for the exception hierarchy."""

import pytest

from openrtl.exceptions import (
    AgentError,
    ConfigError,
    DatabaseError,
    ExternalToolError,
    FileSystemError,
    OpenRTLError,
    PipelineError,
    ToolExecutionError,
    ToolNotFoundError,
)


class TestExceptionHierarchy:
    def test_all_are_openrtl_errors(self):
        exceptions = [
            ConfigError(""),
            DatabaseError(""),
            FileSystemError(""),
            ToolExecutionError(""),
            AgentError(""),
            PipelineError(""),
            ToolNotFoundError(""),
            ExternalToolError(""),
        ]
        for exc in exceptions:
            assert isinstance(exc, OpenRTLError)

    def test_custom_messages(self):
        exc = ConfigError("API key missing")
        assert str(exc) == "API key missing"

    def test_exception_can_be_raised_and_caught(self):
        with pytest.raises(OpenRTLError):
            raise DatabaseError("db failure")
