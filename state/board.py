from typing import Dict, List, Callable, Optional, Any
import sys
from state.task import Task, TaskStatus

class TaskStatusBoard:
    def __init__(self):
        self.tasks: Dict[str, Task] = {}
        self._observers: List[Callable] = []
        self.agents: Dict[str, Any] = {}  # Store agents by their name
        self.task_agent_mapping: Dict[str, str] = {}  # Maps task_id to agent_name        
        
    def register_agent(self, agent_name: str, agent: Any) -> None:
        """Register an agent with the task board"""
        self.agents[agent_name] = agent

    def assign_task_to_agent(self, task_id: str, agent_name: str) -> None:
        """Assign a task to a specific agent"""
        if task_id in self.tasks and agent_name in self.agents:
            self.task_agent_mapping[task_id] = agent_name

    def add_task(self, task: Task) -> None:
        self.tasks[task.id] = task
        
    def get_task(self, task_id: str) -> Optional[Task]:
        return self.tasks.get(task_id)
        
    def update_task_status(self, task_id: str, new_status: TaskStatus) -> None:
        if task_id in self.tasks:
            old_status = self.tasks[task_id].status
            self.tasks[task_id].update_status(new_status)
            self._notify_status_change(task_id, old_status, new_status)
            
    def get_tasks_by_status(self, status: TaskStatus) -> List[Task]:
        return [task for task in self.tasks.values() if task.status == status]
    
    def get_ready_tasks(self) -> List[Task]:
        """Returns tasks that are ready to be worked on (dependencies completed)"""
        ready_tasks = []
        for task in list(self.tasks.values()):
            if task.status == TaskStatus.WAITING:   
                dependencies_complete = all(
                    self.tasks[dep_id].status == TaskStatus.COMPLETED 
                    for dep_id in task.dependencies
                )
                if dependencies_complete:
                    ready_tasks.append(task)
        return ready_tasks
    
    def subscribe_to_status_changes(self, callback: Callable) -> None:
        self._observers.append(callback)
        
    def _notify_status_change(self, task_id: str, old_status: TaskStatus, new_status: TaskStatus) -> None:
        for observer in self._observers:
            observer(task_id, old_status, new_status)

    def all_tasks_completed(self) -> bool:
        return all(
            task.status == TaskStatus.COMPLETED 
            for task_id, task in self.tasks.items() 
            if task_id != "main"
        )