import os
from pathlib import Path
from typing import Dict, Any, List
import yaml


class AgentConfigLoader:
    def __init__(self, config_path: str = None):
        if config_path is None:
            config_path = Path(__file__).parent / "agents_config.yaml"
        self.config_path = config_path
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        with open(self.config_path, 'r') as file:
            return yaml.safe_load(file)
    
    def get_agent_config(self, agent_name: str) -> Dict[str, Any]:
        if agent_name not in self.config:
            raise ValueError(f"Agent '{agent_name}' not found in configuration")
        return self.config[agent_name]
    
    def get_all_agents(self) -> List[str]:
        return list(self.config.keys())
    
    def get_agent_tools(self, agent_name: str) -> List[str]:
        agent_config = self.get_agent_config(agent_name)
        return agent_config.get('tools', [])
    
    def get_agent_model(self, agent_name: str) -> str:
        agent_config = self.get_agent_config(agent_name)
        return agent_config.get('model', 'gpt-4.1')
    
    def get_agent_description(self, agent_name: str) -> str:
        agent_config = self.get_agent_config(agent_name)
        return agent_config.get('description', '')
    
    def get_agent_instructions(self, agent_name: str) -> str:
        agent_config = self.get_agent_config(agent_name)
        return agent_config.get('instructions', '')