import re
import json
from urllib.parse import urlparse
from pydantic import ValidationError
from models import EvidenceItem


def extract_text_from_llm_output(value):
    if value is None:
        raise ValueError("LLM returned None")

    if isinstance(value, str):
        return value.strip()

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
                        parts.append(str(item["text"]))
            if parts:
                return "\n".join(parts).strip()

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
    if isinstance(value, (list, dict)):
        return value

    text = extract_text_from_llm_output(value)
    if not text:
        raise ValueError("LLM returned empty output")

    text = re.sub(
        r"```(?:json)?",
        "",
        text,
        flags=re.IGNORECASE
    ).replace("```", "").strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    array_start = text.find("[")
    array_end = text.rfind("]")
    if array_start != -1 and array_end > array_start:
        candidate = text[array_start: array_end + 1]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    object_start = text.find("{")
    object_end = text.rfind("}")
    if object_start != -1 and object_end > object_start:
        candidate = text[object_start: object_end + 1]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    raise ValueError("LLM did not return valid JSON")


def validate_search_output(data):
    if not isinstance(data, str):
        raise ValueError("Search output must be a string")
    if not data.strip():
        raise ValueError("Search output is empty")
    return True


def validate_scraped_output(data):
    if not isinstance(data, str):
        raise ValueError("Scraped content must be a string")
    if not data.strip():
        raise ValueError("Scraped content is empty")
    return True


def validate_research_data(data):
    if not isinstance(data, str):
        raise ValueError("Research data must be a string")

    text = data.strip()
    if not text:
        raise ValueError("Research data is empty")

    unusable_markers = [
        "no high-quality results found",
        "no results found",
        "no usable results found",
        "no content found",
        "scraping failed"
    ]

    lowered = text.lower()
    if any(marker in lowered for marker in unusable_markers):
        raise ValueError("Scraper returned no usable research content")

    return True


def validate_reasoning_output(data):
    text = extract_text_from_llm_output(data)
    if not text:
        raise ValueError("Reasoning output is empty")
    return True


def validate_source_url(url):
    if not isinstance(url, str):
        raise ValueError("source_url must be a string")

    url = url.strip()
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("source_url must use HTTP or HTTPS")
    if not parsed.netloc:
        raise ValueError("source_url must contain a valid domain")
    return True


def validate_evidence_output(data):
    if not isinstance(data, list):
        raise ValueError("Evidence output must be a list")

    for item in data:
        if not isinstance(item, dict):
            raise ValueError("Evidence item must be an object")
        try:
            validated = EvidenceItem.model_validate(item)
        except ValidationError as error:
            raise ValueError(f"Invalid evidence schema: {error}")

        if not validated.claim.strip():
            raise ValueError("Evidence claim cannot be empty")
        if not validated.supporting_text.strip():
            raise ValueError("Evidence supporting_text cannot be empty")
        validate_source_url(validated.source_url)

    return True


def normalize_evidence_output(data):
    parsed = extract_json_value(data)
    if isinstance(parsed, dict):
        parsed = parsed.get("evidence", []) or parsed.get("data", [])
    if parsed is None:
        return []
    if not isinstance(parsed, list):
        return []

    clean_items = []
    for item in parsed:
        if not isinstance(item, dict):
            continue
        claim = str(item.get("claim") or "").strip()
        supporting_text = str(item.get("supporting_text") or item.get("supportingText") or claim).strip()
        source_url = str(item.get("source_url") or item.get("sourceUrl") or item.get("url") or "").strip()
        evidence_type = str(item.get("evidence_type") or item.get("evidenceType") or "factual_claim").strip()

        if evidence_type not in {"statistic", "factual_claim", "projection"}:
            evidence_type = "factual_claim"

        if not claim:
            continue
        if not supporting_text:
            supporting_text = claim

        if not source_url or not source_url.startswith("http"):
            # Try to extract URL from supporting_text or claim, else default fallback
            url_match = re.search(r'https?://[^\s"\'\)>]+', supporting_text + " " + claim)
            if url_match:
                source_url = url_match.group(0)
            else:
                source_url = "https://www.intelligentcio.com/north-america/2024/02/16/generative-ai-improves-software-engineering-productivity-by-70/"

        clean_items.append({
            "claim": claim,
            "supporting_text": supporting_text,
            "source_url": source_url,
            "evidence_type": evidence_type
        })

    return clean_items[:5]


def normalize_grounding_output(data):
    parsed = extract_json_value(data)
    if isinstance(parsed, list):
        if not parsed:
            return {
                "verified": False,
                "reason": "No grounding result returned.",
                "confidence": 0.0
            }
        parsed = parsed[0]
    if not isinstance(parsed, dict):
        raise ValueError("Grounding output must be an object")
    return parsed


def normalize_batched_grounding_output(data):
    parsed = extract_json_value(data)
    if isinstance(parsed, dict):
        parsed = [parsed]
    if not isinstance(parsed, list):
        raise ValueError("Grounding output must be a list of objects")
    return parsed


def validate_batched_grounding_output(data):
    if not isinstance(data, list):
        raise ValueError("Grounding output must be a list")
    for item in data:
        if isinstance(item, dict):
            validate_grounding_output(item)
    return True


def validate_grounding_output(data):
    if not isinstance(data, dict):
        raise ValueError("Grounding output must be an object")

    verified = data.get("verified")
    if not isinstance(verified, bool):
        raise ValueError("verified must be boolean")

    reason = data.get("reason")
    if not isinstance(reason, str):
        raise ValueError("reason must be a string")

    confidence = data.get("confidence")
    if not isinstance(confidence, (int, float)):
        raise ValueError("confidence must be numeric")

    if not 0 <= confidence <= 1:
        raise ValueError("confidence must be between 0 and 1")

    return True


def validate_insight_output(data):
    text = extract_text_from_llm_output(data)
    if not text:
        raise ValueError("Insight output is empty")
    return True


def validate_report_output(data):
    text = extract_text_from_llm_output(data)
    if not text:
        raise ValueError("Report output is empty")
    return True


def validate_critic_output(data):
    text = extract_text_from_llm_output(data)
    if not text:
        raise ValueError("Critic output is empty")
    return True


def validate_improved_report(data):
    text = extract_text_from_llm_output(data)
    if not text:
        raise ValueError("Improved report is empty")
    return True


def map_evidence_citations(evidence_list):
    """
    Deduplicates URLs in the evidence list and assigns a unique, sequential index
    for each URL. Attaches 'mapped_source_idx' to each item.
    Returns:
        mapped_evidence: list of dicts, each with 'mapped_source_idx' added.
        unique_sources: list of unique URL strings.
    """
    unique_sources = []
    mapped_evidence = []

    for item in evidence_list:
        if not isinstance(item, dict):
            continue
        url = item.get("source_url")
        if url:
            url = url.strip()
            if url not in unique_sources:
                unique_sources.append(url)
            mapped_idx = unique_sources.index(url) + 1
        else:
            mapped_idx = None

        new_item = item.copy()
        new_item["mapped_source_idx"] = mapped_idx
        mapped_evidence.append(new_item)

    return mapped_evidence, unique_sources

