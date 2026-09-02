from langchain.tools import tool
import requests
from bs4 import BeautifulSoup
from tavily import TavilyClient
import os
from dotenv import load_dotenv
import time
from urllib.parse import urlparse
from pypdf import PdfReader
from io import BytesIO

load_dotenv()

tavily = TavilyClient(
    api_key=os.getenv("TAVILY_API_KEY")
)

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
    "Accept": (
        "text/html,application/xhtml+xml,"
        "application/xml;q=0.9,application/pdf;q=0.8,*/*;q=0.7"
    ),
    "Connection": "keep-alive",
}

session = requests.Session()
session.headers.update(HEADERS)


def get_domain_score(url: str) -> int:
    score = 1  # Default baseline score so search results are never discarded

    for domain, value in DOMAIN_SCORES.items():
        if domain in url.lower():
            score = max(score, value)

    return score


from search_providers import multi_provider_web_search


@tool
def web_search(query: str) -> str:
    """
    Search the web for high-quality research sources with automated multi-provider fallback
    (Tavily → Serper → DuckDuckGo).
    """
    output, provider_used = multi_provider_web_search(query)
    return output


def clean_text(text: str) -> str:
    return " ".join(
        text.replace("\xa0", " ").split()
    )


def extract_html_content(html: str) -> str:
    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    for tag in soup([
        "script",
        "style",
        "nav",
        "footer",
        "header",
        "aside",
        "form",
        "noscript",
        "iframe",
        "svg"
    ]):
        tag.decompose()

    content_container = (
        soup.find("article")
        or soup.find("main")
        or soup.find(
            "div",
            class_=lambda value: (
                value and any(
                    keyword in str(value).lower()
                    for keyword in [
                        "article",
                        "content",
                        "post",
                        "entry",
                        "story"
                    ]
                )
            )
        )
    )

    if content_container:
        text = content_container.get_text(
            separator=" ",
            strip=True
        )
    else:
        paragraphs = soup.find_all("p")

        text = " ".join(
            paragraph.get_text(
                separator=" ",
                strip=True
            )
            for paragraph in paragraphs
        )

    return clean_text(text)


def extract_pdf_content(content: bytes) -> str:
    reader = PdfReader(
        BytesIO(content)
    )

    pages = []

    for page in reader.pages:
        try:
            page_text = page.extract_text()

            if page_text:
                pages.append(page_text)

        except Exception:
            continue

    return clean_text(
        " ".join(pages)
    )


def extract_content(response) -> str:
    content_type = response.headers.get(
        "Content-Type",
        ""
    ).lower()

    url_path = urlparse(
        response.url
    ).path.lower()

    is_pdf = (
        "application/pdf" in content_type
        or url_path.endswith(".pdf")
    )

    if is_pdf:
        return extract_pdf_content(
            response.content
        )

    return extract_html_content(
        response.text
    )


def validate_content(text: str) -> bool:
    if not text:
        return False

    if len(text) < 400:
        return False

    words = text.split()

    if len(words) < 60:
        return False

    return True


import asyncio
import httpx


async def async_scrape_single_url(url: str, client: httpx.AsyncClient, logger) -> str:
    """
    Scrape a single URL asynchronously with httpx and fallback to Jina Reader cloud API.
    """
    last_error = None
    for attempt in range(1, 3):
        try:
            response = await client.get(url, timeout=12.0, follow_redirects=True)

            if response.status_code != 200:
                raise httpx.HTTPStatusError(
                    f"HTTP {response.status_code}",
                    request=response.request,
                    response=response
                )

            content_type = response.headers.get("Content-Type", "").lower()
            url_path = urlparse(str(response.url)).path.lower()
            is_pdf = "application/pdf" in content_type or url_path.endswith(".pdf")

            if is_pdf:
                content = extract_pdf_content(response.content)
            else:
                content = extract_html_content(response.text)

            if not validate_content(content):
                raise ValueError("Extracted content is insufficient")

            content = content[:6000]
            return f"SOURCE: {response.url}\n{content}\n"

        except Exception as error:
            last_error = error

            # Cloud bypass fallback: Try Jina Reader API
            try:
                logger.warning(
                    f"Standard async scraping failed for {url} ({error}). "
                    "Attempting Jina Reader cloud fallback..."
                )
                jina_url = f"https://r.jina.ai/{url}"
                jina_resp = await client.get(jina_url, timeout=15.0, follow_redirects=True)

                if jina_resp.status_code == 200:
                    jina_content = jina_resp.text
                    if validate_content(jina_content):
                        content = jina_content[:6000]
                        return f"SOURCE: {url}\n{content}\n"
                    else:
                        raise ValueError("Jina fallback content is empty or too short")
                else:
                    raise httpx.HTTPStatusError(
                        f"HTTP {jina_resp.status_code}",
                        request=jina_resp.request,
                        response=jina_resp
                    )
            except Exception as jina_error:
                last_error = f"{error} (Jina fallback also failed: {jina_error})"

            if attempt < 2:
                await asyncio.sleep(0.5 * attempt)

    logger.error(f"Async scraping failed for {url}: {last_error}")
    return None


async def async_scrape_urls_list(url_list: list[str], logger) -> str:
    """
    Scrape multiple URLs concurrently using asyncio.gather.
    """
    async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True, timeout=15.0) as client:
        tasks = [async_scrape_single_url(url, client, logger) for url in url_list]
        scraped_results = await asyncio.gather(*tasks, return_exceptions=True)

    valid_results = []
    for res in scraped_results:
        if isinstance(res, str) and res.strip():
            valid_results.append(res)

    if not valid_results:
        raise ValueError("No usable content could be scraped from any source")

    return "\n=====\n".join(valid_results)


@tool
def scrape_urls(urls: str) -> str:
    """
    Scrape and extract usable text from the provided URLs concurrently in parallel.
    Supports HTML pages and PDF documents. Includes a lightweight cloud fallback via Jina Reader API.
    """
    import logging
    import concurrent.futures
    logger = logging.getLogger("synapseai")

    url_list = [
        url.strip()
        for url in urls.split(",")
        if url.strip()
    ]

    if not url_list:
        raise ValueError("No valid URLs provided to scrape")

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        with concurrent.futures.ThreadPoolExecutor() as pool:
            return pool.submit(
                lambda: asyncio.run(async_scrape_urls_list(url_list, logger))
            ).result()
    else:
        return asyncio.run(async_scrape_urls_list(url_list, logger))