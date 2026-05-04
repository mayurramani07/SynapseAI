from langchain.tools import tool
import requests
from bs4 import BeautifulSoup
from tavily import TavilyClient
import os
from dotenv import load_dotenv
import time
from urllib.parse import urlparse

load_dotenv()

tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

DOMAIN_SCORES = {
    ".gov": 5,
    ".edu": 5,
    "reuters": 4,
    "bloomberg": 4,
    "worldbank": 5,
    "imf": 5,
    "cnbc": 3,
    "forbes": 3,
    "investopedia": 3,
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive"
}

session = requests.Session()
session.headers.update(HEADERS)


def get_domain_score(url: str) -> int:
    score = 0
    for domain, value in DOMAIN_SCORES.items():
        if domain in url.lower():
            score = max(score, value)
    return score


@tool
def web_search(query: str) -> str:
    """
    Smart web search:
    - filters low-quality sources
    - ranks by domain credibility
    """

    try:
        results = tavily.search(query=query, max_results=10)
    except Exception as e:
        return f" Search failed: {str(e)}"

    processed = []

    for r in results.get("results", []):
        url = r.get("url", "").strip()
        if not url:
            continue

        score = get_domain_score(url)

        if score == 0:
            continue

        title = r.get("title", "No Title")
        content = r.get("content", "")

        summary = content.replace("\n", " ").strip()
        summary = summary[:300].rsplit(" ", 1)[0]

        processed.append({
            "title": title,
            "url": url,
            "summary": summary,
            "score": score
        })

    if not processed:
        return "No high-quality results found."

    
    processed = sorted(processed, key=lambda x: x["score"], reverse=True)[:5]


    out = []
    for item in processed:
        out.append(
            f"SCORE: {item['score']}\n"
            f"TITLE: {item['title']}\n"
            f"URL: {item['url']}\n"
            f"SUMMARY: {item['summary']}\n"
        )

    return "\n----\n".join(out)


@tool
def scrape_urls(urls: str) -> str:
    """
    Advanced scraper:
    - retry logic
    - content validation
    - removes noise
    - prioritizes readable content
    """

    results = []

    for url in urls.split(","):
        url = url.strip()
        if not url:
            continue

        success = False

        for attempt in range(2):
            try:
                resp = session.get(url, timeout=8)

                if resp.status_code != 200:
                    time.sleep(1)
                    continue

                soup = BeautifulSoup(resp.text, "html.parser")

                # remove junk
                for tag in soup([
                    "script", "style", "nav", "footer",
                    "header", "aside", "form"
                ]):
                    tag.decompose()

                
                paragraphs = soup.find_all("p")
                text = " ".join(p.get_text() for p in paragraphs)

                text = " ".join(text.split())

               
                if len(text) < 400:
                    continue

                text = text[:2500]

                results.append(
                    f"\nSOURCE: {url}\n{text}\n"
                )

                success = True
                break

            except Exception:
                time.sleep(1)

        if not success:
            results.append(
                f"\nSOURCE: {url}\n Failed / Low-quality content\n"
            )

    if not results:
        return "No content could be scraped."

    return "\n=====\n".join(results)