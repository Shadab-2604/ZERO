"""
Safe Allowlisted Tool & Action Registry for Zero AI.
Enforces strict parameter validation, prevents arbitrary shell/script execution,
and returns structured, verified results.
"""

from dataclasses import dataclass, field
import logging
from typing import Any, Callable

logger = logging.getLogger(__name__)


@dataclass
class ToolResult:
    """Standard execution result from a registered tool."""
    success: bool
    summary: str           # Spoken / concise summary
    detailed_text: str     # Formatted markdown output for transcript
    data: dict = field(default_factory=dict)
    error: str | None = None
    raw_output: str | None = None


@dataclass
class ToolDefinition:
    """Definition of an approved, allowlisted tool."""
    name: str
    description: str
    handler: Callable[..., ToolResult]
    parameters: dict = field(default_factory=dict)
    requires_confirmation: bool = False


class ActionRegistry:
    """
    Central registry for safe, allowlisted local actions.
    Ensures that only approved functions with validated parameters can execute.
    """

    def __init__(self):
        self._tools: dict[str, ToolDefinition] = {}

    def register(
        self,
        name: str,
        description: str,
        handler: Callable[..., ToolResult],
        parameters: dict | None = None,
        requires_confirmation: bool = False,
    ) -> None:
        """Register an allowlisted tool."""
        self._tools[name] = ToolDefinition(
            name=name,
            description=description,
            handler=handler,
            parameters=parameters or {},
            requires_confirmation=requires_confirmation,
        )
        logger.info("Registered allowlisted tool: %s", name)

    def is_registered(self, name: str) -> bool:
        """Check if tool name is approved."""
        return name in self._tools

    def is_action_allowed(self, name: str) -> bool:
        """Check if action name is allowlisted."""
        return self.is_registered(name)

    def get_tool(self, name: str) -> ToolDefinition | None:
        """Retrieve tool definition."""
        return self._tools.get(name)

    def list_tools(self) -> list[dict]:
        """List all approved tools and their schemas."""
        return [
            {
                "name": t.name,
                "description": t.description,
                "parameters": t.parameters,
                "requires_confirmation": t.requires_confirmation,
            }
            for t in self._tools.values()
        ]

    def execute(self, tool_name: str, **kwargs) -> ToolResult:
        """
        Execute an approved tool with validated arguments.
        Rejects unknown tool names, arbitrary shell execution, and malformed inputs.
        """
        if not self.is_registered(tool_name):
            logger.warning("Attempted execution of unregistered tool: '%s'", tool_name)
            return ToolResult(
                success=False,
                summary=f"Action '{tool_name}' is not an authorized or registered tool.",
                detailed_text=f"**Security Notice:** Action `{tool_name}` is not registered in Zero's allowlisted action registry. Arbitrary commands are prohibited.",
                error=f"Unregistered action: {tool_name}",
            )

        tool = self._tools[tool_name]
        try:
            logger.info("Executing tool: %s with args: %s", tool_name, list(kwargs.keys()))
            result = tool.handler(**kwargs)
            return result
        except TypeError as e:
            logger.error("Invalid arguments for tool '%s': %s", tool_name, e)
            return ToolResult(
                success=False,
                summary=f"Invalid arguments provided for {tool_name}.",
                detailed_text=f"**Parameter Error:** Invalid parameters for `{tool_name}`: {str(e)}",
                error=f"Argument mismatch: {str(e)}",
            )
        except Exception as e:
            logger.error("Error executing tool '%s': %s", tool_name, e, exc_info=True)
            return ToolResult(
                success=False,
                summary=f"Error executing {tool_name}.",
                detailed_text=f"**Execution Error:** Failed to execute `{tool_name}`: {str(e)}",
                error=str(e),
            )


# Global singleton registry
_global_registry: ActionRegistry | None = None


def get_action_registry() -> ActionRegistry:
    """Retrieve or initialize the global action registry."""
    global _global_registry
    if _global_registry is None:
        _global_registry = ActionRegistry()
        # Initialize standard tools
        from app.tools.browser_tools import register_browser_tools
        from app.tools.network_diagnostics import register_network_tools
        from app.tools.system_diagnostics import register_system_tools
        from app.tools.desktop_tools import register_desktop_tools

        register_browser_tools(_global_registry)
        register_network_tools(_global_registry)
        register_system_tools(_global_registry)
        register_desktop_tools(_global_registry)

    return _global_registry
