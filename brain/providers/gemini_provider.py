import time
import json
import logging
from typing import List, Dict, Any, Optional
from google import genai
from google.genai import types
from config import GEMINI_API_KEY
from .base import LLMProvider

# Silence Google GenAI automatic function calling logger warning
logging.getLogger("google_genai.models").setLevel(logging.ERROR)
logging.getLogger("google.genai.models").setLevel(logging.ERROR)


class GeminiProvider(LLMProvider):
    def __init__(self, model="gemini-3.1-flash-lite"):
        self.model_name = model
        self.client = genai.Client(api_key=GEMINI_API_KEY)

    def _convert_messages(self, messages: List[Dict[str, Any]]) -> tuple[Optional[str], List[types.Content]]:
        system_instruction = None
        gemini_messages = []

        for msg in messages:
            role = msg.get("role")
            content = msg.get("content", "")

            if role == "system":
                system_instruction = content
                continue

            # Handle tool result messages
            if role == "tool":
                tool_name = msg.get("name", "tool")
                gemini_messages.append(
                    types.Content(
                        role="user",
                        parts=[types.Part.from_text(text=f"[Hasil Tool '{tool_name}']: {content}\nRingkas hasil ini dan jawab pertanyaan pengguna secara ramah dan ringkas.")]
                    )
                )
                continue

            # Handle assistant messages with tool calls
            if role == "assistant" and msg.get("tool_calls"):
                tool_names = [tc.get("name") or tc.get("function", {}).get("name", "tool") for tc in msg.get("tool_calls", [])]
                text_content = content if (isinstance(content, str) and content) else f"Menjalankan tool: {', '.join(tool_names)}"
                gemini_messages.append(
                    types.Content(
                        role="model",
                        parts=[types.Part.from_text(text=text_content)]
                    )
                )
                continue

            if isinstance(content, str) and content:
                gemini_role = "user" if role == "user" else "model"
                gemini_messages.append(
                    types.Content(role=gemini_role, parts=[types.Part.from_text(text=content)])
                )

        return system_instruction, gemini_messages

    def _convert_tools(self, tools: Optional[List[Dict[str, Any]]]) -> Optional[types.Tool]:
        if not tools:
            return None
        declarations = []
        for tool in tools:
            func = tool.get("function", {})
            declarations.append(
                types.FunctionDeclaration(
                    name=func.get("name"),
                    description=func.get("description", ""),
                    parameters=func.get("parameters", {"type": "object", "properties": {}}),
                )
            )
        return types.Tool(function_declarations=declarations)

    def send(self, messages: List[Dict[str, Any]], tools: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        system_instruction, gemini_msgs = self._convert_messages(messages)
        gemini_tool = self._convert_tools(tools)

        config_kwargs: Dict[str, Any] = {}
        if system_instruction:
            config_kwargs["system_instruction"] = system_instruction
        if gemini_tool:
            config_kwargs["tools"] = [gemini_tool]

        last_err = None
        for attempt in range(2):
            try:
                start_time = time.perf_counter()
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=gemini_msgs,
                    config=types.GenerateContentConfig(**config_kwargs) if config_kwargs else None,
                )
                latency_ms = (time.perf_counter() - start_time) * 1000
                break
            except Exception as e:
                last_err = e
                if "503" in str(e) and attempt == 0:
                    time.sleep(1.0)
                    continue
                raise e

        # Extract token usage if available
        input_tokens = 0
        output_tokens = 0
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            input_tokens = getattr(response.usage_metadata, "prompt_token_count", 0) or 0
            output_tokens = getattr(response.usage_metadata, "candidates_token_count", 0) or 0

        base_meta = {
            "provider": "gemini",
            "model": self.model_name,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "latency_ms": round(latency_ms, 2)
        }

        if not response.candidates:
            return {
                "type": "text",
                "content": "Error: No response from Gemini.",
                **base_meta
            }

        candidate = response.candidates[0]
        tool_calls_list = []
        text_parts = []

        if candidate.content and candidate.content.parts:
            for p in candidate.content.parts:
                if getattr(p, "function_call", None):
                    fc = p.function_call
                    args = {key: val for key, val in fc.args.items()} if fc.args else {}
                    tool_calls_list.append({
                        "id": f"call_{len(tool_calls_list) + 1}",
                        "name": fc.name,
                        "arguments": args
                    })
                elif getattr(p, "text", None):
                    text_parts.append(p.text)

        if tool_calls_list:
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
                "content": "".join(text_parts).strip() if text_parts else "",
                **base_meta
            }

