"""
JARVIS 2.0 — Extensible Plugin SDK & Tool Registry.
Enables third-party and custom plugin capability registration with explicit permission scopes,
lifecycle hooks, and automated schema generation.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
import logging
from typing import Any, Callable

logger = logging.getLogger("jarvis.plugins")


class PermissionScope(str, Enum):
    READ = "READ"
    WRITE = "WRITE"
    DELETE = "DELETE"
    EXTERNAL_NETWORK = "EXTERNAL_NETWORK"
    SYSTEM_COMMAND = "SYSTEM_COMMAND"
    FINANCIAL = "FINANCIAL"


@dataclass
class PluginToolDefinition:
    name: str
    description: str
    parameters_schema: dict[str, Any]
    handler: Callable[..., Any]
    required_permissions: list[PermissionScope] = field(default_factory=lambda: [PermissionScope.READ])
    is_high_impact: bool = False


class JARVISPlugin(ABC):
    """Base abstract class for all JARVIS 2.0 Plugins."""

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def version(self) -> str:
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        pass

    @abstractmethod
    def get_tools(self) -> list[PluginToolDefinition]:
        """Return list of tools exposed by this plugin."""
        pass

    def on_init(self) -> None:
        """Lifecycle hook executed upon plugin registration."""
        pass

    def on_shutdown(self) -> None:
        """Lifecycle hook executed upon system shutdown."""
        pass


class PluginRegistry:
    """Central registry managing loaded plugins and their tool bindings."""

    _instance: "PluginRegistry | None" = None

    def __init__(self) -> None:
        self._plugins: dict[str, JARVISPlugin] = {}
        self._tools: dict[str, PluginToolDefinition] = {}

    @classmethod
    def get_instance(cls) -> "PluginRegistry":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def register_plugin(self, plugin: JARVISPlugin) -> None:
        self._plugins[plugin.name] = plugin
        plugin.on_init()

        for tool_def in plugin.get_tools():
            self._tools[tool_def.name] = tool_def
            logger.info("PluginRegistry: Registered tool '%s' from plugin '%s'", tool_def.name, plugin.name)

    def list_plugins(self) -> list[dict[str, Any]]:
        return [
            {
                "name": p.name,
                "version": p.version,
                "description": p.description,
                "toolCount": len(p.get_tools()),
            }
            for p in self._plugins.values()
        ]

    def get_tool(self, tool_name: str) -> PluginToolDefinition | None:
        return self._tools.get(tool_name)

    def execute_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        tool_def = self.get_tool(tool_name)
        if not tool_def:
            raise KeyError(f"Tool '{tool_name}' is not registered in PluginRegistry.")
        return tool_def.handler(**arguments)


# Built-in Core System Plugin Example
class SystemInfoPlugin(JARVISPlugin):
    name = "system_info_plugin"
    version = "2.0.0"
    description = "Provides OS diagnostics, memory, CPU, and disk metrics."

    def get_tools(self) -> list[PluginToolDefinition]:
        from app.services.tools.system_info import get_system_diagnostics

        return [
            PluginToolDefinition(
                name="get_system_diagnostics",
                description="Retrieve current system CPU, RAM, and disk utilization.",
                parameters_schema={"type": "object", "properties": {}},
                handler=get_system_diagnostics,
                required_permissions=[PermissionScope.READ],
                is_high_impact=False,
            )
        ]


# Initialize default registry
plugin_registry = PluginRegistry.get_instance()
plugin_registry.register_plugin(SystemInfoPlugin())
