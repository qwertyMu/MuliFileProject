from config import Config

def search_instagram(alert):
    # Credentials go in .env:
    # INSTAGRAM_ACCESS_TOKEN
    # optionally INSTAGRAM_APP_ID / INSTAGRAM_APP_SECRET
    if not Config.INSTAGRAM_ACCESS_TOKEN:
        return []
    return []