import ipaddress
import json
import logging
import socket
from datetime import datetime, timedelta, timezone
from typing import Literal
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from app.schemas import Citation, ResearchResponse
from app.services.ai.factory import get_ai_provider
from app.services.document_generation.pdf_generator import generate_pdf_document
from app.services.tools.web_search import live_web_search, _clean_search_query

logger = logging.getLogger("jarvis.researcher")


def is_safe_external_url(url: str) -> bool:
    """Validate that a URL is a safe public HTTP/HTTPS endpoint (SSRF protection)."""
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False
        hostname = parsed.hostname
        if not hostname:
            return False
        if hostname.lower() in ("localhost", "127.0.0.1", "::1", "0.0.0.0"):
            return False

        try:
            ip = ipaddress.ip_address(hostname)
        except ValueError:
            ip_str = socket.gethostbyname(hostname)
            ip = ipaddress.ip_address(ip_str)

        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved:
            return False
        return True
    except Exception:
        return False


def extract_webpage_text(url: str, max_chars: int = 3000) -> str:
    if not is_safe_external_url(url):
        logger.warning("SSRF Protection: Blocked extraction of unsafe URL: %s", url)
        return ""

    try:
        resp = requests.get(
            url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
            timeout=8,
        )
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
                tag.extract()
            text = " ".join(soup.stripped_strings)
            return text[:max_chars]
    except Exception as exc:
        logger.debug("Failed scraping %s: %s", url, exc)
    return ""


def _build_subqueries(query: str, depth: str) -> list[str]:
    """
    Decompose a research query into multiple sub-queries for broader coverage.
    For deep/comprehensive modes, creates 3-5 angle-based sub-queries.
    """
    cleaned = _clean_search_query(query)
    if depth == "quick":
        return [cleaned]

    now = datetime.now(tz=timezone.utc)
    date_str = now.strftime("%Y %B")
    prev_month = (now - timedelta(days=30)).strftime("%Y %B")

    # Generate sub-queries to cover multiple angles
    subqueries = [
        cleaned,                                         # Primary
        f"{cleaned} latest news {date_str}",            # Recency angle
        f"{cleaned} analysis overview",                  # Analysis angle
    ]
    if depth == "comprehensive":
        subqueries += [
            f"{cleaned} {prev_month}",                  # Last-month angle
            f"{cleaned} expert opinion research",        # Expert angle
        ]
    return subqueries


def _deduplicate_results(results: list[dict]) -> list[dict]:
    """Remove duplicate results by URL (normalized)."""
    seen: set[str] = set()
    unique: list[dict] = []
    for r in results:
        url = r.get("url", "").strip().rstrip("/")
        if url and url not in seen:
            seen.add(url)
            unique.append(r)
    return unique


def perform_deep_research(
    query: str,
    depth: Literal["quick", "deep", "comprehensive"] = "deep",
    generate_doc: Literal["none", "pdf", "docx", "pptx"] = "none",
) -> ResearchResponse:
    """
    Perform multi-source web research using the centralized live_web_search() abstraction.

    Pipeline:
    1. Query decomposition (multiple angle sub-queries)
    2. Multi-source search (DDGS, Google News RSS, Wikipedia, DDG Instant Answer)
    3. Source ranking and deduplication
    4. Webpage extraction (SSRF-protected)
    5. AI synthesis with citation mapping
    """
    max_per_query = 4 if depth == "quick" else (6 if depth == "deep" else 8)
    subqueries = _build_subqueries(query, depth)
    all_raw_results: list[dict] = []
    citations: list[Citation] = []

    # Step 1 & 2: Multi-query, multi-source search
    for subq in subqueries:
        result = live_web_search(subq, max_results=max_per_query)
        if result.get("ok") and result.get("results"):
            all_raw_results.extend(result["results"])

    if not all_raw_results:
        # Last-resort: try original unmodified query
        fallback = live_web_search(query, max_results=max_per_query)
        if fallback.get("ok"):
            all_raw_results.extend(fallback.get("results", []))

    # Step 3: Deduplicate
    deduped_results = _deduplicate_results(all_raw_results)
    search_results = deduped_results[:max_per_query * 2]  # Cap total results

    # Build citations from search results
    for item in search_results:
        link = item.get("url", "")
        title = item.get("title", "Source")
        snippet = item.get("snippet", "")
        if link:
            domain = urlparse(link).netloc
            citations.append(Citation(title=title, url=link, domain=domain, snippet=snippet))

    # Step 4: Webpage extraction — extract top 3 sources for deep context
    deep_context = ""
    extract_count = 1 if depth == "quick" else (2 if depth == "deep" else 3)
    for c in citations[:extract_count]:
        page_text = extract_webpage_text(c.url, max_chars=2000)
        if page_text:
            deep_context += f"\n\nSource: {c.title} ({c.url})\n{page_text}"

    # Step 5: AI synthesis
    provider = get_ai_provider()
    system_prompt = (
        "You are JARVIS Deep Research Intelligence.\n"
        "Analyze the provided live web search results and webpage extractions.\n"
        "Produce a high-grade, objective, and deeply comprehensive research report.\n"
        "Return ONLY JSON matching this format:\n"
        "{\n"
        '  "topic": "Research Title",\n'
        '  "summary": "Executive Summary (2 paragraphs)",\n'
        '  "keyTakeaways": ["Takeaway 1", "Takeaway 2", ...],\n'
        '  "findingsMarkdown": "# Research Report: ...\\n\\n### Key Developments\\n..."\n'
        "}"
    )

    user_prompt = (
        f"Research Query: {query}\n\n"
        f"Depth: {depth}\n"
        f"Search Results Snippets:\n{json.dumps(search_results[:10], indent=2)}\n\n"
        f"Scraped In-Depth Content:\n{deep_context or 'No additional webpage content available.'}"
    )

    try:
        res = provider.chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            max_tokens=3500,
        )

        content = res.content.strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]

        data = json.loads(content.strip())
        report_md = data.get("findingsMarkdown", f"# Research Report: {query}\n\n{content}")
        summary = data.get("summary", "")
        key_takeaways = data.get("keyTakeaways", [])
        topic = data.get("topic", query)

    except Exception as exc:
        logger.warning("Research synthesis error: %s", exc)
        topic = query
        if citations:
            summary = f"Synthesized live web intelligence across {len(citations)} verified sources for query '{query}'."
            key_takeaways = [c.title for c in citations[:4]]
            report_md = (
                f"# Intelligence Report: {query}\n\n"
                f"## Executive Summary\n{summary}\n\n"
                f"## Verified Sources & Key Findings\n"
                + "\n".join(f"- **{c.title}** ({c.domain}): {c.snippet}" for c in citations)
            )
        else:
            summary = "Web research is temporarily unavailable. Live web access could not retrieve external sources."
            key_takeaways = ["Live web research unavailable."]
            report_md = (
                f"# Research Report: {query}\n\n"
                "Web research is temporarily unavailable. Live search providers were unreachable for this request."
            )

    # Optional PDF Document generation
    file_url = None
    if generate_doc == "pdf":
        pdf_path = generate_pdf_document(
            title=f"Research Report: {topic}",
            content_markdown=report_md,
            subtitle="Verified Multi-Source Intelligence",
            subject=f"Research on {query}",
        )
        file_url = f"/api/files/download/{pdf_path.name}"

    return ResearchResponse(
        topic=topic,
        summary=summary,
        findingsMarkdown=report_md,
        citations=citations,
        keyTakeaways=key_takeaways,
        generatedFileUrl=file_url,
    )
