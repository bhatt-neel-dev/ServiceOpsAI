# Tool Registry Architecture

## Overview

The Tool Registry system provides a centralized way to manage both local and MCP (Model Context Protocol) tools in ServiceOpsAI. This architecture solves the problem of dynamically loading and managing tools at runtime while maintaining compatibility with Agno's tool system.

## Key Components

### 1. Tool Registry (`core/tool_registry.py`)
- Central registry for all tools with runtime object management
- Maintains metadata about each tool (name, type, server, configuration)
- Provides factory methods to create tool instances
- Caches MCP runtime objects for efficiency
- Supports both individual and combined MCP server access

### 2. MCP Server Manager (`core/mcp_server_manager.py`)
- Manages MCP server lifecycle
- Discovers available tools from MCP servers
- Handles server initialization at startup
- Resolves environment variables in configurations
- Builds command strings for stdio-based MCP servers

### 3. Startup Module (`core/startup.py`)
- Initializes the tool system at application startup
- Registers all local/built-in tools
- Initializes configured MCP servers
- Provides summary of available tools

### 4. Agent Factory (`agents/agent_factory.py`)
- Creates agents with tools from the registry
- Handles MCP context management
- Supports both simple and context-aware agent creation
- Integrates with existing memory and storage systems

## How It Works

### Application Startup Flow

1. **FastAPI Lifespan**: The application uses FastAPI's lifespan context to initialize tools
2. **Local Tool Registration**: Built-in tools (DuckDuckGo, YFinance) are registered with factory functions
3. **MCP Server Discovery**: Each configured MCP server is initialized and its tools discovered
4. **Tool Registration**: All discovered MCP tools are registered in the central registry
5. **Ready State**: The system is ready to create agents with any combination of tools

### Agent Creation Flow

1. **Configuration Loading**: Agent YAML configuration is loaded
2. **Tool Resolution**: Tool references are resolved from the registry
3. **Runtime Creation**: Tool runtime objects are created (local tools instantiated, MCP connections established)
4. **Agent Assembly**: Agent is created with all resolved tools
5. **Context Management**: MCP tools are managed as async context managers

## Configuration

### Agent YAML Configuration
```yaml
agent_name:
  name: "Agent Display Name"
  agent_id: "unique_agent_id"
  model: "gpt-4.1"
  tools:
    # Local tools
    - "DuckDuckGoTools"
    - "YFinanceTools"
    
    # MCP servers (full access)
    - "mcp:filesystem"
    - "mcp:github"
    
    # MCP with specific tools
    - "mcp:custom_tools[tool1,tool2]"
```

### MCP Server Configuration
```yaml
mcp_servers:
  server_name:
    type: stdio
    command: "command"
    args: ["arg1", "arg2"]
    env:
      ENV_VAR: "${ENV_VAR}"
```

## Benefits

1. **Centralized Management**: All tools managed through a single registry
2. **Dynamic Loading**: Tools loaded and initialized only when needed
3. **Efficient Caching**: MCP runtime objects cached to avoid recreation
4. **Flexible Configuration**: Support for both full server and specific tool access
5. **Clean Separation**: Tool management separated from agent logic
6. **Agno Compatibility**: Full compatibility with Agno's tool system

## API Endpoints

### New Endpoints (agents_v2)
- `POST /v1/agents/run` - Run an agent with registry tools
- `GET /v1/agents/list` - List all agents with their tools
- `GET /v1/agents/tools` - List all registered tools
- `GET /v1/agents/{agent_id}` - Get agent details
- `POST /v1/agents/reload-tools` - Reload tool configurations

## Migration Guide

### From old approach to new registry system

Old approach:
- Tools loaded dynamically per request
- MCP context managed in router
- Duplicate agent creation logic

New approach (agents_v2):
- Tools pre-registered at startup
- MCP context managed by factory
- Centralized agent creation

### Code Changes Required

1. Use `AgentFactory` instead of manual agent creation
2. Reference tools by name in YAML (no code changes for tools)
3. MCP servers automatically discovered and registered
4. No need for `DynamicToolLoader` in routes

## Example Usage

```python
from agents.agent_factory import AgentFactory

# Create factory
factory = AgentFactory()

# Create agent with automatic tool resolution
agent, mcp_context = await factory.create_agent_with_context(
    agent_id="service_ops_agent",
    use_memory=True,
    use_storage=True
)

# Use agent with MCP context
if mcp_context:
    async with mcp_context as active_mcp:
        agent.tools = agent.tools + [active_mcp]
        response = await agent.arun("Your query here")
```

## Future Enhancements

1. **Hot Reload**: Support for adding/removing tools without restart
2. **Tool Versioning**: Support for multiple versions of the same tool
3. **Permission System**: Fine-grained permissions for tool access
4. **Tool Analytics**: Track tool usage and performance
5. **Custom Tool Plugins**: Support for user-defined tool plugins