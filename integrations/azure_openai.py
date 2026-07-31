"""Azure OpenAI client wrapper."""

from __future__ import annotations

from functools import lru_cache

from openai import AzureOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from config.settings import ConfigurationError, Settings, get_settings


@lru_cache(maxsize=1)
def get_azure_openai_client(settings: Settings | None = None) -> AzureOpenAI:
    cfg = settings or get_settings()
    cfg.require_azure_openai()
    return AzureOpenAI(
        azure_endpoint=cfg.resolved_azure_endpoint(),
        api_key=cfg.azure_openai_api_key,
        api_version=cfg.azure_openai_api_version,
    )


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
def chat_completion(
    messages: list[dict[str, str]],
    *,
    settings: Settings | None = None,
    temperature: float = 0.1,
    max_tokens: int = 1500,
) -> str:
    client = get_azure_openai_client(settings)
    cfg = settings or get_settings()
    deployment = cfg.resolved_chat_deployment()
    response = client.chat.completions.create(
        model=deployment,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    content = response.choices[0].message.content
    return content or ""


async def health_check(settings: Settings | None = None) -> dict[str, str]:
    cfg = settings or get_settings()
    try:
        cfg.require_azure_openai()
        client = get_azure_openai_client(cfg)
        deployment = cfg.resolved_chat_deployment()
        response = client.chat.completions.create(
            model=deployment,
            messages=[{"role": "user", "content": "ping"}],
            max_tokens=1,
            temperature=0,
        )
        model = getattr(response, "model", deployment)
        return {"status": "ok", "integration": "azure_openai", "model": str(model)}
    except ConfigurationError as exc:
        return {"status": "error", "integration": "azure_openai", "reason": str(exc)}
    except Exception as exc:
        return {"status": "error", "integration": "azure_openai", "reason": str(exc)}
