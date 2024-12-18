from dataclasses import dataclass
from typing import Optional

@dataclass
class Action:
    """Base class for all actions"""
    action_type: str
    content: str

@dataclass
class MessageAction(Action):
    """Action for sending messages between agents"""
    sender: str
    receiver: str
    
@dataclass
class TaskAction(Action):
    """Action for task-related operations"""
    task_id: str
    agent_id: str