import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret")
    DATABASE_PATH = os.getenv("DATABASE_PATH", "signal_atlas.db")

    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_API_ID = os.getenv("TELEGRAM_API_ID", "")
    TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH", "")
    TELEGRAM_PHONE = os.getenv("TELEGRAM_PHONE", "")

    X_BEARER_TOKEN = os.getenv("X_BEARER_TOKEN", "")
    X_CLIENT_ID = os.getenv("X_CLIENT_ID", "")
    X_CLIENT_SECRET = os.getenv("X_CLIENT_SECRET", "")

    INSTAGRAM_ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN", "")
    INSTAGRAM_APP_ID = os.getenv("INSTAGRAM_APP_ID", "")
    INSTAGRAM_APP_SECRET = os.getenv("INSTAGRAM_APP_SECRET", "")

    TRANSLATION_API_KEY = os.getenv("TRANSLATION_API_KEY", "")
    TRANSLATION_PROVIDER = os.getenv("TRANSLATION_PROVIDER", "libretranslate")
    TRANSLATION_URL = os.getenv("TRANSLATION_URL", "https://libretranslate.de/translate")

def connector_status():
    return {
        "telegram": {
            "enabled": bool(Config.TELEGRAM_BOT_TOKEN or (Config.TELEGRAM_API_ID and Config.TELEGRAM_API_HASH)),
            "mode": "bot_or_api"
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
            "enabled": True,
            "mode": Config.TRANSLATION_PROVIDER
        }
    }