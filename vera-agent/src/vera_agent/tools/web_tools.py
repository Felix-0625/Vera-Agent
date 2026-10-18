"""Web search and page fetching tools.

- web_search: uses Tavily when TAVILY_API_KEY is set, otherwise DuckDuckGo
- fetch_web_page: fetches a URL over HTTP and converts the HTML to Markdown
"""

from __future__ import annotations

import os
import re
from typing import Any

import httpx

try:
    from ddgs import DDGS
except ImportError:
    try:
        from duckduckgo_search import DDGS  # type: ignore
    except ImportError:
        DDGS = None  # type: ignore

try:
    from markdownify import markdownify
except ImportError:
    markdownify = None  # type: ignore

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None  # type: ignore


def web_search_op(query: str, num_results: int = 5) -> dict[str, Any]:
    """Execute web search and return structured summary of top results.

    Supports zero-key DuckDuckGo Search (via ddgs) and optional Tavily API if configured.
    """
    if not query or not query.strip():
        return {
            "output": "Error: Search query cannot be empty.",
            "returncode": 1,
            "exception_info": "EmptyQueryError",
        }

    clean_query = query.strip()
    num_results = max(1, min(10, num_results))

    # 1. Check if Tavily API key is provided
    tavily_key = os.getenv("TAVILY_API_KEY")
    if tavily_key:
        try:
            resp = httpx.post(
                "https://api.tavily.com/search",
                json={"query": clean_query, "max_results": num_results, "search_depth": "basic"},
                headers={"Authorization": f"Bearer {tavily_key}"},
                timeout=12.0,
            )
            if resp.status_code == 200:
                data = resp.json()
                results = data.get("results", [])
                lines = [f"# Web Search Results for: `{clean_query}`\n"]
                for i, r in enumerate(results, 1):
                    lines.append(f"### {i}. [{r.get('title', 'Untitled')}]({r.get('url', '')})")
                    if r.get("content"):
                        lines.append(f"{r['content'].strip()}\n")
                return {"output": "\n".join(lines).strip(), "returncode": 0}
        except Exception:
            pass  # Fallback to zero-config DDGS

    # 2. Zero-config DuckDuckGo search
    if DDGS is not None:
        try:
            ddgs_client = DDGS(timeout=15)
            raw_results = list(ddgs_client.text(clean_query, max_results=num_results))
            if raw_results:
                lines = [f"# Web Search Results for: `{clean_query}`\n"]
                for i, r in enumerate(raw_results, 1):
                    title = r.get("title", "Untitled")
                    url = r.get("href", "")
                    body = r.get("body", "").strip()
                    lines.append(f"### {i}. [{title}]({url})")
                    if body:
                        lines.append(f"{body}\n")
                return {"output": "\n".join(lines).strip(), "returncode": 0}
            else:
                return {
                    "output": f"No web search results found for: '{clean_query}'. Try refining your search query.",
                    "returncode": 0,
                }
        except Exception as e:
            return {
                "output": f"Web search failed: {e}. You can retry with alternative keywords or fetch specific URLs directly.",
                "returncode": 1,
                "exception_info": str(e),
            }

    return {
        "output": "Error: Search backend not available. Please install ddgs (`uv pip install ddgs`).",
        "returncode": 1,
        "exception_info": "DependencyMissing",
    }


def fetch_web_page_op(url: str, max_chars: int = 8000) -> dict[str, Any]:
    """Fetch webpage content and convert HTML to clean, token-efficient Markdown."""
    if not url or not url.strip():
        return {
            "output": "Error: URL cannot be empty.",
            "returncode": 1,
            "exception_info": "EmptyUrlError",
        }

    clean_url = url.strip()
    if not clean_url.startswith(("http://", "https://")):
        clean_url = "https://" + clean_url

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
    }

    try:
        with httpx.Client(timeout=15.0, follow_redirects=True, headers=headers) as client:
            resp = client.get(clean_url)
            if resp.status_code >= 400:
                return {
                    "output": f"Error: HTTP {resp.status_code} {resp.reason_phrase} fetching '{clean_url}'",
                    "returncode": 1,
                    "exception_info": f"HTTP_{resp.status_code}",
                }
            html_text = resp.text
    except Exception as e:
        return {
            "output": f"Error fetching URL '{clean_url}': {e}",
            "returncode": 1,
            "exception_info": type(e).__name__,
        }

    # Clean HTML: strip scripts, styles, navs, footers, headers
    cleaned_html = html_text
    if BeautifulSoup is not None:
        try:
            soup = BeautifulSoup(html_text, "html.parser")
            for tag in soup(["script", "style", "noscript", "svg", "nav", "footer", "header", "aside"]):
                tag.decompose()
            cleaned_html = str(soup)
        except Exception:
            cleaned_html = html_text

    # Convert to Markdown
    if markdownify is not None:
        try:
            md_text = markdownify(cleaned_html, heading_style="ATX", strip=["img"])
        except Exception:
            md_text = re.sub(r"<[^>]+>", "", cleaned_html)
    else:
        md_text = re.sub(r"<[^>]+>", "", cleaned_html)

    # Collapse excessive blank lines
    md_text = re.sub(r"\n{3,}", "\n\n", md_text).strip()

    total_chars = len(md_text)
    if total_chars > max_chars:
        elided = total_chars - max_chars
        md_text = (
            md_text[:max_chars]
            + f"\n\n... [Content truncated: {elided} characters omitted. Original length: {total_chars} chars] ..."
        )

    return {
        "output": f"# Web Page Content: {clean_url}\n\n{md_text}",
        "returncode": 0,
    }


# ============================================================================
# OpenAI Tool Schemas & Definitions
# ============================================================================

WEB_SEARCH_TOOL = {
    "type": "function",
    "function": {
        "name": "web_search",
        "description": "Search the web for up-to-date technical documentation, API specs, latest library releases, or bug solutions.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query keywords (e.g. 'pydantic ai agent handoff', 'django 4.2 file permissions')",
                },
                "num_results": {
                    "type": "integer",
                    "description": "Number of search results to return (default: 5, max: 10)",
                },
            },
            "required": ["query"],
        },
    },
}

FETCH_WEB_PAGE_TOOL = {
    "type": "function",
    "function": {
        "name": "fetch_web_page",
        "description": "Fetch and read the full text of a web page (documentation, GitHub issue/PR, StackOverflow answer) in clean Markdown format.",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The URL of the webpage to fetch",
                },
                "max_chars": {
                    "type": "integer",
                    "description": "Maximum characters to return to prevent token explosion (default: 8000)",
                },
            },
            "required": ["url"],
        },
    },
}

# OpenAI Responses API flat schemas
WEB_SEARCH_TOOL_RESPONSE_API = {
    "type": "function",
    "name": "web_search",
    "description": WEB_SEARCH_TOOL["function"]["description"],
    "parameters": WEB_SEARCH_TOOL["function"]["parameters"],
}

FETCH_WEB_PAGE_TOOL_RESPONSE_API = {
    "type": "function",
    "name": "fetch_web_page",
    "description": FETCH_WEB_PAGE_TOOL["function"]["description"],
    "parameters": FETCH_WEB_PAGE_TOOL["function"]["parameters"],
}

WEB_TOOLS = [WEB_SEARCH_TOOL, FETCH_WEB_PAGE_TOOL]
WEB_TOOLS_RESPONSE_API = [WEB_SEARCH_TOOL_RESPONSE_API, FETCH_WEB_PAGE_TOOL_RESPONSE_API]
WEB_TOOL_NAMES = {"web_search", "fetch_web_page"}
