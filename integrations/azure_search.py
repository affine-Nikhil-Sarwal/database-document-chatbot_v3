"""Azure AI Search client wrapper."""

from __future__ import annotations

from functools import lru_cache

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from tenacity import retry, stop_after_attempt, wait_exponential

from config.settings import Settings, get_settings


@lru_cache(maxsize=1)
def get_search_client(settings: Settings | None = None) -> SearchClient:
    cfg = settings or get_settings()
    cfg.require_azure_search()
    return SearchClient(
        endpoint=cfg.azure_search_service_endpoint,
        index_name=cfg.azure_search_index_name,
        credential=AzureKeyCredential(cfg.azure_search_api_key),
    )


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
def search_documents(query: str, *, top: int = 3, settings: Settings | None = None) -> list[dict]:
    client = get_search_client(settings)
    results = client.search(search_text=query, top=top)
    return [dict(doc) for doc in results]


async def health_check(settings: Settings | None = None) -> dict[str, str]:
    cfg = settings or get_settings()
    try:
        cfg.require_azure_search()
        client = get_search_client(cfg)
        stats = client.get_document_count()
        return {
            "status": "ok",
            "integration": "azure_search",
            "document_count": str(stats),
            "index": cfg.azure_search_index_name,
        }
    except Exception as exc:
        return {"status": "error", "integration": "azure_search", "reason": str(exc)}
