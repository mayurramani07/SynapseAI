import os
import re
import json
import hashlib
import time

CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cache")
CACHE_FILE = os.path.join(CACHE_DIR, "research_cache.json")


def normalize_topic(topic: str) -> str:
    """
    Normalize topic string for consistent hashing.
    """
    cleaned = topic.lower().strip()
    cleaned = re.sub(r'[^\w\s]', '', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned)
    return cleaned


def get_topic_hash(topic: str) -> str:
    """
    Generate SHA-256 hash for normalized topic.
    """
    normalized = normalize_topic(topic)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _ensure_cache_dir():
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR, exist_ok=True)
    if not os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f)


def get_cached_research(topic: str) -> dict | None:
    """
    Retrieve cached research result if available.
    """
    try:
        _ensure_cache_dir()
        topic_hash = get_topic_hash(topic)

        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            cache = json.load(f)

        if topic_hash in cache:
            cached_entry = cache[topic_hash]
            data = dict(cached_entry.get("data", {}))
            data["cached"] = True
            data["cached_at"] = cached_entry.get("timestamp")
            return data
    except Exception as e:
        print(f"[CacheManager] Read error: {e}")

    return None


def set_cached_research(topic: str, data: dict):
    """
    Save research result payload to disk cache.
    """
    try:
        _ensure_cache_dir()
        topic_hash = get_topic_hash(topic)

        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            cache = json.load(f)

        clean_data = dict(data)
        clean_data["cached"] = True

        cache[topic_hash] = {
            "topic": topic,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "data": clean_data
        }

        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=2, ensure_ascii=False)

    except Exception as e:
        print(f"[CacheManager] Write error: {e}")
