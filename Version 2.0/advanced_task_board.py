from dataclasses import dataclass
from enum import Enum
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from openhands.events import Action, Observation

@dataclass
class TaskStatus(Enum):
    WAITING = "waiting"           
    IN_PROGRESS = "in_progress"   
    PENDING_REVIEW = "pending_review"  
    REWORK_NEEDED = "rework_needed"    
    COMPLETE = "complete"         
    STALLED = "stalled"          
    ABANDONED = "abandoned"       

@dataclass
class TaskBoardEntry:
    id: str
    description: str
    dependencies: List[str]
    status: TaskStatus
    history: List[Tuple[Action, Observation]]
    verification_feedback: List[Dict[str, Any]]
    output: Optional[Any]
    priority: int = 5
    max_iterations: int = 10
    current_iterations: int = 0
    last_updated: datetime
    assigned_agent: Optional[str] = None

@dataclass
class TaskBoardEvent(Event):
    event_type: str
    task_id: str
    data: Dict[str, Any]
    timestamp: datetime

@dataclass
class StateTransitionEvent(Event):
    task_id: str
    old_status: TaskStatus
    new_status: TaskStatus
    reason: str
    timestamp: datetime

# State transition rules
VALID_TRANSITIONS = {
    TaskStatus.WAITING: {TaskStatus.IN_PROGRESS, TaskStatus.ABANDONED},
    TaskStatus.IN_PROGRESS: {TaskStatus.PENDING_REVIEW, TaskStatus.STALLED},
    TaskStatus.PENDING_REVIEW: {TaskStatus.COMPLETE, TaskStatus.REWORK_NEEDED},
    TaskStatus.REWORK_NEEDED: {TaskStatus.IN_PROGRESS, TaskStatus.ABANDONED},
    TaskStatus.STALLED: {TaskStatus.IN_PROGRESS, TaskStatus.ABANDONED},
}