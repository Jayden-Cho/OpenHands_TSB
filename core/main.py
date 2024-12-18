import asyncio
import sys
from typing import Optional, Dict, List
from llm.llm import Claude35LLM
from state.board import TaskStatusBoard
from events.event_stream import EventStream
from agents.delegator import DelegatorAgent
from agents.verifier import VerifierAgent
from agents.swe_agent import SWEAgent
from state.task import Task, TaskStatus
from dotenv import load_dotenv
import os

class MultiAgentSystem:
    def __init__(self, max_iterations: int):
        load_dotenv()  # Load API key at initialization
        self.api_key = os.getenv('ANTHROPIC_API_KEY')
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment variables")
        self.max_iterations = max_iterations
        self.current_iteration = 0
        self.task_board = TaskStatusBoard()
        self.event_stream = EventStream()
        
        # Initialize LLMs
        self.delegator_llm = Claude35LLM(model_name="claude-3-sonnet-20240229")
        self.verifier_llm = Claude35LLM(model_name="claude-3-sonnet-20240229")
        self.swe_agent_llm = Claude35LLM(model_name="claude-3-sonnet-20240229")
        # Initialize core agents
        self.delegator = DelegatorAgent("delegator", self.delegator_llm, 
                                      self.task_board, self.event_stream)
        self.verifier = VerifierAgent("verifier", self.verifier_llm,
                                    self.task_board, self.event_stream)
        self.swe_agent = SWEAgent("swe_agent", self.swe_agent_llm,
                                    self.task_board, self.event_stream)
        
        self.task_board.register_agent("delegator", self.delegator)
        self.task_board.register_agent("verifier", self.verifier)        
        self.task_board.register_agent("swe_agent", self.swe_agent)


    async def process_query(self, task: Task) -> str:
        """
        Process task and return result
        
        Args:
            task: Task object containing:
                - id: str (instance_id)
                - name: str (bug fix description)
                - description: str (problem statement)
                - requirements: List[str] (repository, base commit, code changes, etc)
                - dependencies: List[str]
                - status: TaskStatus
        
        Returns:
            str: Generated patch in git diff format
        """
        # Create comprehensive task description from Task object fields
        task_description = f"""
        Task: {task.name}
        
        Problem Description:
        {task.description}
        
        Requirements:
        {chr(10).join(task.requirements)}
        """
        
        # Add task to board if not already added
        if task.id not in self.task_board.tasks:
            self.task_board.add_task(task)

        while self.current_iteration < self.max_iterations:
            print(f"\n=== Iteration {self.current_iteration + 1} ===")

            # Decompose main task into subtasks for the first iteration, or
            # Aggregate results from subtasks when all subtasks are completed
            if self.current_iteration == 0:
                print("\n1. Delegator decomposing main task...")
                await self.delegator.process_task(task)
                print("✓ Delegator finished decomposing task into subtasks")
            elif self.task_board.all_tasks_completed():
                print("\n1. All subtasks completed, delegator aggregating results...")
                await self.delegator.process_task(task)
                print("✓ Delegator finished aggregating results")
            else:
                print("\n1. Delegator waiting for subtasks to complete...")
            
            # After delegator, before verifier
            print("\n2. Finding tasks ready for processing...")
            ready_tasks = []
            for task_id, task in self.task_board.tasks.items():
                if task.status == TaskStatus.WAITING:
                    # Check if all dependencies are completed
                    deps_completed = all(
                        self.task_board.get_task(dep_id).status == TaskStatus.COMPLETED 
                        for dep_id in task.dependencies
                    ) if task.dependencies else True
                    
                    if deps_completed:
                        ready_tasks.append(task_id)

            if ready_tasks:
                print(f"   Ready tasks: {ready_tasks}")
                for task_id in ready_tasks:
                    task = self.task_board.get_task(task_id)
                    print(f"   Processing task {task_id}:")
                    print("   - Changing status to IN_PROGRESS")
                    task.status = TaskStatus.IN_PROGRESS
                    # Map task to swe_agent in task board
                    self.task_board.task_agent_mapping[task_id] = "swe_agent"
                    # Process task with existing agent
                    await self.swe_agent.process_task(task)
            else:
                print("\n2. No tasks ready for processing")
            
            # Check for tasks pending review
            print("\n3. Verifier checking pending reviews...")
            await self.verifier.check_pending_reviews()
            print("✓ Verifier finished checking")

            # Print current task statuses
            print("\n4. Current task statuses:")
            print("   ID | Status | Agent | Dependencies | Description")
            print("   " + "-" * 80)
            for task_id, task in self.task_board.tasks.items():
                agent_name = self.task_board.task_agent_mapping.get(task_id, "unassigned")
                deps = ", ".join([f"{dep_id}" for dep_id in task.dependencies]) or "none"
                desc = task.description[:50] + "..." if len(task.description) > 50 else task.description
                
                print(f"   {task_id:8} | {task.status.value:12} | {agent_name:8} | {deps:12} | {desc}")
            
            # Check completion status
            all_tasks_status = {
                TaskStatus.WAITING: 0,
                TaskStatus.IN_PROGRESS: 0,
                TaskStatus.PENDING_REVIEW: 0,
                TaskStatus.COMPLETED: 0,
                TaskStatus.RE_PROGRESS: 0
            }
            
            # Count tasks in each status
            for t in self.task_board.tasks.values():
                all_tasks_status[t.status] += 1
            
            # Check termination conditions
            if task.status == TaskStatus.COMPLETED:
                print("\n✓ Main task completed! Returning result.")
                if task.result:
                    if not task.result.startswith('diff --git'):
                        return self._format_as_git_diff(task.result)
                    return task.result
                return None
            
            # Check for stuck states
            if (all_tasks_status[TaskStatus.WAITING] == 0 and 
                all_tasks_status[TaskStatus.IN_PROGRESS] == 0 and
                all_tasks_status[TaskStatus.PENDING_REVIEW] == 0 and
                all_tasks_status[TaskStatus.RE_PROGRESS] > 0):
                print("\n⚠ Tasks stuck in RE_PROGRESS state. Terminating.")
                return None
                
            # Check if no progress is being made
            if (self.current_iteration > 0 and
                all_tasks_status[TaskStatus.IN_PROGRESS] == 0 and
                all_tasks_status[TaskStatus.PENDING_REVIEW] == 0):
                print("\n⚠ No tasks being processed. Terminating.")
                return None
            
            # Move RE_PROGRESS tasks back to IN_PROGRESS for next iteration
            re_progress_tasks = self.task_board.get_tasks_by_status(TaskStatus.RE_PROGRESS)
            for task in re_progress_tasks:
                print(f"\nRetrying task with feedback: {task.feedback}")  # Debug info
                self.task_board.update_task_status(task.id, TaskStatus.IN_PROGRESS)
            
            self.current_iteration += 1

        return None

    def _format_as_git_diff(self, patch_content: str) -> str:
        """Convert plain patch content to git diff format if needed"""
        if not patch_content.startswith('diff --git'):
            return f"diff --git a/file b/file\n--- a/file\n+++ b/file\n{patch_content}"
        return patch_content

async def main():
    # Example usage
    system = MultiAgentSystem(max_iterations=30)
    query = "Write me a bash script that prints hello world."
    print(f"Processing query: {query}")
    result = await system.process_query(query)
    print(f"Final Result: {result}")

if __name__ == "__main__":
    asyncio.run(main())

