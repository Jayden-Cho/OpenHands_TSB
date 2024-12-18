import pytest
from unittest.mock import Mock, patch
from ..state.task import Task, TaskStatus
from ..agents.delegator import DelegatorAgent
from ..agents.verifier import VerifierAgent
from ..llm.claude import Claude35LLM

@pytest.mark.asyncio
async def test_delegator_agent_decomposition(task_board, event_stream, mock_config):
    """Test task decomposition by DelegatorAgent"""
    # Mock LLM response
    mock_llm = Mock(spec=Claude35LLM)
    mock_llm.generate.return_value = """
    Subtask 1: Set up project structure
    Requirements: Create directory structure
    Dependencies: None

    Subtask 2: Implement core functionality
    Requirements: Write main function
    Dependencies: Subtask 1
    """
    
    delegator = DelegatorAgent(
        agent_id="test_delegator",
        llm=mock_llm,
        task_board=task_board,
        event_stream=event_stream
    )
    
    # Create test task
    test_task = Task(
        id="test",
        name="Test Task",
        description="Create a Python project",
        requirements=[],
        dependencies=[],
        status=TaskStatus.WAITING
    )
    
    # Process task
    await delegator.process_task(test_task)
    
    # Verify subtasks were created
    assert len(delegator.subtasks) > 0
    assert all(isinstance(task, Task) for task in delegator.subtasks)

@pytest.mark.asyncio
async def test_verifier_agent(task_board, event_stream, mock_config):
    """Test task verification by VerifierAgent"""
    # Mock LLM response
    mock_llm = Mock(spec=Claude35LLM)
    mock_llm.generate.return_value = "YES - The implementation meets all requirements."
    
    verifier = VerifierAgent(
        agent_id="test_verifier",
        llm=mock_llm,
        task_board=task_board,
        event_stream=event_stream
    )
    
    # Create test task
    test_task = Task(
        id="test",
        name="Test Task",
        description="Implement a function",
        requirements=["Must return integer"],
        dependencies=[],
        status=TaskStatus.PENDING_REVIEW,
        result="def func(): return 42"
    )
    
    task_board.add_task(test_task)
    
    # Verify task
    await verifier.verify_task(test_task)
    
    # Check if task status was updated
    assert test_task.status == TaskStatus.COMPLETED
