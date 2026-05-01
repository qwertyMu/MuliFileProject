import requests
from config import Config

def translate_text(text, source="auto", target="en"):
    if not text:
        return text

    try:
        response = requests.post(
            Config.TRANSLATION_URL,
            json={
                "q": text,
                "source": source,
                "target": target,
                "format": "text"
            },
            timeout=8
        )
        if response.status_code == 200:
            data = response.json()
            return data.get("translatedText", text)
    except Exception as exc:
        print(f"[translation] error: {exc}")

    return text