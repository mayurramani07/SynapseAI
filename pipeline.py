from agents import (
    writer_chain,
    critic_chain,
    evidence_chain,
    insight_chain,
    reasoning_chain,
    improver_chain
)
from tools import web_search, scrape_urls
import re
import time

def smart_search(topic: str) -> str:
    try:
        result = web_search.invoke({"query": topic})
        return str(result)
    except Exception as e:
        return f" Fallback summary: Basic info about {topic}. Error: {e}"

def extract_urls(text: str) -> list:
    urls = re.findall(r'https?://\S+', text)
    return list(set(urls))


def rank_urls(urls: list) -> list:
    priority = {
        ".gov": 5,
        ".edu": 5,
        "worldbank": 5,
        "reuters": 4,
        "bloomberg": 4,
        "forbes": 3,
        "cnbc": 3,
        "investopedia": 3
    }

    def score(url):
        return sum(v for k, v in priority.items() if k in url.lower())

    return sorted(urls, key=score, reverse=True)[:3]


def run_research_pipeline(topic: str) -> dict:
    state = {}
    start_time = time.time()

    print("\n AI Research System Started")
    print("=" * 60)

    print("\nSTEP 1 - Smart Search")
    t1 = time.time()

    state["search_results"] = smart_search(topic)

    print(state["search_results"][:800])
    print(f" {round(time.time() - t1, 2)}s")


    
    print("\nSTEP 2 - URL Ranking + Scraping")
    t2 = time.time()

    try:
        urls = rank_urls(extract_urls(state["search_results"]))
        urls_str = ", ".join(urls)

        print("\nURLs:", urls_str)

        scraped = scrape_urls.invoke({"urls": urls_str})

        if not scraped.strip():
            raise Exception("Empty scrape")

        state["scraped_content"] = scraped

    except Exception as e:
        state["scraped_content"] = f"Fallback:\n{state['search_results']}"
        print("Scrape fallback:", e)

    print(state["scraped_content"][:800])
    print(f" {round(time.time() - t2, 2)}s")

    print("\nSTEP 3 - Reasoning")
    t3 = time.time()

    try:
        state["reasoning"] = reasoning_chain.invoke({
            "research": state["search_results"] + "\n\n" + state["scraped_content"]
        })
    except Exception as e:
        state["reasoning"] = f"Reasoning Error: {e}"

    print(state["reasoning"][:800])
    print(f" {round(time.time() - t3, 2)}s")

    print("\nSTEP 4 - Evidence Extraction")
    t4 = time.time()

    try:
        state["evidence"] = evidence_chain.invoke({
            "research": state["scraped_content"]
        })
    except Exception as e:
        state["evidence"] = f"Evidence Error: {e}"

    print(state["evidence"][:800])
    print(f" {round(time.time() - t4, 2)}s")


    print("\nSTEP 5 - Insight Generation")
    t5 = time.time()

    try:
        state["insights"] = insight_chain.invoke({
            "research": state["scraped_content"],
            "evidence": state["evidence"]
        })
    except Exception as e:
        state["insights"] = f"Insight Error: {e}"

    print(state["insights"][:800])
    print(f" {round(time.time() - t5, 2)}s")


    print("\nSTEP 6 - Writer")
    t6 = time.time()

    try:
        state["report"] = writer_chain.invoke({
            "topic": topic,
            "research": state["search_results"] + "\n\n" + state["scraped_content"],
            "reasoning": state["reasoning"],
            "evidence": state["evidence"],
            "insights": state["insights"]
        })
    except Exception as e:
        state["report"] = f"Writer Error: {e}"

    print(state["report"][:1200])
    print(f" {round(time.time() - t6, 2)}s")



    print("\nSTEP 7 - Critic")
    t7 = time.time()

    try:
        state["feedback"] = critic_chain.invoke({
            "report": state["report"]
        })
    except Exception as e:
        state["feedback"] = f"Critic Error: {e}"

    print(state["feedback"])
    print(f" {round(time.time() - t7, 2)}s")



    print("\nSTEP 8 - Improver")
    t8 = time.time()

    try:
        state["final_report"] = improver_chain.invoke({
            "report": state["report"],
            "feedback": state["feedback"]
        })
    except Exception as e:
        state["final_report"] = f"Improver Error: {e}"

    print(state["final_report"][:1200])
    print(f" {round(time.time() - t8, 2)}s")


    print("\n DONE")
    print("Total Time:", round(time.time() - start_time, 2), "s")

    return state

if __name__ == "__main__":
    topic = input("Enter topic: ")
    run_research_pipeline(topic)