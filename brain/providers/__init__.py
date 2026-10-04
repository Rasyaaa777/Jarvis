from .base import LLMProvider
from .openai_provider import OpenAIProvider
from .gemini_provider import GeminiProvider

def get_provider(provider_name: str) -> LLMProvider:
    if provider_name.lower() == "openai":
        return OpenAIProvider()
    elif provider_name.lower() == "gemini":
        return GeminiProvider()
    else:
        raise ValueError(f"Unknown provider: {provider_name}")
