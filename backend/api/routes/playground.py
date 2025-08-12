from agno.playground import Playground

from agents.selector import get_agent, get_available_agents

######################################################
## Routes for the Playground Interface
######################################################

# Get Agents to serve in the playground using the new selector
agents = []
for agent_id in get_available_agents():
    agent = get_agent(agent_id=agent_id, debug_mode=True)
    agents.append(agent)

# Create a playground instance
playground = Playground(agents=agents)

# Get the router for the playground
playground_router = playground.get_async_router()
