from config import Config

def search_x(alert):
    # Credentials go in .env:
    # X_BEARER_TOKEN
    # or X_CLIENT_ID / X_CLIENT_SECRET
    if not (Config.X_BEARER_TOKEN or (Config.X_CLIENT_ID and Config.X_CLIENT_SECRET)):
        return []
    return []