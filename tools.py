from langchain.tools import tool
import requests
from bs4 import BeautifulSoup
from tavily import TavilyClient
import os 
from dotenv import load_dotenv
from rich import print

load_dotenv()

tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

@tool
def web_search(query: str) -> str:
    """Search the web and return structured results with titles, URLs and summaries."""
    
    results = tavily.search(query=query, max_results=5)

    out = []
    seen = set()

    for r in results.get('results', []):
        url = r.get('url', '').strip()
        if not url or url in seen:
            continue
        
        seen.add(url)

        content = r.get('content', '').replace('\n', ' ')
        summary = content[:300].rsplit(' ', 1)[0]

        out.append(
            f"""TITLE: {r.get('title')} URL: {url} SUMMARY: {summary}"""
        )

    if not out:
        return "No results found."

    return "\n----\n".join(out)


print(web_search.invoke("How companies are using AI agents in production systems 2026"))
