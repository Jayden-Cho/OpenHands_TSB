from dataclasses import dataclass
from typing import Dict, Optional
import yaml
import os

@dataclass
class LLMConfig:
    model_name: str
    api_key: str
    temperature: float = 0.7
    max_tokens: Optional[int] = None

@dataclass
class AgentConfig:
    type: str
    llm_config: LLMConfig
    max_retries: int = 3
    timeout: int = 300

@dataclass
class SystemConfig:
    max_iterations: int
    agents: Dict[str, AgentConfig]
    log_level: str = "INFO"

class ConfigLoader:
    @staticmethod
    def load_config(config_path: str) -> SystemConfig:
        """Load configuration from YAML file"""
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Config file not found: {config_path}")
            
        with open(config_path, 'r') as f:
            config_data = yaml.safe_load(f)
            
        # Parse LLM configs
        agent_configs = {}
        for agent_name, agent_data in config_data['agents'].items():
            llm_config = LLMConfig(**agent_data['llm'])
            agent_configs[agent_name] = AgentConfig(
                type=agent_data['type'],
                llm_config=llm_config,
                max_retries=agent_data.get('max_retries', 3),
                timeout=agent_data.get('timeout', 300)
            )
            
        return SystemConfig(
            max_iterations=config_data['max_iterations'],
            agents=agent_configs,
            log_level=config_data.get('log_level', 'INFO')
        )
