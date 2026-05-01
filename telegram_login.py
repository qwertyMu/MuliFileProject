from config import Config


def main():
    if not (Config.TELEGRAM_API_ID and Config.TELEGRAM_API_HASH):
        raise SystemExit("Set TELEGRAM_API_ID and TELEGRAM_API_HASH in .env or .dev first.")

    try:
        from telethon.sync import TelegramClient
    except ImportError as exc:
        raise SystemExit("Telethon is not installed. Run pip install -r requirements.txt.") from exc

    client = TelegramClient(
        Config.TELEGRAM_SESSION,
        int(Config.TELEGRAM_API_ID),
        Config.TELEGRAM_API_HASH,
    )

    with client:
        client.start(phone=Config.TELEGRAM_PHONE or None)
        me = client.get_me()
        username = getattr(me, "username", None) or getattr(me, "phone", None) or me.id
        print(f"Telegram session authorized for {username}.")
        print(f"Session file: {Config.TELEGRAM_SESSION}")


if __name__ == "__main__":
    main()
