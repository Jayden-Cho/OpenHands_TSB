from abc import ABC, abstractmethod
from typing import Optional, Any
import asyncio
from events.event_stream import EventStream
from state.task import Task, TaskStatus
from state.board import TaskStatusBoard
from llm.llm import LLM
from core.logger import Logger

logger = Logger.get_logger()

class AgentError(Exception):
    """Base class for agent-related errors"""
    pass

class TaskProcessingError(AgentError):
    """Error occurred during task processing"""
    pass

class LLMError(AgentError):
    """Error occurred during LLM interaction"""
    pass

class BaseAgent(ABC):
    def __init__(self, 
                 agent_id: str,
                 llm: LLM,
                 task_board: TaskStatusBoard,
                 event_stream: EventStream,
                 max_retries: int = 3,
                 retry_delay: float = 1.0):
        self.agent_id = agent_id
        self.llm = llm
        self.task_board = task_board
        self.event_stream = event_stream
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.logger = Logger.get_logger()

    @abstractmethod
    async def process_task(self, task: Task) -> None:
        """Process assigned task"""
        pass

    async def retry_with_backoff(self, func: callable, *args, **kwargs) -> Any:
        """Execute function with exponential backoff retry"""
        last_error = None
        for attempt in range(self.max_retries):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    delay = self.retry_delay * (2 ** attempt)  # Exponential backoff
                    self.logger.warning(
                        f"Attempt {attempt + 1} failed for {func.__name__}. "
                        f"Retrying in {delay} seconds. Error: {str(e)}"
                    )
                    await asyncio.sleep(delay)
                else:
                    self.logger.error(
                        f"All retry attempts failed for {func.__name__}. "
                        f"Final error: {str(e)}"
                    )
        
        raise last_error

    def update_task_status(self, task_id: str, new_status: TaskStatus) -> None:
        """Update task status in the board"""
        try:
            self.task_board.update_task_status(task_id, new_status)
            # self.logger.info(f"Task {task_id} status updated to {new_status}")
        except Exception as e:
            self.logger.error(f"Failed to update task status: {str(e)}")
            raise TaskProcessingError(f"Failed to update task status: {str(e)}")

    def get_task_context(self, task_id: str) -> Optional[Task]:
        """Get task context from the board"""
        try:
            return self.task_board.get_task(task_id)
        except Exception as e:
            self.logger.error(f"Failed to get task context: {str(e)}")
            raise TaskProcessingError(f"Failed to get task context: {str(e)}")

    async def safe_llm_call(self, prompt: str) -> str:
        """Make a safe LLM call with retry logic"""
        try:
            return await self.retry_with_backoff(self.llm.generate, prompt)
        except Exception as e:
            self.logger.error(f"LLM call failed after all retries: {str(e)}")
            raise LLMError(f"LLM call failed: {str(e)}")