from typing import List
from agents.base import BaseAgent
from events.event_stream import EventStream
from state.task import Task, TaskStatus
from events.action import MessageAction
import uuid
import sys
from agents.swe_agent import SWEAgent 
from llm.llm import Claude35LLM


class DelegatorAgent(BaseAgent):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.subtasks: List[Task] = []

    async def decompose_query(self, query: str) -> List[Task]:
        """Decompose the initial query into subtasks using LLM"""
        prompt = f"""
        Decompose the following task into subtasks:
        {query}
        
        For each subtask, provide:
        1. subtask id
        2. A clear description
        3. Requirements
        4. Dependencies (if any. this should be a list of subtask ids)

        Try to keep the subtasks as small as possible.

        Example: 

        Subtask 1:
        1. Subtask ID: 1
        2. Description: Define the Fibonacci sequence.
        3. Requirements: Understand the mathematical definition of the Fibonacci sequence, where each number is the sum of the two preceding ones, and the first two numbers are 0 and 1.
        4. Dependencies: []

        Subtask 2:
        1. Subtask ID: 2
        2. Description: Determine the function signature.
        3. Requirements: Decide whether the function will take an argument (e.g., the number of Fibonacci numbers to generate) or return a specific number in the sequence.
        4. Dependencies: [1]

        Subtask 3:
        1. Subtask ID: 3
        2. Description: Initialize the base cases for the Fibonacci sequence.
        3. Requirements: Set the initial values for the first two numbers in the sequence (0 and 1).
        4. Dependencies: [2]

        """
        
        response = await self.llm.generate(prompt)
        # Parse LLM response, create Task objects, and add them to the task board
        self._parse_subtasks(response)    

    async def process_task(self, task: Task) -> None:
        """Main processing loop for DelegatorAgent"""
        # Get all tasks except main task
        subtasks = [t for tid, t in self.task_board.tasks.items() if tid != "main"]
        
        if not subtasks:
            # Initial decomposition
            await self.decompose_query(task.description)
        elif self.task_board.all_tasks_completed():
            # All subtasks completed, aggregate results
            final_result = await self._aggregate_results()
            task.result = final_result
            self.update_task_status(task.id, TaskStatus.COMPLETED)

    async def _aggregate_results(self) -> str:
        """Aggregate results from all completed subtasks"""
        results = []
        subtasks = [task for task_id, task in self.task_board.tasks.items() if task_id != "main"]
        
        for task in subtasks:
            if task.status == TaskStatus.COMPLETED:
                results.append(f"Subtask {task.id}:\n- Description: {task.description}\n- Result: {task.result}")
        

        prompt = f"""
        You are tasked with combining the results of multiple subtasks into a cohesive final solution.

        Original Task:
        {self.task_board.get_task("main").description}

        Completed Subtask Results:
        {"\n".join(results)}

        Please provide a final solution that:
        1. Combines all subtask results into a single, coherent solution
        2. Ensures all requirements from the original task are met
        3. Includes any necessary documentation or explanations
        4. Maintains consistency across all components
        5. Resolves any potential conflicts between subtask solutions

        Format your response as a complete, production-ready solution that directly addresses the original task.
        If the solution includes code, ensure it's properly formatted and documented.
        """
        
        final_result = await self.llm.generate(prompt)
        return final_result

    def _parse_subtasks(self, decomposition_text: str):
        """Parse LLM response into Task objects"""
        subtasks = []
        current_subtask = {}

        # Split text into lines and remove empty lines
        lines = [line.strip() for line in decomposition_text.split('\n') if line.strip()]
        for line in lines:
            if line.startswith('Subtask'):
                # If we have a previous subtask, add it to our list
                if current_subtask:
                    subtask = Task(
                        id=str(current_subtask['id']),
                        name=f"Subtask {current_subtask['id']}",
                        description=current_subtask.get('description', ''),
                        requirements=current_subtask.get('requirements', []),
                        dependencies=current_subtask.get('dependencies', []),
                        status=TaskStatus.WAITING,
                        assigned_agent='swe_agent'
                    )
                    self.task_board.add_task(subtask)
                    self.task_board.assign_task_to_agent(subtask.id, subtask.assigned_agent)
                current_subtask = {}
            elif line.startswith('1. Subtask ID:'):
                current_subtask['id'] = line.split(':')[1].strip()
            elif line.startswith('2. Description:'):
                current_subtask['description'] = line.split(':')[1].strip()
            elif line.startswith('3. Requirements:'):
                current_subtask['requirements'] = [line.split(':')[1].strip()]
            elif line.startswith('4. Dependencies:'):
                # Parse dependencies string (e.g., "[1]" or "[1, 2]")
                deps_str = line.split(':')[1].strip()
                deps = eval(deps_str)  # Convert string representation of list to actual list
                current_subtask['dependencies'] = [str(d) for d in deps]  # Convert to string IDs
        

        for task in subtasks:
            self.task_board.add_task(task)