from enum import Enum
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime

class TaskStatus(Enum):
    WAITING = "waiting"
    IN_PROGRESS = "in_progress"
    PENDING_REVIEW = "pending_review"
    COMPLETED = "completed"
    RE_PROGRESS = "re_progress"

@dataclass
class TaskContext:
    last_action: str
    last_observation: str
    timestamp: datetime

@dataclass
class Task:
    id: str
    name: str
    description: str
    requirements: List[str]
    dependencies: List[str]
    status: TaskStatus
    assigned_agent: Optional[str] = None
    context: Optional[TaskContext] = None
    feedback: Optional[str] = None
    result: Optional[str] = None

    def update_status(self, new_status: TaskStatus) -> None:
        self.status = new_status

    def update_context(self, action: str, observation: str) -> None:
        self.context = TaskContext(
            last_action=action,
            last_observation=observation,
            timestamp=datetime.now()
        )
    
    # TODO: 기존에 initialized된 Task에 feedback과 result를 추가할 수 있는 method를 추가해야 함.