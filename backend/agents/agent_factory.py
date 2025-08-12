"""Agent Factory for creating agents with tools from registry."""

import logging
from typing import Dict, Any, List, Optional

from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.memory.v2.db.postgres import PostgresMemoryDb
from agno.memory.v2.memory import Memory
from agno.storage.agent.postgres import PostgresAgentStorage

from agents.config_loader import AgentConfigLoader
from core.tool_registry import tool_registry
from db.session import db_url

logger = logging.getLogger(__name__)


class AgentFactory:
    """Factory for creating agents with tools from the registry."""
    
    def __init__(self, config_loader: Optional[AgentConfigLoader] = None):
        self.config_loader = config_loader or AgentConfigLoader()
    
    async def create_agent(
        self,
        agent_id: str,
        use_memory: bool = True,
        use_storage: bool = True,
        debug_mode: bool = False
    ) -> Agent:
        """Create an agent with tools from the registry.
        
        Args:
            agent_id: Agent identifier
            use_memory: Whether to use memory
            use_storage: Whether to use storage
            debug_mode: Whether to enable debug mode
            
        Returns:
            Configured Agent instance
        """
        # Get agent configuration
        if agent_id not in self.config_loader.get_all_agents():
            raise ValueError(f"Agent {agent_id} not found in configuration")
        
        config = self.config_loader.get_agent_config(agent_id)
        
        # Get tools from registry
        tools_config = config.get('tools', [])
        tools = await self._get_tools_from_registry(tools_config)
        
        # Prepare agent parameters
        agent_params = {
            "name": config.get('name'),
            "agent_id": config.get('agent_id'),
            "model": OpenAIChat(id=config.get('model', 'gpt-4.1')),
            "tools": tools,
            "description": config.get('description', ''),
            "instructions": config.get('instructions', ''),
            "debug_mode": debug_mode,
        }
        
        # Add storage if requested
        if use_storage:
            agent_params["storage"] = PostgresAgentStorage(
                table_name=f"{agent_id}_storage",
                db_url=db_url
            )
        
        # Add memory if requested
        if use_memory:
            agent_params["memory"] = Memory(
                db=PostgresMemoryDb(
                    table_name=f"{agent_id}_memory",
                    db_url=db_url
                ),
                debug_mode=debug_mode,
            )
        
        return Agent(**agent_params)
    
    async def _get_tools_from_registry(self, tools_config: List[str]) -> List[Any]:
        """Get tool instances from the registry.
        
        Args:
            tools_config: List of tool references from YAML
            
        Returns:
            List of tool instances
        """
        local_tools = []
        mcp_refs = []
        
        for tool_ref in tools_config:
            if isinstance(tool_ref, str):
                if tool_ref.startswith("mcp:"):
                    # Collect MCP references
                    mcp_refs.append(tool_ref)
                else:
                    # Get local tool from registry
                    tool = await tool_registry.get_tool_runtime(tool_ref)
                    if tool:
                        local_tools.append(tool)
                    else:
                        logger.warning(f"Tool {tool_ref} not found in registry")
        
        # Get MCP tools (potentially combined)
        if mcp_refs:
            mcp_runtime = await tool_registry._get_combined_mcp_runtime(mcp_refs)
            if mcp_runtime:
                local_tools.append(mcp_runtime)
            else:
                logger.warning(f"Could not create MCP runtime for {mcp_refs}")
        
        return local_tools
    
    async def create_agent_with_context(
        self,
        agent_id: str,
        use_memory: bool = True,
        use_storage: bool = True,
        debug_mode: bool = False
    ):
        """Create an agent that returns both the agent and its MCP context.
        
        This is useful when you need to manage the MCP tools lifecycle manually.
        
        Args:
            agent_id: Agent identifier
            use_memory: Whether to use memory
            use_storage: Whether to use storage
            debug_mode: Whether to enable debug mode
            
        Returns:
            Tuple of (Agent, MCPTools context or None)
        """
        # Get agent configuration
        if agent_id not in self.config_loader.get_all_agents():
            raise ValueError(f"Agent {agent_id} not found in configuration")
        
        config = self.config_loader.get_agent_config(agent_id)
        
        # Separate local and MCP tools
        tools_config = config.get('tools', [])
        local_tools = []
        mcp_refs = []
        
        for tool_ref in tools_config:
            if isinstance(tool_ref, str):
                if tool_ref.startswith("mcp:"):
                    mcp_refs.append(tool_ref)
                else:
                    tool = await tool_registry.get_tool_runtime(tool_ref)
                    if tool:
                        local_tools.append(tool)
        
        # Get MCP runtime if needed
        mcp_runtime = None
        if mcp_refs:
            mcp_runtime = await tool_registry._get_combined_mcp_runtime(mcp_refs)
        
        # Prepare agent parameters
        agent_params = {
            "name": config.get('name'),
            "agent_id": config.get('agent_id'),
            "model": OpenAIChat(id=config.get('model', 'gpt-4.1')),
            "tools": local_tools,  # Will add MCP tools in context
            "description": config.get('description', ''),
            "instructions": config.get('instructions', ''),
            "debug_mode": debug_mode,
        }
        
        # Add storage if requested
        if use_storage:
            agent_params["storage"] = PostgresAgentStorage(
                table_name=f"{agent_id}_storage",
                db_url=db_url
            )
        
        # Add memory if requested
        if use_memory:
            agent_params["memory"] = Memory(
                db=PostgresMemoryDb(
                    table_name=f"{agent_id}_memory",
                    db_url=db_url
                ),
                debug_mode=debug_mode,
            )
        
        agent = Agent(**agent_params)
        
        return agent, mcp_runtime
    
    def list_agent_tools(self, agent_id: str) -> Dict[str, List[str]]:
        """List tools configured for an agent.
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            Dictionary with local and MCP tools
        """
        if agent_id not in self.config_loader.get_all_agents():
            return {"local": [], "mcp": []}
        
        config = self.config_loader.get_agent_config(agent_id)
        tools_config = config.get('tools', [])
        
        local_tools = []
        mcp_tools = []
        
        for tool in tools_config:
            if isinstance(tool, str):
                if tool.startswith("mcp:"):
                    mcp_tools.append(tool)
                else:
                    local_tools.append(tool)
        
        return {
            "local": local_tools,
            "mcp": mcp_tools
        }