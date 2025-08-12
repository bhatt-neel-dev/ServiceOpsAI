"""MCP Server Manager for initializing and managing MCP servers."""

import os
import asyncio
from typing import Dict, Any, List, Optional
from pathlib import Path
import yaml
import logging
from agno.tools.mcp import MCPTools

from core.tool_registry import tool_registry

logger = logging.getLogger(__name__)


class MCPServerManager:
    """Manages MCP server initialization and lifecycle."""
    
    def __init__(self, config_path: Optional[str] = None):
        if config_path is None:
            config_path = Path(__file__).parent.parent / "agents" / "mcp_config.yaml"
        self.config_path = config_path
        self.config = self._load_config()
        self.initialized_servers: Dict[str, bool] = {}
    
    def _load_config(self) -> Dict[str, Any]:
        """Load MCP configuration from YAML."""
        if not os.path.exists(self.config_path):
            logger.warning(f"MCP config not found at {self.config_path}")
            return {}
        
        with open(self.config_path, 'r') as file:
            return yaml.safe_load(file) or {}
    
    def _resolve_env_vars(self, value: Any) -> Any:
        """Recursively resolve environment variables in config values."""
        if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
            env_var = value[2:-1]
            return os.getenv(env_var, "")
        elif isinstance(value, dict):
            return {k: self._resolve_env_vars(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [self._resolve_env_vars(v) for v in value]
        return value
    
    def _build_command(self, server_config: Dict[str, Any]) -> str:
        """Build command string from server configuration."""
        server_config = self._resolve_env_vars(server_config)
        
        command_parts = []
        if "command" in server_config:
            command_parts.append(server_config["command"])
        if "args" in server_config:
            command_parts.extend(server_config["args"])
        
        return " ".join(command_parts) if command_parts else None
    
    async def discover_server_tools(self, server_name: str, server_config: Dict[str, Any]) -> List[str]:
        """Discover available tools from an MCP server.
        
        Args:
            server_name: Name of the MCP server
            server_config: Server configuration
            
        Returns:
            List of tool names available from the server
        """
        try:
            # Build command
            command = self._build_command(server_config)
            if not command:
                logger.warning(f"No command found for server {server_name}")
                return []
            
            # Resolve environment variables
            env = self._resolve_env_vars(server_config.get("env", {}))
            
            # Create temporary MCPTools instance to discover tools
            async with MCPTools(command=command, env=env if env else None) as mcp:
                # Get available tools from the server
                tools = await mcp.list_tools()
                return [tool.name for tool in tools] if tools else []
        
        except Exception as e:
            logger.error(f"Error discovering tools for server {server_name}: {e}")
            return []
    
    async def initialize_server(self, server_name: str) -> bool:
        """Initialize a single MCP server and register its tools.
        
        Args:
            server_name: Name of the MCP server
            
        Returns:
            True if successful, False otherwise
        """
        if server_name in self.initialized_servers:
            return self.initialized_servers[server_name]
        
        mcp_servers = self.config.get("mcp_servers", {})
        
        if server_name not in mcp_servers:
            logger.warning(f"Server {server_name} not found in configuration")
            return False
        
        server_config = mcp_servers[server_name]
        
        # Only support stdio type for now
        if server_config.get("type") != "stdio":
            logger.warning(f"Server {server_name} is not stdio type")
            return False
        
        try:
            # Build runtime configuration
            command = self._build_command(server_config)
            env = self._resolve_env_vars(server_config.get("env", {}))
            
            runtime_config = {
                "command": command,
                "env": env,
                "type": "stdio"
            }
            
            # Discover available tools
            tools = await self.discover_server_tools(server_name, server_config)
            
            if tools:
                # Register all discovered tools
                tool_registry.register_mcp_server_tools(server_name, tools, runtime_config)
                logger.info(f"Registered {len(tools)} tools from server {server_name}: {tools}")
            else:
                # Register server without specific tools (will have access to all)
                tool_registry.register_mcp_tool(None, server_name, runtime_config)
                logger.info(f"Registered server {server_name} without specific tools")
            
            self.initialized_servers[server_name] = True
            return True
            
        except Exception as e:
            logger.error(f"Error initializing server {server_name}: {e}")
            self.initialized_servers[server_name] = False
            return False
    
    async def initialize_all_servers(self) -> Dict[str, bool]:
        """Initialize all configured MCP servers.
        
        Returns:
            Dictionary of server names to initialization status
        """
        mcp_servers = self.config.get("mcp_servers", {})
        results = {}
        
        # Initialize servers in parallel
        tasks = []
        for server_name in mcp_servers:
            tasks.append(self.initialize_server(server_name))
        
        if tasks:
            statuses = await asyncio.gather(*tasks, return_exceptions=True)
            for server_name, status in zip(mcp_servers.keys(), statuses):
                if isinstance(status, Exception):
                    logger.error(f"Failed to initialize {server_name}: {status}")
                    results[server_name] = False
                else:
                    results[server_name] = status
        
        return results
    
    def get_server_config(self, server_name: str) -> Optional[Dict[str, Any]]:
        """Get configuration for a specific server.
        
        Args:
            server_name: Name of the MCP server
            
        Returns:
            Server configuration or None
        """
        mcp_servers = self.config.get("mcp_servers", {})
        return mcp_servers.get(server_name)
    
    def list_configured_servers(self) -> List[str]:
        """List all configured MCP servers.
        
        Returns:
            List of server names
        """
        return list(self.config.get("mcp_servers", {}).keys())
    
    def is_server_initialized(self, server_name: str) -> bool:
        """Check if a server is initialized.
        
        Args:
            server_name: Name of the MCP server
            
        Returns:
            True if initialized, False otherwise
        """
        return self.initialized_servers.get(server_name, False)


# Global MCP server manager instance
mcp_manager = MCPServerManager()