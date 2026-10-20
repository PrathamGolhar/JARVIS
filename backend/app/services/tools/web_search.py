import logging
import re
from typing import Any
from urllib.parse import unquote, urlparse

from bs4 import BeautifulSoup
import requests

from app.endpoints import DUCKDUCKGO_API_URL, DUCKDUCKGO_HTML_URL
from app.settings import settings

logger = logging.getLogger("jarvis.web_search")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


def _clean_ddg_url(raw_url: str) -> str:
    """Extract destination URL from DuckDuckGo redirect link."""
    if "duckduckgo.com/l/?" in raw_url:
        match = re.search(r"[?&]uddg=([^&]+)", raw_url)
        if match:
            return unquote(match.group(1))
    return raw_url


def live_web_search(query: str, max_results: int = 5) -> dict[str, Any]:
    """
    Perform a real, live web search using DDGS as primary with HTML/API fallbacks
    and return top verified results with citations and structured diagnostics.
    """
    if not settings.web_search_enabled:
        return {
            "ok": False,
            "query": query,
            "error": "WEB_SEARCH_DISABLED",
            "message": "Web search capability is currently disabled in system settings.",
            "diagnostic": {
                "status": "DISABLED",
                "provider": "DuckDuckGo",
                "reason": "web_search_enabled is false",
            },
        }

    trimmed = query.strip()
    if not trimmed:
        return {
            "ok": False,
            "query": query,
            "error": "EMPTY_QUERY",
            "message": "Search query cannot be empty.",
        }

    results: list[dict[str, str]] = []

    # 1. Primary: Use ddgs / duckduckgo_search library with modern TLS impersonation
    try:
        try:
            from ddgs import DDGS
        except ImportError:
            from duckduckgo_search import DDGS

        with DDGS() as ddgs:
            raw_results = list(ddgs.text(trimmed, max_results=max_results))
            for item in raw_results:
                link = item.get("href") or item.get("link") or ""
                title = item.get("title") or "Source"
                snippet = item.get("body") or item.get("snippet") or ""
                if link and link.startswith("http"):
                    parsed = urlparse(link)
                    domain = parsed.hostname or link
                    results.append({
                        "title": title,
                        "url": link,
                        "domain": domain,
                        "snippet": snippet,
                    })
                    if len(results) >= max_results:
                        break
    except Exception as exc:
        logger.warning("Primary DDGS live search error: %s", exc)

    # 2. Secondary fallback: DuckDuckGo HTML endpoint
    if not results:
        try:
            response = requests.post(
                DUCKDUCKGO_HTML_URL,
                data={"q": trimmed, "b": ""},
                headers=HEADERS,
                timeout=6,
            )
            if response.status_code in (200, 202):
                soup = BeautifulSoup(response.text, "html.parser")
                elements = soup.select(".result")
                for el in elements:
                    title_link = el.select_one(".result__title .result__url, .result__title a")
                    snippet_el = el.select_one(".result__snippet")
                    if title_link:
                        href = title_link.get("href", "")
                        clean_url = _clean_ddg_url(href)
                        title = title_link.get_text(strip=True)
                        snippet = snippet_el.get_text(strip=True) if snippet_el else ""
                        if clean_url and clean_url.startswith("http") and "duckduckgo.com" not in clean_url:
                            parsed = urlparse(clean_url)
                            domain = parsed.hostname or clean_url
                            results.append({
                                "title": title,
                                "url": clean_url,
                                "domain": domain,
                                "snippet": snippet,
                            })
                            if len(results) >= max_results:
                                break
        except Exception as exc:
            logger.debug("Secondary HTML search fallback failed: %s", exc)

    # 3. Tertiary fallback: DuckDuckGo Instant Answer API
    if not results:
        try:
            ia_res = requests.get(
                DUCKDUCKGO_API_URL,
                params={"q": trimmed, "format": "json", "no_html": "1", "skip_disambig": "1"},
                headers=HEADERS,
                timeout=5,
            )
            if ia_res.status_code == 200:
                data = ia_res.json()
                abstract = data.get("AbstractText", "")
                abstract_url = data.get("AbstractURL", "")
                heading = data.get("Heading", trimmed)
                if abstract and abstract_url:
                    results.append({
                        "title": heading,
                        "url": abstract_url,
                        "domain": urlparse(abstract_url).hostname or abstract_url,
                        "snippet": abstract,
                    })
                for topic in data.get("RelatedTopics", [])[:max_results]:
                    if isinstance(topic, dict) and topic.get("Text") and topic.get("FirstURL"):
                        results.append({
                            "title": topic.get("Text", "").split(" - ")[0],
                            "url": topic.get("FirstURL"),
                            "domain": urlparse(topic.get("FirstURL")).hostname or "",
                            "snippet": topic.get("Text"),
                        })
        except Exception:
            pass

    if not results:
        return {
            "ok": False,
            "query": trimmed,
            "results": [],
            "error": "WEB_SEARCH_UNAVAILABLE",
            "message": "Web research is temporarily unavailable. Live search providers were unreachable.",
            "diagnostic": {
                "status": "DEGRADED",
                "provider": "DuckDuckGo",
                "reason": "Providers unreachable or query yielded 0 results",
            },
        }

    return {
        "ok": True,
        "query": trimmed,
        "results_count": len(results),
        "results": results,
    }
