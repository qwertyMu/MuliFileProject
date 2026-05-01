import sqlite3
from contextlib import contextmanager
from config import Config

@contextmanager
def get_conn():
    conn = sqlite3.connect(Config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

def init_db():
    with get_conn() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            country TEXT,
            region TEXT,
            keywords TEXT,
            exclude_keywords TEXT,
            languages TEXT,
            sources TEXT,
            window TEXT,
            refresh TEXT,
            created_at TEXT NOT NULL
        )
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS source_items (
            id TEXT PRIMARY KEY,
            alert_id TEXT,
            source_platform TEXT,
            source_type TEXT,
            source_url TEXT,
            source_domain TEXT,
            author_name TEXT,
            author_handle TEXT,
            author_url TEXT,
            posted_at TEXT,
            first_seen_at TEXT,
            text TEXT,
            translated_text TEXT,
            language TEXT,
            matched_keywords TEXT,
            hashtags TEXT,
            country TEXT,
            region TEXT,
            city TEXT,
            lat REAL,
            lng REAL,
            geo_precision TEXT,
            geo_method TEXT,
            confidence_score REAL,
            severity TEXT,
            severity_score REAL,
            duplicate_cluster_id TEXT,
            verification_state TEXT,
            engagement INTEGER,
            summary TEXT,
            UNIQUE(source_url, summary)
        )
        """)

def insert_alert(alert):
    with get_conn() as conn:
        conn.execute("""
        INSERT OR REPLACE INTO alerts (
            id, name, country, region, keywords, exclude_keywords,
            languages, sources, window, refresh, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            alert["id"],
            alert["name"],
            alert.get("country", "All"),
            alert.get("region", "All"),
            ",".join(alert.get("keywords", [])),
            ",".join(alert.get("exclude_keywords", [])),
            ",".join(alert.get("languages", [])),
            ",".join(alert.get("sources", [])),
            alert.get("window", "24h"),
            alert.get("refresh", "30s"),
            alert["createdAt"],
        ))

def insert_source_item(item):
    with get_conn() as conn:
        conn.execute("""
        INSERT OR IGNORE INTO source_items (
            id, alert_id, source_platform, source_type, source_url, source_domain,
            author_name, author_handle, author_url, posted_at, first_seen_at,
            text, translated_text, language, matched_keywords, hashtags,
            country, region, city, lat, lng, geo_precision, geo_method,
            confidence_score, severity, severity_score, duplicate_cluster_id,
            verification_state, engagement, summary
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            item["id"],
            item["alertId"],
            item["sourcePlatform"],
            item["sourceType"],
            item["sourceUrl"],
            item["sourceDomain"],
            item["authorName"],
            item["authorHandle"],
            item["authorUrl"],
            item["postedAt"],
            item["firstSeenAt"],
            item["text"],
            item["translatedText"],
            item["language"],
            ",".join(item.get("keywords", [])),
            ",".join(item.get("hashtags", [])),
            item["country"],
            item["region"],
            item["city"],
            item["lat"],
            item["lng"],
            item["geoPrecision"],
            item["geoMethod"],
            item["confidenceScore"],
            item["severity"],
            item["severityScore"],
            item.get("duplicateClusterId"),
            item["verificationState"],
            item.get("engagement", 0),
            item["summary"],
        ))

def get_recent_items(limit=500):
    with get_conn() as conn:
        rows = conn.execute("""
        SELECT * FROM source_items
        ORDER BY first_seen_at DESC
        LIMIT ?
        """, (limit,)).fetchall()
        return [dict(r) for r in rows]

def get_alerts():
    with get_conn() as conn:
        rows = conn.execute("""
        SELECT * FROM alerts
        ORDER BY created_at DESC
        """).fetchall()
        return [dict(r) for r in rows]