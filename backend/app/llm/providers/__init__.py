"""Реестр реализаций провайдера по типу из БД."""

from app.core.enums import ProviderType
from app.llm.base import LLMProvider
from app.llm.providers.anthropic import AnthropicProvider
from app.llm.providers.cli import CLIProvider
from app.llm.providers.ollama import OllamaProvider
from app.llm.providers.openai_like import OpenAILikeProvider, OpenRouterProvider

REGISTRY: dict[str, type[LLMProvider]] = {
    ProviderType.OLLAMA: OllamaProvider,
    ProviderType.ANTHROPIC: AnthropicProvider,
    ProviderType.OPENAI: OpenAILikeProvider,
    ProviderType.OPENROUTER: OpenRouterProvider,
    ProviderType.CLI: CLIProvider,
}

__all__ = [
    "REGISTRY",
    "AnthropicProvider",
    "CLIProvider",
    "LLMProvider",
    "OllamaProvider",
    "OpenAILikeProvider",
    "OpenRouterProvider",
]
