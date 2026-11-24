import logging
import re
from typing import Any
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from app.services.security_network import SSRFSecurityError, safe_http_fetch

logger = logging.getLogger("jarvis.tools.web_reader")

MAX_CONTENT_CHARS = 4000


def read_webpage_content(url: str, max_chars: int = MAX_CONTENT_CHARS) -> dict[str, Any]:
    """
    Fetch and extract clean text content from a web page URL with strict SSRF protection.
    """
    cleaned_url = url.strip()
    parsed = urlparse(cleaned_url)
    if parsed.scheme not in {"http", "https"}:
        return {"ok": False, "url": cleaned_url, "error": "Invalid URL scheme. Must be http or https."}

    try:
        status_code, html_text, headers = safe_http_fetch(cleaned_url)
        if status_code != 200:
            return {"ok": False, "url": cleaned_url, "error": f"Failed to fetch page. HTTP status code: {status_code}"}

        soup = BeautifulSoup(html_text, "html.parser")

        # Strip scripts, styles, forms, navigation, footers
        for tag in soup(["script", "style", "nav", "footer", "header", "noscript", "iframe", "svg", "form"]):
            tag.decompose()

        title = soup.title.get_text(strip=True) if soup.title else (parsed.hostname or "Webpage")

        # Extract main article or body text
        main_content = soup.find("article") or soup.find("main") or soup.find("body")
        if not main_content:
            text = soup.get_text(separator=" ", strip=True)
        else:
            text = main_content.get_text(separator=" ", strip=True)

        cleaned_text = re.sub(r"\s+", " ", text).strip()
        truncated = cleaned_text[:max_chars]

        return {
            "ok": True,
            "url": cleaned_url,
            "title": title,
            "content": truncated,
            "length": len(truncated),
            "is_truncated": len(cleaned_text) > max_chars,
        }
    except SSRFSecurityError as ssrf_err:
        logger.warning("SSRF blocked request to '%s': %s", cleaned_url, ssrf_err)
        return {"ok": False, "url": cleaned_url, "error": f"Access restricted by security policy: {ssrf_err}"}
    except Exception as exc:
        logger.warning("Error reading webpage '%s': %s", cleaned_url, exc)
        return {"ok": False, "url": cleaned_url, "error": f"Failed to read webpage: {exc}"}
