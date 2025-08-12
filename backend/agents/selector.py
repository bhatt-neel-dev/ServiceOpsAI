from typing import List, Optional
import asyncio

from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.memory.v2.db.postgres import PostgresMemoryDb
from agno.memory.v2.memory import Memory
from agno.storage.agent.postgres import PostgresAgentStorage

from agents.config_loader import AgentConfigLoader
from agents.tool_loader import DynamicToolLoader
from db.session import db_url


config_loader = AgentConfigLoader()
tool_loader = DynamicToolLoader()


def get_available_agents() -> List[str]:
    """Returns a list of all available agent IDs from configuration."""
    return config_loader.get_all_agents()


def _build_agent_from_config(
    agent_name: str,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    debug_mode: bool = True,
    model_override: Optional[str] = None,
) -> Agent:
    """Build an agent dynamically from YAML configuration."""
    config = config_loader.get_agent_config(agent_name)

    # Get model from config or use override
    model_id = model_override or config.get('model', 'gpt-4.1')

    # Process tools configuration using dynamic tool loader
    tools_config = config.get('tools', [])
    local_tools, mcp_configs = tool_loader.process_tools_list(tools_config)
    
    # Combine all tools into a single list
    tools = local_tools.copy()
    
    # Add MCP tools if any (will be handled as context manager later)
    mcp_tools = None
    if mcp_configs:
        mcp_tools = tool_loader.get_mcp_tools(mcp_configs)
        if mcp_tools:
            tools.append(mcp_tools)

    # Create agent with configuration
    agent = Agent(
        name=config.get('name'),
        agent_id=config.get('agent_id'),
        user_id=user_id,
        session_id=session_id,
        model=OpenAIChat(id=model_id),
        tools=tools,
        description=config.get('description', ''),
        instructions=config.get('instructions', ''),
        # Storage and memory handled internally
        storage=PostgresAgentStorage(table_name=f"{agent_name}_storage", db_url=db_url),
        memory=Memory(
            db=PostgresMemoryDb(table_name=f"{agent_name}_memory", db_url=db_url),
            debug_mode=debug_mode,
        ),
        debug_mode=debug_mode,
    )

    # Handle special case for agno_assist knowledge
    if agent_name == "agno_assist":
        from agno.agent import AgentKnowledge
        from agno.embedder.openai import OpenAIEmbedder
        from agno.knowledge.url import UrlKnowledge
        from agno.vectordb.pgvector import PgVector, SearchType

        knowledge = UrlKnowledge(
            urls=["https://docs.agno.com/llms-full.txt"],
            vector_db=PgVector(
                db_url=db_url,
                table_name="agno_assist_knowledge",
                search_type=SearchType.hybrid,
                embedder=OpenAIEmbedder(id="text-embedding-3-small"),
            ),
        )
        agent.knowledge = knowledge

    return agent


def get_agent(
    model_id: str = "gpt-4.1",
    agent_id: Optional[str] = None,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    debug_mode: bool = True,
) -> Agent:
    """Get agent using YAML configuration."""
    if agent_id is None:
        raise ValueError("agent_id is required")

    # Check if agent exists in configuration
    if agent_id not in config_loader.get_all_agents():
        raise ValueError(f"Agent: {agent_id} not found in configuration")

    return _build_agent_from_config(
        agent_name=agent_id,
        user_id=user_id,
        session_id=session_id,
        debug_mode=debug_mode,
        model_override=model_id,
    )
