import os
import logging
from datetime import datetime

import requests
from requests.adapters import HTTPAdapter, Retry

from .models import TrendingStory, db

# -----------------------
# Configuration & Logging
# -----------------------

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

NEWS_API_KEY = os.getenv("NEWS_API_KEY")

# OpenAI (support both old and new clients gracefully)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

_openai_client = None
try:
    # Newer style (openai>=1.0)
    from openai import OpenAI  # type: ignore
    if OPENAI_API_KEY:
        _openai_client = OpenAI(api_key=OPENAI_API_KEY)
except Exception:
    pass

if _openai_client is None:
    # Fallback to legacy openai
    try:
        import openai  # type: ignore
        if OPENAI_API_KEY:
            openai.api_key = OPENAI_API_KEY
    except Exception:
        openai = None  # type: ignore

# HTTP session with retries/timeouts
_session = requests.Session()
_retries = Retry(
    total=3,
    backoff_factor=0.5,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["GET", "POST"],
)
_session.mount("https://", HTTPAdapter(max_retries=_retries))
_session.headers.update({"User-Agent": "TechBlogAI/1.0"})

# --------------
# Topic filtering
# --------------
# Strongly bias to *computer* tech by restricting to tech-focused domains
_TECH_DOMAINS = ",".join([
    "techcrunch.com",
    "theverge.com",
    "wired.com",
    "arstechnica.com",
    "engadget.com",
    "thenextweb.com",
    "venturebeat.com",
    "gizmodo.com",
    "tomshardware.com",
    "anandtech.com",
    "bleepingcomputer.com",
    "darkreading.com",
    "zdnet.com",
    "cnet.com",
    "makeuseof.com",
    "pcgamer.com",
    "hackaday.com",
])

# Extra keyword guard (keeps it *computer* focused)
_KEYWORDS = [
    "ai", "machine learning", "neural", "gpu", "cpu", "chip", "semiconductor",
    "programming", "developer", "devops", "framework", "python", "javascript",
    "cybersecurity", "malware", "exploit", "vulnerability", "zero-day",
    "cloud", "kubernetes", "docker", "linux", "windows", "mac",
    "game dev", "game engine", "unreal", "unity",
    "robotics", "automation", "nlp", "computer vision",
    "data center", "datacenter",
]

def _matches_topic(title: str, description: str) -> bool:
    text = f"{title or ''} {description or ''}".lower()
    return any(k in text for k in _KEYWORDS)

# -------------------------------
# Fetch trending computer/tech news
# -------------------------------

def fetch_trending_news():
    """
    Fetch fresh computer/tech focused stories (AI, programming, security, hardware).
    Uses NewsAPI 'everything' endpoint, restricted to tech domains, newest first.
    """
    if not NEWS_API_KEY:
        logger.error("NEWS_API_KEY is not set. Skipping fetch.")
        return []

    url = "https://newsapi.org/v2/everything"
    params = {
        # broad query to include common computer-tech terms
        "q": "AI OR computer OR programming OR cybersecurity OR GPU OR CPU OR chip OR 'game development'",
        "language": "en",
        "sortBy": "publishedAt",
        "pageSize": 50,
        "domains": _TECH_DOMAINS,   # <-- strong domain filter
        "apiKey": NEWS_API_KEY,
    }

    try:
        resp = _session.get(url, params=params, timeout=15)
    except Exception as e:
        logger.error("Error calling NewsAPI: %s", e)
        return []

    if resp.status_code != 200:
        logger.error("NewsAPI error (%s): %s", resp.status_code, resp.text[:300])
        return []

    payload = resp.json() or {}
    articles = payload.get("articles", [])
    stories = []

    for a in articles:
        title = (a.get("title") or "").strip()
        description = (a.get("description") or a.get("content") or "").strip()
        image_url = (a.get("urlToImage") or "").strip()
        source_url = (a.get("url") or "").strip()

        if not title or not source_url:
            continue

        # extra guard to keep it computer-tech only
        if not _matches_topic(title, description):
            continue

        stories.append({
            "title": title,
            "description": description or "No description available.",
            "image_url": image_url or None,
            "source_url": source_url,
        })

    logger.info("Fetched %d candidate stories from NewsAPI.", len(stories))
    return stories

# -------------------------------
# Generate AI-enhanced summary
# -------------------------------

def generate_summary(text: str) -> str:
    """
    Generate a short, catchy summary (2–3 sentences).
    Falls back to truncated text if AI is unavailable.
    """
    text = (text or "").strip()
    if not text:
        return "No description available."

    prompt = (
        "Summarize this computer/tech news item in 2–3 punchy sentences. "
        "Be clear, engaging, and avoid hypey buzzwords:\n\n"
        f"{text}"
    )

    # New client
    if _openai_client is not None:
        try:
            res = _openai_client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=120,
                temperature=0.6,
            )
            return res.choices[0].message.content.strip()
        except Exception as e:
            logger.warning("OpenAI (new client) failed: %s", e)

    # Legacy client
    if "openai" in globals() and openai is not None:
        try:
            res = openai.ChatCompletion.create(
                model=OPENAI_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=120,
                temperature=0.6,
            )
            return res.choices[0].message.content.strip()
        except Exception as e:
            logger.warning("OpenAI (legacy client) failed: %s", e)

    # Fallback
    return (text[:400] + "…") if len(text) > 400 else text

# ---------------------------------------------
# Update database with fresh, de-duplicated data
# ---------------------------------------------

def update_trending_stories():
    """
    Pulls fresh tech stories and updates DB.
    - Avoids duplicates by checking source_url (better than title).
    - Summarizes with OpenAI if available.
    - Keeps table from growing unbounded (optional trimming).
    """
    stories = fetch_trending_news()
    if not stories:
        logger.info("No stories fetched this cycle.")
        return

    new_count = 0

    for s in stories:
        exists = TrendingStory.query.filter_by(source_url=s["source_url"]).first()
        if exists:
            continue

        summary = generate_summary(s["description"])
        new_story = TrendingStory(
            title=s["title"],
            description=summary,
            image_url=s["image_url"],
            source_url=s["source_url"],
            date_posted=datetime.utcnow(),
        )
        db.session.add(new_story)
        new_count += 1

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.error("DB commit failed: %s", e)
        return

    logger.info("%d new trending stories added.", new_count)

    # (Optional) Trim to last N stories to keep DB lean
    _trim_trending(keep_last=200)

def _trim_trending(keep_last: int = 200):
    """
    Keep only the most recent `keep_last` stories.
    """
    try:
        total = TrendingStory.query.count()
        if total > keep_last:
            cutoff = total - keep_last
            # Oldest first
            old_ids = (
                db.session.query(TrendingStory.id)
                .order_by(TrendingStory.date_posted.asc())
                .limit(cutoff)
                .all()
            )
            old_ids = [i for (i,) in old_ids]
            if old_ids:
                TrendingStory.query.filter(TrendingStory.id.in_(old_ids)).delete(synchronize_session=False)
                db.session.commit()
                logger.info("Trimmed %d old trending stories.", len(old_ids))
    except Exception as e:
        db.session.rollback()
        logger.warning("Trimming failed (ignored): %s", e)
