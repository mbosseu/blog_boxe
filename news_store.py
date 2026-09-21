"""Read approved public registries; never expose private audit source URLs."""
import json
from pathlib import Path


def _registry(name: str, root: Path | None = None) -> list[dict]:
    path = (root or Path(__file__).resolve().parent) / 'data' / name
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding='utf-8'))['items']


def regular_news_articles(root: Path | None = None) -> list[dict]:
    return _registry('news_articles.json', root)


def featured_news_articles(root: Path | None = None) -> list[dict]:
    return _registry('featured_articles.json', root)


def news_articles(root: Path | None = None) -> list[dict]:
    return regular_news_articles(root) + featured_news_articles(root)
