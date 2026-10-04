import time
import json
import openai
from typing import List, Dict, Any, Optional
from config import OPENAI_API_KEY
from .base import LLMProvider


class OpenAIProvider(LLMProvider):
    def __init__(self, model="gpt-4o-mini"):
        self.model_name = model
        self.client = openai.OpenAI(api_key=OPENAI_API_KEY)

    def send(self, messages: List[Dict[str, Any]], tools: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        kwargs = {
            "model": self.model_name,
            "messages": messages,
        }
        if tools:
            kwargs["tools"] = tools

        start_time = time.perf_counter()
        response = self.client.chat.completions.create(**kwargs)
        latency_ms = (time.perf_counter() - start_time) * 1000

        input_tokens = 0
        output_tokens = 0
        if hasattr(response, "usage") and response.usage:
            input_tokens = getattr(response.usage, "prompt_tokens", 0) or 0
            output_tokens = getattr(response.usage, "completion_tokens", 0) or 0

        base_meta = {
            "provider": "openai",
            "model": self.model_name,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "latency_ms": round(latency_ms, 2)
        }

        message = response.choices[0].message

        if message.tool_calls:
            tool_calls_list = []
            for tc in message.tool_calls:
                try:
                    args = json.loads(tc.function.arguments)
                except Exception:
                    args = {}
                tool_calls_list.append({
                    "id": tc.id,
                    "name": tc.function.name,
                    "arguments": args
                })

            return {
                "type": "tool_call",
                "name": tool_calls_list[0]["name"],
                "arguments": tool_calls_list[0]["arguments"],
                "tool_calls": tool_calls_list,
                **base_meta
            }
        else:
            return {
                "type": "text",
                "content": message.content or "",
                **base_meta
            }

