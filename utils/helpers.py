from typing import List, Dict, Any
import json
from ..state.task import Task, TaskStatus
from ..core.logger import Logger

logger = Logger.get_logger()

def parse_llm_subtasks(llm_response: str) -> List[Dict[str, Any]]:
    """Parse LLM response into structured subtask data"""
    try:
        # Split response into subtask blocks
        subtask_blocks = [block.strip() for block in llm_response.split('Subtask') if block.strip()]
        
        parsed_tasks = []
        for block in subtask_blocks:
            # Extract task components
            lines = block.split('\n')
            task_data = {
                'name': lines[0].split(':', 1)[1].strip() if ':' in lines[0] else lines[0].strip(),
                'requirements': [],
                'dependencies': []
            }
            
            # Parse requirements and dependencies
            for line in lines[1:]:
                if 'Requirements:' in line:
                    reqs = line.split('Requirements:', 1)[1].strip()
                    task_data['requirements'] = [r.strip() for r in reqs.split(',')]
                elif 'Dependencies:' in line:
                    deps = line.split('Dependencies:', 1)[1].strip()
                    if deps.lower() != 'none':
                        task_data['dependencies'] = [d.strip() for d in deps.split(',')]
            
            parsed_tasks.append(task_data)
            
        return parsed_tasks
        
    except Exception as e:
        logger.error(f"Error parsing LLM subtasks: {str(e)}")
        raise ValueError(f"Failed to parse LLM response: {str(e)}")

def create_task_from_dict(task_data: Dict[str, Any], task_id: str) -> Task:
    """Create Task instance from parsed data"""
    return Task(
        id=task_id,
        name=task_data['name'],
        description=task_data['name'],  # Using name as description for simplicity
        requirements=task_data['requirements'],
        dependencies=task_data['dependencies'],
        status=TaskStatus.WAITING
    )

def serialize_task(task: Task) -> str:
    """Serialize task to JSON string"""
    task_dict = {
        'id': task.id,
        'name': task.name,
        'description': task.description,
        'requirements': task.requirements,
        'dependencies': task.dependencies,
        'status': task.status.value,
        'result': task.result
    }
    return json.dumps(task_dict)

def deserialize_task(task_json: str) -> Task:
    """Deserialize task from JSON string"""
    task_dict = json.loads(task_json)
    return Task(
        id=task_dict['id'],
        name=task_dict['name'],
        description=task_dict['description'],
        requirements=task_dict['requirements'],
        dependencies=task_dict['dependencies'],
        status=TaskStatus(task_dict['status']),
        result=task_dict.get('result')
    )
