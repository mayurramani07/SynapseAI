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

    return results

print(web_search.invoke("How companies are using AI agents in production systems 2026"))
