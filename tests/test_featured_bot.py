"""Offline tests for the independent homepage-featured bot."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import build_pages
import featured_bot
import featured_editor
import news_store
from content import get as content_get
from test_news_bot import NOW, good_draft


class FeaturedBotTests(unittest.TestCase):
    def test_publication_uses_its_own_registry_audit_image_and_lock(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            record = featured_bot.publish(good_draft(), root, NOW)

            self.assertTrue(record["featured"])
            self.assertEqual(record["bot_instance"], "featured-editorial")
            self.assertTrue((root / "data/featured_articles.json").exists())
            self.assertTrue((root / "data/featured_audit" / f"{record['slug']}.json").exists())
            self.assertTrue((root / "actu-boxe/assets/img/featured" / f"{record['slug']}.svg").exists())
            self.assertFalse((root / "data/news_articles.json").exists())
            self.assertFalse((root / "data/.featured-publish.lock").exists())

    def test_regular_bot_does_not_consume_featured_daily_quota(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "data").mkdir()
            regular = {
                "slug": "autre-article-regulier",
                "topic_key": "autre-sujet-regulier",
                "title": "Un autre article régulier",
                "published_at": NOW.isoformat(),
            }
            (root / "data/news_articles.json").write_text(
                json.dumps({"items": [regular]}), encoding="utf-8"
            )

            self.assertEqual(featured_bot.validate_featured_draft(good_draft(), root, NOW), [])

    def test_featured_quota_blocks_a_second_featured_article(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            featured_bot.publish(good_draft(), root, NOW)
            second = good_draft()
            second.update(
                slug="second-tournoi-fictif-de-test",
                topic_key="second-test-tournoi-fictif-2026",
                title="Un second tournoi fictif annonce son programme sportif",
            )

            with self.assertRaisesRegex(ValueError, "un article par jour"):
                featured_bot.publish(second, root, NOW)

            self.assertEqual(len(featured_bot.registry_items(root)), 1)

    def test_duplicate_from_regular_bot_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "data").mkdir()
            draft = good_draft()
            (root / "data/news_articles.json").write_text(
                json.dumps({"items": [{"slug": draft["slug"]}]}), encoding="utf-8"
            )

            errors = featured_bot.validate_featured_draft(draft, root, NOW)

            self.assertTrue(any("déjà publié" in error.lower() for error in errors))

    def test_news_store_combines_both_public_registries(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "data").mkdir()
            (root / "data/news_articles.json").write_text(
                json.dumps({"items": [{"slug": "regular"}]}), encoding="utf-8"
            )
            (root / "data/featured_articles.json").write_text(
                json.dumps({"items": [{"slug": "featured", "featured": True}]}), encoding="utf-8"
            )

            self.assertEqual(
                [article["slug"] for article in news_store.news_articles(root)],
                ["regular", "featured"],
            )

    def test_homepage_promotes_the_newest_featured_article(self):
        fallback = content_get("championnats-d-europe-2026-la-selection-francaise-pour-sofia")
        featured = deepcopy(fallback)
        featured.update(
            slug="article-test-a-la-une",
            title="Article test placé à la une",
            featured=True,
            date="21 septembre 2026",
            date_iso="2026-09-21",
            image="/assets/img/featured/article-test-a-la-une.svg",
            image_alt="Illustration de test à la une",
        )
        with (
            patch.object(build_pages, "all_articles", return_value=[featured, fallback]),
            patch.object(build_pages, "get", return_value=fallback),
            patch.object(build_pages, "by_tag", return_value=[]),
        ):
            html = build_pages.home()

        self.assertIn("À la une ·", html)
        self.assertLess(html.index(featured["title"]), html.index(fallback["title"]))
        self.assertIn(featured["image"], html)

    def test_homepage_uses_latest_articles_before_first_featured_publication(self):
        articles = []
        for index, slug in enumerate(("nouveau-un", "nouveau-deux", "nouveau-trois", "nouveau-quatre", "nouveau-cinq")):
            article = deepcopy(content_get("championnats-d-europe-2026-la-selection-francaise-pour-sofia"))
            article.update(
                slug=slug,
                title=f"Nouvel article {index + 1}",
                image=f"/assets/img/news/{slug}.svg",
                image_alt=f"Illustration {index + 1}",
                date_iso=f"2026-09-{22 - index:02d}",
            )
            articles.append(article)
        fallback = content_get("championnats-d-europe-2026-la-selection-francaise-pour-sofia")
        with (
            patch.object(build_pages, "all_articles", return_value=articles),
            patch.object(build_pages, "get", return_value=fallback),
            patch.object(build_pages, "by_tag", return_value=[]),
        ):
            html = build_pages.home()

        self.assertIn("À la une ·", html)
        for article in articles:
            self.assertIn(article["title"], html)
            self.assertIn(article["image"], html)
        self.assertNotIn(fallback["title"], html)


class FeaturedEditorTests(unittest.TestCase):
    def test_research_and_json_writing_use_separate_supported_calls(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "data").mkdir()
            (root / "data/featured_candidates.json").write_text('{"items": []}', encoding="utf-8")
            research_response = SimpleNamespace(
                output_text="Rapport documenté",
                model_dump=lambda: {"output": [{"content": [{"annotations": [
                    {"url": "https://example.org/source", "title": "Source"}
                ]}]}]},
            )
            writing_response = SimpleNamespace(choices=[SimpleNamespace(
                message=SimpleNamespace(
                    content='{"action":"skip","reason":"preuves insuffisantes","draft":null}'
                )
            )])
            responses = unittest.mock.Mock()
            responses.create.return_value = research_response
            completions = unittest.mock.Mock()
            completions.create.return_value = writing_response
            client = SimpleNamespace(
                responses=responses,
                chat=SimpleNamespace(completions=completions),
            )
            now = datetime(2026, 9, 22, 8, tzinfo=timezone.utc)

            dossier = featured_editor.research(client, root, now)
            proposal = featured_editor.propose(client, root, now, dossier)

            self.assertIn("https://example.org/source", dossier)
            self.assertEqual(proposal["action"], "skip")
            research_call = responses.create.call_args
            writing_call = completions.create.call_args
            self.assertEqual(research_call.kwargs["tool_choice"], "required")
            self.assertEqual(writing_call.kwargs["response_format"], {"type": "json_object"})
            self.assertIn("messages", writing_call.kwargs)
            self.assertNotIn("tools", writing_call.kwargs)

    def test_local_env_only_loads_featured_variables_without_overriding_ci(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / ".env.featured").write_text(
                "GROQ_FEATURED_API_KEY=local-test-value\n"
                "GROQ_FEATURED_WRITING_MODEL=test-model\n"
                "UNRELATED_SECRET=must-not-load\n",
                encoding="utf-8",
            )
            with patch.dict(
                os.environ,
                {"GROQ_FEATURED_API_KEY": "ci-test-value"},
                clear=True,
            ):
                featured_editor.load_local_env(root)
                self.assertEqual(os.environ["GROQ_FEATURED_API_KEY"], "ci-test-value")
                self.assertEqual(os.environ["GROQ_FEATURED_WRITING_MODEL"], "test-model")
                self.assertNotIn("UNRELATED_SECRET", os.environ)

    def test_featured_quota_stops_before_creating_api_client(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "data").mkdir()
            (root / "data/featured_articles.json").write_text(
                json.dumps({"items": [{"published_at": "2026-09-20T06:00:00+00:00"}]}),
                encoding="utf-8",
            )
            with patch.object(featured_editor, "OpenAI") as client:
                result = featured_editor.run(
                    root, datetime(2026, 9, 20, 12, tzinfo=timezone.utc)
                )

            self.assertEqual(result, 0)
            client.assert_not_called()


if __name__ == "__main__":
    unittest.main()
