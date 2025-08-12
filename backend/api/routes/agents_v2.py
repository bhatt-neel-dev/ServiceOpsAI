"""Improved agents API routes using the tool registry system."""

import logging
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from agents.agent_factory import AgentFactory
from agents.config_loader import AgentConfigLoader
from core.tool_registry import tool_registry
from core.startup import get_tool_summary

logger = logging.getLogger(__name__)

agents_v2_router = APIRouter(prefix="/agents", tags=["Agents V2"])

# Initialize components
config_loader = AgentConfigLoader()
agent_factory = AgentFactory(config_loader)


class AgentRequest(BaseModel):
    """Request model for agent interactions."""
    message: str
    agent_id: str
    stream: bool = False
    use_memory: bool = True
    use_storage: bool = True
    debug_mode: bool = False


class AgentResponse(BaseModel):
    """Response model for agent interactions."""
    agent: str
    agent_id: str
    message: str
    response: str
    tools_used: List[str] = []
    debug_info: Optional[Dict[str, Any]] = None


@agents_v2_router.post("/run")
async def run_agent(request: AgentRequest):
    """Run an agent with tools from the registry."""
    try:
        # Create agent with MCP context
        agent, mcp_context = await agent_factory.create_agent_with_context(
            agent_id=request.agent_id,
            use_memory=request.use_memory,
            use_storage=request.use_storage,
            debug_mode=request.debug_mode
        )
        
        # Handle MCP context if present
        if mcp_context:
            async with mcp_context as active_mcp:
                # Add MCP tools to agent
                agent.tools = agent.tools + [active_mcp]
                
                # Run agent
                if request.stream:
                    # Stream response
                    async def generate():
                        async for chunk in agent.arun_stream(request.message):
                            yield chunk
                    
                    return StreamingResponse(generate(), media_type="text/event-stream")
                else:
                    # Non-streaming response
                    response = await agent.arun(request.message, stream=False)
                    
                    # Extract tool usage information
                    tools_used = []
                    for msg in response.messages:
                        if hasattr(msg, 'tool_calls'):
                            for tool_call in msg.tool_calls:
                                tools_used.append(tool_call.function.name)
                    
                    return AgentResponse(
                        agent=agent.name,
                        agent_id=request.agent_id,
                        message=request.message,
                        response=response.content,
                        tools_used=tools_used,
                        debug_info={"message_count": len(response.messages)} if request.debug_mode else None
                    )
        else:
            # No MCP context, run normally
            if request.stream:
                async def generate():
                    async for chunk in agent.arun_stream(request.message):
                        yield chunk
                
                return StreamingResponse(generate(), media_type="text/event-stream")
            else:
                response = await agent.arun(request.message, stream=False)
                
                tools_used = []
                for msg in response.messages:
                    if hasattr(msg, 'tool_calls'):
                        for tool_call in msg.tool_calls:
                            tools_used.append(tool_call.function.name)
                
                return AgentResponse(
                    agent=agent.name,
                    agent_id=request.agent_id,
                    message=request.message,
                    response=response.content,
                    tools_used=tools_used,
                    debug_info={"message_count": len(response.messages)} if request.debug_mode else None
                )
                
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error running agent {request.agent_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@agents_v2_router.get("/list")
async def list_agents():
    """List all configured agents with their tools."""
    agents = []
    
    for agent_id in config_loader.get_all_agents():
        config = config_loader.get_agent_config(agent_id)
        tools = agent_factory.list_agent_tools(agent_id)
        
        agents.append({
            "agent_id": agent_id,
            "name": config.get('name'),
            "model": config.get('model', 'gpt-4.1'),
            "description": config.get('description', '')[:100] + "...",
            "tools": tools,
            "total_tools": len(tools['local']) + len(tools['mcp'])
        })
    
    return {
        "agents": agents,
        "total": len(agents)
    }


@agents_v2_router.get("/tools")
async def list_tools():
    """List all registered tools in the system."""
    return get_tool_summary()


@agents_v2_router.get("/{agent_id}")
async def get_agent_details(agent_id: str):
    """Get detailed information about an agent."""
    if agent_id not in config_loader.get_all_agents():
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
    
    config = config_loader.get_agent_config(agent_id)
    tools = agent_factory.list_agent_tools(agent_id)
    
    # Get detailed tool information
    tool_details = []
    
    for tool_ref in tools['local']:
        metadata = tool_registry.get_tool_metadata(tool_ref)
        if metadata:
            tool_details.append({
                "name": tool_ref,
                "type": "local",
                "description": metadata.config.get('description', 'No description')
            })
    
    for tool_ref in tools['mcp']:
        parts = tool_ref.split(":")
        server = parts[1] if len(parts) > 1 else "unknown"
        specific_tools = parts[2] if len(parts) > 2 else None
        
        tool_details.append({
            "name": tool_ref,
            "type": "mcp",
            "server": server,
            "specific_tools": specific_tools.split(",") if specific_tools else None
        })
    
    return {
        "agent_id": agent_id,
        "name": config.get('name'),
        "model": config.get('model', 'gpt-4.1'),
        "description": config.get('description', ''),
        "instructions": config.get('instructions', ''),
        "tools": tool_details,
        "tools_summary": tools
    }


@agents_v2_router.post("/reload-tools")
async def reload_tools():
    """Reload tool configurations and re-initialize MCP servers."""
    try:
        from core.startup import initialize_tools_system
        
        # Clear MCP cache
        tool_registry.clear_mcp_cache()
        
        # Re-initialize
        result = await initialize_tools_system()
        
        return {
            "status": "success",
            "result": result
        }
    except Exception as e:
        logger.error(f"Error reloading tools: {e}")
        raise HTTPException(status_code=500, detail=str(e))