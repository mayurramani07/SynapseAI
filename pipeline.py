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
import json
import random

MAX_ATTEMPTS = 2
BASE_RETRY_DELAY = 1.0
MAX_RETRY_DELAY = 8.0


def stage_success(data, duration=None, attempts=1):
    return {
        "status": "success",
        "data": data,
        "error": None,
        "attempts": attempts,
        "duration": duration,
        "fallback_used": False
    }


def stage_failure(
    error,
    duration=None,
    attempts=1,
    fallback_used=False
):
    return {
        "status": "failed",
        "data": None,
        "error": str(error),
        "attempts": attempts,
        "duration": duration,
        "fallback_used": fallback_used
    }


def classify_error(error):
    error_text = str(error).lower()

    non_retryable_errors = [
        "authentication",
        "invalid api key",
        "api key",
        "unauthorized",
        "forbidden",
        "bad request",
        "invalid request",
        "model_not_found",
        "does not exist or you do not have access"
    ]

    retryable_errors = [
        "timeout",
        "timed out",
        "connection",
        "connection reset",
        "connection refused",
        "temporarily unavailable",
        "service unavailable",
        "rate limit",
        "too many requests",
        "429",
        "500",
        "502",
        "503",
        "504",
        "server error"
    ]

    for pattern in non_retryable_errors:
        if pattern in error_text:
            return "non_retryable"

    for pattern in retryable_errors:
        if pattern in error_text:
            return "retryable"

    return "retryable"


def calculate_retry_delay(attempt):
    exponential_delay = BASE_RETRY_DELAY * (2 ** (attempt - 1))
    jitter = random.uniform(0, 0.5)

    return min(
        exponential_delay + jitter,
        MAX_RETRY_DELAY
    )


def run_with_retry(
    stage_name,
    operation,
    fallback=None,
    max_attempts=MAX_ATTEMPTS
):
    start_time = time.time()
    last_error = None

    for attempt in range(1, max_attempts + 1):
        try:
            result = operation()

            if result is None:
                raise ValueError(
                    f"{stage_name} returned None"
                )

            duration = round(
                time.time() - start_time,
                2
            )

            return stage_success(
                data=result,
                duration=duration,
                attempts=attempt
            )

        except Exception as error:
            last_error = error
            error_type = classify_error(error)

            print(
                f"{stage_name} attempt "
                f"{attempt}/{max_attempts} failed: "
                f"{error}"
            )

            print(
                f"{stage_name} error type: "
                f"{error_type}"
            )

            if error_type == "non_retryable":
                print(
                    f"{stage_name}: "
                    f"non-retryable error"
                )
                break

            if attempt < max_attempts:
                delay = calculate_retry_delay(attempt)

                print(
                    f"{stage_name}: "
                    f"retrying in {round(delay, 2)}s"
                )

                time.sleep(delay)

    duration = round(
        time.time() - start_time,
        2
    )

    if fallback is not None:
        try:
            fallback_data = (
                fallback()
                if callable(fallback)
                else fallback
            )

            return {
                "status": "degraded",
                "data": fallback_data,
                "error": str(last_error),
                "attempts": attempt,
                "duration": duration,
                "fallback_used": True
            }

        except Exception as fallback_error:
            return stage_failure(
                error=fallback_error,
                duration=duration,
                attempts=attempt,
                fallback_used=True
            )

    return stage_failure(
        error=last_error,
        duration=duration,
        attempts=attempt,
        fallback_used=False
    )


def smart_search(topic):
    result = web_search.invoke({
        "query": topic
    })

    if not result:
        raise ValueError(
            "Search returned empty result"
        )

    return str(result)


def extract_urls(text):
    urls = re.findall(
        r'https?://\S+',
        text
    )

    return list(set(urls))


def rank_urls(urls):
    priority = {
        ".gov": 5,
        ".edu": 5,
        "worldbank": 5,
        "imf": 5,
        "reuters": 4,
        "bloomberg": 4,
        "forbes": 3,
        "cnbc": 3,
        "investopedia": 3
    }

    def score(url):
        return sum(
            value
            for domain, value in priority.items()
            if domain in url.lower()
        )

    return sorted(
        urls,
        key=score,
        reverse=True
    )[:3]


def run_research_pipeline(topic):
    state = {}
    start_time = time.time()

    print("\nAI Research System Started")
    print("=" * 60)

    print("\nSTEP 1 - Smart Search")

    state["search_results"] = run_with_retry(
        stage_name="Smart Search",
        operation=lambda: smart_search(topic),
        fallback=None
    )

    print(
        json.dumps(
            state["search_results"],
            indent=2,
            ensure_ascii=False
        )[:1000]
    )

    if state["search_results"]["status"] == "failed":
        print(
            "\nSearch failed. "
            "Research pipeline cannot continue."
        )

        print(
            "\nTotal Time:",
            round(time.time() - start_time, 2),
            "s"
        )

        return state

    search_data = state["search_results"]["data"]

    print("\nSTEP 2 - URL Ranking + Scraping")

    def scrape_operation():
        urls = rank_urls(
            extract_urls(search_data)
        )

        if not urls:
            raise ValueError(
                "No valid URLs found in search results"
            )

        urls_str = ", ".join(urls)

        print("\nURLs:", urls_str)

        scraped = scrape_urls.invoke({
            "urls": urls_str
        })

        if not scraped or not scraped.strip():
            raise ValueError(
                "Scraper returned empty content"
            )

        return scraped

    state["scraped_content"] = run_with_retry(
        stage_name="URL Ranking + Scraping",
        operation=scrape_operation,
        fallback=lambda: search_data
    )

    print(
        json.dumps(
            state["scraped_content"],
            indent=2,
            ensure_ascii=False
        )[:1200]
    )

    research_data = state["scraped_content"]["data"]

    print("\nSTEP 3 - Reasoning")

    state["reasoning"] = run_with_retry(
        stage_name="Reasoning",
        operation=lambda: reasoning_chain.invoke({
            "research": (
                search_data
                + "\n\n"
                + research_data
            )
        }),
        fallback="Reasoning unavailable."
    )

    print(
        json.dumps(
            state["reasoning"],
            indent=2,
            ensure_ascii=False
        )[:1000]
    )

    reasoning_data = state["reasoning"]["data"]

    print("\nSTEP 4 - Evidence Extraction")

    state["evidence"] = run_with_retry(
        stage_name="Evidence Extraction",
        operation=lambda: evidence_chain.invoke({
            "research": research_data
        }),
        fallback=[]
    )

    print(
        json.dumps(
            state["evidence"],
            indent=2,
            ensure_ascii=False
        )[:1500]
    )

    evidence_data = state["evidence"]["data"]

    print("\nSTEP 5 - Insight Generation")

    if evidence_data:
        state["insights"] = run_with_retry(
            stage_name="Insight Generation",
            operation=lambda: insight_chain.invoke({
                "research": research_data,
                "evidence": json.dumps(
                    evidence_data,
                    ensure_ascii=False
                )
            }),
            fallback=(
                "Insights unavailable because "
                "insight generation failed."
            )
        )
    else:
        state["insights"] = {
            "status": "skipped",
            "data": (
                "Insights skipped because no "
                "verified evidence was available."
            ),
            "error": None,
            "attempts": 0,
            "duration": 0,
            "fallback_used": True
        }

    print(
        json.dumps(
            state["insights"],
            indent=2,
            ensure_ascii=False
        )[:1000]
    )

    insights_data = state["insights"]["data"]

    print("\nSTEP 6 - Writer")

    state["report"] = run_with_retry(
        stage_name="Writer",
        operation=lambda: writer_chain.invoke({
            "topic": topic,
            "research": (
                search_data
                + "\n\n"
                + research_data
            ),
            "reasoning": reasoning_data,
            "evidence": json.dumps(
                evidence_data,
                ensure_ascii=False
            ),
            "insights": insights_data
        }),
        fallback=None
    )

    print(
        json.dumps(
            state["report"],
            indent=2,
            ensure_ascii=False
        )[:1500]
    )

    if state["report"]["status"] == "failed":
        print(
            "\nWriter failed. "
            "Cannot continue to critic/improver."
        )

        state["final_report"] = state["report"]

        print(
            "\nTotal Time:",
            round(time.time() - start_time, 2),
            "s"
        )

        return state

    report_data = state["report"]["data"]

    print("\nSTEP 7 - Critic")

    state["feedback"] = run_with_retry(
        stage_name="Critic",
        operation=lambda: critic_chain.invoke({
            "report": report_data,
            "evidence": json.dumps(
                evidence_data,
                ensure_ascii=False
            )
        }),
        fallback=None
    )

    print(
        json.dumps(
            state["feedback"],
            indent=2,
            ensure_ascii=False
        )[:1500]
    )

    if state["feedback"]["status"] == "failed":
        state["final_report"] = {
            "status": "degraded",
            "data": report_data,
            "error": state["feedback"]["error"],
            "attempts": state["feedback"]["attempts"],
            "duration": state["feedback"]["duration"],
            "fallback_used": True
        }

        print(
            "\nCritic unavailable. "
            "Returning original report."
        )

        print(
            "\nTotal Time:",
            round(time.time() - start_time, 2),
            "s"
        )

        return state

    feedback_data = state["feedback"]["data"]

    print("\nSTEP 8 - Improver")

    state["final_report"] = run_with_retry(
        stage_name="Improver",
        operation=lambda: improver_chain.invoke({
            "report": report_data,
            "feedback": feedback_data
        }),
        fallback=report_data
    )

    print(
        json.dumps(
            state["final_report"],
            indent=2,
            ensure_ascii=False
        )[:1500]
    )

    print("\nDONE")

    print(
        "Total Time:",
        round(time.time() - start_time, 2),
        "s"
    )

    return state


if __name__ == "__main__":
    topic = input(
        "Enter topic: "
    ).strip()

    if not topic:
        print(
            "Please enter a research topic."
        )
    else:
        run_research_pipeline(topic)