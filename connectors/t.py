from config import Config
import uuid
from datetime import datetime, timezone

def _now_iso():
    return datetime.now(timezone.utc).isoformat()

def _matches(text, keywords):
    lowered = (text or "").lower()
    return [kw for kw in keywords if kw and kw.lower() in lowered]

def _channel_url(channel, message_id):
    value = str(channel).strip()
    if value.startswith("https://t.me/"):
        return f"{value.rstrip('/')}/{message_id}"
    if value.startswith("@"):
        return f"https://t.me/{value[1:]}/{message_id}"
    if value and "/" not in value and not value.startswith("-"):
        return f"https://t.me/{value}/{message_id}"
    return ""

def _diagnose(diagnostics, status, message):
    if diagnostics is not None:
        diagnostics["Telegram"] = {"status": status, "message": message}

def search_telegram(alert, diagnostics=None):
    if not (Config.TELEGRAM_API_ID and Config.TELEGRAM_API_HASH):
        _diagnose(diagnostics, "disabled", "TELEGRAM_API_ID and TELEGRAM_API_HASH are not configured.")
        return []
    if not Config.TELEGRAM_CHANNELS:
        _diagnose(diagnostics, "disabled", "TELEGRAM_CHANNELS is empty.")
        return []

    try:
        from telethon.sync import TelegramClient
    except ImportError:
        _diagnose(diagnostics, "error", "Telethon is not installed. Run pip install -r requirements.txt.")
        return []

    try:
        api_id = int(Config.TELEGRAM_API_ID)
    except ValueError:
        _diagnose(diagnostics, "error", "TELEGRAM_API_ID must be a number.")
        return []

    keywords = alert.get("keywords", [])
    language_pref = set(alert.get("languages", ["All"]))
    items = []

    client = TelegramClient(Config.TELEGRAM_SESSION, api_id, Config.TELEGRAM_API_HASH)
    try:
        client.connect()
        if not client.is_user_authorized():
            _diagnose(
                diagnostics,
                "unauthorized",
                "Telegram session is not authorized. Run python telegram_login.py once.",
            )
            return []

        for channel in Config.TELEGRAM_CHANNELS:
            try:
                entity = client.get_entity(channel)
                author_name = getattr(entity, "title", None) or getattr(entity, "username", None) or str(channel)
                author_handle = f"@{getattr(entity, 'username', '')}" if getattr(entity, "username", None) else str(channel)

                for message in client.iter_messages(entity, limit=Config.TELEGRAM_LIMIT):
                    text = (getattr(message, "message", None) or "").strip()
                    if not text:
                        continue

                    matched = _matches(text, keywords)
                    if not matched:
                        continue

                    language = "Unknown"
                    if "All" not in language_pref and language not in language_pref:
                        continue

                    posted = message.date or datetime.now(timezone.utc)
                    if posted.tzinfo is None:
                        posted = posted.replace(tzinfo=timezone.utc)

                    items.append({
                        "id": str(uuid.uuid4()),
                        "alertId": alert["id"],
                        "sourcePlatform": "Telegram",
                        "sourceType": "social",
                        "sourceUrl": _channel_url(channel, message.id),
                        "sourceDomain": "telegram.org",
                        "authorName": author_name,
                        "authorHandle": author_handle,
                        "authorUrl": _channel_url(channel, ""),
                        "postedAt": posted.isoformat(),
                        "firstSeenAt": _now_iso(),
                        "text": text,
                        "translatedText": text,
                        "language": language,
                        "keywords": matched,
                        "hashtags": [f"#{k.replace(' ', '')}" for k in matched[:2]],
                        "country": alert.get("country", "All"),
                        "region": alert.get("region", "All"),
                        "city": alert.get("region", ""),
                        "lat": None,
                        "lng": None,
                        "geoPrecision": "unknown",
                        "geoMethod": "channel monitoring",
                        "confidenceScore": 0.78,
                        "severity": "Medium",
                        "severityScore": 0.78,
                        "duplicateClusterId": None,
                        "verificationState": "Open source",
                        "engagement": 0,
                        "summary": text[:120],
                    })
            except Exception as exc:
                if diagnostics is not None:
                    diagnostics[f"Telegram:{channel}"] = {"status": "error", "message": str(exc)}

        _diagnose(diagnostics, "ok", f"Checked {len(Config.TELEGRAM_CHANNELS)} channel(s), matched {len(items)} item(s).")
        return items
    except Exception as exc:
        _diagnose(diagnostics, "error", str(exc))
        return []
    finally:
        client.disconnect()