import ipaddress
import re
from typing import Any
from urllib.parse import urlparse

from bs4 import BeautifulSoup
import requests

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
}

MAX_CONTENT_CHARS = 4000


def _is_private_host(hostname: str) -> bool:
    """Validate against SSRF (private / loopback IPs)."""
    if hostname.lower() in {"localhost", "127.0.0.1", "::1"}:
        return True
    try:
        ip = ipaddress.ip_address(hostname)
        return ip.is_private or ip.is_loopback or ip.is_reserved or ip.is_link_local
    except ValueError:
        return False


def read_webpage_content(url: str, max_chars: int = MAX_CONTENT_CHARS) -> dict[str, Any]:
    """
    Fetch and extract clean text content from a web page URL.
    """
    parsed = urlparse(url.strip())
    if parsed.scheme not in {"http", "https"}:
        return {"ok": False, "url": url, "error": "Invalid URL scheme. Must be http or https."}

    if not parsed.hostname or _is_private_host(parsed.hostname):
        return {"ok": False, "url": url, "error": "Access to local or private network addresses is restricted."}

    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code != 200:
            return {"ok": False, "url": url, "error": f"Failed to fetch page. HTTP status code: {response.status_code}"}

        soup = BeautifulSoup(response.text, "html.parser")

        # Strip scripts, styles, forms, navigation, footers
        for tag in soup(["script", "style", "nav", "footer", "header", "noscript", "iframe", "svg", "form"]):
            tag.decompose()

        title = soup.title.get_text(strip=True) if soup.title else parsed.hostname

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
            "url": url,
            "title": title,
            "content": truncated,
            "length": len(truncated),
            "is_truncated": len(cleaned_text) > max_chars,
        }
    except requests.RequestException as exc:
        return {"ok": False, "url": url, "error": f"Network error reading page: {exc}"}
    except Exception as exc:
        return {"ok": False, "url": url, "error": f"Failed to parse page content: {exc}"}
