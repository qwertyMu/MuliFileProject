from flask import Flask, jsonify, request, render_template_string, Response
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor
import random
import uuid
import csv
import io

app = Flask(__name__)

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

ALL_SOURCES = ["Telegram", "Instagram", "X", "News", "Registry", "Forum"]
USER_SELECTABLE_PLATFORMS = ["Telegram", "Instagram", "X", "News"]
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

BASE_ITEMS = [
    {"title": "Reports of drone activity near strategic route", "country": "Syria", "region": "Aleppo", "sourcePlatform": "Telegram", "authorName": "North Watch Channel", "authorHandle": "@northwatch", "keywords": ["drone", "drone attack"], "language": "Arabic", "text": "Witness reports mention drone movement and road disruption near a key logistics corridor.", "translatedText": "Witness reports mention drone movement and road disruption near a key logistics corridor.", "lat": 36.21, "lng": 37.16, "verification": "Open source", "severity": "High", "confidence": 0.78, "engagement": 1280, "sourceUrl": "https://example.com/source/drone-activity"},
    {"title": "Small protest gathering reported in city center", "country": "Lebanon", "region": "Beirut", "sourcePlatform": "X", "authorName": "City Monitor", "authorHandle": "@citymonitor", "keywords": ["protest", "demonstration"], "language": "English", "text": "Posts reference a gathering near central roads with banners and traffic slowdown.", "translatedText": "Posts reference a gathering near central roads with banners and traffic slowdown.", "lat": 33.8938, "lng": 35.5018, "verification": "Corroborated", "severity": "Medium", "confidence": 0.84, "engagement": 963, "sourceUrl": "https://example.com/source/protest-beirut"},
    {"title": "Displacement reports rising near border area", "country": "Jordan", "region": "Mafraq", "sourcePlatform": "News", "authorName": "Regional Desk", "authorHandle": "regional-desk", "keywords": ["displacement", "border"], "language": "English", "text": "Web reports reference temporary movement of families and checkpoints near the border road.", "translatedText": "Web reports reference temporary movement of families and checkpoints near the border road.", "lat": 32.34, "lng": 36.21, "verification": "Priority source", "severity": "High", "confidence": 0.88, "engagement": 411, "sourceUrl": "https://example.com/source/displacement-border"},
    {"title": "Infrastructure disruption at airport access road", "country": "Iraq", "region": "Baghdad", "sourcePlatform": "Forum", "authorName": "Baghdad Ops Feed", "authorHandle": "@baghdadops", "keywords": ["airport", "roadblock"], "language": "Arabic", "text": "Users mention a blockage affecting vehicles around the airport approach road.", "translatedText": "Users mention a blockage affecting vehicles around the airport approach road.", "lat": 33.2625, "lng": 44.2346, "verification": "Unverified", "severity": "Medium", "confidence": 0.62, "engagement": 265, "sourceUrl": "https://example.com/source/airport-road"},
    {"title": "Public posts mention unrest near coastal district", "country": "Syria", "region": "Latakia", "sourcePlatform": "Instagram", "authorName": "Coast Signals", "authorHandle": "@coastsignals", "keywords": ["unrest", "attack"], "language": "Arabic", "text": "Several public posts mention tense movement and isolated sounds reported by residents.", "translatedText": "Several public posts mention tense movement and isolated sounds reported by residents.", "lat": 35.52, "lng": 35.79, "verification": "Open source", "severity": "Low", "confidence": 0.55, "engagement": 188, "sourceUrl": "https://example.com/source/coastal-unrest"},
    {"title": "Demonstration calls spreading in central London", "country": "United Kingdom", "region": "London", "sourcePlatform": "X", "authorName": "UK Street Watch", "authorHandle": "@ukstreetwatch", "keywords": ["protest", "demonstration"], "language": "English", "text": "Public posts indicate demonstration planning and road gathering points in central London.", "translatedText": "Public posts indicate demonstration planning and road gathering points in central London.", "lat": 51.5072, "lng": -0.1276, "verification": "Open source", "severity": "Medium", "confidence": 0.79, "engagement": 2100, "sourceUrl": "https://example.com/source/london-demo"},
    {"title": "Transport disruption chatter in Paris", "country": "France", "region": "Paris", "sourcePlatform": "News", "authorName": "Metro Bulletin", "authorHandle": "metro-bulletin", "keywords": ["strike", "roadblock"], "language": "French", "text": "Local reporting mentions transport disruption and possible gathering points in Paris.", "translatedText": "Local reporting mentions transport disruption and possible gathering points in Paris.", "lat": 48.8566, "lng": 2.3522, "verification": "Publisher", "severity": "Medium", "confidence": 0.82, "engagement": 640, "sourceUrl": "https://example.com/source/paris-disruption"},
    {"title": "Public video posts mention crowd activity in Berlin", "country": "Germany", "region": "Berlin", "sourcePlatform": "Instagram", "authorName": "Berlin Signals", "authorHandle": "@berlinsignals", "keywords": ["crowd", "protest"], "language": "German", "text": "Public content suggests crowd buildup and protest signage in central Berlin.", "translatedText": "Public content suggests crowd buildup and protest signage in central Berlin.", "lat": 52.52, "lng": 13.405, "verification": "Open source", "severity": "Low", "confidence": 0.73, "engagement": 512, "sourceUrl": "https://example.com/source/berlin-crowd"},
    {"title": "Border tension posts increasing around Warsaw monitoring set", "country": "Poland", "region": "Warsaw", "sourcePlatform": "Telegram", "authorName": "Eastern Monitor", "authorHandle": "@easternmonitor", "keywords": ["border", "tension"], "language": "Polish", "text": "Public channel posts reference border tension and checkpoint discussion in the monitoring set.", "translatedText": "Public channel posts reference border tension and checkpoint discussion in the monitoring set.", "lat": 52.2297, "lng": 21.0122, "verification": "Open source", "severity": "High", "confidence": 0.81, "engagement": 920, "sourceUrl": "https://example.com/source/warsaw-border"},
]

ALERTS = [
    {"id": "alert-syria-drone", "name": "Syria drone and infrastructure watch", "country": "Syria", "region": "Aleppo", "keywords": ["drone", "drone attack", "airport", "roadblock"], "sources": ["Telegram", "X", "News"], "window": "24h", "refresh": "30s"},
    {"id": "alert-lebanon-protest", "name": "Lebanon protest watch", "country": "Lebanon", "region": "Beirut", "keywords": ["protest", "demonstration", "strike"], "sources": ["Instagram", "X", "Telegram", "News"], "window": "7d", "refresh": "30s"},
]

MAP_BOUNDS = {
    "minLat": 24.0,
    "maxLat": 65.0,
    "minLng": -12.0,
    "maxLng": 49.0,
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

def build_item(seed_item, offset_minutes):
    posted = now_utc() - timedelta(minutes=offset_minutes)
    first_seen = posted + timedelta(minutes=random.randint(1, 4))
    item = dict(seed_item)
    item["id"] = str(uuid.uuid4())
    item["alertId"] = random.choice(ALERTS)["id"]
    item["postedAt"] = iso(posted)
    item["firstSeenAt"] = iso(first_seen)
    item["postedAgo"] = ago(posted)
    item["geoPrecision"] = random.choice(["exact", "inferred", "region"])
    item["geoMethod"] = random.choice(["embedded coordinates", "place name extraction", "linked article location", "account region association"])
    item["duplicateClusterId"] = random.choice([None, None, "cluster-a12", "cluster-b07"])
    item["verificationState"] = item.pop("verification")
    item["severityScore"] = round(random.uniform(0.35, 0.98), 2)
    item["confidenceScore"] = item.pop("confidence")
    item["sourceType"] = "social" if item["sourcePlatform"] in {"Telegram", "Instagram", "X", "Forum"} else "web"
    item["sourceDomain"] = item["sourceUrl"].split("/")[2]
    item["authorUrl"] = f"https://example.com/profile/{item['authorHandle'].replace('@', '')}"
    item["hashtags"] = [f"#{kw.replace(' ', '')}" for kw in item["keywords"][:2]]
    item["city"] = item["region"]
    item["mediaThumbnail"] = ""
    item["locationLabel"] = f"{item['region']}, {item['country']}"
    item["engagementLabel"] = f"{item['engagement']:,} interactions"
    item["summary"] = item["title"]
    return item

def collect_from_platform(platform_name):
    # Safe stub for approved public/licensed connectors.
    # Replace with official APIs or licensed feeds later.
    matching = [seed for seed in BASE_ITEMS if seed["sourcePlatform"] == platform_name]
    return [build_item(seed, random.randint(2, 18)) for seed in matching]

def collect_live_items(enabled_platforms=None):
    enabled = enabled_platforms or USER_SELECTABLE_PLATFORMS
    valid = [p for p in enabled if p in USER_SELECTABLE_PLATFORMS]
    items = []
    with ThreadPoolExecutor(max_workers=max(1, len(valid))) as executor:
        futures = [executor.submit(collect_from_platform, platform) for platform in valid]
        for future in futures:
            items.extend(future.result())
    forum_items = [build_item(seed, random.randint(4, 20)) for seed in BASE_ITEMS if seed["sourcePlatform"] == "Forum"]
    items.extend(forum_items)
    return items

LIVE_ITEMS = collect_live_items(["Telegram", "Instagram", "X", "News"])

HTML = r'''
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Signal Atlas</title>
  <style>
    :root {
      --surface: rgba(255,255,255,.08);
      --surface-2: rgba(255,255,255,.06);
      --border: rgba(255,255,255,.14);
      --text: #f5f5f5;
      --muted: rgba(245,245,245,.68);
      --accent: linear-gradient(135deg, #cc6b8e, #f67280, #6c5b7b);
      --shadow: 0 20px 60px rgba(0,0,0,.35);
      --r1: 28px;
      --r2: 22px;
      --r3: 18px;
    }
    * { box-sizing: border-box; }
    html { scroll-behavior: smooth; }
    body {
      margin: 0;
      font-family: Inter, system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
      color: var(--text);
      background:
        radial-gradient(circle at 20% 20%, rgba(204,107,142,.24), transparent 25%),
        radial-gradient(circle at 80% 20%, rgba(246,114,128,.18), transparent 30%),
        radial-gradient(circle at 80% 80%, rgba(108,91,123,.20), transparent 24%),
        linear-gradient(135deg, #2a1f3d 0%, #1a1326 35%, #130f1d 70%, #0f0c16 100%);
      min-height: 100vh;
      overflow-x: hidden;
    }
    body::before {
      content: "";
      position: fixed;
      inset: -20%;
      background: linear-gradient(120deg, rgba(204,107,142,.18), rgba(246,114,128,.08), rgba(108,91,123,.16), rgba(42,31,61,.18));
      filter: blur(60px);
      animation: drift 16s ease-in-out infinite alternate;
      z-index: -2;
    }
    @keyframes drift {
      from { transform: translate3d(-2%, -1%, 0) scale(1); }
      to { transform: translate3d(2%, 2%, 0) scale(1.08); }
    }
    .loader {
      position: fixed; inset: 0; display: grid; place-items: center; z-index: 9999;
      background: rgba(10,8,18,.92); transition: opacity .6s ease, visibility .6s ease;
    }
    .loader.hidden { opacity: 0; visibility: hidden; }
    .loader-inner {
      width: 84px; height: 84px; border-radius: 999px; border: 2px solid rgba(255,255,255,.12);
      border-top-color: rgba(246,114,128,.95); animation: spin 1s linear infinite;
      box-shadow: 0 0 80px rgba(246,114,128,.25);
    }
    @keyframes spin { to { transform: rotate(360deg); } }
    .cursor-glow {
      position: fixed; width: 280px; height: 280px; pointer-events: none; border-radius: 50%;
      background: radial-gradient(circle, rgba(246,114,128,.18), rgba(246,114,128,.06), transparent 70%);
      transform: translate(-50%, -50%); z-index: -1; mix-blend-mode: screen; filter: blur(24px);
    }
    .shell { width: min(1460px, calc(100vw - 32px)); margin: 0 auto; padding: 20px 0 44px; }
    .nav {
      position: sticky; top: 16px; z-index: 50; display: flex; align-items: center; justify-content: space-between;
      gap: 12px; padding: 14px 16px; margin-bottom: 18px; background: rgba(255,255,255,.08); backdrop-filter: blur(18px);
      border: 1px solid var(--border); border-radius: 999px; box-shadow: var(--shadow);
    }
    .brand { display:flex; align-items:center; gap:12px; font-weight:700; letter-spacing:.02em; }
    .brand-badge { width:38px; height:38px; border-radius:50%; background: var(--accent); box-shadow: 0 10px 30px rgba(246,114,128,.35); }
    .nav-tabs { display:flex; gap:10px; flex-wrap:wrap; justify-content:center; }
    .tab-btn, .ghost-btn, .primary-btn, .chip, .export-btn {
      border:1px solid var(--border); color:var(--text); background:rgba(255,255,255,.06); backdrop-filter:blur(16px);
      border-radius:999px; transition: transform .22s ease, background .22s ease, opacity .22s ease, border-color .22s ease;
    }
    .tab-btn { padding:10px 14px; cursor:pointer; font-weight:600; opacity:.82; }
    .tab-btn:hover, .ghost-btn:hover, .primary-btn:hover, .chip:hover, .export-btn:hover { transform: translateY(-1px) scale(1.01); opacity:1; }
    .tab-btn.active { background: linear-gradient(135deg, rgba(204,107,142,.85), rgba(246,114,128,.85), rgba(108,91,123,.85)); border-color: rgba(255,255,255,.18); opacity:1; box-shadow: 0 10px 30px rgba(246,114,128,.22); }
    .ghost-btn, .primary-btn, .export-btn { padding:12px 16px; font-weight:700; cursor:pointer; }
    .primary-btn { background: var(--accent); border-color: transparent; color:white; box-shadow:0 12px 28px rgba(246,114,128,.22); }
    .export-btn { text-decoration:none; display:inline-flex; align-items:center; }
    .page { display:none; }
    .page.active { display:block; }
    .glass-card { background: rgba(255,255,255,.08); border:1px solid var(--border); border-radius:var(--r1); backdrop-filter:blur(18px); box-shadow:var(--shadow); }
    .hero { min-height:86vh; display:grid; grid-template-columns:1.2fr .8fr; gap:18px; align-items:stretch; margin-bottom:20px; }
    .hero-main { padding:34px; display:flex; flex-direction:column; justify-content:space-between; position:relative; overflow:hidden; }
    .hero-main::after { content:""; position:absolute; inset:auto -20% -20% auto; width:420px; height:420px; border-radius:50%; background: radial-gradient(circle, rgba(246,114,128,.24), transparent 60%); filter: blur(20px); }
    .eyebrow { display:inline-flex; gap:8px; align-items:center; width:fit-content; padding:8px 12px; border-radius:999px; background:rgba(255,255,255,.08); border:1px solid rgba(255,255,255,.12); color:var(--muted); font-size:13px; letter-spacing:.04em; text-transform:uppercase; }
    h1 { margin:18px 0 14px; font-size: clamp(3rem, 7vw, 6.2rem); line-height:.94; letter-spacing:-.05em; max-width:10ch; }
    .lede { max-width:56ch; color:var(--muted); font-size:1.05rem; line-height:1.7; }
    .hero-actions { display:flex; gap:12px; flex-wrap:wrap; margin:26px 0 24px; }
    .search-bar, .toolbar { display:grid; gap:10px; padding:14px; border-radius:24px; background:rgba(255,255,255,.06); border:1px solid rgba(255,255,255,.1); }
    .search-bar { grid-template-columns:1.25fr .8fr .8fr auto; }
    .toolbar { grid-template-columns:1.2fr .9fr .9fr .8fr .8fr auto; margin-bottom:16px; position: sticky; top:94px; z-index:20; }
    .input, .select, .textarea {
      width:100%; padding:14px 16px; border-radius:18px; border:1px solid rgba(255,255,255,.1); background:rgba(255,255,255,.06); color:var(--text); outline:none;
    }
    .textarea { min-height:110px; resize:vertical; }
    .input::placeholder, .textarea::placeholder { color: rgba(245,245,245,.45); }
    .select option { color:#111; }
    .hero-side { padding:20px; display:grid; gap:16px; align-content:start; }
    .metric-grid { display:grid; grid-template-columns: repeat(2, minmax(0,1fr)); gap:14px; }
    .metric { padding:18px; border-radius:22px; background:var(--surface-2); border:1px solid rgba(255,255,255,.08); }
    .metric .value { font-size:2rem; font-weight:800; margin-top:8px; }
    .metric .label, .muted { color:var(--muted); }
    .section { margin:18px 0; padding:22px; }
    .section-header { display:flex; align-items:center; justify-content:space-between; gap:14px; margin-bottom:18px; }
    .section-title { font-size:1.4rem; font-weight:700; letter-spacing:-.03em; }
    .two-col, .overview-grid, .live-layout, .map-layout { display:grid; gap:18px; }
    .two-col, .overview-grid, .live-layout, .map-layout { grid-template-columns:1fr 1fr; }
    .overview-grid { grid-template-columns:1.1fr .9fr; }
    .card { padding:18px; border-radius:var(--r2); background:var(--surface-2); border:1px solid rgba(255,255,255,.08); box-shadow:0 12px 36px rgba(0,0,0,.22); transition: transform .22s ease, border-color .22s ease; }
    .card:hover { transform: translateY(-4px); border-color: rgba(255,255,255,.16); }
    .chip-row { display:flex; gap:10px; flex-wrap:wrap; }
    .chip { padding:10px 12px; font-size:13px; }
    .platform-checks { display:flex; gap:8px; flex-wrap:wrap; align-items:center; padding:10px 0 2px; }
    .platform-check { display:flex; gap:8px; align-items:center; background:rgba(255,255,255,.06); border:1px solid rgba(255,255,255,.08); padding:8px 12px; border-radius:999px; }
    .feed-column { display:grid; gap:12px; max-height:72vh; overflow:auto; padding-right:6px; }
    .result-card { padding:16px; border-radius:22px; background:var(--surface-2); border:1px solid rgba(255,255,255,.08); cursor:pointer; transition:transform .18s ease, border-color .18s ease; }
    .result-card:hover { transform: translateY(-2px); border-color: rgba(255,255,255,.16); }
    .row { display:flex; align-items:center; justify-content:space-between; gap:12px; }
    .platform-badge, .severity-badge { padding:7px 10px; border-radius:999px; font-size:12px; border:1px solid rgba(255,255,255,.12); background:rgba(255,255,255,.08); white-space:nowrap; }
    .marker-map { position:relative; height:72vh; border-radius:28px; overflow:hidden; background:linear-gradient(180deg, rgba(255,255,255,.04), rgba(255,255,255,.02)), radial-gradient(circle at 30% 35%, rgba(246,114,128,.16), transparent 16%), linear-gradient(135deg, #15111f, #22192f, #120f1b); border:1px solid rgba(255,255,255,.08); }
    .map-grid { position:absolute; inset:0; background-image: linear-gradient(rgba(255,255,255,.04) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,.04) 1px, transparent 1px); background-size:48px 48px; }
    .map-label { position:absolute; top:18px; left:18px; padding:10px 14px; border-radius:999px; background:rgba(255,255,255,.08); border:1px solid rgba(255,255,255,.1); backdrop-filter: blur(12px); z-index:2; }
    .map-marker { position:absolute; width:18px; height:18px; border-radius:50%; background:linear-gradient(135deg, #f67280, #cc6b8e); box-shadow:0 0 0 6px rgba(246,114,128,.14), 0 0 26px rgba(246,114,128,.32); transform:translate(-50%, -50%); cursor:pointer; }
    .deck-board { display:grid; grid-template-columns: repeat(4, minmax(280px, 1fr)); gap:16px; overflow-x:auto; align-items:start; }
    .deck-col { min-height:70vh; padding:14px; border-radius:24px; background:var(--surface-2); border:1px solid rgba(255,255,255,.08); }
    .deck-head { display:flex; align-items:center; justify-content:space-between; gap:10px; margin-bottom:12px; position:sticky; top:0; padding-bottom:8px; background: linear-gradient(180deg, rgba(23,17,34,.92), rgba(23,17,34,.72), transparent); }
    .deck-items, .chart-bars, .table-like { display:grid; gap:12px; }
    .bar-track { width:100%; height:10px; border-radius:999px; background:rgba(255,255,255,.06); overflow:hidden; }
    .bar-fill { height:100%; border-radius:999px; background:var(--accent); }
    .detail-drawer { position:fixed; top:18px; right:18px; width:min(480px, calc(100vw - 28px)); max-height: calc(100vh - 36px); overflow:auto; background: rgba(20,15,30,.92); border:1px solid rgba(255,255,255,.12); border-radius:28px; backdrop-filter: blur(18px); box-shadow:var(--shadow); padding:20px; z-index:80; transform: translateX(110%); transition: transform .3s ease; }
    .detail-drawer.open { transform: translateX(0); }
    .detail-grid { display:grid; gap:10px; grid-template-columns: repeat(2, minmax(0, 1fr)); margin:14px 0; }
    .detail-box, .list-row { padding:12px; border-radius:18px; background: rgba(255,255,255,.05); border:1px solid rgba(255,255,255,.08); }
    .list-row { display:grid; grid-template-columns:1fr auto auto; gap:10px; align-items:center; }
    .footer-note { margin-top:18px; color: rgba(245,245,245,.55); font-size:13px; line-height:1.6; }
    @media (max-width: 1200px) { .hero, .overview-grid, .live-layout, .map-layout, .two-col { grid-template-columns:1fr; } .toolbar, .search-bar, .metric-grid { grid-template-columns:1fr 1fr; } .deck-board { grid-template-columns: repeat(2, minmax(280px,1fr)); } }
    @media (max-width: 760px) { .shell { width:min(100vw - 18px, 1460px); } .nav { border-radius:28px; align-items:flex-start; } .nav, .nav-tabs { flex-direction:column; } .hero-main, .hero-side, .section { padding:18px; } .search-bar, .toolbar, .metric-grid { grid-template-columns:1fr; } .deck-board { grid-template-columns:1fr; } h1 { max-width:100%; } }
  </style>
</head>
<body>
  <div class="loader" id="loader"><div class="loader-inner"></div></div>
  <div class="cursor-glow" id="cursorGlow"></div>
  <div class="shell">
    <nav class="nav">
      <div class="brand"><div class="brand-badge"></div><div><div>Signal Atlas</div><div class="muted" style="font-size:12px">Premium monitoring website</div></div></div>
      <div class="nav-tabs">
        <button class="tab-btn active" data-page="landing">Landing</button>
        <button class="tab-btn" data-page="overview">Overview</button>
        <button class="tab-btn" data-page="livefeed">Live Feed</button>
        <button class="tab-btn" data-page="map">Map</button>
        <button class="tab-btn" data-page="deck">Deck</button>
        <button class="tab-btn" data-page="trends">Trends</button>
        <button class="tab-btn" data-page="entities">Entities</button>
        <button class="tab-btn" data-page="accounts">Accounts</button>
        <button class="tab-btn" data-page="reports">Reports</button>
        <button class="tab-btn" data-page="settings">Settings</button>
      </div>
      <div style="display:flex; gap:10px;">
        <button class="ghost-btn" id="refreshAllBtn">Refresh all</button>
        <a class="export-btn" href="/api/export.csv" target="_blank">Export CSV</a>
      </div>
    </nav>

    <section class="page active" id="page-landing">
      <div class="hero">
        <div class="hero-main glass-card">
          <div>
            <div class="eyebrow">Real-time monitoring · Middle East + Europe · 30s refresh</div>
            <h1>Live signals, mapped and ranked.</h1>
            <p class="lede">A premium monitoring website prototype for public and licensed sources. Select Telegram, Instagram, X, and website/news sources together and view one combined result flow.</p>
            <div class="hero-actions">
              <button class="primary-btn" id="heroStart">Create alert</button>
              <button class="ghost-btn" id="heroMap">Open live map</button>
            </div>
          </div>
          <div class="search-bar">
            <input class="input" id="landingKeywords" placeholder="Keywords or exact phrases: protest, drone attack, airport" />
            <select class="select" id="landingCountry"></select>
            <select class="select" id="landingWindow"><option>1h</option><option>2h</option><option>12h</option><option selected>24h</option><option>7d</option><option>30d</option></select>
            <button class="primary-btn" id="createAlertBtn">Create</button>
          </div>
          <div class="platform-checks" id="platformChecks"></div>
        </div>
        <div class="hero-side glass-card">
          <div class="metric-grid">
            <div class="metric"><div class="label">Live matches</div><div class="value" id="kpiMatches">428</div></div>
            <div class="metric"><div class="label">High-priority incidents</div><div class="value" id="kpiHigh">18</div></div>
            <div class="metric"><div class="label">New accounts</div><div class="value" id="kpiAccounts">42</div></div>
            <div class="metric"><div class="label">Active alerts</div><div class="value" id="kpiAlerts">8</div></div>
          </div>
          <div class="card"><div class="section-title">Quick-start templates</div><div class="chip-row" id="templatePills"></div></div>
          <div class="card"><div class="section-title">Source coverage</div><div class="chip-row"><span class="chip">Telegram</span><span class="chip">Instagram</span><span class="chip">X</span><span class="chip">Websites / News</span><span class="chip">Europe</span><span class="chip">UK</span><span class="chip">Middle East</span></div><p class="footer-note">The platform selection is combined into one result stream. Connector functions below are safe stubs that you can later replace with approved APIs or licensed feeds.</p></div>
        </div>
      </div>
      <div class="two-col">
        <div class="section glass-card"><div class="section-header"><div><div class="section-title">Recent alerts</div><div class="muted">Saved alert rules ready to reopen</div></div></div><div id="alertCards" class="table-like"></div></div>
        <div class="section glass-card"><div class="section-header"><div><div class="section-title">Featured live incidents</div><div class="muted">Fast glance at current high-signal items</div></div></div><div id="featuredIncidents" class="table-like"></div></div>
      </div>
    </section>

    <section class="page" id="page-overview">
      <div class="toolbar">
        <input class="input" id="searchInput" placeholder="Search countries, regions, keywords, hashtags, accounts, domains" />
        <select class="select" id="countryFilter"></select>
        <select class="select" id="platformFilter"></select>
        <select class="select" id="languageFilter"></select>
        <select class="select" id="severityFilter"><option value="All">All severities</option><option>Low</option><option>Medium</option><option>High</option></select>
        <button class="primary-btn" id="applyFilters">Apply</button>
      </div>
      <div class="overview-grid">
        <div class="section glass-card">
          <div class="section-header"><div class="section-title">Executive overview</div><div class="muted">Live analyst summary</div></div>
          <div class="metric-grid" id="overviewMetrics"></div>
          <div class="card" style="margin-top:16px"><div class="section-title">Incident map preview</div><div class="marker-map" id="overviewMap" style="height:300px; margin-top:12px;"><div class="map-grid"></div><div class="map-label">Map preview · current alert focus</div></div></div>
        </div>
        <div class="section glass-card">
          <div class="section-header"><div class="section-title">Top regions and keywords</div><div class="muted">Volume and spike indicators</div></div>
          <div class="card"><div class="muted">Top regions</div><div class="chart-bars" id="regionBars"></div></div>
          <div class="card" style="margin-top:14px"><div class="muted">Top keywords</div><div class="chart-bars" id="keywordBars"></div></div>
          <div class="card" style="margin-top:14px"><div class="muted">Analyst notes</div><p class="muted">The unified feed combines selected platform sources into one result model with shared filtering, map placement, and export.</p></div>
        </div>
      </div>
    </section>

    <section class="page" id="page-livefeed">
      <div class="toolbar">
        <input class="input" id="liveSearch" placeholder="Live feed query" />
        <select class="select" id="liveCountry"></select>
        <select class="select" id="livePlatform"></select>
        <select class="select" id="liveSeverity"><option value="All">All severities</option><option>Low</option><option>Medium</option><option>High</option></select>
        <select class="select" id="liveLanguage"></select>
        <button class="primary-btn" id="liveRefresh">Refresh</button>
      </div>
      <div class="live-layout">
        <div class="section glass-card"><div class="section-header"><div class="section-title">Identified social posts</div><div class="muted">Refresh target: 30 seconds</div></div><div id="socialFeed" class="feed-column"></div></div>
        <div class="section glass-card"><div class="section-header"><div class="section-title">Identified websites reporting on the matter</div><div class="muted">Public web and news matches</div></div><div id="webFeed" class="feed-column"></div></div>
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
        <div class="section glass-card"><div class="section-header"><div class="section-title">Live incident panel</div><div class="muted">Click a marker or card for detail</div></div><div id="mapFeed" class="feed-column"></div></div>
      </div>
    </section>

    <section class="page" id="page-deck">
      <div class="toolbar">
        <input class="input" id="deckSearch" placeholder="Search across deck columns" />
        <select class="select" id="deckCountry"></select>
        <select class="select" id="deckMode"><option value="source">By source</option><option value="region">By region</option><option value="keyword">By keyword group</option><option value="severity">By severity</option></select>
        <select class="select" id="deckLanguage"></select>
        <select class="select" id="deckSeverity"><option value="All">All severities</option><option>Low</option><option>Medium</option><option>High</option></select>
        <button class="primary-btn" id="deckRefresh">Refresh deck</button>
      </div>
      <div class="deck-board" id="deckBoard"></div>
    </section>

    <section class="page" id="page-trends">
      <div class="section glass-card"><div class="section-header"><div class="section-title">Trends</div><div class="muted">Keywords, hashtags, regions, spike detection</div></div><div class="two-col"><div class="card"><div class="muted">Trending keywords</div><div id="trendingKeywords" class="chart-bars"></div></div><div class="card"><div class="muted">Top regions by volume</div><div id="trendingRegions" class="chart-bars"></div></div></div></div>
    </section>

    <section class="page" id="page-entities">
      <div class="section glass-card"><div class="section-header"><div class="section-title">Entities</div><div class="muted">People, organizations, locations, assets</div></div><div id="entityList" class="table-like"></div></div>
    </section>

    <section class="page" id="page-accounts">
      <div class="section glass-card"><div class="section-header"><div class="section-title">Accounts</div><div class="muted">Newly seen, most active, high-signal sources</div></div><div id="accountList" class="table-like"></div></div>
    </section>

    <section class="page" id="page-reports">
      <div class="section glass-card"><div class="section-header"><div class="section-title">Reports</div><div class="muted">Saved items, export-ready analyst notes</div></div><div class="card"><p class="muted">This prototype provides the website structure and unified result model. Replace the platform collector stubs with official APIs or licensed connectors before production use.</p></div></div>
    </section>

    <section class="page" id="page-settings">
      <div class="section glass-card">
        <div class="section-header"><div class="section-title">Settings</div><div class="muted">Alert creation and workspace configuration</div></div>
        <div class="two-col">
          <div class="card">
            <div class="section-title">Alert builder</div>
            <div style="display:grid; gap:10px; margin-top:14px;">
              <input class="input" id="alertName" placeholder="Alert name" />
              <select class="select" id="settingsCountry"></select>
              <select class="select" id="settingsRegion"></select>
              <input class="input" id="alertKeywords" placeholder="Keywords, phrases, hashtags" />
              <select class="select" id="alertLanguage"><option>Arabic</option><option>English</option><option>French</option><option>German</option><option>Spanish</option><option>Italian</option></select>
              <select class="select" id="alertWindow"><option>1h</option><option>2h</option><option>12h</option><option selected>24h</option><option>7d</option><option>30d</option></select>
              <textarea class="textarea" id="alertNotes" placeholder="Optional notes, exclusion terms, boolean logic"></textarea>
              <div class="platform-checks" id="alertPlatformChecks"></div>
              <div style="display:flex; gap:10px; flex-wrap:wrap;">
                <button class="primary-btn" id="saveAlertBtn">Save alert</button>
                <span class="muted" id="saveAlertStatus">No alert saved yet.</span>
              </div>
            </div>
          </div>
          <div class="card">
            <div class="section-title">Compliance and workflow</div>
            <div class="chip-row" style="margin-top:14px;"><span class="chip">Public sources</span><span class="chip">Licensed feeds</span><span class="chip">Geo inference</span><span class="chip">Translation</span><span class="chip">Deduplication</span><span class="chip">Export</span></div>
            <p class="footer-note">Use official APIs or licensed feeds instead of raw scraping when you convert the connector stubs into real ingestion.</p>
          </div>
        </div>
      </div>
    </section>
  </div>

  <aside class="detail-drawer" id="detailDrawer">
    <div class="row"><div class="section-title">Incident detail</div><button class="ghost-btn" id="closeDrawer">Close</button></div>
    <div id="detailContent"></div>
  </aside>

  <script>
    const appState = { data: null, filtered: [], selectedId: null, enabledPlatforms: ['Telegram', 'Instagram', 'X', 'News'] };
    const pages = document.querySelectorAll('.page');
    const tabButtons = document.querySelectorAll('.tab-btn');

    function switchPage(name) {
      pages.forEach(p => p.classList.toggle('active', p.id === `page-${name}`));
      tabButtons.forEach(btn => btn.classList.toggle('active', btn.dataset.page === name));
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }

    tabButtons.forEach(btn => btn.addEventListener('click', () => switchPage(btn.dataset.page)));
    document.getElementById('heroStart').addEventListener('click', () => switchPage('settings'));
    document.getElementById('heroMap').addEventListener('click', () => switchPage('map'));
    document.getElementById('createAlertBtn').addEventListener('click', () => switchPage('settings'));
    document.getElementById('refreshAllBtn').addEventListener('click', () => refreshData());

    const loader = document.getElementById('loader');
    window.addEventListener('load', () => setTimeout(() => loader.classList.add('hidden'), 600));

    const cursorGlow = document.getElementById('cursorGlow');
    window.addEventListener('mousemove', (e) => {
      cursorGlow.style.left = `${e.clientX}px`;
      cursorGlow.style.top = `${e.clientY}px`;
    });

    function optionFill(el, items, addAll = false, allText = 'All') {
      el.innerHTML = '';
      if (addAll) {
        const opt = document.createElement('option');
        opt.value = 'All';
        opt.textContent = allText;
        el.appendChild(opt);
      }
      items.forEach(item => {
        const opt = document.createElement('option');
        opt.value = item;
        opt.textContent = item;
        el.appendChild(opt);
      });
    }

    function renderPlatformChecks(containerId, selected) {
      const host = document.getElementById(containerId);
      host.innerHTML = '';
      appState.data.userSelectablePlatforms.forEach(platform => {
        const label = document.createElement('label');
        label.className = 'platform-check';
        label.innerHTML = `<input type="checkbox" value="${platform}" ${selected.includes(platform) ? 'checked' : ''}/> ${platform}`;
        host.appendChild(label);
      });
      host.querySelectorAll('input[type="checkbox"]').forEach(box => {
        box.addEventListener('change', syncPlatformSelectionFromUI);
      });
    }

    function syncPlatformSelectionFromUI() {
      const checked = Array.from(document.querySelectorAll('#platformChecks input[type="checkbox"]:checked')).map(x => x.value);
      appState.enabledPlatforms = checked.length ? checked : ['Telegram'];
      document.querySelectorAll('#alertPlatformChecks input[type="checkbox"]').forEach(box => {
        box.checked = appState.enabledPlatforms.includes(box.value);
      });
      refreshData();
    }

    function populateSelectors(data) {
      const countries = data.countries;
      ['landingCountry','countryFilter','liveCountry','mapCountry','deckCountry','settingsCountry'].forEach(id => optionFill(document.getElementById(id), countries, id !== 'landingCountry'));
      optionFill(document.getElementById('platformFilter'), data.sources, true);
      optionFill(document.getElementById('mapPlatform'), data.sources, true);
      optionFill(document.getElementById('livePlatform'), data.sources, true);
      optionFill(document.getElementById('liveLanguage'), data.languages, true);
      optionFill(document.getElementById('deckLanguage'), data.languages, true);
      optionFill(document.getElementById('languageFilter'), data.languages, true);
      updateRegionOptions();
      renderPlatformChecks('platformChecks', appState.enabledPlatforms);
      renderPlatformChecks('alertPlatformChecks', appState.enabledPlatforms);

      const pillHost = document.getElementById('templatePills');
      pillHost.innerHTML = '';
      data.templates.forEach(t => {
        const span = document.createElement('span');
        span.className = 'chip';
        span.textContent = t;
        pillHost.appendChild(span);
      });
    }

    function updateRegionOptions() {
      const country = document.getElementById('settingsCountry').value;
      const regions = appState.data.countryRegions[country] || [];
      optionFill(document.getElementById('settingsRegion'), regions);
    }

    function severityRank(severity) {
      return { Low: 1, Medium: 2, High: 3, Critical: 4 }[severity] || 0;
    }

    function projectLatLng(lat, lng) {
      const bounds = appState.data.mapBounds;
      const left = ((lng - bounds.minLng) / (bounds.maxLng - bounds.minLng)) * 100;
      const top = 100 - (((lat - bounds.minLat) / (bounds.maxLat - bounds.minLat)) * 100);
      return { left: Math.max(3, Math.min(97, left)), top: Math.max(3, Math.min(97, top)) };
    }

    function itemCard(item) {
      return `
        <div class="result-card" data-id="${item.id}">
          <div class="row">
            <div class="platform-badge">${item.sourcePlatform}</div>
            <div class="muted">${item.postedAgo}</div>
          </div>
          <div style="font-size:1.05rem; font-weight:700; margin:10px 0 6px;">${item.summary}</div>
          <div class="muted" style="line-height:1.55;">${item.text}</div>
          <div class="chip-row" style="margin-top:12px;">${item.keywords.map(k => `<span class="chip">${k}</span>`).join('')}</div>
          <div class="row" style="margin-top:12px;">
            <div class="muted">${item.authorName} · ${item.locationLabel}</div>
            <div class="severity-badge">${item.severity}</div>
          </div>
        </div>`;
    }

    function attachCardHandlers() {
      document.querySelectorAll('.result-card').forEach(card => {
        card.addEventListener('click', () => openDetail(card.dataset.id));
      });
    }

    function openDetail(id) {
      const item = appState.data.items.find(x => x.id === id);
      if (!item) return;
      document.getElementById('detailContent').innerHTML = `
        <div class="muted">${item.sourcePlatform} · ${item.locationLabel}</div>
        <div style="font-size:1.4rem; font-weight:800; margin:8px 0 10px;">${item.summary}</div>
        <a href="${item.sourceUrl}" target="_blank" rel="noopener" style="color:#ffd1dc;">${item.sourceUrl}</a>
        <div class="detail-grid">
          <div class="detail-box"><strong>Posted</strong><br>${item.postedAt}</div>
          <div class="detail-box"><strong>First seen</strong><br>${item.firstSeenAt}</div>
          <div class="detail-box"><strong>Username</strong><br>${item.authorName} (${item.authorHandle})</div>
          <div class="detail-box"><strong>Geo method</strong><br>${item.geoMethod}</div>
          <div class="detail-box"><strong>Confidence</strong><br>${item.confidenceScore}</div>
          <div class="detail-box"><strong>Verification</strong><br>${item.verificationState}</div>
        </div>
        <div class="card" style="padding:14px; margin:10px 0;"><div class="muted">Original text</div><div style="margin-top:8px; line-height:1.6;">${item.text}</div></div>
        <div class="card" style="padding:14px; margin:10px 0;"><div class="muted">Translation</div><div style="margin-top:8px; line-height:1.6;">${item.translatedText}</div></div>
        <div class="chip-row" style="margin-top:10px;">${item.keywords.map(k => `<span class="chip">${k}</span>`).join('')}</div>
      `;
      document.getElementById('detailDrawer').classList.add('open');
    }

    document.getElementById('closeDrawer').addEventListener('click', () => {
      document.getElementById('detailDrawer').classList.remove('open');
    });

    function getFirstNonAll(ids) {
      for (const id of ids) {
        const el = document.getElementById(id);
        if (el && el.value && el.value !== 'All') return el.value;
      }
      return 'All';
    }

    function getQueryValue() {
      for (const id of ['searchInput', 'liveSearch', 'mapSearch', 'deckSearch']) {
        const el = document.getElementById(id);
        if (el && el.value.trim()) return el.value.trim().toLowerCase();
      }
      return '';
    }

    function filterItems() {
      const query = getQueryValue();
      const country = getFirstNonAll(['countryFilter', 'liveCountry', 'mapCountry', 'deckCountry']);
      const platform = getFirstNonAll(['platformFilter', 'livePlatform', 'mapPlatform']);
      const language = getFirstNonAll(['languageFilter', 'liveLanguage', 'deckLanguage']);
      const severity = getFirstNonAll(['severityFilter', 'liveSeverity', 'mapSeverity', 'deckSeverity']);
      const geo = getFirstNonAll(['mapGeo']);

      let items = [...appState.data.items];
      items = items.filter(i => appState.enabledPlatforms.includes(i.sourcePlatform) || i.sourcePlatform === 'Forum');

      if (country !== 'All') items = items.filter(i => i.country === country);
      if (platform !== 'All') items = items.filter(i => i.sourcePlatform === platform);
      if (language !== 'All') items = items.filter(i => i.language === language);
      if (severity !== 'All') items = items.filter(i => i.severity === severity);
      if (geo !== 'All') items = items.filter(i => i.geoPrecision === geo);

      if (query) {
        items = items.filter(i =>
          [i.summary, i.text, i.authorName, i.region, i.country, ...(i.keywords || [])]
            .join(' ')
            .toLowerCase()
            .includes(query)
        );
      }
      appState.filtered = items;
      return items;
    }

    function groupCounts(items, keyFn) {
      const map = new Map();
      items.forEach(i => {
        const key = keyFn(i);
        map.set(key, (map.get(key) || 0) + 1);
      });
      return [...map.entries()].map(([name, count]) => ({ name, count })).sort((a,b) => b.count - a.count);
    }

    function renderBars(id, counts) {
      const root = document.getElementById(id);
      const max = Math.max(...counts.map(c => c.count), 1);
      root.innerHTML = counts.slice(0, 6).map(c => `
        <div>
          <div class="row"><span>${c.name}</span><span class="muted">${c.count}</span></div>
          <div class="bar-track"><div class="bar-fill" style="width:${(c.count/max)*100}%"></div></div>
        </div>
      `).join('');
    }

    function renderMiniMap(container, items) {
      container.querySelectorAll('.map-marker').forEach(el => el.remove());
      items.forEach(item => {
        const marker = document.createElement('div');
        marker.className = 'map-marker';
        const pos = projectLatLng(item.lat, item.lng);
        marker.style.left = `${pos.left}%`;
        marker.style.top = `${pos.top}%`;
        marker.title = item.summary;
        marker.addEventListener('click', () => openDetail(item.id));
        container.appendChild(marker);
      });
    }

    function renderLanding(data) {
      document.getElementById('alertCards').innerHTML = data.alerts.map(a => `
        <div class="list-row">
          <div><strong>${a.name}</strong><div class="muted">${a.country} · ${a.region} · ${a.window}</div></div>
          <div class="muted">${a.sources.join(', ')}</div>
          <button class="ghost-btn" onclick="switchPage('overview')">Open</button>
        </div>
      `).join('');

      document.getElementById('featuredIncidents').innerHTML = data.items.slice(0, 4).map(i => `
        <div class="list-row">
          <div><strong>${i.summary}</strong><div class="muted">${i.authorName} · ${i.locationLabel}</div></div>
          <div class="muted">${i.postedAgo}</div>
          <button class="ghost-btn" onclick="openDetail('${i.id}')">View</button>
        </div>
      `).join('');
    }

    function renderOverview(items) {
      const metrics = [
        ['Total matches', items.length],
        ['High-priority incidents', items.filter(i => severityRank(i.severity) >= severityRank('High')).length],
        ['New accounts', new Set(items.map(i => i.authorHandle)).size],
        ['Active alerts', appState.data.alerts.length],
      ];
      document.getElementById('overviewMetrics').innerHTML = metrics.map(([label, value]) => `<div class="metric"><div class="label">${label}</div><div class="value">${value}</div></div>`).join('');
      renderMiniMap(document.getElementById('overviewMap'), items);
      renderBars('regionBars', groupCounts(items, i => i.region));
      renderBars('keywordBars', groupCounts(items.flatMap(i => i.keywords).map(k => ({name:k})), x => x.name));
    }

    function renderFeeds(items) {
      const social = items.filter(i => i.sourceType === 'social');
      const web = items.filter(i => i.sourceType === 'web');
      document.getElementById('socialFeed').innerHTML = social.map(itemCard).join('');
      document.getElementById('webFeed').innerHTML = web.map(itemCard).join('');
      attachCardHandlers();
    }

    function renderMap(items) {
      const map = document.getElementById('mainMap');
      map.querySelectorAll('.map-marker').forEach(el => el.remove());
      document.getElementById('mapFeed').innerHTML = items.map(itemCard).join('');
      items.forEach(item => {
        const marker = document.createElement('div');
        marker.className = 'map-marker';
        const pos = projectLatLng(item.lat, item.lng);
        marker.style.left = `${pos.left}%`;
        marker.style.top = `${pos.top}%`;
        marker.addEventListener('click', () => openDetail(item.id));
        map.appendChild(marker);
      });
      attachCardHandlers();
    }

    function renderDeck(items) {
      const board = document.getElementById('deckBoard');
      const groups = {
        'Telegram matches': items.filter(i => i.sourcePlatform === 'Telegram'),
        'Instagram matches': items.filter(i => i.sourcePlatform === 'Instagram'),
        'X matches': items.filter(i => i.sourcePlatform === 'X'),
        'Website matches': items.filter(i => i.sourcePlatform === 'News'),
      };
      board.innerHTML = Object.entries(groups).map(([name, rows]) => `
        <div class="deck-col">
          <div class="deck-head"><strong>${name}</strong><span class="muted">${rows.length}</span></div>
          <div class="deck-items">${rows.map(itemCard).join('')}</div>
        </div>
      `).join('');
      attachCardHandlers();
    }

    function renderTrends(items) {
      renderBars('trendingKeywords', groupCounts(items.flatMap(i => i.keywords).map(k => ({name:k})), x => x.name));
      renderBars('trendingRegions', groupCounts(items, i => i.region));
    }

    function renderEntities() {
      const entities = ['Damascus International Airport', 'Central London roads', 'Paris transport corridor', 'Berlin civic square', 'Baghdad checkpoint', 'Border crossing'];
      document.getElementById('entityList').innerHTML = entities.map((e, idx) => `
        <div class="list-row">
          <div><strong>${e}</strong><div class="muted">Related incidents: ${1 + (idx % 4)}</div></div>
          <div class="muted">Location/asset</div>
          <button class="ghost-btn">Open</button>
        </div>
      `).join('');
    }

    function renderAccounts(items) {
      const grouped = {};
      items.forEach(i => {
        grouped[i.authorHandle] = grouped[i.authorHandle] || { name: i.authorName, handle: i.authorHandle, platform: i.sourcePlatform, count: 0, region: i.region };
        grouped[i.authorHandle].count += 1;
      });
      document.getElementById('accountList').innerHTML = Object.values(grouped).map(a => `
        <div class="list-row">
          <div><strong>${a.name}</strong><div class="muted">${a.handle} · ${a.platform} · ${a.region}</div></div>
          <div class="muted">${a.count} matches</div>
          <button class="ghost-btn">Profile</button>
        </div>
      `).join('');
    }

    function updateKPIs(items) {
      document.getElementById('kpiMatches').textContent = String(400 + items.length * 7);
      document.getElementById('kpiHigh').textContent = String(items.filter(i => severityRank(i.severity) >= severityRank('High')).length);
      document.getElementById('kpiAccounts').textContent = String(new Set(items.map(i => i.authorHandle)).size * 6);
      document.getElementById('kpiAlerts').textContent = String(appState.data.alerts.length);
    }

    function renderAll() {
      const items = filterItems();
      renderLanding(appState.data);
      renderOverview(items);
      renderFeeds(items);
      renderMap(items);
      renderDeck(items);
      renderTrends(items);
      renderEntities();
      renderAccounts(items);
      updateKPIs(items);
    }

    async function loadData() {
      const res = await fetch('/api/dashboard');
      appState.data = await res.json();
      populateSelectors(appState.data);
      renderAll();
    }

    async function refreshData() {
      const params = new URLSearchParams();
      appState.enabledPlatforms.forEach(p => params.append('platform', p));
      const res = await fetch('/api/refresh?' + params.toString());
      appState.data = await res.json();
      renderAll();
    }

    async function saveAlert() {
      const selectedPlatforms = Array.from(document.querySelectorAll('#alertPlatformChecks input[type="checkbox"]:checked')).map(x => x.value);
      const payload = {
        name: document.getElementById('alertName').value || 'New monitoring alert',
        country: document.getElementById('settingsCountry').value || 'Syria',
        region: document.getElementById('settingsRegion').value || 'Aleppo',
        keywords: (document.getElementById('alertKeywords').value || 'protest, drone').split(',').map(x => x.trim()).filter(Boolean),
        sources: selectedPlatforms.length ? selectedPlatforms : ['Telegram', 'Instagram', 'X', 'News'],
        window: document.getElementById('alertWindow').value || '24h',
        refresh: '30s'
      };
      const res = await fetch('/api/alerts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (data.ok) {
        document.getElementById('saveAlertStatus').textContent = `Saved: ${data.alert.name}`;
        appState.data.alerts.unshift(data.alert);
        renderLanding(appState.data);
        updateKPIs(filterItems());
      } else {
        document.getElementById('saveAlertStatus').textContent = 'Failed to save alert.';
      }
    }

    document.getElementById('settingsCountry').addEventListener('change', updateRegionOptions);
    document.getElementById('saveAlertBtn').addEventListener('click', saveAlert);

    ['applyFilters','liveRefresh','mapRefresh','deckRefresh'].forEach(id => {
      document.getElementById(id)?.addEventListener('click', renderAll);
    });

    setInterval(refreshData, 30000);
    loadData();
  </script>
</body>
</html>
'''

def dashboard_payload():
    return {
        "countries": list(COUNTRIES.keys()),
        "countryRegions": {country: meta["regions"] for country, meta in COUNTRIES.items()},
        "sources": ["All"] + ALL_SOURCES,
        "languages": ["All"] + LANGUAGES,
        "templates": TEMPLATES,
        "alerts": ALERTS,
        "items": list(LIVE_ITEMS),
        "userSelectablePlatforms": USER_SELECTABLE_PLATFORMS,
        "mapBounds": MAP_BOUNDS,
    }

@app.route("/")
def index():
    return render_template_string(HTML)

@app.route("/api/dashboard")
def api_dashboard():
    return jsonify(dashboard_payload())

@app.route("/api/refresh")
def api_refresh():
    requested_platforms = request.args.getlist("platform")
    LIVE_ITEMS[:] = collect_live_items(requested_platforms or USER_SELECTABLE_PLATFORMS)
    return jsonify(dashboard_payload())

@app.route("/api/alerts", methods=["POST"])
def create_alert():
    payload = request.get_json(silent=True) or {}
    alert = {
        "id": f"alert-{uuid.uuid4().hex[:8]}",
        "name": payload.get("name", "New monitoring alert"),
        "country": payload.get("country", "Syria"),
        "region": payload.get("region", "Aleppo"),
        "keywords": payload.get("keywords", ["protest", "drone"]),
        "sources": payload.get("sources", ["Telegram", "Instagram", "X", "News"]),
        "window": payload.get("window", "24h"),
        "refresh": payload.get("refresh", "30s"),
    }
    ALERTS.insert(0, alert)
    return jsonify({"ok": True, "alert": alert})

@app.route("/api/export.csv")
def export_csv_file():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "id", "alertId", "sourcePlatform", "sourceUrl", "sourceDomain", "authorName",
        "authorHandle", "postedAt", "firstSeenAt", "keywords", "text", "translatedText",
        "language", "country", "region", "city", "lat", "lng", "geoPrecision",
        "geoMethod", "confidenceScore", "severity", "severityScore", "verificationState"
    ])
    for item in LIVE_ITEMS:
        writer.writerow([
            item["id"], item["alertId"], item["sourcePlatform"], item["sourceUrl"], item["sourceDomain"],
            item["authorName"], item["authorHandle"], item["postedAt"], item["firstSeenAt"],
            ", ".join(item["keywords"]), item["text"], item["translatedText"], item["language"],
            item["country"], item["region"], item["city"], item["lat"], item["lng"],
            item["geoPrecision"], item["geoMethod"], item["confidenceScore"], item["severity"],
            item["severityScore"], item["verificationState"],
        ])
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=signal_atlas_export.csv"},
    )

if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)