import re
import time
import json
import uuid

from agents import (
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
from pipeline_utils import (
    log_event,
    pace_groq_call,
    run_with_retry,
    logger
)
from pipeline_validators import (
    extract_text_from_llm_output,
    validate_search_output,
    validate_research_data,
    validate_reasoning_output,
    normalize_evidence_output,
    validate_evidence_output,
    normalize_batched_grounding_output,
    validate_batched_grounding_output,
    validate_insight_output,
    validate_report_output,
    validate_critic_output,
    validate_improved_report,
    map_evidence_citations
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
from cache_manager import get_cached_research, set_cached_research

# ============================================================
# MAIN PIPELINE
# ============================================================

def run_research_pipeline(topic):
    request_id = str(uuid.uuid4())
    pipeline_start = time.time()

    # Check local cache first
    cached_result = get_cached_research(topic)
    if cached_result:
        logger.info("Local cache hit for topic: %s", topic)
        return cached_result

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
        operation=lambda: smart_search(topic),
        validator=validate_search_output,
        fallback=None
    )
    state["search_results"] = search_results

    if search_results["status"] == "failed":
        log_event(
            request_id,
            "pipeline",
            "failed",
            duration=round(time.time() - pipeline_start, 2)
        )
        return state

    search_data = search_results["data"]

    # --------------------------------------------------------
    # 2. SCRAPING
    # --------------------------------------------------------
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
    state["scraped_content"] = scraped_content

    research_data = scraped_content.get("data") or search_data or ""
    if not isinstance(research_data, str):
        research_data = extract_text_from_llm_output(research_data)

    if not research_data.strip():
        log_event(
            request_id,
            "pipeline",
            "failed",
            duration=round(time.time() - pipeline_start, 2)
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
                {"research": search_data + "\n\n" + research_data}
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
    logger.debug("EVIDENCE INPUT PREVIEW:\n%s", research_data[:5000])

    pace_groq_call()
    evidence = run_with_retry(
        request_id=request_id,
        stage_name="Evidence Extraction",
        operation=lambda: normalize_evidence_output(
            execute_prompt_with_fallback(
                evidence_prompt,
                {"research": f"SEARCH DATA & SOURCES:\n{search_data}\n\nRESEARCH CONTENT:\n{research_data}"},
                json_mode=True
            )
        ),
        validator=validate_evidence_output,
        fallback=[]
    )
    state["evidence"] = evidence
    evidence_data = evidence.get("data") or []

    logger.debug("RAW EVIDENCE OUTPUT:\n%s", json.dumps(evidence_data, indent=2, ensure_ascii=False))
    logger.info("Extracted Evidence Count: %d", len(evidence_data))

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
                        },
                        json_mode=True
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
                match = {
                    "verified": False,
                    "reason": "Grounding verification missing.",
                    "confidence": 0.0
                }
            verified_item["grounding"] = match
            if match.get("verified", False) is True and match.get("confidence", 0) >= 0.8:
                verified_evidence.append(verified_item)

    state["verified_evidence"] = {
        "status": "success",
        "data": verified_evidence,
        "error": None,
        "attempts": 1,
        "duration": None,
        "fallback_used": False
    }

    # Map citations: attach mapped_source_idx for consistent footnote numbering
    evidence_data, unique_sources = map_evidence_citations(verified_evidence)
    state["unique_sources"] = unique_sources

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
            fallback="Insights unavailable because insight generation failed."
        )
    else:
        insights = {
            "status": "skipped",
            "data": "Insights skipped because no verified evidence was available.",
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
            duration=round(time.time() - pipeline_start, 2)
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
            duration=round(time.time() - pipeline_start, 2),
            fallback_used=True
        )
        return state

    feedback_data = feedback["data"]

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

        logger.info("FINAL REPORT (degraded - critic fallback used)")
        logger.debug("%s", final_report["data"])
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

        logger.info("FINAL REPORT (HIGH CRITIC SCORE %.1f/10 - IMPROVER SKIPPED)", critic_score)
        logger.debug("%s", final_report["data"])
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
        fallback=report_data
    )
    state["final_report"] = final_report

    total_duration = round(time.time() - pipeline_start, 2)
    final_status = "completed" if final_report["status"] == "success" else "degraded"

    log_event(
        request_id,
        "pipeline",
        final_status,
        duration=total_duration,
        fallback_used=final_report.get("fallback_used", False)
    )

    logger.info("FINAL REPORT")
    logger.debug("%s", final_report.get("data") or "No final report was generated.")

    set_cached_research(topic, state)

    return state


# ============================================================
# REAL-TIME SSE STREAMING PIPELINE
# ============================================================

def run_research_pipeline_stream(topic):
    request_id = str(uuid.uuid4())
    pipeline_start = time.time()

    # Check local cache first
    cached_data = get_cached_research(topic)
    if cached_data:
        logger.info("Local cache hit for stream topic: %s", topic)
        yield {
            "event": "stage_start",
            "stage": "Cache Lookup",
            "message": "⚡ Instant local cache match found!",
            "request_id": request_id
        }
        time.sleep(0.1)
        yield {
            "event": "pipeline_complete",
            "stage": "pipeline",
            "status": "completed",
            "cached": True,
            "duration": 0.05,
            "final_report": cached_data.get("final_report") or cached_data.get("final_report_text") or "",
            "reasoning": cached_data.get("reasoning") or "",
            "evidence": cached_data.get("evidence") or [],
            "insights": cached_data.get("insights") or "",
            "feedback": cached_data.get("feedback") or ""
        }
        return

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
                {"research": research_data},
                json_mode=True
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
                            "evidence_items": json.dumps(
                                evidence_data,
                                ensure_ascii=False
                            )
                        },
                        json_mode=True
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
                match = {
                    "verified": False,
                    "reason": "Grounding verification missing.",
                    "confidence": 0.0
                }
            verified_item["grounding"] = match
            if match.get("verified", False) is True and match.get("confidence", 0) >= 0.8:
                verified_evidence.append(verified_item)

    # Map citations for consistent footnote numbering
    evidence_data, unique_sources = map_evidence_citations(verified_evidence)
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
                        "evidence": json.dumps(
                            evidence_data,
                            ensure_ascii=False
                        )
                    }
                )
            ),
            validator=validate_insight_output,
            fallback="Insights unavailable."
        )
    else:
        insights = {
            "status": "skipped",
            "data": "Insights skipped because no verified evidence was available."
        }

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
                    "evidence": json.dumps(
                        evidence_data,
                        ensure_ascii=False
                    )
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
                        "evidence": json.dumps(
                            evidence_data,
                            ensure_ascii=False
                        )
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

    completed_payload = {
        "event": "pipeline_complete",
        "stage": "pipeline",
        "status": "completed",
        "cached": False,
        "duration": total_duration,
        "final_report": final_report_text,
        "reasoning": reasoning_data,
        "evidence": evidence_data,
        "insights": insights_data,
        "feedback": feedback_data
    }

    set_cached_research(topic, completed_payload)
    yield completed_payload



# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    try:
        topic = input("Enter topic: ").strip()
        if not topic:
            print("Please enter a research topic.")
        else:
            run_research_pipeline(topic)
    except KeyboardInterrupt:
        print("\nPipeline stopped by user.")
    except Exception as error:
        print("\nPipeline failed safely.")
        print(f"Error: {error}")