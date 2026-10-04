from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class LLMProvider(ABC):
    @abstractmethod
    def send(self, messages: List[Dict[str, Any]], tools: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Sends messages to the LLM and returns the response in a standardized format:
        {
            "type": "text" | "tool_call",
            "content": "...", # if type is text
            "name": "...", # if type is tool_call
            "arguments": {...}, # if type is tool_call
            "provider": "gemini" | "openai",
            "model": "model_name",
            "input_tokens": int,
            "output_tokens": int,
            "latency_ms": float
        }
        """
        pass

