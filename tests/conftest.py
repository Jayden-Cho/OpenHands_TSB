import pytest
import asyncio
from typing import Dict
from ..state.board import TaskStatusBoard
from ..events.event_stream import EventStream
from ..core.config import SystemConfig, AgentConfig, LLMConfig

@pytest.fixture
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def task_board():
    """Create a clean TaskStatusBoard instance"""
    return TaskStatusBoard()

@pytest.fixture
def event_stream():
    """Create a clean EventStream instance"""
    return EventStream()

@pytest.fixture
def mock_config() -> SystemConfig:
    """Create a mock system configuration"""
    agent_configs: Dict[str, AgentConfig] = {
        "delegator": AgentConfig(
            type="DelegatorAgent",
            llm_config=LLMConfig(
                model_name="mock-model",
                api_key="mock-key",
                temperature=0.7
            ),
            max_retries=1
        ),
        "verifier": AgentConfig(
            type="VerifierAgent",
            llm_config=LLMConfig(
                model_name="mock-model",
                api_key="mock-key",
                temperature=0.2
            ),
            max_retries=1
        )
    }
    
    return SystemConfig(
        max_iterations=5,
        agents=agent_configs,
        log_level="DEBUG"
    )
