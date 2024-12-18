from dataclasses import dataclass
from typing import Optional

@dataclass
class Observation:
    """Base class for all observations"""
    content: str
    success: bool

@dataclass
class TaskObservation(Observation):
    """Observation for task-related operations"""
    task_id: str
    agent_id: str
    error: Optional[str] = None 