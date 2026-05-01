import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
load_dotenv(".dev", override=False)

BASE_DIR = Path(__file__).resolve().parent

def csv_env(name, default=""):
    return [item.strip() for item in os.getenv(name, default).split(",") if item.strip()]

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret")
    DATABASE_PATH = os.getenv("DATABASE_PATH", "signal_atlas.db")
    FEEDS_PATH = os.getenv("FEEDS_PATH", str(BASE_DIR / "connectors" / "cConfig" / "feeds.json"))

    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_API_ID = os.getenv("TELEGRAM_API_ID", "")
    TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH", "")
    TELEGRAM_PHONE = os.getenv("TELEGRAM_PHONE", "")
    TELEGRAM_SESSION = os.getenv("TELEGRAM_SESSION", str(BASE_DIR / "telegram.session"))
    TELEGRAM_CHANNELS = csv_env("TELEGRAM_CHANNELS")
    TELEGRAM_LIMIT = int(os.getenv("TELEGRAM_LIMIT", "100"))

    X_BEARER_TOKEN = os.getenv("X_BEARER_TOKEN", "")
    X_CLIENT_ID = os.getenv("X_CLIENT_ID", "")
    X_CLIENT_SECRET = os.getenv("X_CLIENT_SECRET", "")

    INSTAGRAM_ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN", "")
    INSTAGRAM_APP_ID = os.getenv("INSTAGRAM_APP_ID", "")
    INSTAGRAM_APP_SECRET = os.getenv("INSTAGRAM_APP_SECRET", "")

    TRANSLATION_API_KEY = os.getenv("TRANSLATION_API_KEY", "")
    TRANSLATION_PROVIDER = os.getenv("TRANSLATION_PROVIDER", "disabled")
    TRANSLATION_URL = os.getenv("TRANSLATION_URL", "https://libretranslate.de/translate")

def connector_status():
    telegram_user_ready = bool(Config.TELEGRAM_API_ID and Config.TELEGRAM_API_HASH and Config.TELEGRAM_CHANNELS)
    return {
        "telegram": {
            "enabled": bool(Config.TELEGRAM_BOT_TOKEN or telegram_user_ready),
            "mode": "user_client" if telegram_user_ready else "bot_or_api",
            "configuredChannels": len(Config.TELEGRAM_CHANNELS)
        },
        "x": {
            "enabled": bool(Config.X_BEARER_TOKEN or (Config.X_CLIENT_ID and Config.X_CLIENT_SECRET)),
            "mode": "official_api"
        },
        "instagram": {
            "enabled": bool(Config.INSTAGRAM_ACCESS_TOKEN),
            "mode": "official_api"
        },
        "websites": {
            "enabled": True,
            "mode": "rss_and_public_feeds"
        },
        "translation": {
            "enabled": Config.TRANSLATION_PROVIDER not in ("", "disabled", "none"),
            "mode": Config.TRANSLATION_PROVIDER
        }
    }