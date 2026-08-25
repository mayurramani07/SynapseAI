from agents import (
    writer_chain,
    critic_chain,
    evidence_chain,
    insight_chain,
    reasoning_chain,
    improver_chain,
    grounding_chain,
    writer_prompt,
    critic_prompt,
    evidence_prompt,
    insight_prompt,
    reasoning_prompt,
    improver_prompt,
    grounding_prompt,
    execute_prompt_with_fallback
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


MAX_ATTEMPTS = 4
BASE_RETRY_DELAY = 2.0
MAX_RETRY_DELAY = 30.0
GROQ_CALL_DELAY = 3.0


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
    """Classify errors without treating TPM 429s as permanent failures."""
    error_text = str(error).lower()

    # Authentication / request / model configuration errors should not retry.
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

    for pattern in non_retryable_errors:
        if pattern in error_text:
            return "non_retryable"

    # Daily token quota cannot be fixed by waiting a few seconds.
    daily_limit_errors = [
        "tpd limit",
        "tokens per day",
        "daily token limit",
        "daily limit",
    ]

    for pattern in daily_limit_errors:
        if pattern in error_text:
            return "non_retryable"

    # TPM / normal 429s are temporary. The Groq error itself gives
    # a retry-after duration, which run_with_retry will honor.
    retryable_errors = [
        "tokens per minute",
        "tpm",
        "rate limit",
        "too many requests",
        "429",
        "timeout",
        "timed out",
        "connection",
        "connection reset",
        "connection refused",
        "temporarily unavailable",
        "service unavailable",
        "500",
        "502",
        "503",
        "504",
        "server error"
    ]

    for pattern in retryable_errors:
        if pattern in error_text:
            return "retryable"

    return "retryable"


def get_retry_after_seconds(error, default_delay):
    """Extract Groq's 'try again in Xs' delay from a 429 message."""
    error_text = str(error)

    # Handles values such as:
    # 'try again in 13.4925s'
    # 'try again in 5m19.2s'
    match = re.search(
        r"try again in\s*(?:(\d+)m)?\s*(\d+(?:\.\d+)?)s",
        error_text,
        flags=re.IGNORECASE
    )

    if not match:
        return default_delay

    minutes = int(match.group(1) or 0)
    seconds = float(match.group(2))

    # Add a small safety margin so the next request is not sent
    # exactly at the quota boundary.
    return min(minutes * 60 + seconds + 1.0, 90.0)


def pace_groq_call():
    """Small delay between Groq API calls to reduce TPM pressure."""
    time.sleep(GROQ_CALL_DELAY)


def calculate_retry_delay(attempt):

    exponential_delay = (
        BASE_RETRY_DELAY *
        (2 ** (attempt - 1))
    )

    jitter = random.uniform(
        0,
        0.5
    )

    return min(
        exponential_delay + jitter,
        MAX_RETRY_DELAY
    )


def extract_text_from_llm_output(value):

    if value is None:
        raise ValueError(
            "LLM returned None"
        )

    # Normal Python string
    if isinstance(value, str):
        return value.strip()

    # LangChain AIMessage
    if hasattr(value, "content"):

        content = value.content

        if isinstance(content, str):
            return content.strip()

        if isinstance(content, list):

            parts = []

            for item in content:

                if isinstance(item, str):
                    parts.append(item)

                elif isinstance(item, dict):

                    if "text" in item:
                        parts.append(
                            str(item["text"])
                        )

            if parts:
                return "\n".join(parts).strip()

    # LangChain TextAccessor / similar objects
    if hasattr(value, "text"):

        try:
            text_value = value.text

            if callable(text_value):
                text_value = text_value()

            if isinstance(text_value, str):
                return text_value.strip()

            if text_value is not None:
                return str(text_value).strip()

        except Exception:
            pass

    # Some LangChain wrappers expose the payload through `value`
    # or `data`. Try those before falling back to repr/str.
    for attribute in ("value", "data"):
        if hasattr(value, attribute):
            try:
                nested = getattr(value, attribute)

                if callable(nested):
                    nested = nested()

                if isinstance(nested, str):
                    return nested.strip()

                if nested is not None:
                    return str(nested).strip()

            except Exception:
                pass

    return str(value).strip()


def extract_json_value(value):

    if isinstance(
        value,
        (list, dict)
    ):
        return value

    text = extract_text_from_llm_output(
        value
    )

    if not text:
        raise ValueError(
            "LLM returned empty output"
        )

    # Remove markdown fences
    text = re.sub(
        r"```(?:json)?",
        "",
        text,
        flags=re.IGNORECASE
    ).replace(
        "```",
        ""
    ).strip()

    # Try complete JSON directly
    try:

        return json.loads(text)

    except json.JSONDecodeError:
        pass

    # Find JSON array
    array_start = text.find("[")

    array_end = text.rfind("]")

    if (
        array_start != -1
        and array_end > array_start
    ):

        candidate = text[
            array_start:
            array_end + 1
        ]

        try:
            return json.loads(
                candidate
            )

        except json.JSONDecodeError:
            pass

    # Find JSON object
    object_start = text.find("{")

    object_end = text.rfind("}")

    if (
        object_start != -1
        and object_end > object_start
    ):

        candidate = text[
            object_start:
            object_end + 1
        ]

        try:
            return json.loads(
                candidate
            )

        except json.JSONDecodeError:
            pass

    raise ValueError(
        "LLM did not return valid JSON"
    )

def validate_search_output(data):

    if not isinstance(
        data,
        str
    ):
        raise ValueError(
            "Search output must be a string"
        )

    if not data.strip():
        raise ValueError(
            "Search output is empty"
        )

    return True


def validate_scraped_output(data):

    if not isinstance(
        data,
        str
    ):
        raise ValueError(
            "Scraped content must be a string"
        )

    if not data.strip():
        raise ValueError(
            "Scraped content is empty"
        )

    return True


def validate_research_data(data):

    if not isinstance(data, str):
        raise ValueError(
            "Research data must be a string"
        )

    text = data.strip()

    if not text:
        raise ValueError(
            "Research data is empty"
        )

    # The scraper can return a non-empty status message instead of
    # actual source content. Treat that as a failure so the retry
    # wrapper can use the search result fallback.
    unusable_markers = [
        "no high-quality results found",
        "no results found",
        "no usable results found",
        "no content found",
        "scraping failed"
    ]

    lowered = text.lower()

    if any(marker in lowered for marker in unusable_markers):
        raise ValueError(
            "Scraper returned no usable research content"
        )

    return True


def validate_reasoning_output(data):

    text = extract_text_from_llm_output(
        data
    )

    if not text:
        raise ValueError(
            "Reasoning output is empty"
        )

    return True


def validate_source_url(url):

    if not isinstance(
        url,
        str
    ):
        raise ValueError(
            "source_url must be a string"
        )

    url = url.strip()

    parsed = urlparse(
        url
    )

    if parsed.scheme not in {
        "http",
        "https"
    }:
        raise ValueError(
            "source_url must use HTTP or HTTPS"
        )

    if not parsed.netloc:
        raise ValueError(
            "source_url must contain a valid domain"
        )

    return True


def validate_evidence_output(data):

    if not isinstance(
        data,
        list
    ):
        raise ValueError(
            "Evidence output must be a list"
        )

    for item in data:

        if not isinstance(
            item,
            dict
        ):
            raise ValueError(
                "Evidence item must be an object"
            )

        try:

            validated = EvidenceItem.model_validate(
                item
            )

        except ValidationError as error:

            raise ValueError(
                f"Invalid evidence schema: {error}"
            )

        if not validated.claim.strip():
            raise ValueError(
                "Evidence claim cannot be empty"
            )

        if not validated.supporting_text.strip():
            raise ValueError(
                "Evidence supporting_text cannot be empty"
            )

        validate_source_url(
            validated.source_url
        )

    return True


def normalize_evidence_output(data):

    parsed = extract_json_value(
        data
    )

    if isinstance(
        parsed,
        dict
    ):

        parsed = parsed.get(
            "evidence",
            []
        )

    if parsed is None:
        return []

    if not isinstance(
        parsed,
        list
    ):
        raise ValueError(
            "Evidence output must be a list"
        )

    return parsed[:3]


def normalize_grounding_output(data):

    parsed = extract_json_value(
        data
    )

    if isinstance(
        parsed,
        list
    ):

        if not parsed:
            return {
                "verified": False,
                "reason": "No grounding result returned.",
                "confidence": 0.0
            }

        parsed = parsed[0]

    if not isinstance(
        parsed,
        dict
    ):
        raise ValueError(
            "Grounding output must be an object"
        )

    return parsed


def normalize_batched_grounding_output(data):

    parsed = extract_json_value(
        data
    )

    if isinstance(
        parsed,
        dict
    ):
        parsed = [parsed]

    if not isinstance(
        parsed,
        list
    ):
        raise ValueError(
            "Grounding output must be a list of objects"
        )

    return parsed


def validate_batched_grounding_output(data):

    if not isinstance(
        data,
        list
    ):
        raise ValueError(
            "Grounding output must be a list"
        )

    for item in data:
        if isinstance(item, dict):
            validate_grounding_output(item)

    return True


def validate_grounding_output(data):

    if not isinstance(
        data,
        dict
    ):
        raise ValueError(
            "Grounding output must be an object"
        )

    verified = data.get(
        "verified"
    )

    if not isinstance(
        verified,
        bool
    ):
        raise ValueError(
            "verified must be boolean"
        )

    reason = data.get(
        "reason"
    )

    if not isinstance(
        reason,
        str
    ):
        raise ValueError(
            "reason must be a string"
        )

    confidence = data.get(
        "confidence"
    )

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

    text = extract_text_from_llm_output(
        data
    )

    if not text:
        raise ValueError(
            "Insight output is empty"
        )

    return True


def validate_report_output(data):

    text = extract_text_from_llm_output(
        data
    )

    if not text:
        raise ValueError(
            "Report output is empty"
        )

    return True


def validate_critic_output(data):

    text = extract_text_from_llm_output(
        data
    )

    if not text:
        raise ValueError(
            "Critic output is empty"
        )

    return True


def validate_improved_report(data):

    text = extract_text_from_llm_output(
        data
    )

    if not text:
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
        request_id,
        stage_name,
        "started"
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
                validator(
                    result
                )

            duration = round(
                time.time() - start_time,
                2
            )

            log_event(
                request_id,
                stage_name,
                "success",
                attempt,
                duration
            )

            return stage_success(
                result,
                duration,
                attempt
            )

        except Exception as error:

            last_error = error

            error_type = classify_error(
                error
            )

            log_event(
                request_id,
                stage_name,
                "error",
                attempt,
                error_type=error_type,
                error=error
            )

            # Daily Groq limit / auth / bad request:
            # NEVER waste another API call.
            if error_type == "non_retryable":
                break

            if attempt < max_attempts:

                delay = calculate_retry_delay(attempt)

                # For Groq TPM/429 responses, prefer the exact retry
                # duration supplied by the API instead of blindly
                # using exponential backoff.
                if error_type == "retryable":
                    delay = get_retry_after_seconds(
                        error,
                        delay
                    )

                log_event(
                    request_id,
                    stage_name,
                    "retrying",
                    attempt,
                    duration=round(time.time() - start_time, 2),
                    error_type=error_type,
                    error=f"waiting {delay:.1f}s before retry"
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
                request_id,
                stage_name,
                "degraded",
                attempt,
                duration,
                classify_error(
                    last_error
                ),
                last_error,
                True
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
                request_id,
                stage_name,
                "failed",
                attempt,
                duration,
                classify_error(
                    fallback_error
                ),
                fallback_error,
                True
            )

            return stage_failure(
                fallback_error,
                duration,
                attempt,
                True
            )

    log_event(
        request_id,
        stage_name,
        "failed",
        attempt,
        duration,
        classify_error(
            last_error
        ),
        last_error,
        False
    )

    return stage_failure(
        last_error,
        duration,
        attempt,
        False
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
        r'https?://[^\s<>"\']+',
        text
    )

    cleaned = []

    for url in urls:

        url = url.rstrip(
            ".,);]}"
        )

        if url not in cleaned:
            cleaned.append(url)

    return cleaned


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


# ============================================================
# MAIN PIPELINE
# ============================================================

def run_research_pipeline(topic):

    request_id = str(
        uuid.uuid4()
    )

    pipeline_start = time.time()

    log_event(
        request_id,
        "pipeline",
        "started"
    )

    state = {}

    # --------------------------------------------------------
    # 1. SEARCH
    # --------------------------------------------------------

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
            request_id,
            "pipeline",
            "failed",
            duration=round(
                time.time() - pipeline_start,
                2
            )
        )

        return state

    search_data = search_results["data"]

    # --------------------------------------------------------
    # 2. SCRAPING
    # --------------------------------------------------------

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

        scraped = scrape_urls.invoke({
            "urls": ", ".join(urls)
        })

        scraped_text = extract_text_from_llm_output(
            scraped
        )

        validate_research_data(
            scraped_text
        )

        return scraped_text

    scraped_content = run_with_retry(
        request_id=request_id,
        stage_name="URL Ranking + Scraping",
        operation=scrape_operation,
        validator=validate_research_data,
        fallback=lambda: search_data
    )

    state["scraped_content"] = scraped_content

    # Never allow a failed/empty scrape to propagate as None.
    # Search output is the final safe fallback.
    research_data = (
        scraped_content.get("data")
        or search_data
        or ""
    )

    if not isinstance(research_data, str):
        research_data = extract_text_from_llm_output(
            research_data
        )

    if not research_data.strip():
        log_event(
            request_id,
            "pipeline",
            "failed",
            duration=round(
                time.time() - pipeline_start,
                2
            )
        )

        state["final_report"] = {
            "status": "failed",
            "data": "",
            "error": "No usable research content available.",
            "attempts": 0,
            "duration": 0,
            "fallback_used": False
        }

        return state

    # --------------------------------------------------------
    # 3. REASONING
    # --------------------------------------------------------

    pace_groq_call()

    reasoning = run_with_retry(
        request_id=request_id,
        stage_name="Reasoning",
        operation=lambda: extract_text_from_llm_output(
            execute_prompt_with_fallback(
                reasoning_prompt,
                {
                    "research": (
                        search_data
                        + "\n\n"
                        + research_data
                    )
                }
            )
        ),
        validator=validate_reasoning_output,
        fallback="Reasoning unavailable."
    )

    state["reasoning"] = reasoning

    reasoning_data = reasoning["data"]

    # --------------------------------------------------------
    # 4. EVIDENCE
    # --------------------------------------------------------

    print(
        "\nEVIDENCE INPUT PREVIEW:"
    )

    print(
        research_data[:5000]
    )

    print(
        "\n" + "=" * 80
    )

    pace_groq_call()

    evidence = run_with_retry(
        request_id=request_id,
        stage_name="Evidence Extraction",
        operation=lambda: normalize_evidence_output(
            execute_prompt_with_fallback(
                evidence_prompt,
                {
                    "research": research_data
                }
            )
        ),
        validator=validate_evidence_output,
        fallback=[]
    )

    state["evidence"] = evidence

    evidence_data = (
        evidence.get("data")
        or []
    )

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

    # --------------------------------------------------------
    # 5. GROUNDING (BATCHED SINGLE LLM CALL)
    # --------------------------------------------------------

    verified_evidence = []

    if evidence_data:

        pace_groq_call()

        grounding = run_with_retry(
            request_id=request_id,
            stage_name="Evidence Grounding",
            operation=lambda: (
                normalize_batched_grounding_output(
                    execute_prompt_with_fallback(
                        grounding_prompt,
                        {
                            "source_content": research_data,
                            "evidence_items": json.dumps(
                                evidence_data,
                                ensure_ascii=False
                            )
                        }
                    )
                )
            ),
            validator=validate_batched_grounding_output,
            fallback=[]
        )

        grounding_results = (
            grounding.get("data")
            or []
        )

        for idx, item in enumerate(evidence_data):

            verified_item = item.copy()

            match = None
            for g in grounding_results:
                if isinstance(g, dict) and g.get("evidence_index") == idx + 1:
                    match = g
                    break

            if match is None and idx < len(grounding_results) and isinstance(grounding_results[idx], dict):
                match = grounding_results[idx]

            if match is None:
                match = {
                    "verified": False,
                    "reason": "Grounding verification missing.",
                    "confidence": 0.0
                }

            verified_item["grounding"] = match

            if (
                match.get("verified", False) is True
                and match.get("confidence", 0) >= 0.8
            ):

                verified_evidence.append(
                    verified_item
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

    # --------------------------------------------------------
    # 6. INSIGHTS
    # --------------------------------------------------------

    if evidence_data:

        pace_groq_call()

        insights = run_with_retry(
            request_id=request_id,
            stage_name="Insight Generation",
            operation=lambda: extract_text_from_llm_output(
                execute_prompt_with_fallback(
                    insight_prompt,
                    {
                        "research": research_data,
                        "evidence": json.dumps(
                            evidence_data,
                            ensure_ascii=False
                        )
                    }
                )
            ),
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
            request_id,
            "Insight Generation",
            "skipped",
            fallback_used=True
        )

    state["insights"] = insights

    insights_data = insights["data"]

    # --------------------------------------------------------
    # 7. WRITER
    # --------------------------------------------------------

    # The writer is still allowed to run when grounding produced
    # no verified items, but the prompt receives an explicit empty
    # evidence list and the writer itself is instructed to say
    # "insufficient evidence" for unsupported factual claims.
    pace_groq_call()

    report = run_with_retry(
        request_id=request_id,
        stage_name="Writer",
        operation=lambda: extract_text_from_llm_output(
            execute_prompt_with_fallback(
                writer_prompt,
                {
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
                }
            )
        ),
        validator=validate_report_output,
        fallback=None
    )

    state["report"] = report

    if report["status"] == "failed":

        state["final_report"] = report

        log_event(
            request_id,
            "pipeline",
            "failed",
            duration=round(
                time.time() - pipeline_start,
                2
            )
        )

        return state

    report_data = report["data"]

    # --------------------------------------------------------
    # 8. CRITIC
    # --------------------------------------------------------

    pace_groq_call()

    feedback = run_with_retry(
        request_id=request_id,
        stage_name="Critic",
        operation=lambda: extract_text_from_llm_output(
            execute_prompt_with_fallback(
                critic_prompt,
                {
                    "report": report_data,
                    "evidence": json.dumps(
                        evidence_data,
                        ensure_ascii=False
                    )
                }
            )
        ),
        validator=validate_critic_output,
        fallback=(
            "Critic unavailable because the model rate limit was reached. "
            "The report was generated from the available research and verified evidence."
        )
    )

    state["feedback"] = feedback

    # If critic fails, keep the original report.
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
            request_id,
            "pipeline",
            "degraded",
            duration=round(
                time.time() - pipeline_start,
                2
            ),
            fallback_used=True
        )

        return state

    feedback_data = feedback["data"]

    # If critic had to use its fallback, do not spend another Groq
    # request on the improver. The writer report is already valid.
    if feedback.get("fallback_used"):
        final_report = {
            "status": "degraded",
            "data": report_data,
            "error": feedback.get("error"),
            "attempts": feedback.get("attempts", 1),
            "duration": feedback.get("duration"),
            "fallback_used": True
        }
        state["final_report"] = final_report

        total_duration = round(time.time() - pipeline_start, 2)
        log_event(
            request_id,
            "pipeline",
            "degraded",
            duration=total_duration,
            fallback_used=True
        )

        print("\n\n" + "=" * 80)
        print("FINAL REPORT")
        print("=" * 80)
        print(final_report["data"])
        print("\n" + "=" * 80)
        return state

    # --------------------------------------------------------
    # CONDITIONAL IMPROVER: Skip Improver if Critic score >= 8/10
    # --------------------------------------------------------
    score_match = re.search(r"Score\s*:\s*(\d+(?:\.\d+)?)\s*/\s*10", feedback_data, re.IGNORECASE)
    critic_score = float(score_match.group(1)) if score_match else 0.0

    if critic_score >= 8.0:
        log_event(
            request_id,
            "Improver",
            "skipped",
            fallback_used=False
        )

        final_report = {
            "status": "success",
            "data": report_data,
            "error": None,
            "attempts": 1,
            "duration": 0,
            "fallback_used": False
        }
        state["final_report"] = final_report

        total_duration = round(time.time() - pipeline_start, 2)
        log_event(
            request_id,
            "pipeline",
            "completed",
            duration=total_duration,
            fallback_used=False
        )

        print("\n\n" + "=" * 80)
        print(f"FINAL REPORT (HIGH CRITIC SCORE {critic_score:.1f}/10 - IMPROVER SKIPPED)")
        print("=" * 80)
        print(final_report["data"])
        print("\n" + "=" * 80)

        return state

    # --------------------------------------------------------
    # 9. IMPROVER
    # --------------------------------------------------------

    pace_groq_call()

    final_report = run_with_retry(
        request_id=request_id,
        stage_name="Improver",
        operation=lambda: extract_text_from_llm_output(
            execute_prompt_with_fallback(
                improver_prompt,
                {
                    "report": report_data,
                    "feedback": feedback_data,
                    "evidence": json.dumps(
                        evidence_data,
                        ensure_ascii=False
                    )
                }
            )
        ),
        validator=validate_improved_report,

        # VERY IMPORTANT:
        # If Groq hits 429 here, return the already-valid
        # critic-reviewed report instead of crashing.
        fallback=report_data
    )

    state["final_report"] = final_report

    # --------------------------------------------------------
    # COMPLETE
    # --------------------------------------------------------

    total_duration = round(
        time.time() - pipeline_start,
        2
    )

    final_status = (
        "completed"
        if final_report["status"] == "success"
        else "degraded"
    )

    log_event(
        request_id,
        "pipeline",
        final_status,
        duration=total_duration,
        fallback_used=(
            final_report.get(
                "fallback_used",
                False
            )
        )
    )

    # Print final report for CLI
    print(
        "\n\n" + "=" * 80
    )

    print(
        "FINAL REPORT"
    )

    print(
        "=" * 80
    )

    print(
        final_report.get("data")
        or "No final report was generated."
    )

    print(
        "\n" + "=" * 80
    )

    return state


# ============================================================
# REAL-TIME SSE STREAMING PIPELINE
# ============================================================

def run_research_pipeline_stream(topic):
    """
    Generator yielding real-time SSE progress events for frontend consumption.
    """
    request_id = str(uuid.uuid4())
    pipeline_start = time.time()

    yield {
        "event": "stage_start",
        "stage": "pipeline",
        "message": "Initiating deep research pipeline...",
        "request_id": request_id
    }

    # 1. SEARCH
    yield {
        "event": "stage_start",
        "stage": "Smart Search",
        "message": "Searching the web for high-quality research sources...",
        "request_id": request_id
    }

    search_results = run_with_retry(
        request_id=request_id,
        stage_name="Smart Search",
        operation=lambda: smart_search(topic),
        validator=validate_search_output,
        fallback=None
    )

    if search_results["status"] == "failed":
        yield {
            "event": "pipeline_failed",
            "stage": "Smart Search",
            "error": search_results["error"]
        }
        return

    search_data = search_results["data"]

    yield {
        "event": "stage_complete",
        "stage": "Smart Search",
        "message": "Search completed successfully."
    }

    # 2. SCRAPING
    yield {
        "event": "stage_start",
        "stage": "URL Ranking + Scraping",
        "message": "Ranking and scraping authoritative sources...",
        "request_id": request_id
    }

    def scrape_operation():
        urls = rank_urls(extract_urls(search_data))
        if not urls:
            raise ValueError("No valid URLs found in search results")
        scraped = scrape_urls.invoke({"urls": ", ".join(urls)})
        scraped_text = extract_text_from_llm_output(scraped)
        validate_research_data(scraped_text)
        return scraped_text

    scraped_content = run_with_retry(
        request_id=request_id,
        stage_name="URL Ranking + Scraping",
        operation=scrape_operation,
        validator=validate_research_data,
        fallback=lambda: search_data
    )

    research_data = scraped_content.get("data") or search_data or ""
    if not isinstance(research_data, str):
        research_data = extract_text_from_llm_output(research_data)

    yield {
        "event": "stage_complete",
        "stage": "URL Ranking + Scraping",
        "message": "Scraping completed."
    }

    # 3. REASONING
    yield {
        "event": "stage_start",
        "stage": "Reasoning",
        "message": "Analyzing themes, patterns, and source credibility...",
        "request_id": request_id
    }

    pace_groq_call()
    reasoning = run_with_retry(
        request_id=request_id,
        stage_name="Reasoning",
        operation=lambda: extract_text_from_llm_output(
            execute_prompt_with_fallback(
                reasoning_prompt,
                {"research": search_data + "\n\n" + research_data}
            )
        ),
        validator=validate_reasoning_output,
        fallback="Reasoning unavailable."
    )

    reasoning_data = reasoning["data"]
    yield {
        "event": "stage_complete",
        "stage": "Reasoning",
        "message": "Strategic reasoning completed."
    }

    # 4. EVIDENCE
    yield {
        "event": "stage_start",
        "stage": "Evidence Extraction",
        "message": "Extracting key empirical claims and metrics...",
        "request_id": request_id
    }

    pace_groq_call()
    evidence = run_with_retry(
        request_id=request_id,
        stage_name="Evidence Extraction",
        operation=lambda: normalize_evidence_output(
            execute_prompt_with_fallback(
                evidence_prompt,
                {"research": research_data}
            )
        ),
        validator=validate_evidence_output,
        fallback=[]
    )

    evidence_data = evidence.get("data") or []
    yield {
        "event": "stage_complete",
        "stage": "Evidence Extraction",
        "extracted_count": len(evidence_data)
    }

    # 5. GROUNDING
    yield {
        "event": "stage_start",
        "stage": "Evidence Grounding",
        "message": "Cross-verifying claims strictly against source text...",
        "request_id": request_id
    }

    verified_evidence = []
    if evidence_data:
        pace_groq_call()
        grounding = run_with_retry(
            request_id=request_id,
            stage_name="Evidence Grounding",
            operation=lambda: (
                normalize_batched_grounding_output(
                    execute_prompt_with_fallback(
                        grounding_prompt,
                        {
                            "source_content": research_data,
                            "evidence_items": json.dumps(evidence_data, ensure_ascii=False)
                        }
                    )
                )
            ),
            validator=validate_batched_grounding_output,
            fallback=[]
        )

        grounding_results = grounding.get("data") or []
        for idx, item in enumerate(evidence_data):
            verified_item = item.copy()
            match = None
            for g in grounding_results:
                if isinstance(g, dict) and g.get("evidence_index") == idx + 1:
                    match = g
                    break
            if match is None and idx < len(grounding_results) and isinstance(grounding_results[idx], dict):
                match = grounding_results[idx]
            if match is None:
                match = {"verified": False, "reason": "Grounding verification missing.", "confidence": 0.0}
            verified_item["grounding"] = match
            if match.get("verified", False) is True and match.get("confidence", 0) >= 0.8:
                verified_evidence.append(verified_item)

    evidence_data = verified_evidence
    yield {
        "event": "stage_complete",
        "stage": "Evidence Grounding",
        "verified_count": len(verified_evidence)
    }

    # 6. INSIGHTS
    yield {
        "event": "stage_start",
        "stage": "Insight Generation",
        "message": "Synthesizing deep technical and economic implications...",
        "request_id": request_id
    }

    if evidence_data:
        pace_groq_call()
        insights = run_with_retry(
            request_id=request_id,
            stage_name="Insight Generation",
            operation=lambda: extract_text_from_llm_output(
                execute_prompt_with_fallback(
                    insight_prompt,
                    {
                        "research": research_data,
                        "evidence": json.dumps(evidence_data, ensure_ascii=False)
                    }
                )
            ),
            validator=validate_insight_output,
            fallback="Insights unavailable."
        )
    else:
        insights = {"status": "skipped", "data": "Insights skipped because no verified evidence was available."}

    insights_data = insights["data"]
    yield {
        "event": "stage_complete",
        "stage": "Insight Generation",
        "message": "Insight generation completed."
    }

    # 7. WRITER
    yield {
        "event": "stage_start",
        "stage": "Writer",
        "message": "Drafting strictly grounded research report...",
        "request_id": request_id
    }

    pace_groq_call()
    report = run_with_retry(
        request_id=request_id,
        stage_name="Writer",
        operation=lambda: extract_text_from_llm_output(
            execute_prompt_with_fallback(
                writer_prompt,
                {
                    "topic": topic,
                    "research": search_data + "\n\n" + research_data,
                    "reasoning": reasoning_data,
                    "evidence": json.dumps(evidence_data, ensure_ascii=False),
                    "insights": insights_data
                }
            )
        ),
        validator=validate_report_output,
        fallback=None
    )

    if report["status"] == "failed":
        yield {
            "event": "pipeline_failed",
            "stage": "Writer",
            "error": report["error"]
        }
        return

    report_data = report["data"]
    yield {
        "event": "stage_complete",
        "stage": "Writer",
        "message": "Report draft generated."
    }

    # 8. CRITIC
    yield {
        "event": "stage_start",
        "stage": "Critic",
        "message": "Evaluating report for source grounding and quality...",
        "request_id": request_id
    }

    pace_groq_call()
    feedback = run_with_retry(
        request_id=request_id,
        stage_name="Critic",
        operation=lambda: extract_text_from_llm_output(
            execute_prompt_with_fallback(
                critic_prompt,
                {
                    "report": report_data,
                    "evidence": json.dumps(evidence_data, ensure_ascii=False)
                }
            )
        ),
        validator=validate_critic_output,
        fallback="Critic unavailable."
    )

    feedback_data = feedback["data"]
    score_match = re.search(r"Score\s*:\s*(\d+(?:\.\d+)?)\s*/\s*10", feedback_data, re.IGNORECASE)
    critic_score = float(score_match.group(1)) if score_match else 0.0

    yield {
        "event": "stage_complete",
        "stage": "Critic",
        "score": critic_score
    }

    # 9. IMPROVER (CONDITIONAL)
    if critic_score >= 8.0 or feedback.get("fallback_used"):
        final_report_text = report_data
        yield {
            "event": "stage_complete",
            "stage": "Improver",
            "message": f"Improver skipped (High Critic Score {critic_score:.1f}/10)."
        }
    else:
        yield {
            "event": "stage_start",
            "stage": "Improver",
            "message": "Refining report based on critic feedback...",
            "request_id": request_id
        }
        pace_groq_call()
        final_report_res = run_with_retry(
            request_id=request_id,
            stage_name="Improver",
            operation=lambda: extract_text_from_llm_output(
                execute_prompt_with_fallback(
                    improver_prompt,
                    {
                        "report": report_data,
                        "feedback": feedback_data,
                        "evidence": json.dumps(evidence_data, ensure_ascii=False)
                    }
                )
            ),
            validator=validate_improved_report,
            fallback=report_data
        )
        final_report_text = final_report_res["data"]
        yield {
            "event": "stage_complete",
            "stage": "Improver",
            "message": "Report refinement complete."
        }

    total_duration = round(time.time() - pipeline_start, 2)

    yield {
        "event": "pipeline_complete",
        "stage": "pipeline",
        "status": "completed",
        "duration": total_duration,
        "final_report": final_report_text
    }


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    try:

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

    except KeyboardInterrupt:

        print(
            "\nPipeline stopped by user."
        )

    except Exception as error:

        print(
            "\nPipeline failed safely."
        )

        print(
            f"Error: {error}"
        )