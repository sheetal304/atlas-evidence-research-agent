import os
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode

from dotenv import load_dotenv
from tavily import TavilyClient

load_dotenv()

RESULTS_PER_QUERY = 5
SEARCH_TIMEOUT = 40
MAX_EXCERPT_CHARS = 1500
TRACKING_PARAMS = {"utm_source", "utm_medium", "utm_campaign", "utm_term",
                   "utm_content", "fbclid", "gclid", "ref"}


class SearchError(Exception):
    """Tavily key missing hai ya koi bhi search kaam nahi kar saka."""


def _get_client():
    key = os.getenv("TAVILY_API_KEY")
    if not key:
        raise SearchError("TAVILY_API_KEY nahi mili. .env file check karo.")
    return TavilyClient(api_key=key)


def normalize_url(url):
    """Same page ke alag-alag URL ko ek jaisa banata hai (duplicate hatane ke liye)."""
    p = urlparse(url.strip())
    query = [(k, v) for k, v in parse_qsl(p.query) if k.lower() not in TRACKING_PARAMS]
    path = p.path.rstrip("/")
    return urlunparse((p.scheme.lower(), p.netloc.lower(), path, "", urlencode(query), ""))


def get_domain(url):
    host = urlparse(url).netloc.lower()
    return host[4:] if host.startswith("www.") else host


def _search_one(client, sub_question):
    return client.search(
        query=sub_question["search_query"],
        search_depth="advanced",
        max_results=RESULTS_PER_QUERY,
    )


def collect_sources(plan, progress=None):
    """
    Har sub-question ke liye search karta hai.
    Lautata hai: {"sources": [...], "query_log": [...]}
    progress: optional function(done, total, sub_question) UI ke liye.
    """
    client = _get_client()
    subs = plan["sub_questions"]
    by_url = {}
    query_log = []
    total = len(subs)

    for i, sq in enumerate(subs, start=1):
        entry = {"id": sq["id"], "query": sq["search_query"], "found": 0, "error": None}
        try:
            with ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(_search_one, client, sq)
                response = future.result(timeout=SEARCH_TIMEOUT)
            results = response.get("results", [])
        except FutureTimeout:
            entry["error"] = f"{SEARCH_TIMEOUT} second me jawab nahi aaya"
            results = []
        except Exception as e:
            entry["error"] = str(e)[:150]
            results = []

        for r in results:
            url = (r.get("url") or "").strip()
            content = (r.get("content") or "").strip()
            if not url or not content:
                continue
            key = normalize_url(url)
            entry["found"] += 1

            if key in by_url:
                src = by_url[key]
                if sq["id"] not in src["found_for"]:
                    src["found_for"].append(sq["id"])
                if len(content) > len(src["excerpt"]) and len(src["excerpt"]) < 400:
                    src["excerpt"] = content[:MAX_EXCERPT_CHARS]
                continue

            by_url[key] = {
                "title": (r.get("title") or get_domain(url)).strip(),
                "url": url,
                "domain": get_domain(url),
                "excerpt": content[:MAX_EXCERPT_CHARS],
                "score": r.get("score"),
                "published_date": r.get("published_date"),
                "found_for": [sq["id"]],
            }

        query_log.append(entry)
        if progress:
            progress(i, total, sq)

    sources = list(by_url.values())
    if not sources:
        errors = [e["error"] for e in query_log if e["error"]]
        detail = f" Pehla error: {errors[0]}" if errors else ""
        raise SearchError("Koi bhi source nahi mila." + detail)

    # Sabse relevant pehle, phir IDs do
    sources.sort(key=lambda s: (s["score"] is None, -(s["score"] or 0)))
    for n, src in enumerate(sources, start=1):
        src["id"] = f"S{n}"

    return {"sources": sources, "query_log": query_log}