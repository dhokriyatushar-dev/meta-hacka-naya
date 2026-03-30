"""
EduPath AI — Resource Fetcher
Fetches real course links from DuckDuckGo Search API for any topic.
Caches results for 7 days in backend/data/resource_cache.json.
"""
import os
import json
import time
import logging
import asyncio
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
CACHE_FILE = os.path.join(DATA_DIR, "resource_cache.json")
CACHE_EXPIRY_SECONDS = 7 * 24 * 60 * 60  # 7 days

_executor = ThreadPoolExecutor(max_workers=3)


def _load_cache() -> dict:
    """Load the resource cache from disk."""
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def _save_cache(cache: dict):
    """Save the resource cache to disk."""
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)


def _is_cache_fresh(entry: dict) -> bool:
    """Check if a cache entry is still fresh (within 7 days)."""
    cached_at = entry.get("cached_at", 0)
    return (time.time() - cached_at) < CACHE_EXPIRY_SECONDS


def _search_duckduckgo(query: str, max_results: int = 3) -> List[Dict]:
    """Run a single DuckDuckGo search and return parsed results."""
    try:
        from duckduckgo_search import DDGS
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                results.append({
                    "title": r.get("title", ""),
                    "url": r.get("href", ""),
                    "description": r.get("body", ""),
                })
        return results
    except Exception as e:
        logger.warning(f"DuckDuckGo search failed for '{query}': {e}")
        return []


def _detect_source(url: str) -> str:
    """Detect the resource source from its URL."""
    url_lower = url.lower()
    if "kaggle.com" in url_lower:
        return "Kaggle"
    elif "freecodecamp.org" in url_lower:
        return "freeCodeCamp"
    elif "fast.ai" in url_lower:
        return "fast.ai"
    elif "huggingface.co" in url_lower:
        return "HuggingFace"
    elif "ocw.mit.edu" in url_lower:
        return "MIT OCW"
    elif "coursera.org" in url_lower:
        return "Coursera"
    elif "edx.org" in url_lower:
        return "edX"
    elif "khanacademy.org" in url_lower:
        return "Khan Academy"
    else:
        return "Other"


def _detect_resource_type(url: str, title: str) -> str:
    """Detect resource type from URL and title."""
    combined = (url + " " + title).lower()
    if "notebook" in combined or "colab" in combined or "kaggle.com/code" in combined:
        return "notebook"
    elif "article" in combined or "blog" in combined or "news" in combined:
        return "article"
    else:
        return "course"


def _estimate_duration(description: str, resource_type: str) -> str:
    """Estimate learning duration from description or resource type."""
    desc_lower = description.lower()
    # Try to extract time from description
    for pattern in ["hour", "min", "week"]:
        if pattern in desc_lower:
            # Find the number before the time unit
            words = desc_lower.split()
            for i, w in enumerate(words):
                if pattern in w and i > 0:
                    try:
                        num = int(words[i - 1])
                        if "hour" in w:
                            return f"~{num} hours"
                        elif "min" in w:
                            return f"~{num} min"
                        elif "week" in w:
                            return f"~{num} weeks"
                    except ValueError:
                        pass

    # Defaults based on type
    if resource_type == "notebook":
        return "~1 hour"
    elif resource_type == "article":
        return "~30 min"
    else:
        return "~2 hours"


def fetch_resources_for_topic(topic_name: str, topic_id: str = "") -> List[Dict]:
    """
    Fetch real course links for a topic using DuckDuckGo Search.
    Returns max 3 resources with title, url, description, source, type, duration.
    Results are cached for 7 days.
    """
    cache_key = topic_id or topic_name.lower().replace(" ", "_")

    # Check cache first
    cache = _load_cache()
    if cache_key in cache and _is_cache_fresh(cache[cache_key]):
        logger.info(f"Resource cache HIT for '{cache_key}'")
        return cache[cache_key]["resources"]

    logger.info(f"Resource cache MISS for '{cache_key}', fetching from DuckDuckGo...")

    # Search queries targeting high-quality free resources
    queries = [
        f"{topic_name} course site:kaggle.com/learn",
        f"{topic_name} tutorial site:freecodecamp.org",
        f"{topic_name} course fast.ai OR huggingface.co/learn",
    ]

    all_results = []
    for query in queries:
        results = _search_duckduckgo(query, max_results=2)
        all_results.extend(results)

    # Deduplicate by URL
    seen_urls = set()
    unique_results = []
    for r in all_results:
        if r["url"] and r["url"] not in seen_urls:
            seen_urls.add(r["url"])
            source = _detect_source(r["url"])
            rtype = _detect_resource_type(r["url"], r["title"])
            unique_results.append({
                "title": r["title"],
                "url": r["url"],
                "description": r["description"][:200],
                "source": source,
                "resource_type": rtype,
                "duration_estimate": _estimate_duration(r["description"], rtype),
            })

    # Limit to 3
    resources = unique_results[:3]

    # If DuckDuckGo returned nothing, fall back to curated resources
    if not resources:
        resources = _get_fallback_resources(topic_name, topic_id)

    # Save to cache
    cache[cache_key] = {
        "resources": resources,
        "cached_at": time.time(),
    }
    _save_cache(cache)

    return resources


async def fetch_resources_async(topic_name: str, topic_id: str = "") -> List[Dict]:
    """Async wrapper for resource fetching."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        _executor,
        fetch_resources_for_topic,
        topic_name,
        topic_id,
    )


def _get_fallback_resources(topic_name: str, topic_id: str) -> List[Dict]:
    """Fallback to curated resources from curriculum.py when search fails."""
    try:
        from environment.curriculum import TOPIC_GRAPH, RESOURCE_DB

        # Try topic graph first
        topic = TOPIC_GRAPH.get(topic_id)
        if topic and topic.resources:
            return [
                {
                    "title": r.title,
                    "url": r.url,
                    "description": r.description or f"{r.title} on {r.platform}",
                    "source": r.platform or _detect_source(r.url),
                    "resource_type": r.type.value.replace("_", " "),
                    "duration_estimate": "~2 hours",
                }
                for r in topic.resources[:3]
            ]

        # Try resource DB
        if topic_id in RESOURCE_DB:
            return [
                {
                    "title": r.title,
                    "url": r.url,
                    "description": r.description or f"{r.title} on {r.platform}",
                    "source": r.platform or _detect_source(r.url),
                    "resource_type": r.type.value.replace("_", " "),
                    "duration_estimate": "~2 hours",
                }
                for r in RESOURCE_DB[topic_id][:3]
            ]
    except Exception as e:
        logger.warning(f"Fallback resource lookup failed: {e}")

    # Absolute fallback
    return [
        {
            "title": f"Search: {topic_name}",
            "url": f"https://www.google.com/search?q={topic_name.replace(' ', '+')}+free+course",
            "description": f"Find free courses and tutorials for {topic_name}",
            "source": "Other",
            "resource_type": "course",
            "duration_estimate": "~2 hours",
        }
    ]
