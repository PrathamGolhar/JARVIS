import html
import logging
import re
from typing import Any
from urllib.parse import quote_plus, unquote, urlparse
import xml.etree.ElementTree as ET

from bs4 import BeautifulSoup
import requests

from app.endpoints import (
    DUCKDUCKGO_API_URL,
    DUCKDUCKGO_HTML_URL,
    GOOGLE_NEWS_RSS_URL,
    WIKIPEDIA_API_URL,
)
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


def _clean_search_query(raw_query: str) -> str:
    """
    Strip conversational fluff from user queries to improve search engine keyword matching.
    """
    text = raw_query.strip()
    # Strip leading phrases like "give me update on last 3 days on what's happening in this world"
    patterns = [
        r"^(?:please\s+)?(?:can you\s+)?(?:give me\s+(?:an?\s+)?)?(?:update(?:s)?\s+(?:on|for|about)?\s+)?(?:last\s+\d+\s+days\s+(?:on|about)?\s+)?(?:what(?:'s|\s+is)\s+happening\s+(?:in|with|to)\s+)?",
        r"^(?:please\s+)?(?:can you\s+)?(?:search(?:\s+the\s+web)?(?:\s+for)?\s+)",
        r"^(?:please\s+)?(?:can you\s+)?(?:tell me\s+(?:about)?\s+)",
        r"^(?:what(?:'s|\s+is)\s+the\s+latest\s+(?:news\s+(?:on|about)|on|about)\s+)",
    ]
    cleaned = text
    for pat in patterns:
        cleaned = re.sub(pat, "", cleaned, flags=re.IGNORECASE).strip()

    # If the user is asking about "this world" or "the world", map to "world news"
    if cleaned.lower() in ("this world", "the world", "world", "everything"):
        return "world news"

    return cleaned if len(cleaned) >= 2 else text


def _search_ddgs_isolated(query: str, max_results: int) -> list[dict[str, str]]:
    """
    Query DDGS using isolated backends so one failing backend doesn't crash the search.
    """
    results: list[dict[str, str]] = []
    try:
        try:
            from ddgs import DDGS
        except ImportError:
            from duckduckgo_search import DDGS

        is_news_intent = any(w in query.lower() for w in ["news", "latest", "today", "update", "week", "recent", "world"])

        with DDGS() as ddgs:
            # 1. If news-related intent, query news engines individually
            if is_news_intent:
                for n_backend in ["bing", "yahoo"]:
                    try:
                        n_res = ddgs.news(query, backend=n_backend, max_results=max_results)
                        for item in n_res or []:
                            link = item.get("url") or item.get("href") or ""
                            title = item.get("title") or "News Source"
                            snippet = item.get("body") or item.get("snippet") or ""
                            if link and link.startswith("http"):
                                results.append({
                                    "title": title,
                                    "url": link,
                                    "domain": urlparse(link).hostname or n_backend,
                                    "snippet": snippet,
                                })
                        if len(results) >= max_results:
                            return results[:max_results]
                    except Exception as exc:
                        logger.debug("DDGS news %s failed: %s", n_backend, exc)

            # 2. General text search engines individually
            for t_backend in ["duckduckgo", "grokipedia", "wikipedia"]:
                try:
                    t_res = ddgs.text(query, backend=t_backend, max_results=max_results)
                    for item in t_res or []:
                        link = item.get("href") or item.get("link") or ""
                        title = item.get("title") or "Source"
                        snippet = item.get("body") or item.get("snippet") or ""
                        if link and link.startswith("http"):
                            results.append({
                                "title": title,
                                "url": link,
                                "domain": urlparse(link).hostname or t_backend,
                                "snippet": snippet,
                            })
                    if len(results) >= max_results:
                        return results[:max_results]
                except Exception as exc:
                    logger.debug("DDGS text %s failed: %s", t_backend, exc)

    except Exception as exc:
        logger.warning("DDGS isolated search error: %s", exc)

    return results


def _search_google_news_rss(query: str, max_results: int) -> list[dict[str, str]]:
    """
    Search Google News RSS feed for real-time live news headlines and sources.
    No API keys required, zero rate-limit friction, reliable 200 responses.
    """
    results: list[dict[str, str]] = []
    try:
        encoded = quote_plus(query)
        rss_url = f"{GOOGLE_NEWS_RSS_URL}?q={encoded}&hl=en-US&gl=US&ceid=US:en"
        resp = requests.get(rss_url, headers=HEADERS, timeout=6)
        if resp.status_code == 200:
            root = ET.fromstring(resp.text)
            for item in root.findall(".//item")[:max_results]:
                title = item.find("title").text if item.find("title") is not None else ""
                link = item.find("link").text if item.find("link") is not None else ""
                pub_date = item.find("pubDate").text if item.find("pubDate") is not None else ""
                source_el = item.find("source")
                source_name = source_el.text if source_el is not None else "News Source"

                if title and link:
                    clean_title = html.unescape(title)
                    snippet = f"Live News Report via {source_name}"
                    if pub_date:
                        snippet += f" (Published: {pub_date})"
                    results.append({
                        "title": clean_title,
                        "url": link,
                        "domain": source_name,
                        "snippet": snippet,
                    })
    except Exception as exc:
        logger.debug("Google News RSS fallback failed: %s", exc)

    return results


def _search_wikipedia(query: str, max_results: int) -> list[dict[str, str]]:
    """
    Search Wikipedia OpenSearch / API for reliable encyclopedic and factual knowledge.
    """
    results: list[dict[str, str]] = []
    try:
        resp = requests.get(
            WIKIPEDIA_API_URL,
            params={
                "action": "query",
                "list": "search",
                "srsearch": query,
                "format": "json",
                "srlimit": max_results,
            },
            headers={"User-Agent": "JarvisAI/2.0"},
            timeout=5,
        )
        if resp.status_code == 200:
            data = resp.json()
            for item in data.get("query", {}).get("search", []):
                title = item.get("title", "")
                raw_snippet = item.get("snippet", "")
                clean_snippet = re.sub(r"<[^>]+>", "", raw_snippet).strip()
                if title:
                    slug = title.replace(" ", "_")
                    results.append({
                        "title": title,
                        "url": f"https://en.wikipedia.org/wiki/{slug}",
                        "domain": "en.wikipedia.org",
                        "snippet": html.unescape(clean_snippet),
                    })
    except Exception as exc:
        logger.debug("Wikipedia search fallback failed: %s", exc)

    return results


def _search_duckduckgo_instant_answer(query: str, max_results: int) -> list[dict[str, str]]:
    """
    DuckDuckGo Instant Answer API fallback for quick definitions and knowledge graphs.
    """
    results: list[dict[str, str]] = []
    try:
        ia_res = requests.get(
            DUCKDUCKGO_API_URL,
            params={"q": query, "format": "json", "no_html": "1", "skip_disambig": "1"},
            headers=HEADERS,
            timeout=5,
        )
        if ia_res.status_code == 200:
            data = ia_res.json()
            abstract = data.get("AbstractText", "")
            abstract_url = data.get("AbstractURL", "")
            heading = data.get("Heading", query)
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
    except Exception as exc:
        logger.debug("DDG Instant Answer failed: %s", exc)

    return results


def live_web_search(query: str, max_results: int = 5) -> dict[str, Any]:
    """
    Perform a resilient, multi-tiered live web search returning verified results,
    citations, and structured diagnostics.
    """
    if not settings.web_search_enabled:
        return {
            "ok": False,
            "query": query,
            "error": "WEB_SEARCH_DISABLED",
            "message": "Web search capability is currently disabled in system settings.",
            "diagnostic": {
                "status": "DISABLED",
                "provider": "MultiSource",
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

    cleaned_query = _clean_search_query(trimmed)
    results: list[dict[str, str]] = []
    seen_urls: set[str] = set()

    def add_results(items: list[dict[str, str]]) -> None:
        for it in items:
            url = it.get("url", "").strip()
            if url and url not in seen_urls:
                seen_urls.add(url)
                results.append(it)

    # Tier 1: DDGS isolated engines (Bing news, DDG text, Grokipedia, Wikipedia)
    add_results(_search_ddgs_isolated(cleaned_query, max_results))

    # Tier 2: Real-time Google News RSS (vital for breaking current events & news queries)
    if len(results) < max_results:
        add_results(_search_google_news_rss(cleaned_query, max_results - len(results)))

    # Tier 3: Wikipedia Search API (facts, topics, deep encyclopedic context)
    if len(results) < max_results:
        add_results(_search_wikipedia(cleaned_query, max_results - len(results)))

    # Tier 4: DuckDuckGo Instant Answer API
    if len(results) < max_results:
        add_results(_search_duckduckgo_instant_answer(cleaned_query, max_results - len(results)))

    if not results:
        return {
            "ok": False,
            "query": trimmed,
            "results": [],
            "error": "WEB_SEARCH_UNAVAILABLE",
            "message": "Web research is temporarily unavailable. Live search providers were unreachable.",
            "diagnostic": {
                "status": "DEGRADED",
                "provider": "MultiSource",
                "reason": "All search tiers yielded 0 results for query",
            },
        }

    return {
        "ok": True,
        "query": trimmed,
        "results_count": len(results),
        "results": results[:max_results],
    }
