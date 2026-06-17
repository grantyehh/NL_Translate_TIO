from __future__ import annotations

import os
from pathlib import Path

from openai import OpenAI


DEFAULT_CHAT_MODEL = "gpt-5.4"
DEFAULT_AZURE_CHAT_DEPLOYMENT = "gpt-5.4-nano"
DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"
DEFAULT_AZURE_ENDPOINT = "https://cht-tio.services.ai.azure.com/openai/v1"
DEFAULT_AZURE_TOKEN_SCOPE = "https://ai.azure.com/.default"


def load_project_env(path: str | Path | None = None) -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return

    env_path = Path(path) if path is not None else Path(__file__).resolve().parent / ".env"
    load_dotenv(env_path, override=True)


def provider() -> str:
    return os.getenv("OPENAI_PROVIDER", "openai").strip().lower()


def is_azure() -> bool:
    return provider() in {"azure", "azure_openai", "azure-openai"}


def chat_model(default: str = DEFAULT_CHAT_MODEL) -> str:
    if is_azure():
        return (
            os.getenv("AZURE_OPENAI_DEPLOYMENT")
            or os.getenv("OPENAI_CHAT_MODEL")
            or DEFAULT_AZURE_CHAT_DEPLOYMENT
        )
    return os.getenv("OPENAI_CHAT_MODEL") or os.getenv("GRAPHRAG_LLM_MODEL") or default


def embedding_model(default: str = DEFAULT_EMBEDDING_MODEL) -> str:
    if is_azure():
        return (
            os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")
            or os.getenv("OPENAI_EMBEDDING_MODEL")
            or default
        )
    return os.getenv("OPENAI_EMBEDDING_MODEL") or default


def _azure_token_provider():
    try:
        from azure.identity import DefaultAzureCredential, get_bearer_token_provider
    except ImportError as exc:
        raise RuntimeError(
            "Azure provider requires azure-identity. Install with: "
            "python -m pip install azure-identity"
        ) from exc

    return get_bearer_token_provider(
        DefaultAzureCredential(),
        os.getenv("AZURE_OPENAI_TOKEN_SCOPE", DEFAULT_AZURE_TOKEN_SCOPE),
    )


def create_client() -> OpenAI:
    if is_azure():
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", DEFAULT_AZURE_ENDPOINT)
        api_key = os.getenv("AZURE_OPENAI_API_KEY") or _azure_token_provider()
        return OpenAI(base_url=endpoint, api_key=api_key)

    api_key = os.getenv("GRAPHRAG_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "Missing API key. Set GRAPHRAG_API_KEY or OPENAI_API_KEY, "
            "or set OPENAI_PROVIDER=azure for Azure authentication."
        )
    return OpenAI(api_key=api_key)


def create_embedding_client() -> OpenAI:
    if is_azure():
        endpoint = (
            os.getenv("AZURE_OPENAI_EMBEDDING_ENDPOINT")
            or os.getenv("AZURE_OPENAI_ENDPOINT")
            or DEFAULT_AZURE_ENDPOINT
        )
        api_key = (
            os.getenv("AZURE_OPENAI_EMBEDDING_API_KEY")
            or os.getenv("AZURE_OPENAI_API_KEY")
            or _azure_token_provider()
        )
        return OpenAI(base_url=endpoint, api_key=api_key)

    api_key = os.getenv("OPENAI_EMBEDDING_API_KEY") or os.getenv("GRAPHRAG_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "Missing embedding API key. Set OPENAI_EMBEDDING_API_KEY, "
            "GRAPHRAG_API_KEY, or OPENAI_API_KEY, or set OPENAI_PROVIDER=azure."
        )
    return OpenAI(api_key=api_key)
