import os
import requests
from dotenv import load_dotenv

load_dotenv(".dev")
from flask import Flask, jsonify, request, render_template_string, Response
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor
from config import connector_status
from storage import init_db, insert_alert, get_alerts, get_recent_items
from ingestion import start_background_poller
import csv
import io
import random
import uuid

TELEGRAM_BOT_TOKEN = os.getenv("8632040512:AAGrvn2m45_o9mZv-NHFaLlogAgYuNvEn84", "").strip()
TELEGRAM_API_ID = os.getenv("20038314", "").strip()
TELEGRAM_API_HASH = os.getenv("df335901b10654b0cc678b588e607926", "").strip()
TELEGRAM_PHONE = os.getenv("+447938830119", "").strip()

X_BEARER_TOKEN = os.getenv("AAAAAAAAAAAAAAAAAAAAAEhw9QEAAAAAcUTlLHk4OwtHVVNsdfsoNqgbKRo%3DOwoQO4LGrhjwAX20PNXaZjhIMtRz9ELLVCrAJc3p4vi4svvpXg", "").strip()
X_CLIENT_ID = os.getenv("TktmZEpzbzFpMmx3NGYzQW5lUnc6MTpjaQ", "").strip()
X_CLIENT_SECRET = os.getenv("UjQWmoYmT-zWrRPHEpKOql1udgYYIqpGpU5LJP0cs3537fJXFEi6wpg2CcDVSdqNCLojIhKt9", "").strip()

INSTAGRAM_ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN", "").strip()
INSTAGRAM_APP_ID = os.getenv("INSTAGRAM_APP_ID", "").strip()
INSTAGRAM_APP_SECRET = os.getenv("INSTAGRAM_APP_SECRET", "").strip()

TRANSLATION_API_KEY = os.getenv("TRANSLATION_API_KEY", "").strip()
TRANSLATION_PROVIDER = os.getenv("TRANSLATION_PROVIDER", "libretranslate").strip()
TRANSLATION_URL = os.getenv("https://libretranslate.de/translate", "").strip()

app = Flask(__name__)

LIVE_ITEMS = []
DEFAULT_ALERT = None

COUNTRIES = {
    "Syria": {"center": [35.0, 38.5], "regions": ["Damascus", "Aleppo", "Idlib", "Homs", "Latakia", "Raqqa", "Deir ez-Zor", "Daraa"]},
    "Lebanon": {"center": [33.85, 35.85], "regions": ["Beirut", "Bekaa", "South Lebanon", "Mount Lebanon", "North Lebanon", "Nabatieh"]},
    "Jordan": {"center": [31.25, 36.45], "regions": ["Amman", "Irbid", "Zarqa", "Mafraq", "Aqaba", "Karak"]},
    "Iraq": {"center": [33.2, 43.7], "regions": ["Baghdad", "Basra", "Nineveh", "Anbar", "Erbil", "Kirkuk", "Diyala"]},
    "Israel": {"center": [31.0, 35.0], "regions": ["Jerusalem", "Tel Aviv", "Haifa", "Beersheba", "Galilee", "West Bank"]},
    "Palestine": {"center": [31.9, 35.2], "regions": ["Gaza", "North Gaza", "Khan Younis", "Rafah", "Nablus", "Hebron"]},
    "Turkey": {"center": [39.0, 35.0], "regions": ["Istanbul", "Ankara", "Izmir", "Gaziantep", "Hatay", "Adana", "Antalya"]},
    "Egypt": {"center": [26.8, 30.8], "regions": ["Cairo", "Alexandria", "Giza", "North Sinai", "South Sinai", "Aswan", "Luxor"]},
    "Saudi Arabia": {"center": [24.0, 45.0], "regions": ["Riyadh", "Jeddah", "Mecca", "Medina", "Eastern Province", "Tabuk"]},
    "United Arab Emirates": {"center": [24.3, 54.4], "regions": ["Abu Dhabi", "Dubai", "Sharjah", "Ajman", "Ras Al Khaimah", "Fujairah"]},
    "United Kingdom": {"center": [54.5, -2.5], "regions": ["London", "Manchester", "Birmingham", "Glasgow", "Edinburgh", "Cardiff", "Belfast"]},
    "France": {"center": [46.2, 2.2], "regions": ["Paris", "Marseille", "Lyon", "Toulouse", "Lille", "Nice", "Bordeaux"]},
    "Germany": {"center": [51.2, 10.4], "regions": ["Berlin", "Hamburg", "Munich", "Cologne", "Frankfurt", "Stuttgart", "Leipzig"]},
    "Italy": {"center": [42.8, 12.5], "regions": ["Rome", "Milan", "Naples", "Turin", "Palermo", "Bologna", "Venice"]},
    "Spain": {"center": [40.3, -3.7], "regions": ["Madrid", "Barcelona", "Valencia", "Seville", "Bilbao", "Malaga"]},
    "Portugal": {"center": [39.4, -8.2], "regions": ["Lisbon", "Porto", "Braga", "Coimbra", "Faro"]},
    "Netherlands": {"center": [52.2, 5.3], "regions": ["Amsterdam", "Rotterdam", "The Hague", "Utrecht", "Eindhoven"]},
    "Belgium": {"center": [50.8, 4.4], "regions": ["Brussels", "Antwerp", "Ghent", "Liege", "Charleroi"]},
    "Switzerland": {"center": [46.8, 8.2], "regions": ["Zurich", "Geneva", "Basel", "Bern", "Lausanne"]},
    "Austria": {"center": [47.5, 14.5], "regions": ["Vienna", "Graz", "Linz", "Salzburg", "Innsbruck"]},
    "Poland": {"center": [52.0, 19.1], "regions": ["Warsaw", "Krakow", "Gdansk", "Wroclaw", "Poznan", "Lodz"]},
    "Czech Republic": {"center": [49.8, 15.5], "regions": ["Prague", "Brno", "Ostrava", "Plzen", "Olomouc"]},
    "Romania": {"center": [45.9, 24.9], "regions": ["Bucharest", "Cluj-Napoca", "Timisoara", "Iasi", "Constanta"]},
    "Greece": {"center": [39.1, 22.9], "regions": ["Athens", "Thessaloniki", "Patras", "Heraklion", "Larissa"]},
    "Sweden": {"center": [62.0, 15.0], "regions": ["Stockholm", "Gothenburg", "Malmo", "Uppsala", "Vasteras"]},
    "Norway": {"center": [61.0, 8.0], "regions": ["Oslo", "Bergen", "Trondheim", "Stavanger", "Tromso"]},
    "Denmark": {"center": [56.0, 10.0], "regions": ["Copenhagen", "Aarhus", "Odense", "Aalborg", "Esbjerg"]},
    "Finland": {"center": [64.5, 26.0], "regions": ["Helsinki", "Espoo", "Tampere", "Turku", "Oulu"]},
    "Ireland": {"center": [53.3, -8.0], "regions": ["Dublin", "Cork", "Galway", "Limerick", "Waterford"]},
    "Ukraine": {"center": [49.0, 31.0], "regions": ["Kyiv", "Kharkiv", "Lviv", "Odesa", "Dnipro", "Zaporizhzhia"]},
}

USER_SELECTABLE_PLATFORMS = ["Telegram", "Instagram", "X", "Websites"]
LANGUAGES = ["Arabic", "English", "French", "Turkish", "Hebrew", "German", "Spanish", "Italian", "Ukrainian", "Polish"]
TEMPLATES = [
    "Protest monitoring",
    "Demonstration monitoring",
    "Civil unrest",
    "Drone attack monitoring",
    "Armed attack monitoring",
    "Border tensions",
    "Kidnap and hostage indicators",
    "Infrastructure disruption",
    "Airport disruption",
    "Refugee displacement",
    "Attacks on specific assets",
]
MAP_BOUNDS = {"minLat": 24.0, "maxLat": 65.0, "minLng": -12.0, "maxLng": 49.0}

WORKSPACE_PREFERENCES = {
    "table_columns": ["postedAt", "sourcePlatform", "authorName", "country", "region", "summary", "confidenceScore"],
    "hidden_columns": ["geoMethod", "duplicateClusterId"],
    "sort_field": "postedAt",
    "sort_direction": "desc",
    "dense_mode": False,
}

RSS_SOURCES = [
    {
        "name": "Regional Desk",
        "country": "Jordan",
        "region": "Mafraq",
        "language": "English",
        "url": "https://example.com/rss/jordan.xml",
        "entries": [
            {
                "title": "Displacement reports rising near border area",
                "summary": "Reports reference temporary movement of families and checkpoints near the border road.",
                "link": "https://example.com/source/displacement-border",
                "minutes_ago": 9,
                "lat": 32.34,
                "lng": 36.21,
                "severity": "High",
                "confidence": 0.88,
            },
            {
                "title": "Border checkpoint delays reported",
                "summary": "Traffic queues and road checks are being reported at the crossing.",
                "link": "https://example.com/source/checkpoint-delay",
                "minutes_ago": 16,
                "lat": 32.40,
                "lng": 36.28,
                "severity": "Medium",
                "confidence": 0.77,
            },
        ],
    },
    {
        "name": "Metro Bulletin",
        "country": "France",
        "region": "Paris",
        "language": "French",
        "url": "https://example.com/rss/france.xml",
        "entries": [
            {
                "title": "Transport disruption chatter in Paris",
                "summary": "Local reporting mentions transport disruption and possible gathering points in Paris.",
                "link": "https://example.com/source/paris-disruption",
                "minutes_ago": 13,
                "lat": 48.8566,
                "lng": 2.3522,
                "severity": "Medium",
                "confidence": 0.82,
            },
            {
                "title": "Strike notices expand across central districts",
                "summary": "Union messaging and route disruptions are appearing in several city areas.",
                "link": "https://example.com/source/paris-strike",
                "minutes_ago": 21,
                "lat": 48.864,
                "lng": 2.341,
                "severity": "Medium",
                "confidence": 0.74,
            },
        ],
    },
    {
        "name": "Levant Monitor",
        "country": "Syria",
        "region": "Aleppo",
        "language": "Arabic",
        "url": "https://example.com/rss/syria.xml",
        "entries": [
            {
                "title": "Infrastructure disruption reported near strategic route",
                "summary": "Road access and logistics movement are reportedly affected near a key corridor.",
                "link": "https://example.com/source/aleppo-route",
                "minutes_ago": 7,
                "lat": 36.21,
                "lng": 37.16,
                "severity": "High",
                "confidence": 0.84,
            },
            {
                "title": "Airport access road disruption mentioned in local reporting",
                "summary": "Publishing outlets mention congestion and security checks near airport access routes.",
                "link": "https://example.com/source/airport-access",
                "minutes_ago": 18,
                "lat": 36.19,
                "lng": 37.10,
                "severity": "Medium",
                "confidence": 0.72,
            },
        ],
    },
]

SOCIAL_SEED_ITEMS = [
    {
        "title": "Reports of drone activity near strategic route",
        "country": "Syria",
        "region": "Aleppo",
        "sourcePlatform": "Telegram",
        "authorName": "North Watch Channel",
        "authorHandle": "@northwatch",
        "keywords": ["drone", "drone attack"],
        "language": "Arabic",
        "text": "Witness reports mention drone movement and road disruption near a key logistics corridor.",
        "translatedText": "Witness reports mention drone movement and road disruption near a key logistics corridor.",
        "lat": 36.21,
        "lng": 37.16,
        "verification": "Open source",
        "severity": "High",
        "confidence": 0.78,
        "engagement": 1280,
        "sourceUrl": "https://example.com/source/drone-activity",
    },
    {
        "title": "Small protest gathering reported in city center",
        "country": "Lebanon",
        "region": "Beirut",
        "sourcePlatform": "X",
        "authorName": "City Monitor",
        "authorHandle": "@citymonitor",
        "keywords": ["protest", "demonstration"],
        "language": "English",
        "text": "Posts reference a gathering near central roads with banners and traffic slowdown.",
        "translatedText": "Posts reference a gathering near central roads with banners and traffic slowdown.",
        "lat": 33.8938,
        "lng": 35.5018,
        "verification": "Corroborated",
        "severity": "Medium",
        "confidence": 0.84,
        "engagement": 963,
        "sourceUrl": "https://example.com/source/protest-beirut",
    },
    {
        "title": "Public posts mention unrest near coastal district",
        "country": "Syria",
        "region": "Latakia",
        "sourcePlatform": "Instagram",
        "authorName": "Coast Signals",
        "authorHandle": "@coastsignals",
        "keywords": ["unrest", "attack"],
        "language": "Arabic",
        "text": "Several public posts mention tense movement and isolated sounds reported by residents.",
        "translatedText": "Several public posts mention tense movement and isolated sounds reported by residents.",
        "lat": 35.52,
        "lng": 35.79,
        "verification": "Open source",
        "severity": "Low",
        "confidence": 0.55,
        "engagement": 188,
        "sourceUrl": "https://example.com/source/coastal-unrest",
    },
    {
        "title": "Demonstration calls spreading in central London",
        "country": "United Kingdom",
        "region": "London",
        "sourcePlatform": "X",
        "authorName": "UK Street Watch",
        "authorHandle": "@ukstreetwatch",
        "keywords": ["protest", "demonstration"],
        "language": "English",
        "text": "Public posts indicate demonstration planning and road gathering points in central London.",
        "translatedText": "Public posts indicate demonstration planning and road gathering points in central London.",
        "lat": 51.5072,
        "lng": -0.1276,
        "verification": "Open source",
        "severity": "Medium",
        "confidence": 0.79,
        "engagement": 2100,
        "sourceUrl": "https://example.com/source/london-demo",
    },
    {
        "title": "Public video posts mention crowd activity in Berlin",
        "country": "Germany",
        "region": "Berlin",
        "sourcePlatform": "Instagram",
        "authorName": "Berlin Signals",
        "authorHandle": "@berlinsignals",
        "keywords": ["crowd", "protest"],
        "language": "German",
        "text": "Public content suggests crowd buildup and protest signage in central Berlin.",
        "translatedText": "Public content suggests crowd buildup and protest signage in central Berlin.",
        "lat": 52.52,
        "lng": 13.405,
        "verification": "Open source",
        "severity": "Low",
        "confidence": 0.73,
        "engagement": 512,
        "sourceUrl": "https://example.com/source/berlin-crowd",
    },
    {
        "title": "Border tension posts increasing around Warsaw monitoring set",
        "country": "Poland",
        "region": "Warsaw",
        "sourcePlatform": "Telegram",
        "authorName": "Eastern Monitor",
        "authorHandle": "@easternmonitor",
        "keywords": ["border", "tension"],
        "language": "Polish",
        "text": "Public channel posts reference border tension and checkpoint discussion in the monitoring set.",
        "translatedText": "Public channel posts reference border tension and checkpoint discussion in the monitoring set.",
        "lat": 52.2297,
        "lng": 21.0122,
        "verification": "Open source",
        "severity": "High",
        "confidence": 0.81,
        "engagement": 920,
        "sourceUrl": "https://example.com/source/warsaw-border",
    },
]

DEFAULT_QUERY = {
    "query": "protest, drone, unrest, border, disruption",
    "country": "All",
    "region": "All",
    "language": "All",
    "platforms": ["Telegram", "Instagram", "X", "Websites"],
}


def now_utc():
    return datetime.now(timezone.utc)


def iso(dt):
    return dt.isoformat()


def ago(dt):
    seconds = int((now_utc() - dt).total_seconds())
    if seconds < 60:
        return f"{seconds}s ago"
    if seconds < 3600:
        return f"{seconds // 60}m ago"
    return f"{seconds // 3600}h ago"


def next_alert_id():
    return f"alert-{uuid.uuid4().hex[:8]}"


def get_or_create_default_alert():
    alerts = get_alerts()
    if alerts:
        return alerts[0]
    alert = {
        "id": next_alert_id(),
        "name": "Live monitoring request",
        "country": "All",
        "region": "All",
        "keywords": [DEFAULT_QUERY["query"]],
        "exclude_keywords": [],
        "languages": ["All"],
        "sources": list(DEFAULT_QUERY["platforms"]),
        "window": "24h",
        "refresh": "30s",
        "createdAt": now_utc().isoformat(),
    }
    insert_alert(alert)
    return alert


def matches_keywords(text, keywords):
    lowered = text.lower()
    return [keyword for keyword in keywords if keyword and keyword.lower() in lowered]


def build_social_item(seed_item, offset_minutes, keywords, alert_id):
    posted = now_utc() - timedelta(minutes=offset_minutes)
    first_seen = posted + timedelta(minutes=random.randint(1, 4))
    item = dict(seed_item)
    combined = f"{item['title']} {item['text']}"
    matched = matches_keywords(combined, keywords) or item["keywords"]

    item["id"] = str(uuid.uuid4())
    item["alertId"] = alert_id
    item["postedAt"] = iso(posted)
    item["firstSeenAt"] = iso(first_seen)
    item["postedAgo"] = ago(posted)
    item["geoPrecision"] = random.choice(["exact", "inferred", "region"])
    item["geoMethod"] = random.choice([
        "embedded coordinates",
        "place name extraction",
        "linked article location",
        "account region association",
    ])
    item["duplicateClusterId"] = random.choice([None, None, "cluster-a12", "cluster-b07"])
    item["verificationState"] = item.pop("verification")
    item["severityScore"] = round(random.uniform(0.35, 0.98), 2)
    item["confidenceScore"] = item.pop("confidence")
    item["sourceType"] = "social"
    item["sourceDomain"] = item["sourceUrl"].split("/")[2]
    item["authorUrl"] = f"https://example.com/profile/{item['authorHandle'].replace('@', '')}"
    item["hashtags"] = [f"#{kw.replace(' ', '')}" for kw in matched[:2]]
    item["city"] = item["region"]
    item["mediaThumbnail"] = ""
    item["locationLabel"] = f"{item['region']}, {item['country']}"
    item["engagementLabel"] = f"{item['engagement']:,} interactions"
    item["summary"] = item["title"]
    item["keywords"] = matched
    return item


def build_rss_item(source, entry, keywords, alert_id):
    posted = now_utc() - timedelta(minutes=entry["minutes_ago"])
    first_seen = posted + timedelta(minutes=1)
    title = entry["title"]
    summary = entry["summary"]
    combined = f"{title} {summary}"
    matched = matches_keywords(combined, keywords)

    return {
        "id": str(uuid.uuid4()),
        "alertId": alert_id,
        "sourcePlatform": "Websites",
        "sourceType": "web",
        "sourceUrl": entry["link"],
        "sourceDomain": entry["link"].split("/")[2],
        "authorName": source["name"],
        "authorHandle": source["name"].lower().replace(" ", "-"),
        "authorUrl": source["url"],
        "postedAt": iso(posted),
        "firstSeenAt": iso(first_seen),
        "postedAgo": ago(posted),
        "text": summary,
        "translatedText": summary,
        "language": source["language"],
        "keywords": matched,
        "hashtags": [f"#{kw.replace(' ', '')}" for kw in matched[:2]],
        "country": source["country"],
        "region": source["region"],
        "city": source["region"],
        "lat": entry["lat"],
        "lng": entry["lng"],
        "geoPrecision": random.choice(["exact", "inferred"]),
        "geoMethod": random.choice(["article location", "place name extraction", "publisher region association"]),
        "confidenceScore": entry["confidence"],
        "severity": entry["severity"],
        "severityScore": round(random.uniform(0.45, 0.96), 2),
        "duplicateClusterId": random.choice([None, None, "cluster-web-11"]),
        "verificationState": "Publisher",
        "engagement": random.randint(50, 650),
        "engagementLabel": "publisher update",
        "locationLabel": f"{source['region']}, {source['country']}",
        "summary": title,
        "mediaThumbnail": "",
    }


def rss_collector(keywords, country, region, alert_id):
    items = []
    for source in RSS_SOURCES:
        if country != "All" and source["country"] != country:
            continue
        if region != "All" and source["region"] != region:
            continue
        for entry in source["entries"]:
            combined = f"{entry['title']} {entry['summary']}"
            if matches_keywords(combined, keywords):
                items.append(build_rss_item(source, entry, keywords, alert_id))
    return items


def social_collector(platform_name, keywords, country, region, alert_id):
    items = []
    for seed in SOCIAL_SEED_ITEMS:
        if seed["sourcePlatform"] != platform_name:
            continue
        if country != "All" and seed["country"] != country:
            continue
        if region != "All" and seed["region"] != region:
            continue
        combined = f"{seed['title']} {seed['text']}"
        if matches_keywords(combined, keywords):
            items.append(build_social_item(seed, random.randint(2, 18), keywords, alert_id))
    return items


def collect_live_items(query_text="", enabled_platforms=None, country="All", region="All", language="All", alert_id=None):
    platforms = enabled_platforms or USER_SELECTABLE_PLATFORMS
    keywords = [k.strip() for k in query_text.split(",") if k.strip()] if query_text else ["protest"]
    current_alert_id = alert_id or get_or_create_default_alert()["id"]
    items = []

    with ThreadPoolExecutor(max_workers=max(1, len(platforms))) as executor:
        futures = []
        for platform in platforms:
            if platform == "Websites":
                futures.append(executor.submit(rss_collector, keywords, country, region, current_alert_id))
            else:
                futures.append(executor.submit(social_collector, platform, keywords, country, region, current_alert_id))
        for future in futures:
            items.extend(future.result())

    if language != "All":
        items = [i for i in items if i["language"] == language]

    return sorted(items, key=lambda x: x["postedAt"], reverse=True)


def apply_filters(items, country="All", region="All", language="All", severity="All", geo="All", platform="All", query=""):
    filtered = list(items)

    if country != "All":
        filtered = [i for i in filtered if i.get("country") == country]
    if region != "All":
        filtered = [i for i in filtered if i.get("region") == region]
    if language != "All":
        filtered = [i for i in filtered if i.get("language") == language]
    if severity != "All":
        filtered = [i for i in filtered if i.get("severity") == severity]
    if geo != "All":
        filtered = [i for i in filtered if i.get("geoPrecision") == geo]
    if platform != "All":
        filtered = [i for i in filtered if i.get("sourcePlatform") == platform]

    if query:
        terms = [part.strip().lower() for part in query.split(",") if part.strip()]
        if terms:
            filtered = [
                i for i in filtered
                if any(
                    term in " ".join([
                        i.get("summary", ""),
                        i.get("text", ""),
                        i.get("authorName", ""),
                        i.get("country", ""),
                        i.get("region", ""),
                        " ".join(i.get("keywords", [])),
                    ]).lower()
                    for term in terms
                )
            ]

    return filtered


HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>ATLAS</title>
  <style>
    :root { --surface: rgba(255,255,255,.08); --surface-2: rgba(255,255,255,.06); --border: rgba(255,255,255,.14); --text: #f5f5f5; --muted: rgba(245,245,245,.68); --accent: linear-gradient(135deg, #cc6b8e, #f67280, #6c5b7b); --shadow: 0 20px 60px rgba(0,0,0,.35); --r1: 28px; --r2: 22px; }
    * { box-sizing:border-box; }
    html { scroll-behavior:smooth; }
    body { margin:0; font-family:Inter,system-ui,sans-serif; color:var(--text); background:radial-gradient(circle at 20% 20%, rgba(204,107,142,.24), transparent 25%),radial-gradient(circle at 80% 20%, rgba(246,114,128,.18), transparent 30%),radial-gradient(circle at 80% 80%, rgba(108,91,123,.20), transparent 24%),linear-gradient(135deg, #2a1f3d 0%, #1a1326 35%, #130f1d 70%, #0f0c16 100%); min-height:100vh; overflow-x:hidden; }
    .shell { width:min(1460px, calc(100vw - 32px)); margin:0 auto; padding:20px 0 44px; }
    .loader { position:fixed; inset:0; display:grid; place-items:center; z-index:9999; background:rgba(10,8,18,.92); transition:opacity .6s ease, visibility .6s ease; }
    .loader.hidden { opacity:0; visibility:hidden; }
    .loader-inner { width:84px; height:84px; border-radius:999px; border:2px solid rgba(255,255,255,.12); border-top-color:rgba(246,114,128,.95); animation:spin 1s linear infinite; }
    @keyframes spin { to { transform:rotate(360deg); } }
    .nav { position:sticky; top:16px; z-index:50; display:flex; align-items:center; justify-content:space-between; gap:12px; padding:14px 16px; margin-bottom:18px; background:rgba(255,255,255,.08); backdrop-filter:blur(18px); border:1px solid var(--border); border-radius:999px; box-shadow:var(--shadow); }
    .brand { display:flex; align-items:center; gap:12px; font-weight:700; }
    .brand-badge { width:38px; height:38px; border-radius:50%; background:var(--accent); }
    .nav-tabs { display:flex; gap:10px; flex-wrap:wrap; justify-content:center; }
    .tab-btn,.ghost-btn,.primary-btn,.chip,.export-btn { border:1px solid var(--border); color:var(--text); background:rgba(255,255,255,.06); backdrop-filter:blur(16px); border-radius:999px; transition:transform .22s ease, background .22s ease; }
    .tab-btn { padding:10px 14px; cursor:pointer; font-weight:600; opacity:.82; }
    .tab-btn.active { background:linear-gradient(135deg, rgba(204,107,142,.85), rgba(246,114,128,.85), rgba(108,91,123,.85)); opacity:1; }
    .ghost-btn,.primary-btn,.export-btn { padding:12px 16px; font-weight:700; cursor:pointer; }
    .primary-btn { background:var(--accent); border-color:transparent; color:white; }
    .export-btn { text-decoration:none; display:inline-flex; align-items:center; }
    .page { display:none; }
    .page.active { display:block; }
    .glass-card { background:rgba(255,255,255,.08); border:1px solid var(--border); border-radius:var(--r1); backdrop-filter:blur(18px); box-shadow:var(--shadow); }
    .hero { min-height:76vh; display:grid; grid-template-columns:1.2fr .8fr; gap:18px; margin-bottom:20px; }
    .hero-main,.hero-side,.section { padding:22px; }
    .eyebrow { display:inline-flex; gap:8px; padding:8px 12px; border-radius:999px; background:rgba(255,255,255,.08); border:1px solid rgba(255,255,255,.12); color:var(--muted); font-size:13px; text-transform:uppercase; }
    h1 { margin:18px 0 14px; font-size:clamp(3rem, 7vw, 6rem); line-height:.94; letter-spacing:-.05em; max-width:11ch; }
    .lede,.muted { color:var(--muted); }
    .search-bar,.toolbar { display:grid; gap:10px; padding:14px; border-radius:24px; background:rgba(255,255,255,.06); border:1px solid rgba(255,255,255,.1); }
    .search-bar { grid-template-columns:1.3fr .8fr .8fr auto; }
    .toolbar { grid-template-columns:1.2fr .9fr .9fr .8fr .8fr auto; margin-bottom:16px; }
    .input,.select,.table-sort { width:100%; padding:14px 16px; border-radius:18px; border:1px solid rgba(255,255,255,.1); background:rgba(255,255,255,.06); color:var(--text); outline:none; }
    .select option,.table-sort option { color:#111; }
    .metric-grid { display:grid; grid-template-columns:repeat(2, minmax(0,1fr)); gap:14px; }
    .metric,.card { padding:18px; border-radius:22px; background:var(--surface-2); border:1px solid rgba(255,255,255,.08); }
    .metric .value { font-size:2rem; font-weight:800; margin-top:8px; }
    .two-col,.overview-grid,.map-layout { display:grid; gap:18px; grid-template-columns:1fr 1fr; }
    .overview-grid { grid-template-columns:1.05fr .95fr; }
    .section-header,.row { display:flex; align-items:center; justify-content:space-between; gap:12px; }
    .section-title { font-size:1.4rem; font-weight:700; }
    .chip-row,.platform-checks { display:flex; gap:10px; flex-wrap:wrap; }
    .chip { padding:10px 12px; font-size:13px; }
    .platform-check { display:flex; gap:8px; align-items:center; background:rgba(255,255,255,.06); border:1px solid rgba(255,255,255,.08); padding:8px 12px; border-radius:999px; }
    .feed-column,.deck-items,.chart-bars,.table-like { display:grid; gap:12px; }
    .feed-column { max-height:72vh; overflow:auto; }
    .result-card { padding:16px; border-radius:22px; background:var(--surface-2); border:1px solid rgba(255,255,255,.08); cursor:pointer; }
    .platform-badge,.severity-badge { padding:7px 10px; border-radius:999px; font-size:12px; border:1px solid rgba(255,255,255,.12); background:rgba(255,255,255,.08); }
    .marker-map { position:relative; height:72vh; border-radius:28px; overflow:hidden; background:linear-gradient(135deg, #15111f, #22192f, #120f1b); border:1px solid rgba(255,255,255,.08); }
    .map-grid { position:absolute; inset:0; background-image:linear-gradient(rgba(255,255,255,.04) 1px, transparent 1px),linear-gradient(90deg, rgba(255,255,255,.04) 1px, transparent 1px); background-size:48px 48px; }
    .map-label { position:absolute; top:18px; left:18px; padding:10px 14px; border-radius:999px; background:rgba(255,255,255,.08); border:1px solid rgba(255,255,255,.1); z-index:2; }
    .map-marker { position:absolute; width:18px; height:18px; border-radius:50%; background:linear-gradient(135deg, #f67280, #cc6b8e); box-shadow:0 0 0 6px rgba(246,114,128,.14), 0 0 26px rgba(246,114,128,.32); transform:translate(-50%, -50%); cursor:pointer; }
    .deck-board { display:grid; grid-template-columns:repeat(4, minmax(260px,1fr)); gap:16px; }
    .deck-col { min-height:70vh; padding:14px; border-radius:24px; background:var(--surface-2); border:1px solid rgba(255,255,255,.08); }
    .deck-head { display:flex; align-items:center; justify-content:space-between; gap:10px; margin-bottom:12px; }
    .bar-track { width:100%; height:10px; border-radius:999px; background:rgba(255,255,255,.06); overflow:hidden; }
    .bar-fill { height:100%; border-radius:999px; background:var(--accent); }
    .detail-drawer { position:fixed; top:18px; right:18px; width:min(480px, calc(100vw - 28px)); max-height:calc(100vh - 36px); overflow:auto; background:rgba(20,15,30,.92); border:1px solid rgba(255,255,255,.12); border-radius:28px; backdrop-filter:blur(18px); box-shadow:var(--shadow); padding:20px; z-index:80; transform:translateX(110%); transition:transform .3s ease; }
    .detail-drawer.open { transform:translateX(0); }
    .detail-grid { display:grid; gap:10px; grid-template-columns:repeat(2, minmax(0,1fr)); margin:14px 0; }
    .detail-box,.list-row { padding:12px; border-radius:18px; background:rgba(255,255,255,.05); border:1px solid rgba(255,255,255,.08); }
    .list-row { display:grid; grid-template-columns:1fr auto auto; gap:10px; align-items:center; }
    .table-wrap { overflow:auto; border-radius:18px; border:1px solid rgba(255,255,255,.08); }
    table { width:100%; border-collapse:collapse; }
    th,td { padding:12px 14px; border-bottom:1px solid rgba(255,255,255,.08); text-align:left; font-size:14px; }
    th { position:sticky; top:0; background:rgba(28,21,41,.98); }
    .prefs-row { display:flex; gap:10px; flex-wrap:wrap; align-items:center; margin-bottom:12px; }
    .front-results { margin-top:18px; }
  </style>
</head>
<body>
  <div class="loader" id="loader"><div class="loader-inner"></div></div>
  <div class="shell">
    <nav class="nav">
      <div class="brand"><div class="brand-badge"></div><div><div>ATLAS</div><div class="muted" style="font-size:12px">Premium monitoring website</div></div></div>
      <div class="nav-tabs">
        <button class="tab-btn active" data-page="landing">Landing</button>
        <button class="tab-btn" data-page="overview">Overview</button>
        <button class="tab-btn" data-page="map">Map</button>
        <button class="tab-btn" data-page="deck">Deck</button>
        <button class="tab-btn" data-page="reports">Reports</button>
        <button class="tab-btn" data-page="settings">Settings</button>
      </div>
      <div style="display:flex; gap:10px;"><button class="ghost-btn" id="refreshAllBtn">Refresh all</button><a class="export-btn" id="exportCsvLink" href="/api/export.csv" target="_blank">Export CSV</a></div>
    </nav>

    <section class="page active" id="page-landing">
      <div class="hero">
        <div class="hero-main glass-card">
          <div>
            <div class="eyebrow">Live request first · results immediately · alert saved below</div>
            <h1>Search once, monitor live.</h1>
            <p class="lede">Enter a topic, choose region and source types, and the website immediately returns matching website feed items and public social-source matches in one live stream.</p>
          </div>
          <div class="search-bar">
            <input class="input" id="landingKeywords" placeholder="Keywords or exact phrases: protest, drone attack, airport" />
            <select class="select" id="landingCountry"></select>
            <select class="select" id="landingRegion"></select>
            <button class="primary-btn" id="runNowBtn">Run live search</button>
          </div>
          <div class="platform-checks" id="platformChecks"></div>
          <div class="front-results">
            <div class="section-header"><div class="section-title">Immediate results</div><div class="muted" id="frontQueryStatus">No live request yet.</div></div>
            <div id="frontResults" class="feed-column"></div>
          </div>
        </div>
        <div class="hero-side glass-card">
          <div class="metric-grid">
            <div class="metric"><div class="label">Live matches</div><div class="value" id="kpiMatches">0</div></div>
            <div class="metric"><div class="label">High-priority incidents</div><div class="value" id="kpiHigh">0</div></div>
            <div class="metric"><div class="label">New accounts</div><div class="value" id="kpiAccounts">0</div></div>
            <div class="metric"><div class="label">Saved alerts</div><div class="value" id="kpiAlerts">0</div></div>
          </div>
          <div class="card"><div class="section-title">Quick-start templates</div><div class="chip-row" id="templatePills"></div></div>
          <div class="card"><div class="section-title">Saved live requests</div><div id="alertCards" class="table-like" style="margin-top:12px;"></div></div>
        </div>
      </div>
    </section>

    <section class="page" id="page-overview">
      <div class="toolbar">
        <input class="input" id="searchInput" placeholder="Search countries, regions, keywords, accounts, domains" />
        <select class="select" id="countryFilter"></select>
        <select class="select" id="platformFilter"></select>
        <select class="select" id="languageFilter"></select>
        <select class="select" id="severityFilter"><option value="All">All severities</option><option>Low</option><option>Medium</option><option>High</option></select>
        <button class="primary-btn" id="applyFilters">Apply</button>
      </div>
      <div class="overview-grid">
        <div class="section glass-card">
          <div class="section-header"><div class="section-title">Executive overview</div><div class="muted">Unified result stream</div></div>
          <div class="metric-grid" id="overviewMetrics"></div>
          <div class="card" style="margin-top:16px"><div class="section-title">Map preview</div><div class="marker-map" id="overviewMap" style="height:300px; margin-top:12px;"><div class="map-grid"></div><div class="map-label">Current request focus</div></div></div>
        </div>
        <div class="section glass-card">
          <div class="section-header"><div class="section-title">Keyword and region volumes</div><div class="muted">Deduplicated from the main flow</div></div>
          <div class="card"><div class="muted">Top regions</div><div class="chart-bars" id="regionBars"></div></div>
          <div class="card" style="margin-top:14px"><div class="muted">Top keywords</div><div class="chart-bars" id="keywordBars"></div></div>
        </div>
      </div>
    </section>

    <section class="page" id="page-map">
      <div class="toolbar">
        <input class="input" id="mapSearch" placeholder="Search within map incidents" />
        <select class="select" id="mapCountry"></select>
        <select class="select" id="mapPlatform"></select>
        <select class="select" id="mapGeo"><option value="All">All geo precision</option><option>exact</option><option>inferred</option><option>region</option></select>
        <select class="select" id="mapSeverity"><option value="All">All severities</option><option>Low</option><option>Medium</option><option>High</option></select>
        <button class="primary-btn" id="mapRefresh">Update map</button>
      </div>
      <div class="map-layout">
        <div class="section glass-card"><div class="marker-map" id="mainMap"><div class="map-grid"></div><div class="map-label">Europe + Middle East map scope</div></div></div>
        <div class="section glass-card"><div class="section-header"><div class="section-title">Live incident panel</div><div class="muted">Map and feed stay synced</div></div><div id="mapFeed" class="feed-column"></div></div>
      </div>
    </section>

    <section class="page" id="page-deck">
      <div class="toolbar">
        <input class="input" id="deckSearch" placeholder="Search across deck columns" />
        <select class="select" id="deckCountry"></select>
        <select class="select" id="deckMode"><option value="source">By source</option><option value="region">By region</option><option value="severity">By severity</option></select>
        <select class="select" id="deckLanguage"></select>
        <select class="select" id="deckSeverity"><option value="All">All severities</option><option>Low</option><option>Medium</option><option>High</option></select>
        <button class="primary-btn" id="deckRefresh">Refresh deck</button>
      </div>
      <div class="deck-board" id="deckBoard"></div>
    </section>

    <section class="page" id="page-reports">
      <div class="section glass-card">
        <div class="section-header"><div class="section-title">Reports</div><div class="muted">Analyst table and filtered export</div></div>
        <div class="prefs-row">
          <select class="table-sort" id="tableSortField">
            <option value="postedAt">Posted time</option>
            <option value="sourcePlatform">Platform</option>
            <option value="authorName">Source</option>
            <option value="country">Country</option>
            <option value="region">Region</option>
            <option value="confidenceScore">Confidence</option>
          </select>
          <select class="table-sort" id="tableSortDirection">
            <option value="desc">Descending</option>
            <option value="asc">Ascending</option>
          </select>
          <label class="platform-check"><input type="checkbox" id="denseModeToggle" /> Dense mode</label>
          <button class="ghost-btn" id="savePrefsBtn">Save layout</button>
          <span class="muted" id="savePrefsStatus">Layout not saved yet.</span>
        </div>
        <div class="table-wrap">
          <table>
            <thead><tr id="reportTableHeader"></tr></thead>
            <tbody id="reportTableBody"></tbody>
          </table>
        </div>
      </div>
    </section>

    <section class="page" id="page-settings">
      <div class="section glass-card">
        <div class="section-header"><div class="section-title">Saved alert editor</div><div class="muted">Optional refinement after live search</div></div>
        <div class="two-col">
          <div class="card">
            <div class="section-title">Alert details</div>
            <div style="display:grid; gap:10px; margin-top:14px;">
              <input class="input" id="alertName" placeholder="Alert name" />
              <select class="select" id="settingsCountry"></select>
              <select class="select" id="settingsRegion"></select>
              <input class="input" id="alertKeywords" placeholder="Keywords, phrases, hashtags" />
              <input class="input" id="alertExcludeKeywords" placeholder="Exclude keywords" />
              <select class="select" id="alertLanguage"><option>All</option><option>Arabic</option><option>English</option><option>French</option><option>German</option><option>Spanish</option><option>Italian</option></select>
              <select class="select" id="alertWindow"><option>1h</option><option>2h</option><option>12h</option><option selected>24h</option><option>7d</option><option>30d</option></select>
              <div class="platform-checks" id="alertPlatformChecks"></div>
              <div style="display:flex; gap:10px; flex-wrap:wrap;"><button class="primary-btn" id="saveAlertBtn">Save alert</button><span class="muted" id="saveAlertStatus">No alert saved yet.</span></div>
            </div>
          </div>
          <div class="card">
            <div class="section-title">Website monitoring mode</div>
            <p class="muted" style="margin-top:14px; line-height:1.7;">The website-source side follows an RSS-style monitoring model. It checks configured public feed entries for keyword matches, then merges those matches with the selected public social-source connectors into one shared result set.</p>
          </div>
        </div>
      </div>
    </section>
  </div>

  <aside class="detail-drawer" id="detailDrawer"><div class="row"><div class="section-title">Incident detail</div><button class="ghost-btn" id="closeDrawer">Close</button></div><div id="detailContent"></div></aside>

  <script>
    const appState = { data: null, filtered: [], selectedId: null, enabledPlatforms: ['Telegram', 'Instagram', 'X', 'Websites'], preferences: null, currentQuery: 'protest', currentCountry: 'All', currentRegion: 'All', currentLanguage: 'All' };
    const pages = document.querySelectorAll('.page');
    const tabButtons = document.querySelectorAll('.tab-btn');

    function switchPage(name){ pages.forEach(p=>p.classList.toggle('active', p.id===`page-${name}`)); tabButtons.forEach(btn=>btn.classList.toggle('active', btn.dataset.page===name)); }
    tabButtons.forEach(btn=>btn.addEventListener('click',()=>switchPage(btn.dataset.page)));
    document.getElementById('refreshAllBtn').addEventListener('click',()=>refreshData());
    document.getElementById('runNowBtn').addEventListener('click',()=>runLiveSearch());

    const loader=document.getElementById('loader');
    window.addEventListener('load',()=>setTimeout(()=>loader.classList.add('hidden'),600));

    function optionFill(el,items){
      el.innerHTML='';
      items.forEach(item=>{
        const opt=document.createElement('option');
        opt.value=item;
        opt.textContent=item;
        el.appendChild(opt);
      });
    }

    function renderPlatformChecks(containerId,selected){
      const host=document.getElementById(containerId);
      host.innerHTML='';
      appState.data.userSelectablePlatforms.forEach(platform=>{
        const label=document.createElement('label');
        label.className='platform-check';
        label.innerHTML=`<input type="checkbox" value="${platform}" ${selected.includes(platform)?'checked':''}/> ${platform}`;
        host.appendChild(label);
      });
      host.querySelectorAll('input[type="checkbox"]').forEach(box=>box.addEventListener('change',syncPlatformSelectionFromUI));
    }

    function syncPlatformSelectionFromUI(){
      const checked=Array.from(document.querySelectorAll('#platformChecks input[type="checkbox"]:checked')).map(x=>x.value);
      appState.enabledPlatforms=checked.length?checked:['Websites'];
      document.querySelectorAll('#alertPlatformChecks input[type="checkbox"]').forEach(box=>{ box.checked=appState.enabledPlatforms.includes(box.value);});
      refreshData();
    }

    function populateSelectors(data){
      const countries=data.countries;
      ['landingCountry','countryFilter','mapCountry','deckCountry','settingsCountry'].forEach(id=>optionFill(document.getElementById(id),countries));
      optionFill(document.getElementById('landingRegion'), ['All']);
      optionFill(document.getElementById('platformFilter'), ['All', ...data.userSelectablePlatforms]);
      optionFill(document.getElementById('mapPlatform'), ['All', ...data.userSelectablePlatforms]);
      optionFill(document.getElementById('languageFilter'), data.languages);
      optionFill(document.getElementById('deckLanguage'), data.languages);
      updateRegionOptions();
      renderPlatformChecks('platformChecks', appState.enabledPlatforms);
      renderPlatformChecks('alertPlatformChecks', appState.enabledPlatforms);

      const pillHost=document.getElementById('templatePills');
      pillHost.innerHTML='';
      data.templates.forEach(t=>{
        const span=document.createElement('span');
        span.className='chip';
        span.textContent=t;
        span.onclick=()=>{
          document.getElementById('landingKeywords').value=t.replace(' monitoring','');
          runLiveSearch();
        };
        pillHost.appendChild(span);
      });
    }

    function updateRegionOptions(){
      const country=document.getElementById('settingsCountry').value || 'All';
      const landingCountry=document.getElementById('landingCountry').value || 'All';
      const regionsForSettings = country === 'All' ? ['All'] : ['All', ...(appState.data.countryRegions[country]||[])];
      const regionsForLanding = landingCountry === 'All' ? ['All'] : ['All', ...(appState.data.countryRegions[landingCountry]||[])];
      optionFill(document.getElementById('settingsRegion'), regionsForSettings);
      optionFill(document.getElementById('landingRegion'), regionsForLanding);
    }

    function severityRank(severity){ return {Low:1, Medium:2, High:3, Critical:4}[severity]||0; }
    function projectLatLng(lat,lng){ const bounds=appState.data.mapBounds; const left=((lng-bounds.minLng)/(bounds.maxLng-bounds.minLng))*100; const top=100-(((lat-bounds.minLat)/(bounds.maxLat-bounds.minLat))*100); return { left:Math.max(3,Math.min(97,left)), top:Math.max(3,Math.min(97,top)) }; }

    function itemCard(item){
      return `<div class="result-card" data-id="${item.id}">
        <div class="row"><div class="platform-badge">${item.sourcePlatform}</div><div class="muted">${item.postedAgo}</div></div>
        <div style="font-size:1.05rem; font-weight:700; margin:10px 0 6px;">${item.summary}</div>
        <div class="muted" style="line-height:1.55;">${item.text}</div>
        <div class="chip-row" style="margin-top:12px;">${(item.keywords||[]).map(k=>`<span class="chip">${k}</span>`).join('')}</div>
        <div class="row" style="margin-top:12px;"><div class="muted">${item.authorName} · ${item.locationLabel}</div><div class="severity-badge">${item.severity}</div></div>
      </div>`;
    }

    function attachCardHandlers(){ document.querySelectorAll('.result-card').forEach(card=>card.addEventListener('click',()=>openDetail(card.dataset.id))); }

    function openDetail(id){
      const sourceItems = Array.isArray(appState.data?.items) ? appState.data.items : [];
      const item = sourceItems.find(x=>x.id===id) || (appState.filtered || []).find(x=>x.id===id);
      if(!item) return;
      appState.selectedId=id;
      document.getElementById('detailContent').innerHTML=`<div class="muted">${item.sourcePlatform} · ${item.locationLabel}</div><div style="font-size:1.4rem; font-weight:800; margin:8px 0 10px;">${item.summary}</div><a href="${item.sourceUrl}" target="_blank" rel="noopener" style="color:#ffd1dc;">${item.sourceUrl}</a><div class="detail-grid"><div class="detail-box"><strong>Posted</strong><br>${item.postedAt}</div><div class="detail-box"><strong>First seen</strong><br>${item.firstSeenAt}</div><div class="detail-box"><strong>Username</strong><br>${item.authorName}</div><div class="detail-box"><strong>Geo method</strong><br>${item.geoMethod}</div><div class="detail-box"><strong>Confidence</strong><br>${item.confidenceScore}</div><div class="detail-box"><strong>Verification</strong><br>${item.verificationState}</div></div><div class="card" style="padding:14px; margin:10px 0;"><div class="muted">Original text</div><div style="margin-top:8px; line-height:1.6;">${item.text}</div></div>`;
      document.getElementById('detailDrawer').classList.add('open');
    }

    document.getElementById('closeDrawer').addEventListener('click',()=>document.getElementById('detailDrawer').classList.remove('open'));

    function getFirstNonAll(ids){
      for(const id of ids){
        const el=document.getElementById(id);
        if(el && el.value && el.value!=='All') return el.value;
      }
      return 'All';
    }

    function getQueryValue(){
      for(const id of ['searchInput','mapSearch','deckSearch']){
        const el=document.getElementById(id);
        if(el && el.value.trim()) return el.value.trim().toLowerCase();
      }
      return (appState.currentQuery || '').toLowerCase();
    }

    function filterItemsFrontend(items){
      const query = getQueryValue();
      const country = getFirstNonAll(['countryFilter','mapCountry','deckCountry']);
      const platform = getFirstNonAll(['platformFilter','mapPlatform']);
      const language = getFirstNonAll(['languageFilter','deckLanguage']);
      const severity = getFirstNonAll(['severityFilter','mapSeverity','deckSeverity']);
      const geo = getFirstNonAll(['mapGeo']);

      let filtered = Array.isArray(items) ? [...items] : [];

      if (appState.enabledPlatforms && appState.enabledPlatforms.length) {
        filtered = filtered.filter(i => !i.sourcePlatform || appState.enabledPlatforms.includes(i.sourcePlatform));
      }
      if (country !== 'All') filtered = filtered.filter(i => i.country === country);
      if (platform !== 'All') filtered = filtered.filter(i => i.sourcePlatform === platform);
      if (language !== 'All') filtered = filtered.filter(i => i.language === language);
      if (severity !== 'All') filtered = filtered.filter(i => i.severity === severity);
      if (geo !== 'All') filtered = filtered.filter(i => i.geoPrecision === geo);

      if (query) {
        const terms = query.split(',').map(x => x.trim().toLowerCase()).filter(Boolean);
        if (terms.length) {
          filtered = filtered.filter(i => {
            const haystack = [
              i.summary || '',
              i.text || '',
              i.authorName || '',
              i.region || '',
              i.country || '',
              ...(i.keywords || [])
            ].join(' ').toLowerCase();
            return terms.some(term => haystack.includes(term));
          });
        }
      }

      return filtered;
    }

    function groupCounts(items,keyFn){
      const map=new Map();
      items.forEach(i=>{
        const key=keyFn(i);
        map.set(key,(map.get(key)||0)+1);
      });
      return [...map.entries()].map(([name,count])=>({name,count})).sort((a,b)=>b.count-a.count);
    }

    function renderBars(id,counts){
      const root=document.getElementById(id);
      const max=Math.max(...counts.map(c=>c.count),1);
      root.innerHTML=counts.slice(0,6).map(c=>`<div><div class="row"><span>${c.name}</span><span class="muted">${c.count}</span></div><div class="bar-track"><div class="bar-fill" style="width:${(c.count/max)*100}%"></div></div></div>`).join('');
    }

    function renderMiniMap(container,items){
      container.querySelectorAll('.map-marker').forEach(el=>el.remove());
      items.forEach(item=>{
        if (typeof item.lat !== 'number' || typeof item.lng !== 'number') return;
        const marker=document.createElement('div');
        marker.className='map-marker';
        const pos=projectLatLng(item.lat,item.lng);
        marker.style.left=`${pos.left}%`;
        marker.style.top=`${pos.top}%`;
        marker.addEventListener('click',()=>openDetail(item.id));
        container.appendChild(marker);
      });
    }

    function renderLanding(data){
  document.getElementById('alertCards').innerHTML = (data.alerts || []).map(a =>
    `<div class="list-row">
      <div>
        <strong>${a.name}</strong>
        <div class="muted">${a.country} · ${a.region} · ${a.window}</div>
      </div>
      <div class="muted">${(a.sources || []).join(', ')}</div>
      <button class="ghost-btn" onclick="loadAlert('${a.id}')">Use</button>
    </div>`
  ).join('');

  renderImmediateResults(data.items || []);
}

    function renderOverview(items){
      const metrics=[['Total matches',items.length],['High-priority incidents',items.filter(i=>severityRank(i.severity)>=severityRank('High')).length],['New accounts',new Set(items.map(i=>i.authorName)).size],['Saved alerts',(appState.data.alerts||[]).length]];
      document.getElementById('overviewMetrics').innerHTML=metrics.map(([label,value])=>`<div class="metric"><div class="label">${label}</div><div class="value">${value}</div></div>`).join('');
      renderMiniMap(document.getElementById('overviewMap'),items);
      renderBars('regionBars',groupCounts(items,i=>i.region));
      renderBars('keywordBars',groupCounts(items.flatMap(i=>i.keywords || []).map(k=>({name:k})),x=>x.name));
    }

    function renderMap(items){
      const map=document.getElementById('mainMap');
      map.querySelectorAll('.map-marker').forEach(el=>el.remove());
      document.getElementById('mapFeed').innerHTML=items.map(itemCard).join('');
      items.forEach(item=>{
        if (typeof item.lat !== 'number' || typeof item.lng !== 'number') return;
        const marker=document.createElement('div');
        marker.className='map-marker';
        const pos=projectLatLng(item.lat,item.lng);
        marker.style.left=`${pos.left}%`;
        marker.style.top=`${pos.top}%`;
        marker.addEventListener('click',()=>openDetail(item.id));
        map.appendChild(marker);
      });
      attachCardHandlers();
    }

    function renderDeck(items){
      const board=document.getElementById('deckBoard');
      const groups={
        'Telegram':items.filter(i=>i.sourcePlatform==='Telegram'),
        'Instagram':items.filter(i=>i.sourcePlatform==='Instagram'),
        'X':items.filter(i=>i.sourcePlatform==='X'),
        'Websites':items.filter(i=>i.sourcePlatform==='Websites')
      };
      board.innerHTML=Object.entries(groups).map(([name,rows])=>`<div class="deck-col"><div class="deck-head"><strong>${name}</strong><span class="muted">${rows.length}</span></div><div class="deck-items">${rows.map(itemCard).join('')}</div></div>`).join('');
      attachCardHandlers();
    }

    function sortItemsForTable(items,prefs){
      const field=prefs.sort_field||'postedAt';
      const direction=prefs.sort_direction||'desc';
      const sorted=[...items].sort((a,b)=>{
        const va=a[field];
        const vb=b[field];
        if(va===vb) return 0;
        return va>vb?1:-1;
      });
      return direction==='desc'?sorted.reverse():sorted;
    }

    function formatCell(item,field){
      if(field==='confidenceScore') return item.confidenceScore;
      return item[field] ?? '';
    }

    function renderReportTable(items){
      const prefs=appState.preferences || appState.data.preferences;
      const columns=(prefs.table_columns||[]).filter(c=>!(prefs.hidden_columns||[]).includes(c));
      const headerMap={postedAt:'Posted',sourcePlatform:'Platform',authorName:'Source',country:'Country',region:'Region',summary:'Summary',confidenceScore:'Confidence'};
      document.getElementById('reportTableHeader').innerHTML=columns.map(c=>`<th>${headerMap[c]||c}</th>`).join('');
      document.getElementById('reportTableBody').innerHTML=sortItemsForTable(items,prefs).map(item=>`<tr data-id="${item.id}">${columns.map(c=>`<td>${formatCell(item,c)}</td>`).join('')}</tr>`).join('');
      document.querySelectorAll('#reportTableBody tr').forEach(row=>row.addEventListener('click',()=>openDetail(row.dataset.id)));
    }

    function updateKPIs(items){
      document.getElementById('kpiMatches').textContent=String(items.length);
      document.getElementById('kpiHigh').textContent=String(items.filter(i=>severityRank(i.severity)>=severityRank('High')).length);
      document.getElementById('kpiAccounts').textContent=String(new Set(items.map(i=>i.authorName)).size);
      document.getElementById('kpiAlerts').textContent=String((appState.data.alerts||[]).length);
    }

    function updateExportLink(){
      const params=new URLSearchParams();
      appState.enabledPlatforms.forEach(p=>params.append('platform',p));
      if(appState.currentCountry!=='All') params.set('country',appState.currentCountry);
      if(appState.currentRegion!=='All') params.set('region',appState.currentRegion);
      if(appState.currentLanguage!=='All') params.set('language',appState.currentLanguage);
      if(appState.currentQuery) params.set('q',appState.currentQuery);
      document.getElementById('exportCsvLink').href='/api/export.csv?'+params.toString();
    }

    function renderAll(){
      const rawItems = Array.isArray(appState.data.items) ? appState.data.items : [];
      let items = filterItemsFrontend(rawItems);
      if (!items.length && rawItems.length) items = rawItems;
      appState.filtered = items;
      renderLanding({ ...appState.data, items });
      renderOverview(items);
      renderMap(items);
      renderDeck(items);
      renderReportTable(items);
      updateKPIs(items);
      updateExportLink();
    }

    async function loadData(){
  const res = await fetch('/api/dashboard');
  appState.data = await res.json();

  appState.currentQuery = appState.data.defaultQuery?.query || 'protest';
  appState.currentCountry = appState.data.defaultQuery?.country || 'All';
  appState.currentRegion = appState.data.defaultQuery?.region || 'All';
  appState.currentLanguage = appState.data.defaultQuery?.language || 'All';
  appState.enabledPlatforms = appState.data.defaultQuery?.platforms || ['Telegram', 'Instagram', 'X', 'Websites'];

  const localPrefs = localStorage.getItem('workspace_preferences');
  appState.preferences = localPrefs ? JSON.parse(localPrefs) : appState.data.preferences;

  populateSelectors(appState.data);
  hydratePreferencesUI();

  const items = Array.isArray(appState.data.items) ? appState.data.items : [];
  appState.filtered = items;

  document.getElementById('landingKeywords').value = appState.currentQuery;
  document.getElementById('frontQueryStatus').textContent =
    `Live request: ${appState.currentQuery} · ${items.length} results`;

  document.getElementById('landingCountry').value = appState.currentCountry;
  updateRegionOptions();
  document.getElementById('landingRegion').value = appState.currentRegion;

  renderPlatformChecks('platformChecks', appState.enabledPlatforms);
  renderPlatformChecks('alertPlatformChecks', appState.enabledPlatforms);

  renderLanding({ ...appState.data, items });
  updateKPIs(items);
  renderOverview(items);
  renderMap(items);
  renderDeck(items);
  renderReportTable(items);
  updateExportLink();
}
    async function runLiveSearch(){
  appState.currentQuery = (document.getElementById('landingKeywords').value || 'protest').trim();
  appState.currentCountry = document.getElementById('landingCountry').value || 'All';
  appState.currentRegion = document.getElementById('landingRegion').value || 'All';
  appState.currentLanguage = 'All';

  const params = new URLSearchParams();
  params.set('q', appState.currentQuery);
  params.set('country', appState.currentCountry);
  params.set('region', appState.currentRegion);
  params.set('language', appState.currentLanguage);
  appState.enabledPlatforms.forEach(p => params.append('platform', p));

  const res = await fetch('/api/live-data?' + params.toString());
  const payload = await res.json();

  const liveItems = Array.isArray(payload.items) ? payload.items : [];

  appState.data.items = liveItems;
  appState.filtered = liveItems;

  if (payload.alert) {
    appState.data.alerts = [
      payload.alert,
      ...(appState.data.alerts || []).filter(a => a.id !== payload.alert.id)
    ];
  }

  document.getElementById('frontQueryStatus').textContent =
    `Live request: ${appState.currentQuery} · ${liveItems.length} results`;

  document.getElementById('alertName').value =
    payload.alert ? payload.alert.name : 'Live monitoring request';

  document.getElementById('settingsCountry').value = appState.currentCountry;
  updateRegionOptions();
  document.getElementById('settingsRegion').value = appState.currentRegion;
  document.getElementById('alertKeywords').value = appState.currentQuery;

  renderImmediateResults(liveItems);
  updateKPIs(liveItems);

  renderOverview(liveItems);
  renderMap(liveItems);
  renderDeck(liveItems);
  renderReportTable(liveItems);
  updateExportLink();

  renderLanding({ ...appState.data, items: liveItems });
}

function renderImmediateResults(items){
  const safeItems = Array.isArray(items) ? items : [];
  document.getElementById('frontResults').innerHTML = safeItems.length
    ? safeItems.map(itemCard).join('')
    : `<div class="card"><div class="muted">No matching results found for this search.</div></div>`;
  attachCardHandlers();
}

   async function refreshData(){
  const params = new URLSearchParams();
  params.set('q', appState.currentQuery || 'protest');
  params.set('country', appState.currentCountry || 'All');
  params.set('region', appState.currentRegion || 'All');
  params.set('language', appState.currentLanguage || 'All');
  appState.enabledPlatforms.forEach(p => params.append('platform', p));

  const res = await fetch('/api/live-data?' + params.toString());
  const payload = await res.json();

  const liveItems = Array.isArray(payload.items) ? payload.items : [];
  appState.data.items = liveItems;
  appState.filtered = liveItems;

  document.getElementById('frontQueryStatus').textContent =
    `Live request: ${appState.currentQuery} · ${liveItems.length} results`;

  renderLanding({ ...appState.data, items: liveItems });
  updateKPIs(liveItems);
  renderOverview(liveItems);
  renderMap(liveItems);
  renderDeck(liveItems);
  renderReportTable(liveItems);
  updateExportLink();
}

    async function saveAlert(){
      const selectedPlatforms=Array.from(document.querySelectorAll('#alertPlatformChecks input[type="checkbox"]:checked')).map(x=>x.value);
      const payload={
        name:document.getElementById('alertName').value || 'Live monitoring request',
        country:document.getElementById('settingsCountry').value || 'All',
        region:document.getElementById('settingsRegion').value || 'All',
        keywords:(document.getElementById('alertKeywords').value || '').split(',').map(x=>x.trim()).filter(Boolean),
        exclude_keywords:(document.getElementById('alertExcludeKeywords').value || '').split(',').map(x=>x.trim()).filter(Boolean),
        languages:[document.getElementById('alertLanguage').value || 'All'],
        sources:selectedPlatforms.length ? selectedPlatforms : ['Telegram','Instagram','X','Websites'],
        window:document.getElementById('alertWindow').value || '24h',
        refresh:'30s'
      };
      const res=await fetch('/api/alerts',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
      const data=await res.json();
      if(data.ok){
        document.getElementById('saveAlertStatus').textContent=`Saved: ${data.alert.name}`;
        appState.data.alerts=[data.alert, ...(appState.data.alerts || []).filter(a=>a.id!==data.alert.id)];
        renderLanding({ ...appState.data, items: appState.filtered });
        updateKPIs(appState.filtered);
      } else {
        document.getElementById('saveAlertStatus').textContent='Failed to save alert.';
      }
    }

    function loadAlert(alertId){
      const alert=(appState.data.alerts || []).find(a=>a.id===alertId);
      if(!alert) return;
      appState.currentQuery=(alert.keywords || ['protest']).join(', ');
      appState.currentCountry=alert.country || 'All';
      appState.currentRegion=alert.region || 'All';
      appState.enabledPlatforms=alert.sources || ['Telegram','Instagram','X','Websites'];
      document.getElementById('landingKeywords').value=appState.currentQuery;
      document.getElementById('landingCountry').value=appState.currentCountry;
      updateRegionOptions();
      document.getElementById('landingRegion').value=appState.currentRegion;
      renderPlatformChecks('platformChecks', appState.enabledPlatforms);
      renderPlatformChecks('alertPlatformChecks', appState.enabledPlatforms);
      runLiveSearch();
    }

    function hydratePreferencesUI(){
      const prefs=appState.preferences;
      document.getElementById('tableSortField').value=prefs.sort_field || 'postedAt';
      document.getElementById('tableSortDirection').value=prefs.sort_direction || 'desc';
      document.getElementById('denseModeToggle').checked=!!prefs.dense_mode;
    }

    async function savePreferences(){
      const prefs={ ...appState.preferences, sort_field:document.getElementById('tableSortField').value, sort_direction:document.getElementById('tableSortDirection').value, dense_mode:document.getElementById('denseModeToggle').checked };
      appState.preferences=prefs;
      localStorage.setItem('workspace_preferences', JSON.stringify(prefs));
      const res=await fetch('/api/preferences',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(prefs)});
      const data=await res.json();
      document.getElementById('savePrefsStatus').textContent=data.ok ? 'Layout saved.' : 'Failed to save layout.';
      renderReportTable(appState.filtered);
    }

    document.getElementById('landingCountry').addEventListener('change', updateRegionOptions);
    document.getElementById('settingsCountry').addEventListener('change', updateRegionOptions);
    document.getElementById('saveAlertBtn').addEventListener('click', saveAlert);
    document.getElementById('savePrefsBtn').addEventListener('click', savePreferences);
    document.getElementById('tableSortField').addEventListener('change', ()=>renderReportTable(appState.filtered));
    document.getElementById('tableSortDirection').addEventListener('change', ()=>renderReportTable(appState.filtered));
    ['applyFilters','mapRefresh','deckRefresh'].forEach(id=>document.getElementById(id)?.addEventListener('click', renderAll));

    setInterval(refreshData, 30000);
    loadData();
  </script>
</body>
</html>
"""
def normalize_text(value):
    return (value or "").strip()

def build_result_item(
    alert_id,
    source_platform,
    source_url,
    author_name,
    author_handle,
    posted_at,
    text,
    language="Unknown",
    country="All",
    region="All",
    city="",
    lat=None,
    lng=None,
    keywords=None,
    verification_state="Open source",
    severity="Medium",
    confidence_score=0.75,
    source_type="social",
    geo_precision="unknown",
    geo_method="unavailable",
):
    now = now_utc()
    posted_dt = posted_at if isinstance(posted_at, datetime) else now

    return {
        "id": str(uuid.uuid4()),
        "alertId": alert_id,
        "sourcePlatform": source_platform,
        "sourceType": source_type,
        "sourceUrl": source_url or "",
        "sourceDomain": source_url.split("/")[2] if source_url and "://" in source_url else "",
        "authorName": author_name or "Unknown source",
        "authorHandle": author_handle or "",
        "authorUrl": "",
        "postedAt": iso(posted_dt),
        "firstSeenAt": iso(now),
        "postedAgo": ago(posted_dt),
        "text": text or "",
        "translatedText": text or "",
        "language": language or "Unknown",
        "keywords": keywords or [],
        "hashtags": [f"#{k.replace(' ', '')}" for k in (keywords or [])[:2]],
        "country": country or "All",
        "region": region or "All",
        "city": city or region or "",
        "lat": lat,
        "lng": lng,
        "geoPrecision": geo_precision,
        "geoMethod": geo_method,
        "confidenceScore": confidence_score,
        "severity": severity,
        "severityScore": round(min(max(confidence_score, 0.1), 0.99), 2),
        "duplicateClusterId": None,
        "verificationState": verification_state,
        "engagement": 0,
        "engagementLabel": "",
        "locationLabel": f"{region}, {country}" if region and country and region != "All" and country != "All" else (country or "Unknown"),
        "summary": (text or "Matched post")[:120],
        "mediaThumbnail": "",
    }

def search_telegram_public(query, country, region, alert_id):
    if not TELEGRAM_BOT_TOKEN:
        print("Telegram token missing")
        return []

    keywords = [k.strip() for k in query.split(",") if k.strip()]
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"

    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        payload = response.json()
        print("Telegram raw updates:", len(payload.get("result", [])))
    except Exception as exc:
        print("Telegram fetch error:", exc)
        return []

    items = []
    for update in payload.get("result", []):
        message = update.get("message") or update.get("channel_post") or {}
        text = (message.get("text") or message.get("caption") or "").strip()
        if not text:
            continue

        matched = matches_keywords(text, keywords)
        if not matched:
            continue

        chat = message.get("chat", {})
        author_name = chat.get("title") or chat.get("username") or "Telegram source"
        author_handle = f"@{chat.get('username')}" if chat.get("username") else ""
        posted_dt = datetime.fromtimestamp(message.get("date", int(now_utc().timestamp())), tz=timezone.utc)

        items.append({
            "id": str(uuid.uuid4()),
            "alertId": alert_id,
            "sourcePlatform": "Telegram",
            "sourceType": "social",
            "sourceUrl": "",
            "sourceDomain": "telegram",
            "authorName": author_name,
            "authorHandle": author_handle,
            "authorUrl": "",
            "postedAt": iso(posted_dt),
            "firstSeenAt": iso(now_utc()),
            "postedAgo": ago(posted_dt),
            "text": text,
            "translatedText": text,
            "language": "Unknown",
            "keywords": matched,
            "hashtags": [f"#{k.replace(' ', '')}" for k in matched[:2]],
            "country": country,
            "region": region,
            "city": region if region != "All" else "",
            "lat": None,
            "lng": None,
            "geoPrecision": "unknown",
            "geoMethod": "unavailable",
            "confidenceScore": 0.8,
            "severity": "Medium",
            "severityScore": 0.8,
            "duplicateClusterId": None,
            "verificationState": "Open source",
            "engagement": 0,
            "engagementLabel": "",
            "locationLabel": f"{region}, {country}" if region != "All" and country != "All" else country,
            "summary": text[:120],
            "mediaThumbnail": "",
        })

    print("Telegram matched items:", len(items))
    return items

def search_x_public(query, country, region, alert_id):
    print("X connector not implemented yet")
    return []

def search_instagram_public(query, country, region, alert_id):
    print("Instagram connector not implemented yet")
    return []
    return []

def search_public_sources(query, country="All", region="All", platforms=None, alert_id=None):
    selected_platforms = platforms or USER_SELECTABLE_PLATFORMS
    current_alert_id = alert_id or get_or_create_default_alert()["id"]
    items = []

    print("SEARCH")
    print("query:", query)
    print("country:", country)
    print("region:", region)
    print("platforms:", selected_platforms)

    if "Telegram" in selected_platforms:
        telegram_items = search_telegram_public(query, country, region, current_alert_id)
        print("Telegram:", len(telegram_items))
        items.extend(telegram_items)

    if "X" in selected_platforms:
        x_items = search_x_public(query, country, region, current_alert_id)
        print("X:", len(x_items))
        items.extend(x_items)

    if "Instagram" in selected_platforms:
        instagram_items = search_instagram_public(query, country, region, current_alert_id)
        print("Instagram:", len(instagram_items))
        items.extend(instagram_items)

    # if "Websites" in selected_platforms:
    #     web_items = search_web_sources(query, country, region, current_alert_id)
    #     print("Websites:", len(web_items))
    #     items.extend(web_items)

    print("Total:", len(items))
    return sorted(items, key=lambda x: x["postedAt"], reverse=True)




def dashboard_payload():
    global DEFAULT_ALERT

    if DEFAULT_ALERT is None:
        DEFAULT_ALERT = get_or_create_default_alert()

    return {
        "countries": ["All", *list(COUNTRIES.keys())],
        "countryRegions": {country: meta["regions"] for country, meta in COUNTRIES.items()},
        "languages": ["All", *LANGUAGES],
        "templates": TEMPLATES,
        "alerts": get_alerts(),
        "items": [],
        "userSelectablePlatforms": USER_SELECTABLE_PLATFORMS,
        "mapBounds": MAP_BOUNDS,
        "preferences": WORKSPACE_PREFERENCES,
        "defaultQuery": DEFAULT_QUERY,
        "connectorStatus": connector_status(),
    }


@app.route("/")
def index():
    return render_template_string(HTML)


@app.route("/api/dashboard")
def api_dashboard():
    return jsonify(dashboard_payload())


@app.route("/api/live-data")
def api_live_data():
    requested_platforms = request.args.getlist("platform") or list(DEFAULT_QUERY["platforms"])
    country = request.args.get("country", "All")
    region = request.args.get("region", "All")
    language = request.args.get("language", "All")
    severity = request.args.get("severity", "All")
    geo = request.args.get("geo", "All")
    source_platform = request.args.get("sourcePlatform", "All")
    q = request.args.get("q", DEFAULT_QUERY["query"]).strip()

    live_alert = {
        "id": next_alert_id(),
        "name": f"Live: {q or 'monitoring request'}",
        "country": country,
        "region": region,
        "keywords": [k.strip() for k in q.split(",") if k.strip()],
        "exclude_keywords": [],
        "languages": [language],
        "sources": requested_platforms,
        "window": "24h",
        "refresh": "30s",
        "createdAt": now_utc().isoformat(),
    }

    print("LIVE SEARCH REQUEST")
    print("q:", q)
    print("country:", country)
    print("region:", region)
    print("requested_platforms:", requested_platforms)

    items = search_public_sources(
        query=q,
        country=country,
        region=region,
        platforms=requested_platforms,
        alert_id=live_alert["id"],
    )

    items = apply_filters(
        items,
        country=country,
        region=region,
        language=language,
        severity=severity,
        geo=geo,
        platform=source_platform,
        query=q,
    )

    global LIVE_ITEMS
    LIVE_ITEMS = items

    return jsonify({
        "items": items,
        "alert": live_alert
    })

@app.route("/api/alerts", methods=["GET", "POST"])
def api_alerts():
    if request.method == "GET":
        return jsonify({"alerts": get_alerts()})

    payload = request.get_json(silent=True) or {}
    alert = {
        "id": next_alert_id(),
        "name": payload.get("name", "Saved monitoring alert"),
        "country": payload.get("country", "All"),
        "region": payload.get("region", "All"),
        "keywords": payload.get("keywords", []),
        "exclude_keywords": payload.get("exclude_keywords", []),
        "languages": payload.get("languages", ["All"]),
        "sources": payload.get("sources", list(USER_SELECTABLE_PLATFORMS)),
        "window": payload.get("window", "24h"),
        "refresh": payload.get("refresh", "30s"),
        "createdAt": now_utc().isoformat(),
    }
    insert_alert(alert)
    return jsonify({"ok": True, "alert": alert})


@app.route("/api/preferences", methods=["POST"])
def save_preferences():
    payload = request.get_json(silent=True) or {}
    WORKSPACE_PREFERENCES.update(payload)
    return jsonify({"ok": True, "preferences": WORKSPACE_PREFERENCES})


@app.route("/api/export.csv")
def export_csv_file():
    requested_platforms = request.args.getlist("platform") or list(DEFAULT_QUERY["platforms"])
    country = request.args.get("country", "All")
    region = request.args.get("region", "All")
    language = request.args.get("language", "All")
    severity = request.args.get("severity", "All")
    geo = request.args.get("geo", "All")
    source_platform = request.args.get("sourcePlatform", "All")
    q = request.args.get("q", DEFAULT_QUERY["query"]).strip()

    items = collect_live_items(q, requested_platforms, country, region, language, get_or_create_default_alert()["id"])
    items = apply_filters(items, country=country, region=region, language=language, severity=severity, geo=geo, platform=source_platform, query=q)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "id", "alertId", "sourcePlatform", "sourceUrl", "sourceDomain", "authorName",
        "authorHandle", "postedAt", "firstSeenAt", "keywords", "text", "translatedText",
        "language", "country", "region", "city", "lat", "lng", "geoPrecision",
        "geoMethod", "confidenceScore", "severity", "severityScore", "verificationState"
    ])

    for item in items:
        writer.writerow([
            item["id"], item["alertId"], item["sourcePlatform"], item["sourceUrl"], item["sourceDomain"],
            item["authorName"], item["authorHandle"], item["postedAt"], item["firstSeenAt"],
            ", ".join(item["keywords"]), item["text"], item["translatedText"], item["language"],
            item["country"], item["region"], item["city"], item["lat"], item["lng"],
            item["geoPrecision"], item["geoMethod"], item["confidenceScore"], item["severity"],
            item["severityScore"], item["verificationState"]
        ])

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=signal_atlas_export.csv"},
    )


if __name__ == "__main__":
    init_db()
    DEFAULT_ALERT = get_or_create_default_alert()
    LIVE_ITEMS = collect_live_items(
        DEFAULT_QUERY["query"],
        DEFAULT_QUERY["platforms"],
        DEFAULT_QUERY["country"],
        DEFAULT_QUERY["region"],
        DEFAULT_QUERY["language"],
        DEFAULT_ALERT["id"],
    )
    start_background_poller(interval_seconds=30)
    app.run(debug=True, host="127.0.0.1", port=5000)