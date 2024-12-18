from typing import Dict, Optional
import anthropic
from llm.llm import LLM
from core.logger import Logger

logger = Logger.get_logger()

class ClaudeError(Exception):
    """Base class for Claude-related errors"""
    pass

class Claude35LLM(LLM):
    def __init__(self, config: Optional[Dict] = None):
        super().__init__("claude-3.5-sonnet", config)
        self.api_key = config.get('api_key') or self._get_api_key()
        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.max_tokens = config.get('max_tokens', 4096)
        self.temperature = config.get('temperature', 0.7)

    def _get_api_key(self) -> str:
        """Get API key from environment variable"""
        import os
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            raise ClaudeError("ANTHROPIC_API_KEY environment variable not set")
        return api_key

    async def generate(self, prompt: str) -> str:
        """Generate response using Claude API"""
        try:
            logger.debug(f"Sending prompt to Claude: {prompt[:100]}...")
            
            message = await self.client.messages.create(
                model=self.model_name,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            response = message.content[0].text
            logger.debug(f"Received response from Claude: {response[:100]}...")
            
            return response
            
        except anthropic.APIError as e:
            logger.error(f"Claude API error: {str(e)}")
            raise ClaudeError(f"Claude API error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error in Claude API call: {str(e)}")
            raise ClaudeError(f"Unexpected error: {str(e)}")
