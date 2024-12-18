# test_llm.py
from anthropic import Anthropic
from dotenv import load_dotenv
import os

def test_claude():
    load_dotenv()
    
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not found in environment variables")
        
    anthropic = Anthropic(api_key=api_key)
    
    # Test with a small code snippet first
    test_input = """
    Here's a simple Python bug to fix:
    ```python
    def add_numbers(a, b):
        return a - b  # Bug: should be addition
    ```
    Please fix this code.
    """
    
    try:
        response = anthropic.messages.create(
            model="claude-3-opus-20240229",
            max_tokens=1000,
            messages=[{
                "role": "user",
                "content": test_input
            }]
        )
        print("Basic API Test:", response.content)
        
        # Test with larger context (simulating real SWE-bench input)
        with open("SWE-bench/README.md", "r") as f:
            large_input = f.read()
        
        response = anthropic.messages.create(
            model="claude-3-opus-20240229",
            max_tokens=1000,
            messages=[{
                "role": "user",
                "content": f"Here's a README file: {large_input}\nSummarize this in one sentence."
            }]
        )
        print("\nLarge Context Test:", response.content)
        
        print("\nAll tests passed successfully!")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_claude()