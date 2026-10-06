import re
from typing import Any
from urllib.parse import unquote, urlparse

from bs4 import BeautifulSoup
import requests

from app.settings import settings

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
    Perform a real, live web search using DuckDuckGo HTML API and return top verified results with citations.
    """
    if not settings.web_search_enabled:
        return {"ok": False, "query": query, "error": "Web search capability is currently disabled."}

    trimmed = query.strip()
    if not trimmed:
        return {"ok": False, "query": query, "error": "Search query cannot be empty."}

    results: list[dict[str, str]] = []

    # 1. Query DuckDuckGo HTML search
    try:
        response = requests.post(
            "https://html.duckduckgo.com/html/",
            data={"q": trimmed, "b": ""},
            headers=HEADERS,
            timeout=8,
        )
        if response.status_code == 200:
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
        pass

    # 2. Fallback to DuckDuckGo Instant Answer API if HTML returned 0 results
    if not results:
        try:
            ia_res = requests.get(
                "https://api.duckduckgo.com/",
                params={"q": trimmed, "format": "json", "no_html": "1", "skip_disambig": "1"},
                headers=HEADERS,
                timeout=6,
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
            "ok": True,
            "query": trimmed,
            "results": [],
            "message": "No direct web results found for this query.",
        }

    return {
        "ok": True,
        "query": trimmed,
        "results_count": len(results),
        "results": results,
    }
