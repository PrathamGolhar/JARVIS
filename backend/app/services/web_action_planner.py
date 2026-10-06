import json
import re
from typing import Literal
from urllib.parse import quote_plus, urlparse

import requests

from app.settings import settings

PlanKind = Literal["web_search", "youtube_search", "spotify_search"]

PLANNER_PROMPT = """Classify a browser-navigation request. Return JSON only:
{"kind":"web_search|youtube_search|spotify_search","query":"short search text"}.
Use youtube_search for requests to find a YouTube video, song, audio, or channel.
Use spotify_search for requests to find music, an artist, album, podcast, or playlist on Spotify.
Use web_search for every other website/search request. Never return a URL, command,
file path, app name, or explanation."""


def _model_classification(text: str) -> dict[str, str] | None:
    """Classify user web navigation request using Groq model if configured."""
    if not settings.groq_api_key:
        return None

    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.groq_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.groq_chat_model,
                "messages": [
                    {"role": "system", "content": PLANNER_PROMPT},
                    {"role": "user", "content": text},
                ],
                "temperature": 0.0,
                "max_tokens": 80,
                "response_format": {"type": "json_object"},
            },
            timeout=8,
        )
        if response.status_code == 200:
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            parsed = json.loads(content)
            kind = parsed.get("kind")
            query = parsed.get("query", "").strip()
            if kind in {"web_search", "youtube_search", "spotify_search"} and query:
                return {"kind": kind, "query": query}
    except Exception:
        pass
    return None


# ==============================================================================
# PHASE 4: THE HANDS (Safe Web Action Destination Planner)
# ==============================================================================
def make_web_action_plan(text: str) -> dict[str, str]:
    """
    Classify user navigation request and return safe destination plan {kind, label, url}.
    - Explicit URL -> open_website
    - YouTube search -> youtube_search
    - Spotify search -> spotify_search
    - Other search -> web_search
    """
    trimmed = text.strip()

    # 1. Check for explicit URL or domain
    url_match = re.search(r"https?://[^\s]+", trimmed, re.I)
    if url_match:
        url = url_match.group(0)
        parsed = urlparse(url)
        label = parsed.hostname or url
        return {
            "kind": "open_website",
            "label": label,
            "url": url,
        }

    # Domain without protocol: e.g. "open github.com"
    domain_match = re.search(r"\b([a-zA-Z0-9-]+\.(?:com|org|net|edu|gov|io|co|ai|in|dev|app)(?:/[^\s]*)?)\b", trimmed, re.I)
    if domain_match:
        matched_str = domain_match.group(1)
        full_url = f"https://{matched_str}"
        parsed = urlparse(full_url)
        label = parsed.hostname or matched_str
        return {
            "kind": "open_website",
            "label": label,
            "url": full_url,
        }

    # 2. Check for YouTube search
    yt_match = re.search(r"^(?:please\s+)?(?:can you\s+)?(?:play|search|find|look up|listen to)?\s*(.*?)\s*(?:on|in)\s+youtube\b", trimmed, re.I)
    if not yt_match:
        yt_match = re.search(r"^(?:please\s+)?(?:can you\s+)?(?:search|open)\s+youtube\s+(?:for|to find)?\s*(.*)", trimmed, re.I)
    if yt_match and yt_match.group(1).strip():
        query = yt_match.group(1).strip()
        query = re.sub(r"^(play|search|find|listen to)\s+", "", query, flags=re.I).strip()
        if query:
            return {
                "kind": "youtube_search",
                "label": f"YouTube: {query}",
                "url": f"https://www.youtube.com/results?search_query={quote_plus(query)}",
            }

    # 3. Check for Spotify search
    sp_match = re.search(r"^(?:please\s+)?(?:can you\s+)?(?:play|search|find|look up|listen to)?\s*(.*?)\s*(?:on|in)\s+spotify\b", trimmed, re.I)
    if not sp_match:
        sp_match = re.search(r"^(?:please\s+)?(?:can you\s+)?(?:search|open)\s+spotify\s+(?:for|to find)?\s*(.*)", trimmed, re.I)
    if sp_match and sp_match.group(1).strip():
        query = sp_match.group(1).strip()
        query = re.sub(r"^(play|search|find|listen to)\s+", "", query, flags=re.I).strip()
        if query:
            return {
                "kind": "spotify_search",
                "label": f"Spotify: {query}",
                "url": f"https://open.spotify.com/search/{quote_plus(query)}",
            }

    # 4. Optional model classification
    model_plan = _model_classification(trimmed)
    if model_plan:
        kind = model_plan["kind"]
        query = model_plan["query"]
        if kind == "youtube_search":
            return {
                "kind": "youtube_search",
                "label": f"YouTube: {query}",
                "url": f"https://www.youtube.com/results?search_query={quote_plus(query)}",
            }
        if kind == "spotify_search":
            return {
                "kind": "spotify_search",
                "label": f"Spotify: {query}",
                "url": f"https://open.spotify.com/search/{quote_plus(query)}",
            }
        return {
            "kind": "web_search",
            "label": f"Google: {query}",
            "url": f"https://www.google.com/search?q={quote_plus(query)}",
        }

    # 5. Fallback to web search
    clean_query = re.sub(
        r"^(?:please\s+)?(?:can you\s+)?(?:open|search|find|google|look up|navigate to|go to|show me)\s+(?:the\s+)?(?:official\s+)?",
        "",
        trimmed,
        flags=re.I,
    ).strip()
    clean_query = re.sub(r"\s+(?:website|site|webpage)$", "", clean_query, flags=re.I).strip()
    query = clean_query if clean_query else trimmed

    return {
        "kind": "web_search",
        "label": f"Google: {query}",
        "url": f"https://www.google.com/search?q={quote_plus(query)}",
    }
