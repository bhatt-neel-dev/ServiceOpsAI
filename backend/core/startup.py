"""Startup initialization for tools and MCP servers."""

import asyncio
import logging
from typing import List, Dict, Any

from agno.tools.duckduckgo import DuckDuckGoTools
from agno.tools.yfinance import YFinanceTools

from core.tool_registry import tool_registry
from core.mcp_server_manager import mcp_manager

logger = logging.getLogger(__name__)


def register_local_tools():
    """Register all local/built-in tools to the registry."""
    
    # Register DuckDuckGo tools
    tool_registry.register_local_tool(
        name="DuckDuckGoTools",
        factory_func=lambda: DuckDuckGoTools(),
        config={"description": "Web search capabilities via DuckDuckGo"}
    )
    
    # Register YFinance tools
    def create_yfinance_tools():
        return YFinanceTools(
            stock_price=True,
            analyst_recommendations=True,
            stock_fundamentals=True,
            historical_prices=True,
            company_info=True,
            company_news=True,
        )
    
    tool_registry.register_local_tool(
        name="YFinanceTools",
        factory_func=create_yfinance_tools,
        config={"description": "Financial data and stock market analysis"}
    )
    
    logger.info("Registered local tools: DuckDuckGoTools, YFinanceTools")


async def initialize_mcp_servers(servers: List[str] = None) -> Dict[str, bool]:
    """Initialize MCP servers at startup.
    
    Args:
        servers: Optional list of specific servers to initialize.
                If None, initializes all configured servers.
    
    Returns:
        Dictionary of server names to initialization status
    """
    if servers:
        results = {}
        for server in servers:
            success = await mcp_manager.initialize_server(server)
            results[server] = success
        return results
    else:
        return await mcp_manager.initialize_all_servers()


async def initialize_tools_system():
    """Initialize the entire tools system at application startup."""
    logger.info("Initializing tools system...")
    
    # Register local tools
    register_local_tools()
    
    # Initialize MCP servers
    mcp_results = await initialize_mcp_servers()
    
    successful = [s for s, status in mcp_results.items() if status]
    failed = [s for s, status in mcp_results.items() if not status]
    
    if successful:
        logger.info(f"Successfully initialized MCP servers: {', '.join(successful)}")
    if failed:
        logger.warning(f"Failed to initialize MCP servers: {', '.join(failed)}")
    
    # Log summary
    total_tools = len(tool_registry.list_tools())
    logger.info(f"Tools system initialized with {total_tools} tools registered")
    
    return {
        "local_tools": tool_registry.list_tools(tool_type="local"),
        "mcp_servers": mcp_results,
        "total_tools": total_tools
    }


def get_tool_summary() -> Dict[str, Any]:
    """Get a summary of registered tools and servers.
    
    Returns:
        Dictionary with tool and server information
    """
    from core.tool_registry import ToolType
    
    return {
        "local_tools": tool_registry.list_tools(tool_type=ToolType.LOCAL),
        "mcp_tools": tool_registry.list_tools(tool_type=ToolType.MCP),
        "initialized_servers": list(mcp_manager.initialized_servers.keys()),
        "configured_servers": mcp_manager.list_configured_servers(),
        "total_tools": len(tool_registry.list_tools())
    }