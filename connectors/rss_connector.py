import uuid
import calendar
from datetime import datetime, timezone
from urllib.parse import urlparse
import feedparser
import requests

from connectors.translation import translate_text

KEYWORD_SEVERITY_HINTS = {
    "attack": "High",
    "drone": "High",
    "drone attack": "High",
    "protest": "Medium",
    "demonstration": "Medium",
    "strike": "Medium",
    "roadblock": "Medium",
    "displacement": "High",
}

def now_iso():
    return datetime.now(timezone.utc).isoformat()

def entry_datetime(entry):
    parsed_time = entry.get("published_parsed") or entry.get("updated_parsed")
    if parsed_time:
        return datetime.fromtimestamp(calendar.timegm(parsed_time), tz=timezone.utc).isoformat()
    return now_iso()

def detect_severity(matched_keywords):
    for keyword in matched_keywords:
        if keyword.lower() in KEYWORD_SEVERITY_HINTS:
            return KEYWORD_SEVERITY_HINTS[keyword.lower()]
    return "Low"

def find_matches(text, keywords):
    lowered = text.lower()
    return [kw for kw in keywords if kw.lower() in lowered]

def fetch_feed(url):
    response = requests.get(
        url,
        headers={"User-Agent": "Mozilla/5.0 (compatible; ATLAS/1.0; +https://localhost)"},
        timeout=15,
    )
    response.raise_for_status()
    return feedparser.parse(response.content)

def parse_feed(feed_config, alert):
    parsed = fetch_feed(feed_config["url"])
    items = []

    keywords = alert.get("keywords", [])
    country = alert.get("country", "All")
    region = alert.get("region", "All")
    language_pref = set(alert.get("languages", ["All"]))

    for entry in parsed.entries:
        title = entry.get("title", "")
        summary = entry.get("summary", "")
        link = entry.get("link", "")
        combined = f"{title} {summary}"

        matched = find_matches(combined, keywords)
        if not matched:
            continue

        item_country = feed_config.get("country", "All")
        item_region = feed_config.get("region", "All")
        item_language = feed_config.get("language", "Unknown")

        if country != "All" and item_country != country and item_country != "All":
            continue
        if region != "All" and item_region != region and item_region != "All":
            continue
        if "All" not in language_pref and item_language not in language_pref:
            continue

        domain = urlparse(link).netloc or urlparse(feed_config["url"]).netloc
        translated_summary = translate_text(summary, source="auto", target="en")

        items.append({
            "id": str(uuid.uuid4()),
            "alertId": alert["id"],
            "sourcePlatform": "Websites",
            "sourceType": "web",
            "sourceUrl": link,
            "sourceDomain": domain,
            "authorName": feed_config.get("name", domain),
            "authorHandle": feed_config.get("name", domain).lower().replace(" ", "-"),
            "authorUrl": feed_config["url"],
            "postedAt": entry_datetime(entry),
            "firstSeenAt": now_iso(),
            "text": summary,
            "translatedText": translated_summary,
            "language": item_language,
            "keywords": matched,
            "hashtags": [f"#{k.replace(' ', '')}" for k in matched[:2]],
            "country": item_country,
            "region": item_region,
            "city": feed_config.get("city", item_region),
            "lat": feed_config.get("lat"),
            "lng": feed_config.get("lng"),
            "geoPrecision": feed_config.get("geoPrecision", "region"),
            "geoMethod": feed_config.get("geoMethod", "feed metadata"),
            "confidenceScore": float(feed_config.get("confidenceScore", 0.75)),
            "severity": detect_severity(matched),
            "severityScore": float(feed_config.get("severityScore", 0.7)),
            "duplicateClusterId": None,
            "verificationState": feed_config.get("verificationState", "Publisher"),
            "engagement": 0,
            "summary": title or "Untitled feed match",
        })

    return items