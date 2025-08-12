"""Tool Registry for managing both local and MCP tools with runtime objects."""

from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
from enum import Enum
import asyncio
from agno.tools.mcp import MCPTools, MultiMCPTools


class ToolType(Enum):
    LOCAL = "local"
    MCP = "mcp"


@dataclass
class ToolMetadata:
    """Metadata for a registered tool."""
    name: str
    type: ToolType
    server: Optional[str] = None  # MCP server name if applicable
    runtime_factory: Optional[Any] = None  # Factory function to create tool instance
    config: Optional[Dict[str, Any]] = None  # Tool-specific configuration


class ToolRegistry:
    """Central registry for all tools with runtime object management."""
    
    def __init__(self):
        self._tools: Dict[str, ToolMetadata] = {}
        self._mcp_runtime_cache: Dict[str, Any] = {}  # Cache for MCP runtime objects
        self._lock = asyncio.Lock()
    
    def register_local_tool(self, name: str, factory_func: Any, config: Optional[Dict] = None):
        """Register a local tool with its factory function.
        
        Args:
            name: Tool name
            factory_func: Function that creates tool instance
            config: Optional configuration for the tool
        """
        self._tools[name] = ToolMetadata(
            name=name,
            type=ToolType.LOCAL,
            runtime_factory=factory_func,
            config=config or {}
        )
    
    def register_mcp_tool(self, name: str, server: str, config: Optional[Dict] = None):
        """Register an MCP tool.
        
        Args:
            name: Tool name
            server: MCP server name
            config: Optional configuration including command, args, env
        """
        full_name = f"mcp:{server}:{name}" if name else f"mcp:{server}"
        self._tools[full_name] = ToolMetadata(
            name=name or server,
            type=ToolType.MCP,
            server=server,
            config=config or {}
        )
    
    def register_mcp_server_tools(self, server: str, tools: List[str], config: Dict[str, Any]):
        """Register all tools from an MCP server.
        
        Args:
            server: MCP server name
            tools: List of tool names from the server
            config: Server configuration
        """
        for tool in tools:
            self.register_mcp_tool(tool, server, config)
        
        # Also register the server itself for full access
        self.register_mcp_tool(None, server, config)
    
    async def get_tool_runtime(self, tool_ref: str) -> Optional[Any]:
        """Get runtime object for a tool.
        
        Args:
            tool_ref: Tool reference (e.g., "DuckDuckGoTools", "mcp:github", "mcp:github:create_issue")
            
        Returns:
            Tool runtime object or None if not found
        """
        async with self._lock:
            # Handle local tools
            if tool_ref in self._tools and self._tools[tool_ref].type == ToolType.LOCAL:
                metadata = self._tools[tool_ref]
                if metadata.runtime_factory:
                    return metadata.runtime_factory()
                return None
            
            # Handle MCP tools
            if tool_ref.startswith("mcp:"):
                return await self._get_mcp_runtime(tool_ref)
            
            return None
    
    async def _get_mcp_runtime(self, tool_ref: str) -> Optional[Any]:
        """Get or create MCP runtime object.
        
        Args:
            tool_ref: MCP tool reference
            
        Returns:
            MCP runtime object
        """
        # Check cache first
        if tool_ref in self._mcp_runtime_cache:
            return self._mcp_runtime_cache[tool_ref]
        
        # Parse tool reference
        parts = tool_ref.split(":")
        if len(parts) < 2:
            return None
        
        server = parts[1]
        specific_tools = parts[2:] if len(parts) > 2 else None
        
        # Find all tools for this server
        server_tools = []
        server_config = None
        
        for key, metadata in self._tools.items():
            if metadata.type == ToolType.MCP and metadata.server == server:
                if metadata.config:
                    server_config = metadata.config
                if metadata.name:
                    server_tools.append(metadata.name)
        
        if not server_config:
            return None
        
        # Create MCP runtime
        command = server_config.get("command")
        env = server_config.get("env", {})
        
        # Filter tools if specific ones requested
        include_tools = specific_tools if specific_tools else None
        
        mcp_runtime = MCPTools(
            command=command,
            env=env if env else None,
            include_tools=include_tools
        )
        
        # Cache the runtime
        self._mcp_runtime_cache[tool_ref] = mcp_runtime
        
        return mcp_runtime
    
    async def get_tools_for_agent(self, tool_refs: List[str]) -> List[Any]:
        """Get runtime objects for multiple tools.
        
        Args:
            tool_refs: List of tool references
            
        Returns:
            List of tool runtime objects
        """
        tools = []
        mcp_configs = []
        
        for ref in tool_refs:
            if ref.startswith("mcp:"):
                # Collect MCP configs to potentially combine
                mcp_configs.append(ref)
            else:
                # Get local tool immediately
                tool = await self.get_tool_runtime(ref)
                if tool:
                    tools.append(tool)
        
        # Handle MCP tools - combine if multiple servers
        if mcp_configs:
            mcp_tools = await self._get_combined_mcp_runtime(mcp_configs)
            if mcp_tools:
                tools.append(mcp_tools)
        
        return tools
    
    async def _get_combined_mcp_runtime(self, mcp_refs: List[str]) -> Optional[Any]:
        """Create combined MCP runtime for multiple servers.
        
        Args:
            mcp_refs: List of MCP tool references
            
        Returns:
            MCPTools or MultiMCPTools instance
        """
        servers = {}
        all_env = {}
        
        for ref in mcp_refs:
            parts = ref.split(":")
            if len(parts) < 2:
                continue
            
            server = parts[1]
            tools = parts[2].split(",") if len(parts) > 2 else None
            
            # Get server config
            for key, metadata in self._tools.items():
                if metadata.type == ToolType.MCP and metadata.server == server and metadata.config:
                    if server not in servers:
                        servers[server] = {
                            "command": metadata.config.get("command"),
                            "tools": tools
                        }
                        env = metadata.config.get("env", {})
                        all_env.update(env)
                    break
        
        if not servers:
            return None
        
        # Single server
        if len(servers) == 1:
            server_name, server_info = next(iter(servers.items()))
            return MCPTools(
                command=server_info["command"],
                env=all_env if all_env else None,
                include_tools=server_info["tools"]
            )
        
        # Multiple servers
        commands = [info["command"] for info in servers.values()]
        include_tools = []
        for info in servers.values():
            if info["tools"]:
                include_tools.extend(info["tools"])
        
        return MultiMCPTools(
            commands,
            env=all_env if all_env else None,
            include_tools=include_tools if include_tools else None
        )
    
    def list_tools(self, tool_type: Optional[ToolType] = None) -> List[str]:
        """List all registered tools.
        
        Args:
            tool_type: Optional filter by tool type
            
        Returns:
            List of tool names/references
        """
        if tool_type:
            return [
                key for key, metadata in self._tools.items() 
                if metadata.type == tool_type
            ]
        return list(self._tools.keys())
    
    def get_tool_metadata(self, tool_ref: str) -> Optional[ToolMetadata]:
        """Get metadata for a tool.
        
        Args:
            tool_ref: Tool reference
            
        Returns:
            Tool metadata or None
        """
        return self._tools.get(tool_ref)
    
    def clear_mcp_cache(self):
        """Clear MCP runtime cache."""
        self._mcp_runtime_cache.clear()


# Global registry instance
tool_registry = ToolRegistry()