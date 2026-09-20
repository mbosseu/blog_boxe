"""Offline regression tests for the editorial publication gate.

All articles and sources below are synthetic fixtures. Publishing only occurs in
temporary directories; discovery is replaced with in-memory RSS responses.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from types import ModuleType
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import news_bot as bot


NOW = datetime(2026, 9, 20, 12, tzinfo=timezone.utc)


def good_draft() -> dict:
    draft = {
        "slug": "tournoi-fictif-de-test-annonce-officielle",
        "topic_key": "test-tournoi-fictif-annonce-2026",
        "title": "Un tournoi fictif de boxe annonce son programme sportif",
        "excerpt": "Ce dossier entièrement fictif sert uniquement à vérifier les règles de publication et ne doit jamais être mis en ligne.",
        "lead": "Le tournoi fictif utilisé dans ces tests présente son programme. Deux publications indépendantes confirment cette annonce de manière concordante, dont le communiqué de l’organisateur. Ces informations constituent uniquement des données de test pour vérifier le fonctionnement de la validation.",
        "tags": ["actualites", "galas"],
        "sources": [
            {
                "id": "official", "url": "https://organisateur.example/annonce",
                "publisher": "Organisateur fictif", "publisher_group": "Organisateur fictif",
                "title": "Annonce officielle du tournoi entièrement fictif", "primary": True,
                "published_at": (NOW - timedelta(hours=18)).isoformat(),
                "retrieved_at": (NOW - timedelta(hours=1)).isoformat(),
                "evidence_summary": "Le programme fictif est confirmé par un communiqué de l’organisateur utilisé uniquement comme fixture de test.",
            },
            {
                "id": "press", "url": "https://redaction.example/reportage",
                "publisher": "Rédaction indépendante fictive", "publisher_group": "Presse fictive",
                "title": "Une rédaction indépendante confirme le programme fictif", "primary": False,
                "published_at": (NOW - timedelta(hours=12)).isoformat(),
                "retrieved_at": (NOW - timedelta(minutes=30)).isoformat(),
                "evidence_summary": "Le compte rendu fictif confirme le programme annoncé en citant une vérification menée auprès de l’organisateur.",
            },
        ],
        "claims": [{"id": "announcement", "text": "Le tournoi fictif annonce officiellement son programme sportif.", "source_ids": ["official", "press"]}],
        "central_claim_id": "announcement", "lead_claim_ids": ["announcement"],
        "sections": [
            {"heading": heading, "paragraphs": [{"text": "Ce texte de test décrit un programme fictif et ne fournit aucune information destinée aux lecteurs du site. Les données sont inventées pour vérifier les contraintes techniques avant toute véritable publication journalistique.", "claim_ids": ["announcement"]}]}
            for heading in ("Une annonce officiellement confirmée", "Le contexte de cette programmation", "Les informations restant à suivre")
        ],
        "review": {**{key: True for key in bot.CHECKS}, "notes": "Dossier fictif réservé aux tests : les sources et les faits servent exclusivement à vérifier les règles automatiques."},
        "image_brief": {"kind": "championship", "headline": "Tournoi fictif : le programme", "kicker": "DONNÉES DE TEST", "facts": ["Annonce du programme", "Sources recoupées"], "claim_ids": ["announcement"]},
    }
    # Keep the fixture inside the stricter two-source limit (350–400 words).
    prose = [draft["title"], draft["excerpt"], draft["lead"]]
    for section in draft["sections"]:
        prose.extend([section["heading"], section["paragraphs"][0]["text"]])
    missing = 375 - len(bot.words(" ".join(prose)))
    padding = ("Ce contexte fictif permet de contrôler la cohérence du dossier sportif ".split() * 50)[:missing]
    for index, word in enumerate(padding):
        draft["sections"][index % 3]["paragraphs"][0]["text"] += " " + word
    return draft


class ValidationTests(unittest.TestCase):
    def assertRejected(self, draft, *, published=None, existing=None, now=NOW, message=None):
        errors = bot.validate_draft(draft, published or [], existing or [], now)
        self.assertIsInstance(errors, list)
        self.assertTrue(errors, "Invalid editorial dossier was accepted")
        if message:
            self.assertIn(message, " ".join(errors))
        return errors

    def test_complete_independent_recent_dossier_is_accepted(self):
        self.assertEqual(bot.validate_draft(good_draft(), [], [], NOW), [])

    def test_two_sources_are_required(self):
        draft = good_draft()
        draft["sources"].pop()
        self.assertRejected(draft)

    def test_two_domains_are_required_even_with_different_publishers(self):
        draft = good_draft()
        draft["sources"][1]["url"] = "https://www.organisateur.example/autre"
        self.assertRejected(draft, message="domaines")

    def test_two_independent_publishers_are_required(self):
        draft = good_draft()
        draft["sources"][1]["publisher_group"] = "  ORGANISATEUR FICTIF  "
        self.assertRejected(draft, message="éditeurs")

    def test_primary_source_is_required(self):
        draft = good_draft()
        draft["sources"][0]["primary"] = False
        self.assertRejected(draft, message="primaire")

    def test_central_claim_must_be_corroborated(self):
        draft = good_draft()
        draft["claims"][0]["source_ids"] = ["official"]
        self.assertRejected(draft, message="central")

    def test_central_claim_requires_independent_domains_not_just_global_sources(self):
        draft = good_draft()
        third = deepcopy(draft["sources"][1])
        third.update(id="other", url="https://troisieme.example/contexte", publisher_group="Autre rédaction")
        draft["sources"].append(third)
        draft["sources"][1]["url"] = "https://organisateur.example/seconde-page"
        self.assertRejected(draft, message="central")

    def test_recent_source_is_required(self):
        draft = good_draft()
        for source in draft["sources"]:
            source["published_at"] = (NOW - timedelta(days=8)).isoformat()
        self.assertRejected(draft, message="sept")

    def test_recent_context_does_not_make_an_old_central_claim_news(self):
        draft = good_draft()
        context = deepcopy(draft["sources"][1])
        context.update(id="context", url="https://contexte.example/actualite", publisher_group="Contexte indépendant")
        for source in draft["sources"]:
            source["published_at"] = (NOW - timedelta(days=8)).isoformat()
        draft["sources"].append(context)
        draft["claims"].append({"id": "context_fact", "text": "Une information récente apporte seulement du contexte au dossier.", "source_ids": ["context"]})
        self.assertRejected(draft, message="central")

    def test_source_publication_cannot_be_in_the_future(self):
        draft = good_draft()
        draft["sources"][0]["published_at"] = (NOW + timedelta(minutes=1)).isoformat()
        self.assertRejected(draft, message="future")

    def test_sources_must_have_been_read_within_24_hours(self):
        draft = good_draft()
        draft["sources"][0]["retrieved_at"] = (NOW - timedelta(hours=25)).isoformat()
        self.assertRejected(draft, message="24")

    def test_thin_evidence_is_rejected(self):
        draft = good_draft()
        draft["sources"][0]["evidence_summary"] = "Vu dans un flux."
        self.assertRejected(draft, message="evidence_summary")

    def test_public_text_cannot_contain_html_or_links(self):
        for payload in ('<a href="https://club.example">Club</a>', "https://club.example", "www.club.example", "[Club](//club.example)"):
            with self.subTest(payload=payload):
                draft = good_draft()
                draft["sections"][0]["paragraphs"][0]["text"] += " " + payload
                self.assertRejected(draft, message="URL")

    def test_untraceable_facts_and_missing_review_are_rejected(self):
        draft = good_draft()
        draft["sections"][0]["paragraphs"][0]["claim_ids"] = ["unknown"]
        self.assertRejected(draft)
        draft = good_draft()
        draft["review"]["facts_checked"] = False
        self.assertRejected(draft, message="Relecture")

    def test_duplicate_topic_slug_and_title_are_rejected(self):
        draft = good_draft()
        for old in ({"topic_key": draft["topic_key"]}, {"slug": draft["slug"]}, {"title": draft["title"] + " !"}):
            with self.subTest(old=old):
                self.assertRejected(draft, existing=[old])

    def test_daily_limit_uses_paris_day_across_utc_midnight(self):
        # 23:30 UTC and 10:00 UTC fall on the same calendar day in Paris.
        published = [{"published_at": "2026-09-19T23:30:00+00:00"}]
        self.assertRejected(good_draft(), published=published, message="un article par jour")

    def test_previous_paris_day_does_not_consume_todays_quota(self):
        published = [{"published_at": "2026-09-19T21:30:00+00:00"}]
        self.assertEqual(bot.validate_draft(good_draft(), published, [], NOW), [])

    def test_daily_limit_handles_winter_offset(self):
        winter = datetime(2026, 1, 10, 23, 30, tzinfo=timezone.utc)
        draft = good_draft()
        for source in draft["sources"]:
            source["published_at"] = (winter - timedelta(hours=1)).isoformat()
            source["retrieved_at"] = (winter - timedelta(minutes=5)).isoformat()
        self.assertRejected(draft, published=[{"published_at": "2026-01-11T00:10:00+01:00"}], now=winter, message="un article par jour")

    def test_bad_publication_history_fails_closed(self):
        for old in ({}, {"published_at": "yesterday"}, {"published_at": None}):
            with self.subTest(old=old):
                self.assertRejected(good_draft(), published=[old])

    def test_image_brief_requires_supported_kind_facts_and_traceability(self):
        for field, value in (("kind", "unrelated"), ("facts", ["One fact"]), ("claim_ids", ["unknown"]), ("headline", "https://club.example")):
            with self.subTest(field=field):
                draft = good_draft()
                draft["image_brief"][field] = value
                self.assertRejected(draft)

    def test_article_length_is_limited_by_available_evidence(self):
        draft = good_draft()
        for section in draft["sections"]:
            section["paragraphs"][0]["text"] += " information" * 20
        self.assertRejected(draft, message="Longueur")

    def test_malformed_nested_structures_fail_closed_without_crashing(self):
        edits = [
            ("tags", [{}]), ("sections", [None, None, None]),
            ("sources", [{"id": "broken", "url": 42}]),
            ("lead_claim_ids", 4), ("claims", [{"id": "broken", "text": "Une affirmation de test suffisamment longue.", "source_ids": [{}]}]),
        ]
        for key, value in edits:
            with self.subTest(key=key):
                draft = good_draft()
                draft[key] = value
                self.assertRejected(draft)


class PublicationTests(unittest.TestCase):
    def test_publish_creates_one_record_local_image_and_private_evidence(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            draft = good_draft()
            record = bot.publish_draft(draft, root, NOW)
            registry = json.loads((root / "data/news_articles.json").read_text(encoding="utf-8"))
            self.assertEqual(registry["items"], [json.loads(json.dumps(record))])
            self.assertTrue((root / "actu-boxe" / record["image"].lstrip("/")).is_file())
            audit = json.loads((root / "data/news_audit" / f"{draft['slug']}.json").read_text(encoding="utf-8"))
            self.assertEqual(audit["draft"]["sources"], draft["sources"])
            public = json.dumps(record, ensure_ascii=False)
            for source in draft["sources"]:
                self.assertNotIn(source["url"], public)
                self.assertIn(source["publisher"], public)
            self.assertNotIn("<a ", record["body"])
            self.assertFalse((root / "data/.news-publish.lock").exists())

    def test_source_urls_do_not_appear_in_rendered_public_html(self):
        from build_pages import article_page
        draft = good_draft()
        html = article_page(bot.make_public_article(draft, NOW))
        for source in draft["sources"]:
            self.assertNotIn(source["url"], html)
            self.assertIn(source["publisher"], html)

    def test_second_publication_same_paris_day_changes_nothing(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            bot.publish_draft(good_draft(), root, NOW)
            before = (root / "data/news_articles.json").read_bytes()
            draft = good_draft()
            draft.update(slug="nouveau-sujet-test-different", topic_key="autre-sujet-test-different", title="Une rencontre sportive expérimentale présente ses modalités")
            with self.assertRaises(ValueError):
                bot.publish_draft(draft, root, NOW + timedelta(hours=1))
            self.assertEqual((root / "data/news_articles.json").read_bytes(), before)
            self.assertFalse((root / "data/.news-publish.lock").exists())

    def test_existing_article_image_or_audit_is_never_overwritten(self):
        draft = good_draft()
        for relative in (f"actu-boxe/articles/{draft['slug']}/index.html", f"actu-boxe/assets/img/news/{draft['slug']}.svg", f"data/news_audit/{draft['slug']}.json"):
            with self.subTest(relative=relative), TemporaryDirectory() as directory:
                root = Path(directory)
                existing = root / relative
                existing.parent.mkdir(parents=True)
                existing.write_text("existing content", encoding="utf-8")
                with self.assertRaises(ValueError):
                    bot.publish_draft(draft, root, NOW)
                self.assertEqual(existing.read_text(encoding="utf-8"), "existing content")
                self.assertFalse((root / "data/news_articles.json").exists())
                self.assertFalse((root / "data/.news-publish.lock").exists())

    def test_validation_failure_releases_owned_lock(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            draft = good_draft()
            draft["review"] = {}
            with self.assertRaises(ValueError):
                bot.publish_draft(draft, root, NOW)
            self.assertFalse((root / "data/.news-publish.lock").exists())
            self.assertFalse((root / "data/news_articles.json").exists())

    def test_image_generation_failure_does_not_publish_and_releases_lock(self):
        with TemporaryDirectory() as directory, patch("news_images.render_news_image", side_effect=OSError("synthetic failure")):
            root = Path(directory)
            with self.assertRaises(OSError):
                bot.publish_draft(good_draft(), root, NOW)
            self.assertFalse((root / "data/.news-publish.lock").exists())
            self.assertFalse((root / "data/news_articles.json").exists())

    def test_existing_concurrent_lock_is_not_deleted(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            lock = root / "data/.news-publish.lock"
            lock.parent.mkdir()
            lock.write_text("other publisher", encoding="utf-8")
            with self.assertRaises((ValueError, FileExistsError)):
                bot.publish_draft(good_draft(), root, NOW)
            self.assertEqual(lock.read_text(encoding="utf-8"), "other publisher")
            self.assertFalse((root / "data/news_articles.json").exists())


class CandidateTests(unittest.TestCase):
    def fake_discovery(self, load):
        module = ModuleType("news_discovery")
        module.VU_FEEDS = [("Presse test", "https://redaction.example/feed")]
        module.load_rss = load
        module.parse_pubdate = lambda value: bot.parse_time(value) if value else None
        module.skip_item = lambda title: "MMA" in title
        return module

    def test_discovery_filters_old_future_irrelevant_and_duplicate_items(self):
        current = datetime.now(timezone.utc)
        item = {"title": "Un programme de boxe anglaise confirmé", "url": "https://organisateur.example/annonce", "pubDate": (current - timedelta(hours=1)).isoformat()}
        entries = [item, {**item, "url": "https://old.example/", "pubDate": (current - timedelta(days=8)).isoformat()}, {**item, "url": "https://future.example/", "pubDate": (current + timedelta(days=1)).isoformat()}, {**item, "url": "https://mma.example/", "title": "Une rencontre MMA"}]
        with TemporaryDirectory() as directory, patch.dict(sys.modules, {"news_discovery": self.fake_discovery(lambda _: entries)}):
            root = Path(directory)
            result = bot.collect_candidates(root)
            self.assertEqual(len(result["items"]), 1)
            self.assertEqual(result["items"][0]["url"], item["url"])
            self.assertEqual(result["unavailable_feeds"], [])
            self.assertFalse((root / "data/news_articles.json").exists())

    def test_all_feed_failures_preserve_previous_discovery(self):
        def fail(_):
            raise OSError("offline test")
        with TemporaryDirectory() as directory, patch.dict(sys.modules, {"news_discovery": self.fake_discovery(fail)}):
            root = Path(directory)
            cache = root / "data/news_candidates.json"
            cache.parent.mkdir()
            cache.write_text('{"items": [{"title": "previous result"}]}', encoding="utf-8")
            before = cache.read_bytes()
            with self.assertRaises(RuntimeError):
                bot.collect_candidates(root)
            self.assertEqual(cache.read_bytes(), before)

    def test_candidates_are_ordered_by_actual_time_not_timezone_text(self):
        current = datetime.now(timezone.utc)
        older = {"title": "Un ancien résultat confirmé", "url": "https://older.example/", "pubDate": (current - timedelta(hours=2)).astimezone(timezone(timedelta(hours=5))).isoformat()}
        newer = {"title": "Un résultat plus récent confirmé", "url": "https://newer.example/", "pubDate": (current - timedelta(hours=1)).isoformat()}
        with TemporaryDirectory() as directory, patch.dict(sys.modules, {"news_discovery": self.fake_discovery(lambda _: [older, newer])}):
            result = bot.collect_candidates(Path(directory))
            self.assertEqual([item["url"] for item in result["items"]], [newer["url"], older["url"]])

    def test_partial_failure_keeps_successful_candidates_and_reports_the_feed(self):
        item = {"title": "Un programme de boxe anglaise confirmé", "url": "https://organisateur.example/annonce", "pubDate": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()}
        def load(url):
            if "redaction.example" in url:
                raise OSError("offline test")
            return [item]
        with TemporaryDirectory() as directory, patch.dict(sys.modules, {"news_discovery": self.fake_discovery(load)}):
            result = bot.collect_candidates(Path(directory))
            self.assertEqual(len(result["items"]), 1)
            self.assertEqual(result["unavailable_feeds"], [{"publisher": "Presse test", "error": "OSError"}])


if __name__ == "__main__":
    unittest.main()
