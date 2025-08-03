"""Tool templates for creating custom tool_templates.

These templates provide patterns and base structures for creating tool_templates
that handle common scenarios like authentication, environment setup,
and integration patterns.
"""

from .base import (
    ToolTemplate,
    DockerToolTemplate,
    AuthenticatedToolTemplate,
    CLIToolTemplate,
    DataProcessingToolTemplate,
)

__all__ = [
    "ToolTemplate",
    "DockerToolTemplate",
    "AuthenticatedToolTemplate",
    "CLIToolTemplate",
    "DataProcessingToolTemplate",
]
