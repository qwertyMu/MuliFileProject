from config import Config

def search_telegram(alert):
    # Credentials go in .env:
    # TELEGRAM_BOT_TOKEN
    # or TELEGRAM_API_ID / TELEGRAM_API_HASH / TELEGRAM_PHONE
    if not (Config.TELEGRAM_BOT_TOKEN or (Config.TELEGRAM_API_ID and Config.TELEGRAM_API_HASH)):
        return []
    return []