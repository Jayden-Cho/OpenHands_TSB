from abc import ABC, abstractmethod
from typing import Dict, Optional
from anthropic import Anthropic, HUMAN_PROMPT, AI_PROMPT
from dotenv import load_dotenv
import os

class LLM(ABC):
    def __init__(self, model_name: str, config: Optional[Dict] = None):
        self.model_name = model_name
        self.config = config or {}

    @abstractmethod
    async def generate(self, prompt: str) -> str:
        """Generate response from the LLM"""
        pass

class Claude35LLM(LLM):
    def __init__(self, model_name: str, config: Optional[Dict] = None):
        super().__init__("claude-3.5-sonnet", config)
        self.model_name = model_name
        
        # Load API key from environment
        load_dotenv()
        self.api_key = os.getenv('ANTHROPIC_API_KEY')
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment variables")
        
        self.claude = Anthropic(api_key=self.api_key)
   
    async def generate(self, prompt: str) -> str:
        response = self.claude.messages.create(
            model=self.model_name,
            max_tokens=1024,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )
        return response.content[0].text # return response['completion']
