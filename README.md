# OpenHands Prototype

A simplified multi-agent system prototype inspired by OpenHands, designed for handling software engineering tasks.

## Overview

This prototype implements a Task Status Board (TSB) based multi-agent system with the following key components:

- **DelegatorAgent**: Decomposes tasks and manages workflow
- **VerifierAgent**: Verifies task completions
- **SWEAgent**: Handles software engineering tasks
- **Task Status Board**: Manages task states and dependencies
- **Event Stream**: Tracks system events and agent interactions

## Setup

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Set up environment variables: `cp .env.example .env` and fill in your API keys
4. Run the prototype: `python -m OpenHands_Prototype.examples.simple_workflow`

## Usage

```python
from OpenHands_Prototype.core.main import MultiAgentSystem
import asyncio
async def main():
system = MultiAgentSystem(max_iterations=10)
result = await system.process_query("Your task description")
print(result)
if name == "main":
asyncio.run(main())
```

This example demonstrates how to initialize the multi-agent system and process a task. Adjust the `max_iterations` parameter as needed for your specific use case.

## Task Status Flow

1. **WAITING**: Initial state for decomposed tasks
2. **IN_PROGRESS**: Task being processed by an agent
3. **PENDING_REVIEW**: Completed task awaiting verification
4. **COMPLETED**: Successfully verified task
5. **RE_PROGRESS**: Task needs rework

## Testing

Run tests using pytest: `pytest OpenHands_Prototype/tests/`


## License

This project is open-sourced under the MIT License - see the LICENSE file for details.