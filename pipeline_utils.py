import re
import time
import json
import random
import logging
from datetime import datetime, timezone

MAX_ATTEMPTS = 4
BASE_RETRY_DELAY = 2.0
MAX_RETRY_DELAY = 30.0
GROQ_CALL_DELAY = 3.0

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s"
)

logger = logging.getLogger("synapseai")


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

    daily_limit_errors = [
        "tpd limit",
        "tokens per day",
        "daily token limit",
        "daily limit",
    ]

    for pattern in daily_limit_errors:
        if pattern in error_text:
            return "non_retryable"

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

    match = re.search(
        r"try again in\s*(?:(\d+)m)?\s*(\d+(?:\.\d+)?)s",
        error_text,
        flags=re.IGNORECASE
    )

    if not match:
        return default_delay

    minutes = int(match.group(1) or 0)
    seconds = float(match.group(2))

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

    for attempt in range(1, max_attempts + 1):
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
            error_type = classify_error(error)

            log_event(
                request_id,
                stage_name,
                "error",
                attempt,
                error_type=error_type,
                error=error
            )

            if error_type == "non_retryable":
                break

            if attempt < max_attempts:
                delay = calculate_retry_delay(attempt)

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
                validator(fallback_data)

            log_event(
                request_id,
                stage_name,
                "degraded",
                attempt,
                duration,
                classify_error(last_error),
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
                classify_error(fallback_error),
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
        classify_error(last_error),
        last_error,
        False
    )

    return stage_failure(
        last_error,
        duration,
        attempt,
        False
    )
