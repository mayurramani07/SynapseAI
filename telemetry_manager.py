import os
import json
import time
import threading

CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cache")
TELEMETRY_FILE = os.path.join(CACHE_DIR, "telemetry.json")

_lock = threading.Lock()

def _ensure_telemetry_file():
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR, exist_ok=True)
    if not os.path.exists(TELEMETRY_FILE):
        initial_data = {
            "created_at": time.time(),
            "total_research_runs": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "llm_calls": 0,
            "llm_prompt_tokens": 0,
            "llm_completion_tokens": 0,
            "provider_calls": {
                "tavily": {"success": 0, "fail": 0},
                "serper": {"success": 0, "fail": 0},
                "duckduckgo": {"success": 0, "fail": 0},
                "jina_reader": {"success": 0, "fail": 0}
            },
            "stage_durations": {
                "smart_search": [],
                "scraping": [],
                "reasoning": [],
                "evidence_extraction": [],
                "grounding": [],
                "insight_generation": [],
                "report_writer": [],
                "critic_improver": []
            },
            "recent_pipeline_durations": [],
            "logs": []
        }
        with open(TELEMETRY_FILE, "w", encoding="utf-8") as f:
            json.dump(initial_data, f, indent=2)

def _read_telemetry() -> dict:
    _ensure_telemetry_file()
    try:
        with open(TELEMETRY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def _write_telemetry(data: dict):
    _ensure_telemetry_file()
    try:
        with open(TELEMETRY_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"[Telemetry] Write error: {e}")

def log_event(category: str, message: str, level: str = "INFO", details: dict = None):
    """
    Record a telemetry event log (stores last 150 events).
    """
    with _lock:
        data = _read_telemetry()
        logs = data.get("logs", [])
        event = {
            "id": f"evt_{int(time.time()*1000)}",
            "timestamp": time.strftime("%H:%M:%S"),
            "category": category.upper(), # LLM, SEARCH, SCRAPE, CACHE, PIPELINE, ERROR
            "level": level.upper(),       # INFO, WARN, ERROR, SUCCESS
            "message": message,
            "details": details or {}
        }
        logs.append(event)
        if len(logs) > 150:
            logs = logs[-150:]
        data["logs"] = logs
        _write_telemetry(data)

def record_research_run(cached: bool, duration: float = 0.0):
    with _lock:
        data = _read_telemetry()
        data["total_research_runs"] = data.get("total_research_runs", 0) + 1
        if cached:
            data["cache_hits"] = data.get("cache_hits", 0) + 1
        else:
            data["cache_misses"] = data.get("cache_misses", 0) + 1
            if duration > 0:
                durations = data.get("recent_pipeline_durations", [])
                durations.append(round(duration, 2))
                data["recent_pipeline_durations"] = durations[-30:]
        _write_telemetry(data)

def record_llm_call(prompt_tokens_est: int = 1500, completion_tokens_est: int = 800, model: str = "gemini-2.5-flash", duration: float = 1.2):
    with _lock:
        data = _read_telemetry()
        data["llm_calls"] = data.get("llm_calls", 0) + 1
        data["llm_prompt_tokens"] = data.get("llm_prompt_tokens", 0) + prompt_tokens_est
        data["llm_completion_tokens"] = data.get("llm_completion_tokens", 0) + completion_tokens_est
        _write_telemetry(data)
    log_event("LLM", f"LLM Inference complete via {model} (~{prompt_tokens_est + completion_tokens_est} tokens)", level="SUCCESS", details={"model": model, "latency_s": duration})

def record_provider_call(provider: str, success: bool, error_msg: str = ""):
    with _lock:
        data = _read_telemetry()
        providers = data.get("provider_calls", {})
        prov_key = provider.lower()
        if prov_key not in providers:
            providers[prov_key] = {"success": 0, "fail": 0}
        
        if success:
            providers[prov_key]["success"] += 1
        else:
            providers[prov_key]["fail"] += 1
        data["provider_calls"] = providers
        _write_telemetry(data)
    
    if success:
        log_event("SEARCH", f"Provider {provider} search query executed successfully", level="SUCCESS")
    else:
        log_event("SEARCH", f"Provider {provider} failed: {error_msg}", level="WARN")

def _normalize_stage_key(stage_name: str) -> str:
    s = stage_name.lower().strip()
    if "search" in s:
        return "smart_search"
    elif "scrap" in s or "url" in s:
        return "scraping"
    elif "reason" in s:
        return "reasoning"
    elif "ground" in s:
        return "grounding"
    elif "evidence" in s or "extract" in s:
        return "evidence_extraction"
    elif "insight" in s:
        return "insight_generation"
    elif "writer" in s or "report" in s:
        return "report_writer"
    elif "critic" in s or "improve" in s:
        return "critic_improver"
    return s.replace(" ", "_")

def record_stage_duration(stage_name: str, duration: float):
    with _lock:
        data = _read_telemetry()
        stages = data.get("stage_durations", {})
        norm_key = _normalize_stage_key(stage_name)
        if norm_key not in stages:
            stages[norm_key] = []
        stages[norm_key].append(round(duration, 2))
        stages[norm_key] = stages[norm_key][-20:] # Keep last 20 runs
        data["stage_durations"] = stages
        _write_telemetry(data)
    
    log_event("PIPELINE", f"Stage '{stage_name}' completed in {duration}s", level="INFO")

def get_telemetry_summary() -> dict:
    with _lock:
        data = _read_telemetry()
        total_runs = data.get("total_research_runs", 0)
        hits = data.get("cache_hits", 0)
        misses = data.get("cache_misses", 0)
        total_cache_reqs = hits + misses
        hit_rate = round((hits / total_cache_reqs * 100), 1) if total_cache_reqs > 0 else 0.0
        
        durations = data.get("recent_pipeline_durations", [])
        avg_pipeline_duration = round(sum(durations) / len(durations), 2) if durations else 0.0

        # Calculate average stage latencies
        avg_stage_latencies = {}
        for stage, list_durs in data.get("stage_durations", {}).items():
            avg_stage_latencies[stage] = round(sum(list_durs) / len(list_durs), 2) if list_durs else 0.0

        # Calculate cache file size
        cache_file_path = os.path.join(CACHE_DIR, "research_cache.json")
        cache_size_kb = 0.0
        cached_topics_count = 0
        if os.path.exists(cache_file_path):
            cache_size_kb = round(os.path.getsize(cache_file_path) / 1024, 2)
            try:
                with open(cache_file_path, "r", encoding="utf-8") as cf:
                    cached_data = json.load(cf)
                    cached_topics_count = len(cached_data)
            except Exception:
                pass

        total_tokens = data.get("llm_prompt_tokens", 0) + data.get("llm_completion_tokens", 0)

        return {
            "system_status": "OPERATIONAL",
            "uptime_seconds": int(time.time() - data.get("created_at", time.time())),
            "total_research_runs": total_runs,
            "cache_hits": hits,
            "cache_misses": misses,
            "cache_hit_rate_pct": hit_rate,
            "avg_pipeline_duration_s": avg_pipeline_duration,
            "llm_calls": data.get("llm_calls", 0),
            "llm_prompt_tokens": data.get("llm_prompt_tokens", 0),
            "llm_completion_tokens": data.get("llm_completion_tokens", 0),
            "llm_total_tokens": total_tokens,
            "provider_calls": data.get("provider_calls", {}),
            "avg_stage_latencies_s": avg_stage_latencies,
            "cache_file_size_kb": cache_size_kb,
            "cached_topics_count": cached_topics_count,
            "logs": data.get("logs", [])[::-1] # Reverse so latest is first
        }

def clear_telemetry_logs():
    with _lock:
        data = _read_telemetry()
        data["logs"] = []
        _write_telemetry(data)
