import json
import threading
import time
from pathlib import Path

from connectors.rss_connector import parse_feed
from connectors.t import search_telegram
from connectors.x import search_x
from connectors.INSTA import search_instagram
from storage import get_alerts, insert_source_item

FEEDS_PATH = Path("config/feeds.json")

def load_feeds():
    if not FEEDS_PATH.exists():
        return []
    return json.loads(FEEDS_PATH.read_text(encoding="utf-8"))

def normalize_alert_row(row):
    return {
        "id": row["id"],
        "name": row["name"],
        "country": row["country"],
        "region": row["region"],
        "keywords": [x.strip() for x in (row["keywords"] or "").split(",") if x.strip()],
        "exclude_keywords": [x.strip() for x in (row["exclude_keywords"] or "").split(",") if x.strip()],
        "languages": [x.strip() for x in (row["languages"] or "").split(",") if x.strip()] or ["All"],
        "sources": [x.strip() for x in (row["sources"] or "").split(",") if x.strip()],
        "window": row["window"],
        "refresh": row["refresh"],
        "createdAt": row["created_at"],
    }

def poll_once():
    feeds = load_feeds()
    alerts = [normalize_alert_row(a) for a in get_alerts()]

    for alert in alerts:
        all_items = []

        if "Websites" in alert.get("sources", []):
            for feed in feeds:
                all_items.extend(parse_feed(feed, alert))

        if "Telegram" in alert.get("sources", []):
            all_items.extend(search_telegram(alert))

        if "X" in alert.get("sources", []):
            all_items.extend(search_x(alert))

        if "Instagram" in alert.get("sources", []):
            all_items.extend(search_instagram(alert))

        for item in all_items:
            insert_source_item(item)

def start_background_poller(interval_seconds=30):
    def loop():
        while True:
            try:
                poll_once()
            except Exception as exc:
                print(f"[ingestion] poll error: {exc}")
            time.sleep(interval_seconds)

    thread = threading.Thread(target=loop, daemon=True)
    thread.start()
    return thread