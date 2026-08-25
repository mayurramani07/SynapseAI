from agents import (
    writer_chain,
    critic_chain,
    evidence_chain,
    insight_chain,
    reasoning_chain,
    improver_chain,
    grounding_chain
)

from tools import web_search, scrape_urls

import re
import time
import json
import random
import logging
import uuid

from datetime import datetime, timezone
from pydantic import BaseModel, ValidationError
from typing import Literal
from urllib.parse import urlparse

MAX_ATTEMPTS = 2
BASE_RETRY_DELAY = 1.0
MAX_RETRY_DELAY = 8.0

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s"
)

logger = logging.getLogger("synapseai")


class EvidenceItem(BaseModel):
    claim: str
    supporting_text: str
    source_url: str
    evidence_type: Literal[
        "statistic",
        "factual_claim",
        "projection"
    ]


def log_event(
    request_id,
    stage,
    status,
    attempt=None,
    duration=None,
    error_type=None,
    error=None,
    fallback_used=False
):
    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "request_id": request_id,
        "stage": stage,
        "status": status,
        "attempt": attempt,
        "duration": duration,
        "error_type": error_type,
        "error": str(error) if error else None,
        "fallback_used": fallback_used
    }

    logger.info(
        json.dumps(
            event,
            ensure_ascii=False
        )
    )


def stage_success(
    data,
    duration=None,
    attempts=1
):
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

    non_retryable_limit_errors = [
        "tpd limit",
        "tokens per day",
        "daily token limit",
        "daily limit",
        "tokens used",
        "requested tokens",
        "rate limit reached for model"
    ]

    for pattern in non_retryable_limit_errors:
        if pattern in error_text:
            return "non_retryable"

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
    exponential_delay = (
        BASE_RETRY_DELAY *
        (2 ** (attempt - 1))
    )

    jitter = random.uniform(0, 0.5)

    return min(
        exponential_delay + jitter,
        MAX_RETRY_DELAY
    )


def validate_search_output(data):
    if not isinstance(data, str):
        raise ValueError(
            "Search output must be a string"
        )

    if not data.strip():
        raise ValueError(
            "Search output is empty"
        )

    if "No high-quality results found" in data:
        raise ValueError(
            "Search returned no high-quality results"
        )

    return True


def validate_scraped_output(data):
    if not isinstance(data, str):
        raise ValueError(
            "Scraped content must be a string"
        )

    if not data.strip():
        raise ValueError(
            "Scraped content is empty"
        )

    if "No content could be scraped" in data:
        raise ValueError(
            "No content could be scraped"
        )

    return True


def validate_reasoning_output(data):
    if not isinstance(data, str):
        raise ValueError(
            "Reasoning output must be a string"
        )

    if not data.strip():
        raise ValueError(
            "Reasoning output is empty"
        )

    return True


def validate_source_url(url):
    if not isinstance(url, str):
        raise ValueError(
            "source_url must be a string"
        )

    url = url.strip()

    if not url:
        raise ValueError(
            "source_url cannot be empty"
        )

    parsed = urlparse(url)

    if parsed.scheme not in {"http", "https"}:
        raise ValueError(
            "source_url must use HTTP or HTTPS"
        )

    if not parsed.netloc:
        raise ValueError(
            "source_url must contain a valid domain"
        )

    return True


def validate_evidence_output(data):

    if not isinstance(data, list):
        raise ValueError(
            "Evidence output must be a list"
        )

    if not data:
        return True

    for item in data:

        if not isinstance(item, dict):
            raise ValueError(
                "Evidence item must be an object"
            )

        try:
            validated_item = EvidenceItem.model_validate(
                item
            )

        except ValidationError as error:
            raise ValueError(
                f"Invalid evidence schema: {error}"
            )

        if not validated_item.claim.strip():
            raise ValueError(
                "Evidence claim cannot be empty"
            )

        if not validated_item.supporting_text.strip():
            raise ValueError(
                "Evidence supporting_text cannot be empty"
            )

        validate_source_url(
            validated_item.source_url
        )

    return True


def normalize_evidence_output(data):

    if isinstance(data, dict):

        evidence = data.get(
            "evidence",
            []
        )

        if evidence is None:
            return []

        if not isinstance(evidence, list):
            raise ValueError(
                "Evidence 'evidence' field must be a list"
            )

        return evidence

    if isinstance(data, list):
        return data

    raise ValueError(
        "Unexpected evidence output type: "
        f"{type(data).__name__}"
    )


def validate_grounding_output(data):

    if not isinstance(data, dict):
        raise ValueError(
            "Grounding output must be an object"
        )

    if "verified" not in data:
        raise ValueError(
            "Grounding output missing verified field"
        )

    if not isinstance(
        data["verified"],
        bool
    ):
        raise ValueError(
            "verified must be boolean"
        )

    if "reason" not in data:
        raise ValueError(
            "Grounding output missing reason"
        )

    if not isinstance(
        data["reason"],
        str
    ):
        raise ValueError(
            "reason must be a string"
        )

    if "confidence" not in data:
        raise ValueError(
            "Grounding output missing confidence"
        )

    confidence = data["confidence"]

    if not isinstance(
        confidence,
        (int, float)
    ):
        raise ValueError(
            "confidence must be numeric"
        )

    if not 0 <= confidence <= 1:
        raise ValueError(
            "confidence must be between 0 and 1"
        )

    return True


def validate_insight_output(data):

    if not isinstance(data, str):
        raise ValueError(
            "Insight output must be a string"
        )

    if not data.strip():
        raise ValueError(
            "Insight output is empty"
        )

    return True


def validate_report_output(data):

    if not isinstance(data, str):
        raise ValueError(
            "Report output must be a string"
        )

    if not data.strip():
        raise ValueError(
            "Report output is empty"
        )

    return True


def validate_critic_output(data):

    if not isinstance(data, str):
        raise ValueError(
            "Critic output must be a string"
        )

    if not data.strip():
        raise ValueError(
            "Critic output is empty"
        )

    return True


def validate_improved_report(data):

    if not isinstance(data, str):
        raise ValueError(
            "Improved report must be a string"
        )

    if not data.strip():
        raise ValueError(
            "Improved report is empty"
        )

    return True


def run_with_retry(
    request_id,
    stage_name,
    operation,
    validator=None,
    fallback=None,
    max_attempts=MAX_ATTEMPTS
):

    start_time = time.time()
    last_error = None
    attempt = 0

    log_event(
        request_id=request_id,
        stage=stage_name,
        status="started"
    )

    for attempt in range(
        1,
        max_attempts + 1
    ):

        try:

            result = operation()

            if result is None:
                raise ValueError(
                    f"{stage_name} returned None"
                )

            if validator:
                validator(result)

            duration = round(
                time.time() - start_time,
                2
            )

            log_event(
                request_id=request_id,
                stage=stage_name,
                status="success",
                attempt=attempt,
                duration=duration
            )

            return stage_success(
                data=result,
                duration=duration,
                attempts=attempt
            )

        except Exception as error:

            last_error = error

            error_type = classify_error(
                error
            )

            log_event(
                request_id=request_id,
                stage=stage_name,
                status="error",
                attempt=attempt,
                error_type=error_type,
                error=error
            )

            if error_type == "non_retryable":
                break

            if attempt < max_attempts:

                delay = calculate_retry_delay(
                    attempt
                )

                log_event(
                    request_id=request_id,
                    stage=stage_name,
                    status="retrying",
                    attempt=attempt,
                    error_type=error_type
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

            if validator:
                validator(
                    fallback_data
                )

            log_event(
                request_id=request_id,
                stage=stage_name,
                status="degraded",
                attempt=attempt,
                duration=duration,
                error_type=classify_error(
                    last_error
                ),
                error=last_error,
                fallback_used=True
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

            log_event(
                request_id=request_id,
                stage=stage_name,
                status="failed",
                attempt=attempt,
                duration=duration,
                error_type=classify_error(
                    fallback_error
                ),
                error=fallback_error,
                fallback_used=True
            )

            return stage_failure(
                error=fallback_error,
                duration=duration,
                attempts=attempt,
                fallback_used=True
            )

    log_event(
        request_id=request_id,
        stage=stage_name,
        status="failed",
        attempt=attempt,
        duration=duration,
        error_type=classify_error(
            last_error
        ),
        error=last_error,
        fallback_used=False
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

    request_id = str(
        uuid.uuid4()
    )

    pipeline_start = time.time()

    log_event(
        request_id=request_id,
        stage="pipeline",
        status="started"
    )

    state = {}

    search_results = run_with_retry(
        request_id=request_id,
        stage_name="Smart Search",
        operation=lambda: smart_search(
            topic
        ),
        validator=validate_search_output,
        fallback=None
    )

    state["search_results"] = search_results

    if search_results["status"] == "failed":

        log_event(
            request_id=request_id,
            stage="pipeline",
            status="failed",
            duration=round(
                time.time() - pipeline_start,
                2
            )
        )

        return state

    search_data = search_results["data"]

    def scrape_operation():

        urls = rank_urls(
            extract_urls(
                search_data
            )
        )

        if not urls:
            raise ValueError(
                "No valid URLs found in search results"
            )

        urls_str = ", ".join(
            urls
        )

        scraped = scrape_urls.invoke({
            "urls": urls_str
        })

        if (
            not scraped
            or not scraped.strip()
        ):
            raise ValueError(
                "Scraper returned empty content"
            )

        return scraped

    scraped_content = run_with_retry(
        request_id=request_id,
        stage_name="URL Ranking + Scraping",
        operation=scrape_operation,
        validator=validate_scraped_output,
        fallback=lambda: search_data
    )

    state["scraped_content"] = scraped_content

    research_data = scraped_content["data"]

    reasoning = run_with_retry(
        request_id=request_id,
        stage_name="Reasoning",
        operation=lambda: reasoning_chain.invoke({
            "research": (
                search_data
                + "\n\n"
                + research_data
            )
        }),
        validator=validate_reasoning_output,
        fallback="Reasoning unavailable."
    )

    state["reasoning"] = reasoning

    reasoning_data = reasoning["data"]

    print(
        "\nEVIDENCE INPUT PREVIEW:"
    )

    print(
        research_data[:5000]
    )

    print(
        "\n" + "=" * 80
    )

    evidence = run_with_retry(
        request_id=request_id,
        stage_name="Evidence Extraction",
        operation=lambda: normalize_evidence_output(
            evidence_chain.invoke({
                "research": research_data
            })
        ),
        validator=validate_evidence_output,
        fallback=[]
    )

    state["evidence"] = evidence

    evidence_data = evidence["data"] or []

    print(
        "\nRAW EVIDENCE OUTPUT:"
    )

    print(
        json.dumps(
            evidence_data,
            indent=2,
            ensure_ascii=False
        )
    )

    print(
        f"\nExtracted Evidence Count: "
        f"{len(evidence_data)}"
    )

    verified_evidence = []

    if evidence_data:

        for item in evidence_data:

            grounding = run_with_retry(
                request_id=request_id,
                stage_name="Evidence Grounding",
                operation=lambda item=item: grounding_chain.invoke({
                    "source_content": research_data,
                    "evidence_items": json.dumps(
                        [item],
                        ensure_ascii=False
                    )
                }),
                validator=validate_grounding_output,
                fallback={
                    "verified": False,
                    "reason": "Grounding verification failed.",
                    "confidence": 0.0
                }
            )

            grounding_data = grounding.get(
                "data"
            ) or {}

            item = item.copy()

            item["grounding"] = grounding_data

            if (
                grounding_data.get("verified") is True
                and grounding_data.get("confidence", 0) >= 0.8
            ):
                verified_evidence.append(
                    item
                )

    state["verified_evidence"] = {
        "status": "success",
        "data": verified_evidence,
        "error": None,
        "attempts": 1,
        "duration": None,
        "fallback_used": False
    }

    evidence_data = verified_evidence

    if evidence_data:

        insights = run_with_retry(
            request_id=request_id,
            stage_name="Insight Generation",
            operation=lambda: insight_chain.invoke({
                "research": research_data,
                "evidence": json.dumps(
                    evidence_data,
                    ensure_ascii=False
                )
            }),
            validator=validate_insight_output,
            fallback=(
                "Insights unavailable because "
                "insight generation failed."
            )
        )

    else:

        insights = {
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

        log_event(
            request_id=request_id,
            stage="Insight Generation",
            status="skipped",
            fallback_used=True
        )

    state["insights"] = insights

    insights_data = insights["data"]

    report = run_with_retry(
        request_id=request_id,
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
        validator=validate_report_output,
        fallback=None
    )

    state["report"] = report

    if report["status"] == "failed":

        state["final_report"] = report

        log_event(
            request_id=request_id,
            stage="pipeline",
            status="failed",
            duration=round(
                time.time() - pipeline_start,
                2
            )
        )

        return state

    report_data = report["data"]

    feedback = run_with_retry(
        request_id=request_id,
        stage_name="Critic",
        operation=lambda: critic_chain.invoke({
            "report": report_data,
            "evidence": json.dumps(
                evidence_data,
                ensure_ascii=False
            )
        }),
        validator=validate_critic_output,
        fallback=None
    )

    state["feedback"] = feedback

    if feedback["status"] == "failed":

        state["final_report"] = {
            "status": "degraded",
            "data": report_data,
            "error": feedback["error"],
            "attempts": feedback["attempts"],
            "duration": feedback["duration"],
            "fallback_used": True
        }

        log_event(
            request_id=request_id,
            stage="pipeline",
            status="degraded",
            duration=round(
                time.time() - pipeline_start,
                2
            ),
            fallback_used=True
        )

        return state

    feedback_data = feedback["data"]

    final_report = run_with_retry(
        request_id=request_id,
        stage_name="Improver",
        operation=lambda: improver_chain.invoke({
            "report": report_data,
            "feedback": feedback_data
        }),
        validator=validate_improved_report,
        fallback=report_data
    )

    state["final_report"] = final_report

    total_duration = round(
        time.time() - pipeline_start,
        2
    )

    log_event(
        request_id=request_id,
        stage="pipeline",
        status="completed",
        duration=total_duration
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

        run_research_pipeline(
            topic
        )