# adapters/swebench_adapter.py
from typing import Dict, Optional
from core.main import MultiAgentSystem
from llm.llm import Claude35LLM
from state.task import Task, TaskStatus
from dotenv import load_dotenv
import os
import json

class SWEBenchAdapter:
    def __init__(self, max_iterations: int = 30):
        load_dotenv()  # Load API key at initialization
        self.api_key = os.getenv('ANTHROPIC_API_KEY')
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment variables")
        self.system = MultiAgentSystem(max_iterations=max_iterations)
    
    async def process_swebench_instance(self, instance: Dict) -> Dict:
        """
        Process a SWE-bench instance through the multi-agent system by adapting it to our Task structure
        
        Args:
            instance: Dict containing SWE-bench instance data with structure:
            {
                "repo": "owner/repo",
                "instance_id": "unique_id",
                "base_commit": "commit_hash",
                "patch": "git diff...",
                "test_patch": "test diff...",
                "problem_statement": "description...",
                "hints_text": "optional hints..."
            }
        
        Returns:
            Dict containing:
                - instance_id: str
                - patch: str (git diff format)
        """
        # Create Task object from SWE-bench instance
        task = Task(
            id=instance['instance_id'],
            name=f"Bug fix for {instance['repo']}",
            description=instance['problem_statement'],
            requirements=[
                f"Repository: {instance['repo']}",
                f"Base Commit: {instance['base_commit']}",
                f"Hints: {instance.get('hints_text', 'No hints provided')}",
                f"Created At: {instance.get('created_at', 'Not specified')}",
                f"Version: {instance.get('version', 'Not specified')}",
                f"Tests to Fix: {json.loads(instance.get('FAIL_TO_PASS', '[]'))}",
                f"Tests to Keep Passing: {json.loads(instance.get('PASS_TO_PASS', '[]'))}",
                f"Environment Setup Commit: {instance.get('environment_setup_commit', instance['base_commit'])}"
            ],
            dependencies=[],  # No dependencies for SWE-bench tasks
            status=TaskStatus.WAITING
        )
        
        # Use system's task board instead of direct task board access
        self.system.task_board.add_task(task)
        result = await self.system.process_query(task)
        
        return {
            'instance_id': instance['instance_id'],
            'patch': result
        }
    
