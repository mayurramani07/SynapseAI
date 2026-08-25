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


@tool
def web_search(query: str) -> str:
    """
    Search the web for high-quality research sources.
    """
    try:
        results = tavily.search(
            query=query,
            max_results=10
        )
    except Exception as e:
        return f"Search failed: {str(e)}"

    processed = []

    for result in results.get("results", []):
        url = result.get("url", "").strip()

        if not url:
            continue

        score = get_domain_score(url)

        if score == 0:
            continue

        title = result.get(
            "title",
            "No Title"
        )

        content = result.get(
            "content",
            ""
        )

        summary = (
            content
            .replace("\n", " ")
            .strip()
        )

        summary = summary[:300]

        processed.append({
            "title": title,
            "url": url,
            "summary": summary,
            "score": score
        })

    if not processed:
        return "No high-quality results found."

    processed = sorted(
        processed,
        key=lambda item: item["score"],
        reverse=True
    )[:5]

    output = []

    for item in processed:
        output.append(
            f"SCORE: {item['score']}\n"
            f"TITLE: {item['title']}\n"
            f"URL: {item['url']}\n"
            f"SUMMARY: {item['summary']}\n"
        )

    return "\n----\n".join(output)


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


@tool
def scrape_urls(urls: str) -> str:
    """
    Scrape and extract usable text from the provided URLs.
    Supports HTML pages and PDF documents.
    """
    results = []

    url_list = [
        url.strip()
        for url in urls.split(",")
        if url.strip()
    ]

    for url in url_list:
        success = False
        last_error = None

        for attempt in range(1, 3):
            try:
                response = session.get(
                    url,
                    timeout=12,
                    allow_redirects=True
                )

                if response.status_code != 200:
                    raise requests.HTTPError(
                        f"HTTP {response.status_code}"
                    )

                content = extract_content(
                    response
                )

                if not validate_content(
                    content
                ):
                    raise ValueError(
                        "Extracted content is insufficient"
                    )

                content = content[:6000]

                results.append(
                    f"SOURCE: {response.url}\n"
                    f"{content}\n"
                )

                success = True
                break

            except Exception as error:
                last_error = error

                if attempt < 2:
                    time.sleep(
                        1.0 * attempt
                    )

        if not success:
            print(
                f"Scraping failed for {url}: "
                f"{last_error}"
            )

    if not results:
        raise ValueError(
            "No usable content could be scraped "
            "from any source"
        )

    return "\n=====\n".join(results)