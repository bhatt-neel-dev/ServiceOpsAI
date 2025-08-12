"""Dynamic tool loader for Agno agents supporting both local and MCP tools."""

import os
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import yaml
from agno.tools.mcp import MCPTools, MultiMCPTools
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.tools.yfinance import YFinanceTools


class DynamicToolLoader:
    """Dynamically loads MCP tools from configuration."""
    
    def __init__(self, config_path: str = None):
        if config_path is None:
            config_path = Path(__file__).parent / "mcp_config.yaml"
        self.config_path = config_path
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load MCP configuration from YAML."""
        if not os.path.exists(self.config_path):
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
    
    def build_mcp_command(self, server_config: Dict[str, Any]) -> str:
        """Build command string from server configuration."""
        server_config = self._resolve_env_vars(server_config)
        
        command_parts = []
        if "command" in server_config:
            command_parts.append(server_config["command"])
        if "args" in server_config:
            command_parts.extend(server_config["args"])
        
        return " ".join(command_parts) if command_parts else None
    
    def parse_mcp_config(self, mcp_configs: List[Any]) -> Dict[str, Any]:
        """Parse MCP configurations to extract servers and tools.
        
        Args:
            mcp_configs: List of MCP configurations (e.g., "mcp:custom_tools", "mcp:custom_tools[generate_id,get_timestamp]")
            
        Returns:
            Dict with server commands and tool filters
        """
        result = {
            "commands": [],
            "env": {},
            "include_tools": None,
            "servers": {}
        }
        
        mcp_servers = self.config.get("mcp_servers", {})
        all_include_tools = []
        
        for config in mcp_configs:
            if config.startswith("mcp:"):
                config = config[4:]  # Remove "mcp:" prefix
                
                # Check if specific tools are requested
                if "[" in config and "]" in config:
                    server_name = config[:config.index("[")]
                    tools_str = config[config.index("[")+1:config.index("]")]
                    tools = [t.strip() for t in tools_str.split(",")]
                    all_include_tools.extend(tools)
                else:
                    server_name = config
                    tools = None
                
                if server_name in mcp_servers:
                    server_config = mcp_servers[server_name]
                    
                    # Build command if it's stdio type
                    if server_config.get("type") == "stdio":
                        command = self.build_mcp_command(server_config)
                        if command:
                            result["commands"].append(command)
                            result["servers"][server_name] = {"tools": tools}
                            
                            # Collect environment variables
                            env = self._resolve_env_vars(server_config.get("env", {}))
                            result["env"].update(env)
        
        # Set include_tools if any specific tools were requested
        if all_include_tools:
            result["include_tools"] = all_include_tools
        
        return result
    
    def get_mcp_tools(self, mcp_configs: List[Any]) -> Optional[Any]:
        """Create MCP tools for the specified configurations.
        
        Args:
            mcp_configs: List of MCP configurations
            
        Returns:
            MCPTools or MultiMCPTools instance, or None
        """
        if not mcp_configs:
            return None
        
        parsed = self.parse_mcp_config(mcp_configs)
        
        if not parsed["commands"]:
            return None
        
        # Single server - return MCPTools
        if len(parsed["commands"]) == 1:
            return MCPTools(
                command=parsed["commands"][0], 
                env=parsed["env"] if parsed["env"] else None,
                include_tools=parsed["include_tools"]
            )
        
        # Multiple servers - return MultiMCPTools
        return MultiMCPTools(
            parsed["commands"], 
            env=parsed["env"] if parsed["env"] else None,
            include_tools=parsed["include_tools"]
        )
    
    def get_local_tool(self, tool_name: str) -> Optional[Any]:
        """Get a local tool instance by name.
        
        Args:
            tool_name: Name of the local tool
            
        Returns:
            Tool instance or None if not found
        """
        if tool_name == "DuckDuckGoTools":
            return DuckDuckGoTools()
        elif tool_name == "YFinanceTools":
            return YFinanceTools(
                stock_price=True,
                analyst_recommendations=True,
                stock_fundamentals=True,
                historical_prices=True,
                company_info=True,
                company_news=True,
            )
        else:
            print(f"Warning: Local tool '{tool_name}' not recognized")
            return None
    
    def process_tools_list(self, tools_config: List[str]) -> Tuple[List[Any], List[str]]:
        """Process a list of tool configurations.
        
        Args:
            tools_config: List of tool names (local or mcp:server_name[tool1,tool2])
            
        Returns:
            Tuple of (local_tools, mcp_configs)
        """
        local_tools = []
        mcp_configs = []
        
        for tool in tools_config:
            if isinstance(tool, str):
                if tool.startswith("mcp:"):
                    # Keep full MCP configuration string
                    mcp_configs.append(tool)
                else:
                    # Local tool
                    local_tool = self.get_local_tool(tool)
                    if local_tool:
                        local_tools.append(local_tool)
        
        return local_tools, mcp_configs