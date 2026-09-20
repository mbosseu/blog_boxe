"""Read only the approved public article registry; never expose audit source URLs."""
import json
from pathlib import Path


def news_articles() -> list[dict]:
    path = Path(__file__).resolve().parent / 'data/news_articles.json'
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding='utf-8'))['items']
