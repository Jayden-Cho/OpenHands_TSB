from typing import Optional
from agents.base import BaseAgent
from state.task import Task, TaskStatus
from events.action import TaskAction
from events.observation import TaskObservation

class SWEAgent(BaseAgent):
    async def process_task(self, task: Task) -> None:
        """Process software engineering tasks"""
        # Get context from dependent tasks if any
        context = self._gather_dependency_context(task)
        
        # Generate solution using LLM
        prompt = self._create_task_prompt(task, context)
        solution = await self.llm.generate(prompt)
        
        # Record action and observation
        action = TaskAction(
            action_type="generate_solution",
            content=prompt,
            task_id=task.id,
            agent_id=self.agent_id
        )
        
        observation = TaskObservation(
            content=solution,
            success=True,
            task_id=task.id,
            agent_id=self.agent_id
        )
        
        # Update task with results
        task.result = solution
        task.update_context(str(action), str(observation))
        
        # Update status to PENDING_REVIEW
        self.update_task_status(task.id, TaskStatus.PENDING_REVIEW)

    def _gather_dependency_context(self, task: Task) -> str:
        """Gather context from dependent tasks"""
        context = []
        for dep_id in task.dependencies:
            dep_task = self.task_board.get_task(dep_id)
            if dep_task and dep_task.status == TaskStatus.COMPLETED:
                context.append(f"Dependency {dep_id}: {dep_task.result}")
        return "\n".join(context)

    def _create_task_prompt(self, task: Task, context: str) -> str:
        """Create prompt for the LLM"""
        prompt = f"""
        Given the following bug fix task:
        {task.description}

        and the requirements:
        {chr(10).join(task.requirements)}

        plus the previous context:
        {context}

        as well as previous feedback:
        {task.feedback if task.feedback else "No previous feedback"}

        You need to come up with a solution following some CRITICAL RESPONSE FORMAT INSTRUCTIONS:
        You must respond ONLY with a git diff patch. Your entire response must:
        1. Start with 'diff --git'
        2. Follow standard git diff format
        3. Include ZERO explanatory text or markdown
        4. Include ONLY implementation changes (no test changes)

        Example of CORRECT response format:
        diff --git a/astropy/wcs/wcsapi/fitswcs.py b/astropy/wcs/wcsapi/fitswcs.py
        --- a/astropy/wcs/wcsapi/fitswcs.py
        +++ b/astropy/wcs/wcsapi/fitswcs.py
        @@ -323,7 +323,17 @@ def pixel_to_world_values(self, *pixel_arrays):
             return world[0] if self.world_n_dim == 1 else tuple(world)

        Example of INCORRECT response format:
        Here's the solution to fix the bug:
        ```diff
        diff --git a/file b/file
        ...
        ```
        This change handles the error by...

        YOUR RESPONSE MUST START DIRECTLY WITH 'diff --git' AND CONTAIN NOTHING ELSE EXCEPT THE PATCH.

        Please solve the task following the instructions and consider all helper functions in the base code. 
        """
        return prompt

    async def execute_task(self, task: Task) -> Optional[str]:
        """
        Returns:
            str: Solution in git diff format:
            Example:
            diff --git a/file b/file
            --- a/file
            +++ b/file
            @@ ... @@
            <changes>
        """
