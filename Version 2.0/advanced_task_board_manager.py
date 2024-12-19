import heapq
from datetime import datetime
from typing import Dict, Set, List, Optional, Union, Tuple, Any
from openhands.events import Action, Observation, EventStream
from openhands.events.task_board import (
    TaskStatus, TaskBoardEntry, TaskBoardEvent, 
    StateTransitionEvent, VALID_TRANSITIONS
)

class CircularDependencyError(Exception):
    pass

class DependencyError(Exception):
    pass

class InvalidTransitionError(Exception):
    pass

class StateError(Exception):
    pass

class FeedbackConflictError(Exception):
    pass

class TaskBoardManager:
    def __init__(self):
        self.tasks: Dict[str, TaskBoardEntry] = {}
        self.event_stream: Optional[EventStream] = None
        self.dependency_graph: Dict[str, Set[str]] = {}
        self.priority_queue: List[Tuple[int, str]] = []  # (priority, task_id)
        self.feedback_threshold = 3  # Number of conflicting feedback before escalation
        self.escalation_agent = "delegator"  # Default escalation handler

    async def add_task(self, task: TaskBoardEntry) -> None:
        """
        Add new task and validate dependencies
        
        Args:
            task: TaskBoardEntry to add
            
        Raises:
            ValueError: If task with same ID exists or if dependencies don't exist
            CircularDependencyError: If adding task creates circular dependency
        """
        if task.id in self.tasks:
            raise ValueError(f"Task {task.id} already exists")
            
        # Validate dependencies exist
        for dep_id in task.dependencies:
            if dep_id not in self.tasks:
                raise ValueError(f"Dependency {dep_id} does not exist")
                
        # Update dependency graph
        self.dependency_graph[task.id] = set(task.dependencies)
        
        # Check for circular dependencies
        if self.detect_circular_dependencies():
            self.dependency_graph.pop(task.id)
            raise CircularDependencyError(f"Adding task {task.id} creates circular dependency")
            
        # Add to tasks dict
        self.tasks[task.id] = task
        
        # Add to priority queue
        heapq.heappush(self.priority_queue, (task.priority, task.id))
        
        # Set initial status based on dependencies
        initial_status = (TaskStatus.WAITING if task.dependencies 
                        else TaskStatus.IN_PROGRESS)
        await self.update_task_status(task.id, initial_status, "Task initialized")
        
        # Emit task added event
        await self.emit_task_event(
            task.id,
            "TASK_ADDED",
            {"task": task}
        )

    async def remove_task(self, task_id: str) -> None:
        """Remove task and clean up dependencies."""
        if task_id not in self.tasks:
            raise KeyError(f"Task {task_id} does not exist")
            
        # Check for dependent tasks
        blocked_tasks = await self.get_blocked_tasks(task_id)
        if blocked_tasks:
            # Instead of preventing removal, handle dependencies
            for blocked_id in blocked_tasks:
                await self.handle_partial_failure(blocked_id)
            
        # Remove from data structures
        task = self.tasks.pop(task_id)
        self.dependency_graph.pop(task_id)
        
        # Remove from priority queue
        self.priority_queue = [(p, tid) for p, tid in self.priority_queue 
                             if tid != task_id]
        heapq.heapify(self.priority_queue)
        
        # Remove from other tasks' dependencies
        for other_deps in self.dependency_graph.values():
            other_deps.discard(task_id)
            
        await self.emit_task_event(
            task_id,
            "TASK_REMOVED",
            {"task": task}
        )

    async def update_task_status(self, task_id: str, new_status: TaskStatus, reason: str) -> None:
        """Update task status with enhanced state management."""
        if task_id not in self.tasks:
            raise KeyError(f"Task {task_id} does not exist")
            
        task = self.tasks[task_id]
        old_status = task.status
        
        # Validate transition
        if new_status not in VALID_TRANSITIONS.get(old_status, set()):
            raise InvalidTransitionError(
                f"Invalid transition from {old_status} to {new_status}"
            )
            
        # Update status
        task.status = new_status
        task.last_updated = datetime.now()
        
        # Handle status-specific logic
        if new_status == TaskStatus.COMPLETE:
            # Propagate results to dependent tasks
            for dep_task_id in await self.get_blocked_tasks(task_id):
                dep_task = self.tasks[dep_task_id]
                if not dep_task.output:
                    dep_task.output = {}
                dep_task.output[task_id] = task.output
                
                # Check if all dependencies are complete
                if await self.check_dependencies(dep_task_id):
                    await self.update_task_status(
                        dep_task_id,
                        TaskStatus.IN_PROGRESS,
                        "All dependencies complete"
                    )
                    
        elif new_status == TaskStatus.ABANDONED:
            # Handle abandoned task
            await self.propagate_status(task_id, TaskStatus.ABANDONED, reason)
            
        elif new_status == TaskStatus.STALLED:
            # Trigger recovery mechanism
            await self.handle_partial_failure(task_id)
            
        elif new_status == TaskStatus.REWORK_NEEDED:
            task.current_iterations += 1
            if task.current_iterations >= task.max_iterations:
                await self.escalate_task(
                    task_id,
                    "Maximum iterations reached during rework"
                )
            
        # Emit status change event
        await self.emit_task_event(
            task_id,
            "STATUS_CHANGED",
            {
                "old_status": old_status,
                "new_status": new_status,
                "reason": reason
            }
        )

    async def handle_status_transition(self, task_id: str, old_status: TaskStatus, new_status: TaskStatus) -> None:
        """
        Handle logic for different status transitions
        
        Args:
            task_id: ID of task being transitioned
            old_status: Previous status
            new_status: New status
        """
        task = self.tasks[task_id]
        
        if new_status == TaskStatus.COMPLETE:
            # Check blocked tasks
            blocked_tasks = await self.get_blocked_tasks(task_id)
            for blocked_id in blocked_tasks:
                blocked_task = self.tasks[blocked_id]
                if await self.check_dependencies(blocked_id):
                    # All dependencies complete, can start task
                    await self.update_task_status(
                        blocked_id,
                        TaskStatus.IN_PROGRESS,
                        f"Dependencies completed"
                    )
                    
        elif new_status == TaskStatus.ABANDONED:
            # Abandon dependent tasks
            blocked_tasks = await self.get_blocked_tasks(task_id)
            for blocked_id in blocked_tasks:
                await self.update_task_status(
                    blocked_id,
                    TaskStatus.ABANDONED,
                    f"Dependency {task_id} abandoned"
                )

    # Dependency Management
    async def check_dependencies(self, task_id: str) -> bool:
        """
        Check if all dependencies are complete
        
        Args:
            task_id: ID of task to check
            
        Returns:
            bool: True if all dependencies are complete, False otherwise
            
        Raises:
            KeyError: If task doesn't exist
        """
        if task_id not in self.tasks:
            raise KeyError(f"Task {task_id} does not exist")
            
        dependencies = self.dependency_graph[task_id]
        for dep_id in dependencies:
            dep_task = self.tasks[dep_id]
            if dep_task.status != TaskStatus.COMPLETE:
                return False
        return True

    async def get_blocked_tasks(self, task_id: str) -> List[str]:
        """
        Get tasks blocked by this task
        
        Args:
            task_id: ID of task to check
            
        Returns:
            List[str]: List of task IDs that depend on this task
            
        Raises:
            KeyError: If task doesn't exist
        """
        if task_id not in self.tasks:
            raise KeyError(f"Task {task_id} does not exist")
            
        blocked = []
        for other_id, deps in self.dependency_graph.items():
            if task_id in deps:
                blocked.append(other_id)
        return blocked

    async def detect_circular_dependencies(self) -> List[List[str]]:
        """
        Detect and report circular dependencies using DFS
        
        Returns:
            List[List[str]]: List of circular dependency chains
        """
        visited = set()
        path = []
        cycles = []

        async def dfs(task_id: str) -> None:
            if task_id in path:
                cycle_start = path.index(task_id)
                cycles.append(path[cycle_start:] + [task_id])
                return
                
            if task_id in visited:
                return
                
            visited.add(task_id)
            path.append(task_id)
            
            for dep_id in self.dependency_graph[task_id]:
                await dfs(dep_id)
                
            path.pop()

        for task_id in self.dependency_graph:
            await dfs(task_id)
            
        return cycles

    # Iteration Management
    async def increment_iteration(self, task_id: str) -> None:
        """
        Increment iteration count and check for max iterations
        
        Args:
            task_id: ID of task to increment
            
        Raises:
            KeyError: If task doesn't exist
        """
        if task_id not in self.tasks:
            raise KeyError(f"Task {task_id} does not exist")
            
        task = self.tasks[task_id]
        task.current_iterations += 1
        
        if task.current_iterations >= task.max_iterations:
            await self.handle_iteration_limit_reached(task_id)
            
        await self.emit_task_event(
            task_id,
            "ITERATION_INCREMENTED",
            {"current_iterations": task.current_iterations}
        )

    async def handle_iteration_limit_reached(self, task_id: str) -> None:
        """
        Handle tasks that reach iteration limit
        
        Args:
            task_id: ID of task that reached limit
        """
        task = self.tasks[task_id]
        
        # If task is in rework, mark as stalled
        if task.status == TaskStatus.REWORK_NEEDED:
            await self.update_task_status(
                task_id,
                TaskStatus.STALLED,
                "Maximum iterations reached during rework"
            )
        # If task is in review loop, mark as stalled
        elif task.status == TaskStatus.PENDING_REVIEW:
            await self.update_task_status(
                task_id,
                TaskStatus.STALLED,
                "Maximum iterations reached during review"
            )

    # Event Stream Integration
    async def handle_event(self, event: Union[Action, Observation]) -> None:
        """
        Process incoming events and update task board accordingly
        
        Args:
            event: Action or Observation to process
        """
        # Handle different event types
        if isinstance(event, Action):
            if isinstance(event, AgentFinishAction):
                task_id = event.task_id
                if task_id in self.tasks:
                    task = self.tasks[task_id]
                    task.output = event.output
                    await self.request_verification(task_id)
                    
            elif isinstance(event, AgentRejectAction):
                task_id = event.task_id
                if task_id in self.tasks:
                    await self.update_task_status(
                        task_id,
                        TaskStatus.ABANDONED,
                        f"Agent rejected: {event.reason}"
                    )
                    
        # Update task history
        if hasattr(event, 'task_id') and event.task_id in self.tasks:
            task = self.tasks[event.task_id]
            task.history.append(event)

    async def emit_task_event(self, task_id: str, event_type: str, data: Dict[str, Any]) -> None:
        """Emit task-related event to event stream."""
        if self.event_stream:
            event = TaskBoardEvent(
                event_type=event_type,
                task_id=task_id,
                data=data,
                timestamp=datetime.now()
            )
            await self.event_stream.emit(event)

    # Verification Integration
    async def request_verification(self, task_id: str) -> None:
        """Request verification for a task."""
        if task_id not in self.tasks:
            raise KeyError(f"Task {task_id} does not exist")
            
        task = self.tasks[task_id]
        
        # Reset feedback for new verification round
        if task.status == TaskStatus.REWORK_NEEDED:
            task.verification_feedback = []
            
        await self.update_task_status(
            task_id,
            TaskStatus.PENDING_REVIEW,
            "Verification requested"
        )
        
        await self.emit_task_event(
            task_id,
            "VERIFICATION_REQUESTED",
            {
                "task_context": task.history,
                "current_output": task.output,
                "iteration": task.current_iterations
            }
        )

    async def handle_verification_result(self, task_id: str, passed: bool, feedback: Dict[str, Any]) -> None:
        """
        Process verification results
        
        Args:
            task_id: ID of verified task
            passed: Whether verification passed
            feedback: Verification feedback
            
        Raises:
            KeyError: If task doesn't exist
            StateError: If task not in pending review
        """
        if task_id not in self.tasks:
            raise KeyError(f"Task {task_id} does not exist")
            
        task = self.tasks[task_id]
        
        if task.status != TaskStatus.PENDING_REVIEW:
            raise StateError(f"Task {task_id} not in pending review")
            
        # Add verification feedback
        task.verification_feedback.append({
            "timestamp": datetime.now(),
            "passed": passed,
            "feedback": feedback
        })
        
        if passed:
            # Mark task as complete
            await self.update_task_status(
                task_id,
                TaskStatus.COMPLETE,
                "Verification passed"
            )
        else:
            # Increment iteration and check if we've hit the limit
            await self.increment_iteration(task_id)
            
            if task.current_iterations < task.max_iterations:
                # Return to in progress for rework
                await self.update_task_status(
                    task_id,
                    TaskStatus.REWORK_NEEDED,
                    f"Verification failed: {feedback.get('reason', 'No reason provided')}"
                )

    # Priority Management
    async def get_next_priority_task(self) -> Optional[str]:
        """Get highest priority task that's ready to execute."""
        while self.priority_queue:
            _, task_id = heapq.heappop(self.priority_queue)
            
            # Skip if task no longer exists
            if task_id not in self.tasks:
                continue
                
            task = self.tasks[task_id]
            
            # Check if task is ready
            if task.status == TaskStatus.WAITING:
                if await self.check_dependencies(task_id):
                    await self.update_task_status(
                        task_id,
                        TaskStatus.IN_PROGRESS,
                        "Dependencies satisfied"
                    )
                    return task_id
            elif task.status == TaskStatus.IN_PROGRESS:
                return task_id
                
            # Re-add to queue if not ready
            heapq.heappush(self.priority_queue, (task.priority, task_id))
            
        return None

    async def update_priority(self, task_id: str, new_priority: int) -> None:
        """
        Update task priority and reorder queue
        
        Args:
            task_id: ID of task to update
            new_priority: New priority value (1-5)
            
        Raises:
            KeyError: If task doesn't exist
            ValueError: If priority not in valid range
        """
        if task_id not in self.tasks:
            raise KeyError(f"Task {task_id} does not exist")
            
        if not 1 <= new_priority <= 5:
            raise ValueError("Priority must be between 1 and 5")
            
        task = self.tasks[task_id]
        old_priority = task.priority
        task.priority = new_priority
        
        # Rebuild priority queue
        self.priority_queue = [(t.priority, t.id) for t in self.tasks.values()]
        heapq.heapify(self.priority_queue)
        
        # Emit priority update event
        await self.emit_task_event(
            task_id,
            "PRIORITY_UPDATED",
            {
                "old_priority": old_priority,
                "new_priority": new_priority
            }
        )

    async def add_subtask(
        self, 
        parent_id: str | None, 
        goal: str, 
        subtasks: list[str] | None = None
    ) -> str:
        """Add a subtask and manage its relationship with parent task."""
        task_id = f"task_{len(self.tasks) + 1}"
        task = TaskBoardEntry(
            id=task_id,
            description=goal,
            dependencies=[parent_id] if parent_id else [],
            status=TaskStatus.WAITING,
            history=[],
            verification_feedback=[],
            output=None,
            priority=3
        )
        
        await self.add_task(task)
        
        # If there are subtasks, add them too
        if subtasks:
            for subtask in subtasks:
                await self.add_subtask(task_id, subtask)
                
        return task_id

    async def update_task_state(self, task_id: str, state: str) -> None:
        """Update task state and propagate changes through task hierarchy."""
        status = TaskStatus[state.upper()]
        await self.update_task_status(task_id, status, f"State updated to {state}")
        
        # Update dependent tasks if needed
        task = self.tasks.get(task_id)
        if task and task.dependencies:
            for dep_id in task.dependencies:
                await self._check_and_update_parent_status(dep_id)

    async def update_dependencies(self, task_id: str, new_dependencies: List[str]) -> None:
        """Dynamically update task dependencies with proper state management."""
        if task_id not in self.tasks:
            raise KeyError(f"Task {task_id} does not exist")
            
        task = self.tasks[task_id]
        old_dependencies = set(task.dependencies)
        new_dependencies_set = set(new_dependencies)
        
        # Validate new dependencies
        for dep_id in new_dependencies_set:
            if dep_id not in self.tasks:
                raise ValueError(f"Dependency {dep_id} does not exist")
                
        # Check for circular dependencies with new deps
        temp_graph = self.dependency_graph.copy()
        temp_graph[task_id] = new_dependencies_set
        if self._detect_cycles_in_graph(temp_graph):
            raise CircularDependencyError("New dependencies would create cycle")
            
        # Update dependencies
        task.dependencies = new_dependencies
        self.dependency_graph[task_id] = new_dependencies_set
        
        # If task was in progress, check if it needs to wait
        if task.status == TaskStatus.IN_PROGRESS:
            all_deps_complete = await self.check_dependencies(task_id)
            if not all_deps_complete:
                await self.update_task_status(
                    task_id,
                    TaskStatus.WAITING,
                    "New dependencies added"
                )
                
        await self.emit_task_event(
            task_id,
            "DEPENDENCIES_UPDATED",
            {
                "old_dependencies": list(old_dependencies),
                "new_dependencies": new_dependencies
            }
        )

    async def handle_feedback(self, task_id: str, feedback: Dict[str, Any], source: str) -> None:
        """Handle feedback with conflict resolution and escalation."""
        if task_id not in self.tasks:
            raise KeyError(f"Task {task_id} does not exist")
            
        task = self.tasks[task_id]
        
        # Add feedback with source
        feedback["source"] = source
        feedback["timestamp"] = datetime.now()
        task.verification_feedback.append(feedback)
        
        # Analyze feedback for conflicts
        approve_count = sum(1 for f in task.verification_feedback 
                          if f.get("verdict") == "approve")
        reject_count = sum(1 for f in task.verification_feedback 
                          if f.get("verdict") == "reject")
        
        # Check for conflicting feedback
        if approve_count > 0 and reject_count > 0:
            if len(task.verification_feedback) >= self.feedback_threshold:
                # Escalate to delegator agent
                await self.escalate_task(task_id, "Conflicting feedback")
                return
                
        # Process clear verdict
        if approve_count > 0 and reject_count == 0:
            await self.update_task_status(
                task_id,
                TaskStatus.COMPLETE,
                "Task approved"
            )
        elif reject_count > 0 and approve_count == 0:
            await self.update_task_status(
                task_id,
                TaskStatus.REWORK_NEEDED,
                "Task needs rework"
            )

    async def escalate_task(self, task_id: str, reason: str) -> None:
        """Escalate task to delegator agent for resolution."""
        task = self.tasks[task_id]
        
        # Create escalation event
        await self.emit_task_event(
            task_id,
            "TASK_ESCALATED",
            {
                "reason": reason,
                "feedback_history": task.verification_feedback,
                "escalation_agent": self.escalation_agent
            }
        )
        
        # Update task status
        await self.update_task_status(
            task_id,
            TaskStatus.STALLED,
            f"Escalated: {reason}"
        )

    async def break_down_task(self, task_id: str, subtasks: List[Dict[str, Any]]) -> List[str]:
        """Break down a task into subtasks with proper dependency management."""
        if task_id not in self.tasks:
            raise KeyError(f"Task {task_id} does not exist")
            
        parent_task = self.tasks[task_id]
        subtask_ids = []
        
        # Create subtasks
        for subtask_data in subtasks:
            subtask = TaskBoardEntry(
                id=f"{task_id}_sub_{len(subtask_ids)}",
                description=subtask_data["description"],
                dependencies=subtask_data.get("dependencies", []),
                status=TaskStatus.WAITING,
                history=[],
                verification_feedback=[],
                output=None,
                priority=parent_task.priority,
                max_iterations=parent_task.max_iterations,
                current_iterations=0,
                last_updated=datetime.now(),
                assigned_agent=subtask_data.get("assigned_agent")
            )
            
            await self.add_task(subtask)
            subtask_ids.append(subtask.id)
            
        # Update parent task dependencies
        await self.update_dependencies(task_id, subtask_ids)
        
        return subtask_ids

    async def handle_partial_failure(self, task_id: str) -> None:
        """Handle recovery for partially failed dependencies."""
        task = self.tasks[task_id]
        failed_deps = []
        
        # Identify failed dependencies
        for dep_id in task.dependencies:
            dep_task = self.tasks[dep_id]
            if dep_task.status in (TaskStatus.ABANDONED, TaskStatus.STALLED):
                failed_deps.append(dep_id)
                
        if failed_deps:
            # Create recovery event
            await self.emit_task_event(
                task_id,
                "DEPENDENCY_RECOVERY_NEEDED",
                {
                    "failed_dependencies": failed_deps,
                    "task_context": task.history,
                    "escalation_agent": self.escalation_agent
                }
            )
            
            # Update task status
            await self.update_task_status(
                task_id,
                TaskStatus.STALLED,
                f"Dependencies failed: {', '.join(failed_deps)}"
            )

    async def setup_cross_agent_collaboration(self, task_id: str, agent_assignments: Dict[str, str]) -> None:
        """Setup collaboration between multiple agents on subtasks."""
        if task_id not in self.tasks:
            raise KeyError(f"Task {task_id} does not exist")
            
        # Create subtasks for each agent
        subtasks = [
            {
                "description": f"Agent {agent} portion of task {task_id}",
                "assigned_agent": agent
            }
            for agent in agent_assignments.keys()
        ]
        
        # Break down into subtasks
        subtask_ids = await self.break_down_task(task_id, subtasks)
        
        # Assign agents to subtasks
        for subtask_id, agent in zip(subtask_ids, agent_assignments.values()):
            self.tasks[subtask_id].assigned_agent = agent
            
        await self.emit_task_event(
            task_id,
            "COLLABORATION_SETUP",
            {
                "subtasks": subtask_ids,
                "agent_assignments": agent_assignments
            }
        )

    async def _detect_cycles_in_graph(self, graph: Dict[str, Set[str]]) -> bool:
        """Helper method to detect cycles in dependency graph."""
        visited = set()
        path = set()
        
        def visit(node: str) -> bool:
            if node in path:
                return True
            if node in visited:
                return False
                
            visited.add(node)
            path.add(node)
            
            # Check all dependencies
            for dep in graph.get(node, set()):
                if visit(dep):
                    return True
                    
            path.remove(node)
            return False
            
        return any(visit(node) for node in graph)

    def get_task_status(self, task_id: str) -> TaskStatus:
        """Get current status of a task."""
        if task_id not in self.tasks:
            raise KeyError(f"Task {task_id} does not exist")
        return self.tasks[task_id].status

    def get_task_dependencies(self, task_id: str) -> Set[str]:
        """Get set of task dependencies."""
        if task_id not in self.tasks:
            raise KeyError(f"Task {task_id} does not exist")
        return self.dependency_graph[task_id].copy()

    def get_all_tasks(self) -> Dict[str, TaskBoardEntry]:
        """Get all tasks in the system."""
        return self.tasks.copy()