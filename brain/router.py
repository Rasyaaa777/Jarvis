import os
import json
import re
import threading
from typing import List, Dict, Any, Optional
from config import ACTIVE_PROVIDER, OPENAI_API_KEY, GEMINI_API_KEY, SYSTEM_PROMPT_PATH, PRICING_PATH
from brain.providers import get_provider, LLMProvider
import brain.tools as tools_module
from memory.facts import get_facts_context, auto_extract_facts
from usage.tracker import log_usage, log_feedback, check_budget_status


class IntentRouter:
    def __init__(self):
        self.active_provider_name = (ACTIVE_PROVIDER or "gemini").lower()
        self.provider: LLMProvider = get_provider(self.active_provider_name)
        self.tools = tools_module.get_all_tools()
        self.pricing = self._load_pricing()

    def _load_base_prompt(self) -> str:
        """Loads base persona prompt from system_prompt.txt, or falls back to default."""
        if os.path.exists(SYSTEM_PROMPT_PATH):
            try:
                with open(SYSTEM_PROMPT_PATH, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if content:
                        return content
            except Exception:
                pass
        return (
            "You are JARVIS, an intelligent, helpful, and polite personal AI assistant for Windows. "
            "Keep your responses concise and natural. Use registered tools whenever the user's intent requires an action."
        )

    def _load_pricing(self) -> Dict[str, Any]:
        """Loads pricing configuration from pricing.json."""
        if os.path.exists(PRICING_PATH):
            try:
                with open(PRICING_PATH, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "gemini": {"default": {"input_per_million": 0.10, "output_per_million": 0.40}},
            "openai": {"default": {"input_per_million": 0.15, "output_per_million": 0.60}}
        }

    def _get_full_system_prompt(self) -> str:
        """Injects long-term memory facts dynamically into the system prompt loaded from file."""
        base = self._load_base_prompt()
        facts_context = get_facts_context()
        if facts_context:
            return f"{base}\n\n{facts_context}"
        return base

    def switch_provider(self, new_provider: str) -> str:
        """Dynamically switches active LLM provider (gemini or openai)."""
        target = new_provider.lower().strip()
        if "gemini" in target or "google" in target:
            if not GEMINI_API_KEY:
                return "Gagal beralih: GEMINI_API_KEY belum disetel di file .env."
            self.active_provider_name = "gemini"
            self.provider = get_provider("gemini")
            return "Berhasil beralih ke model Gemini (gemini-3.6-flash)."
        elif "openai" in target or "gpt" in target:
            if not OPENAI_API_KEY:
                return "Gagal beralih: OPENAI_API_KEY belum disetel di file .env."
            self.active_provider_name = "openai"
            self.provider = get_provider("openai")
            return "Berhasil beralih ke model OpenAI (gpt-4o-mini)."
        else:
            return f"Provider '{new_provider}' tidak dikenali. Pilih antara 'gemini' atau 'openai'."

    def _check_switch_command(self, user_text: str) -> Optional[str]:
        """Checks if the user requested a provider switch."""
        text = user_text.lower().strip()
        patterns = [
            r"^(?:switch\s+to|ganti\s+(?:model|provider)\s+ke|pakai|gunakan)\s+(gemini|openai|gpt|google)",
            r"^(?:ganti\s+ke)\s+(gemini|openai|gpt|google)"
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                target = match.group(1)
                return self.switch_provider(target)
        return None

    def _estimate_cost(self, provider: str, model: str, input_tokens: int, output_tokens: int) -> float:
        """Calculates cost in USD using pricing.json."""
        prov_data = self.pricing.get(provider.lower(), {})
        model_rates = prov_data.get(model, prov_data.get("default", {"input_per_million": 0.15, "output_per_million": 0.60}))
        in_rate = model_rates.get("input_per_million", 0.15)
        out_rate = model_rates.get("output_per_million", 0.60)
        return ((input_tokens / 1_000_000) * in_rate) + ((output_tokens / 1_000_000) * out_rate)

    def _send_with_fallback(self, messages: List[Dict[str, Any]], tools: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Sends request to active provider with auto-fallback to alternative provider on failure."""
        primary_name = self.active_provider_name
        try:
            return self.provider.send(messages, tools=tools)
        except Exception as primary_error:
            # Determine fallback provider
            fallback_name = "openai" if primary_name == "gemini" else "gemini"
            fallback_key = OPENAI_API_KEY if fallback_name == "openai" else GEMINI_API_KEY

            log_usage(
                provider=primary_name,
                model="unknown",
                input_tokens=0,
                output_tokens=0,
                estimated_cost=0.0,
                latency_ms=0,
                status="error",
                error_message=str(primary_error)
            )

            if not fallback_key:
                raise primary_error

            print(f"[Warning] Primary provider '{primary_name}' failed: {primary_error}. Falling back to '{fallback_name}'...")
            try:
                fallback_provider = get_provider(fallback_name)
                response = fallback_provider.send(messages, tools=tools)
                response["is_fallback"] = True
                response["fallback_from"] = primary_name
                return response
            except Exception as fallback_error:
                raise RuntimeError(f"Both primary ({primary_name}: {primary_error}) and fallback ({fallback_name}: {fallback_error}) failed.")

    def process_messages(self, messages: List[Dict[str, Any]]) -> str:
        # Check if last user message was a switch command or feedback
        last_user_msg = next((m["content"] for m in reversed(messages) if m.get("role") == "user"), "").strip()
        
        # Support quick feedback tags (:good / :bad)
        if last_user_msg.lower() in [":good", ":bad", ":bagus", ":jelek"]:
            tag = "good" if last_user_msg.lower() in [":good", ":bagus"] else "bad"
            log_feedback(tag)
            return f"Terima kasih atas penilaian Anda! Feedback '{tag}' berhasil dicatat di sistem."

        switch_result = self._check_switch_command(last_user_msg)
        if switch_result:
            return switch_result

        # Update or set system prompt with latest memory facts
        current_system_prompt = self._get_full_system_prompt()
        if not messages or messages[0].get("role") != "system":
            messages.insert(0, {"role": "system", "content": current_system_prompt})
        else:
            messages[0]["content"] = current_system_prompt

        response = self._send_with_fallback(messages, tools=self.tools)

        # Log usage to SQLite database
        in_tokens = response.get("input_tokens", 0)
        out_tokens = response.get("output_tokens", 0)
        provider_name = response.get("provider", self.active_provider_name)
        model_name = response.get("model", "unknown")
        cost = self._estimate_cost(provider_name, model_name, in_tokens, out_tokens)
        log_usage(
            provider=provider_name,
            model=model_name,
            input_tokens=in_tokens,
            output_tokens=out_tokens,
            estimated_cost=cost,
            tool_called=response.get("name") if response.get("type") == "tool_call" else None,
            latency_ms=response.get("latency_ms", 0),
            status="ok"
        )

        # Check for budget alerts
        budget_alert = ""
        b_status = check_budget_status()
        if b_status.get("alert_message"):
            budget_alert = f"\n\n[Budget Alert: {b_status['alert_message']}]"

        prefix = ""
        if response.get("is_fallback"):
            prefix = f"[Auto-fallback ke {response.get('provider')}] "

        # Asynchronously extract new durable user facts in background
        try:
            threading.Thread(
                target=auto_extract_facts,
                args=(messages.copy(), self.provider),
                daemon=True
            ).start()
        except Exception:
            pass

        if response["type"] == "text":
            return prefix + response.get("content", "") + budget_alert

        elif response["type"] == "tool_call":
            raw_tool_calls = response.get("tool_calls") or [
                {"id": "call_1", "name": response["name"], "arguments": response.get("arguments", {})}
            ]

            assistant_tool_calls = []
            tool_results_list = []

            for idx, tc in enumerate(raw_tool_calls):
                call_id = tc.get("id") or f"call_{idx + 1}"
                t_name = tc.get("name")
                t_args = tc.get("arguments") or {}

                print(f"JARVIS is running tool: {t_name}({t_args})")
                t_res = tools_module.execute_tool(t_name, t_args)

                assistant_tool_calls.append({
                    "id": call_id,
                    "type": "function",
                    "function": {"name": t_name, "arguments": json.dumps(t_args) if isinstance(t_args, dict) else str(t_args)}
                })
                tool_results_list.append({
                    "id": call_id,
                    "name": t_name,
                    "result": str(t_res)
                })

            # Record assistant turn with all tool calls
            messages.append({
                "role": "assistant",
                "content": "",
                "tool_calls": assistant_tool_calls
            })

            # Record each tool result turn
            for tr in tool_results_list:
                messages.append({
                    "role": "tool",
                    "tool_call_id": tr["id"],
                    "name": tr["name"],
                    "content": tr["result"]
                })

            combined_results_str = "\n".join([f"[{tr['name']}]: {tr['result']}" for tr in tool_results_list])

            # Request summary/final answer
            try:
                final_response = self._send_with_fallback(messages)
                final_in = final_response.get("input_tokens", 0)
                final_out = final_response.get("output_tokens", 0)
                final_prov = final_response.get("provider", self.active_provider_name)
                final_model = final_response.get("model", "unknown")
                final_cost = self._estimate_cost(final_prov, final_model, final_in, final_out)

                log_usage(
                    provider=final_prov,
                    model=final_model,
                    input_tokens=final_in,
                    output_tokens=final_out,
                    estimated_cost=final_cost,
                    latency_ms=final_response.get("latency_ms", 0),
                    status="ok"
                )
                return prefix + final_response.get("content", combined_results_str) + budget_alert
            except Exception:
                return prefix + combined_results_str + budget_alert


