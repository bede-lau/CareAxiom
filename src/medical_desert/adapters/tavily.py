from __future__ import annotations

import ipaddress
from urllib.parse import urlparse

from medical_desert.application.errors import ApplicationError
from medical_desert.domain.models import ErrorCode


def validate_external_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("Only public HTTP(S) URLs are permitted.")
    try:
        address = ipaddress.ip_address(parsed.hostname)
    except ValueError:
        return
    if address.is_private or address.is_loopback or address.is_link_local or address.is_reserved:
        raise ValueError("Private, loopback, link-local, and reserved addresses are blocked.")


class TavilyAdapter:
    def __init__(self, mode: str, api_key: str | None) -> None:
        self.mode = mode
        self._api_key = api_key
        self.cache: dict[str, list[dict[str, object]]] = {}

    def search(self, query: str, domains: list[str] | None = None) -> list[dict[str, object]]:
        cache_key = f"{query}|{','.join(sorted(domains or []))}"
        if cache_key in self.cache:
            return self.cache[cache_key]
        if self.mode != "live":
            return []
        if not self._api_key:
            raise ApplicationError(
                ErrorCode.OPTIONAL_SERVICE_UNAVAILABLE,
                "Tavily live mode has no API key.",
                "Switch to cached mode or configure the deployment secret.",
                status_code=503,
            )
        from tavily import TavilyClient  # type: ignore[import-untyped]

        response = TavilyClient(api_key=self._api_key).search(
            query=query,
            search_depth="basic",
            max_results=5,
            country="india",
            include_domains=domains or [],
        )
        results = []
        for item in response.get("results", []):
            validate_external_url(item["url"])
            results.append(
                {
                    "url": item["url"],
                    "title": item.get("title"),
                    "content": item.get("content"),
                    "score": item.get("score"),
                    "request_id": response.get("request_id"),
                }
            )
        self.cache[cache_key] = results
        return results
