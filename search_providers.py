"""
SynapseAI Multi-Provider Search Fallback Engine
Supported Sequence: Tavily → Serper → DuckDuckGo
Detects rate limits (429/403), zero/poor results (<2 items), and automatically
switches provider to preserve pipeline continuity.
"""

import os
import logging
import requests
from bs4 import BeautifulSoup
from tavily import TavilyClient

logger = logging.getLogger("synapseai")

DOMAIN_SCORES = {
    ".gov": 5,
    ".edu": 5,
    "arxiv": 5,
    "nature.com": 5,
    "ieee.org": 5,
    "acm.org": 5,
    "worldbank": 5,
    "imf": 5,
    "reuters": 4,
    "bloomberg": 4,
    "mckinsey": 4,
    "gartner": 4,
    "hbr.org": 4,
    "cnbc": 3,
    "forbes": 3,
    "techcrunch": 3,
    "wired": 3,
    "investopedia": 3,
    "github.com": 2,
    "medium.com": 2,
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/145.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def get_domain_score(url: str) -> int:
    score = 1  # Default baseline score
    for domain, value in DOMAIN_SCORES.items():
        if domain in url.lower():
            score = max(score, value)
    return score


def search_tavily(query: str) -> tuple[bool, str, list]:
    """
    Search using Tavily API client.
    """
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        return False, "TAVILY_API_KEY is not configured", []

    try:
        tavily = TavilyClient(api_key=api_key)
        response = tavily.search(query=query, max_results=10)
        raw_results = response.get("results", [])

        processed = []
        for res in raw_results:
            url = res.get("url", "").strip()
            if not url:
                continue
            title = res.get("title", "No Title").strip()
            content = res.get("content", "").replace("\n", " ").strip()[:300]
            score = get_domain_score(url)

            processed.append({
                "title": title,
                "url": url,
                "summary": content,
                "score": score,
                "provider": "Tavily"
            })

        if len(processed) < 2:
            return False, f"Tavily returned only {len(processed)} result(s)", processed

        return True, "Success", processed

    except Exception as e:
        err_msg = str(e)
        if "429" in err_msg or "rate limit" in err_msg.lower():
            return False, f"Rate limited (HTTP 429): {err_msg}", []
        return False, f"Exception: {err_msg}", []


def search_serper(query: str) -> tuple[bool, str, list]:
    """
    Search using Serper.dev Google Search API.
    """
    api_key = os.getenv("SERPER_API_KEY")
    if not api_key:
        return False, "SERPER_API_KEY is not configured", []

    try:
        url = "https://google.serper.dev/search"
        headers = {
            "X-API-KEY": api_key,
            "Content-Type": "application/json"
        }
        payload = {"q": query, "num": 10}

        resp = requests.post(url, json=payload, headers=headers, timeout=10.0)

        if resp.status_code == 429:
            return False, "Serper Rate limited (HTTP 429)", []
        elif resp.status_code != 200:
            return False, f"Serper HTTP {resp.status_code}: {resp.text[:200]}", []

        data = resp.json()
        organic = data.get("organic", [])

        processed = []
        for item in organic:
            link = item.get("link", "").strip()
            if not link:
                continue
            title = item.get("title", "No Title").strip()
            snippet = item.get("snippet", "").replace("\n", " ").strip()[:300]
            score = get_domain_score(link)

            processed.append({
                "title": title,
                "url": link,
                "summary": snippet,
                "score": score,
                "provider": "Serper"
            })

        if len(processed) < 2:
            return False, f"Serper returned only {len(processed)} result(s)", processed

        return True, "Success", processed

    except Exception as e:
        return False, f"Exception: {str(e)}", []


def search_duckduckgo(query: str) -> tuple[bool, str, list]:
    """
    Zero-config DuckDuckGo fallback search.
    Tries python package duckduckgo_search first, falls back to direct HTML scraping.
    """
    processed = []

    # Method 1: Try duckduckgo_search library
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=10))
            for res in results:
                url = res.get("href", "").strip()
                if not url:
                    continue
                title = res.get("title", "No Title").strip()
                summary = res.get("body", "").replace("\n", " ").strip()[:300]
                score = get_domain_score(url)

                processed.append({
                    "title": title,
                    "url": url,
                    "summary": summary,
                    "score": score,
                    "provider": "DuckDuckGo"
                })

        if len(processed) >= 2:
            return True, "Success", processed

    except Exception:
        pass

    # Method 2: Direct HTTP scrape fallback to html.duckduckgo.com
    import time
    for attempt in range(2):
        try:
            if attempt > 0:
                time.sleep(1.0)
            scrape_url = "https://html.duckduckgo.com/html/"
            resp = requests.post(scrape_url, data={"q": query}, headers=HEADERS, timeout=12.0)

            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                results = soup.find_all("div", class_=lambda c: c and "result" in c)

                for res in results:
                    title_elem = res.find("a", class_=lambda c: c and "result__a" in c)
                    snippet_elem = res.find("a", class_=lambda c: c and "result__snippet" in c)

                    if not title_elem:
                        continue

                    url = title_elem.get("href", "").strip()
                    title = title_elem.get_text(strip=True)
                    summary = snippet_elem.get_text(strip=True) if snippet_elem else ""

                    if not url:
                        continue

                    score = get_domain_score(url)

                    processed.append({
                        "title": title,
                        "url": url,
                        "summary": summary[:300],
                        "score": score,
                        "provider": "DuckDuckGo"
                    })

            if len(processed) >= 2:
                return True, "Success", processed
            elif len(processed) > 0:
                return True, f"Success (Partial: {len(processed)} results)", processed

        except Exception as e:
            if attempt == 1:
                return False, f"Exception: {str(e)}", []

    return False, "DuckDuckGo HTML scraping yielded 0 results", []


def multi_provider_web_search(query: str, log_callback=None) -> tuple[str, str]:
    """
    Orchestrates Multi-Provider Search Fallback down the sequence:
    Tavily → Serper → DuckDuckGo

    Returns:
      (formatted_output_string, provider_name_used)
    """
    providers = [
        ("Tavily", search_tavily),
        ("Serper", search_serper),
        ("DuckDuckGo", search_duckduckgo),
    ]

    fallback_logs = []

    for name, search_fn in providers:
        msg = f"[Search Engine] Attempting search with provider: {name}..."
        logger.info(msg)
        if log_callback:
            log_callback(msg)

        success, reason, results = search_fn(query)

        if success and len(results) >= 2:
            msg = f"[Search Engine] Provider {name} succeeded with {len(results)} high-quality results."
            logger.info(msg)
            if log_callback:
                log_callback(msg)

            # Sort by domain authority score
            sorted_results = sorted(results, key=lambda item: item["score"], reverse=True)[:5]

            output = []
            for item in sorted_results:
                output.append(
                    f"SCORE: {item['score']}\n"
                    f"PROVIDER: {item['provider']}\n"
                    f"TITLE: {item['title']}\n"
                    f"URL: {item['url']}\n"
                    f"SUMMARY: {item['summary']}\n"
                )

            return "\n----\n".join(output), name

        else:
            warn_msg = f"[Search Fallback] Provider {name} failed or returned poor results ({reason}). Switching to next provider..."
            logger.warning(warn_msg)
            fallback_logs.append(warn_msg)
            if log_callback:
                log_callback(warn_msg)

    # If all providers fail
    error_output = "Search failed across all providers (Tavily, Serper, DuckDuckGo)."
    return error_output, "None"
