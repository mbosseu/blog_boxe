"""Offline parser and bounded-download tests for boxing-news discovery."""
from datetime import datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path
import sys
import unittest
from unittest.mock import MagicMock, patch
from xml.etree import ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import news_discovery as discovery


RSS = b'''<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><title>Test feed</title><item>
<title>Boxing &amp; results</title>
<link>https://boxing.example/results#recap</link>
<pubDate>Sun, 20 Sep 2026 10:00:00 +0200</pubDate>
</item></channel></rss>'''

ATOM = b'''<feed xmlns="http://www.w3.org/2005/Atom"><title>Test feed</title>
<entry><title>Boxing announcement</title>
<link rel="self" href="https://boxing.example/api/entry"/>
<link rel="alternate" href="https://boxing.example/news"/>
<published>2026-09-20T09:00:00Z</published>
<updated>2026-09-20T10:00:00Z</updated>
</entry></feed>'''


class DateTests(unittest.TestCase):
    def test_rfc_date_preserves_instant_and_offset(self):
        value = discovery.parse_pubdate("Sun, 20 Sep 2026 10:00:00 +0200")
        self.assertEqual(value.astimezone(timezone.utc), datetime(2026, 9, 20, 8, tzinfo=timezone.utc))
        self.assertEqual(value.utcoffset(), timedelta(hours=2))

    def test_iso_dates_accept_utc_and_numeric_offsets(self):
        for value in ("2026-09-20T08:00:00Z", "2026-09-20T10:00:00+02:00"):
            with self.subTest(value=value):
                self.assertEqual(discovery.parse_pubdate(value), datetime(2026, 9, 20, 8, tzinfo=timezone.utc))

    def test_naive_dates_receive_utc_timezone(self):
        for value in ("2026-09-20T08:00:00", "Sun, 20 Sep 2026 08:00:00"):
            with self.subTest(value=value):
                self.assertEqual(discovery.parse_pubdate(value), datetime(2026, 9, 20, 8, tzinfo=timezone.utc))

    def test_missing_invalid_and_nontext_dates_are_ignored(self):
        for value in (None, "", "not a date", "2026-13-55", 42, {"date": "unknown"}):
            with self.subTest(value=value):
                self.assertIsNone(discovery.parse_pubdate(value))


class FeedTests(unittest.TestCase):
    def test_rss_extracts_title_date_and_url_without_fragment(self):
        self.assertEqual(discovery.parse_feed(RSS), [{"title": "Boxing & results", "url": "https://boxing.example/results", "pubDate": "Sun, 20 Sep 2026 10:00:00 +0200"}])

    def test_atom_uses_alternate_link_and_original_publication_date(self):
        self.assertEqual(discovery.parse_feed(ATOM), [{"title": "Boxing announcement", "url": "https://boxing.example/news", "pubDate": "2026-09-20T09:00:00Z"}])

    def test_atom_accepts_default_alternate_and_updated_fallback(self):
        xml = b'<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Boxing update</title><link href="https://boxing.example/update"/><updated>2026-09-20T08:00:00Z</updated></entry></feed>'
        self.assertEqual(discovery.parse_feed(xml)[0]["pubDate"], "2026-09-20T08:00:00Z")

    def test_non_https_and_incomplete_entries_are_skipped(self):
        xml = b'<rss><channel><item><title>No link</title></item><item><title>Unsafe link</title><link>http://boxing.example/</link></item><item><link>https://boxing.example/</link></item></channel></rss>'
        self.assertEqual(discovery.parse_feed(xml), [])

    def test_empty_valid_feeds_are_accepted(self):
        for xml in (b'<rss><channel/></rss>', b'<feed xmlns="http://www.w3.org/2005/Atom"/>'):
            with self.subTest(xml=xml):
                self.assertEqual(discovery.parse_feed(xml), [])

    def test_html_or_unrecognized_xml_does_not_count_as_successful_empty_feed(self):
        for xml in (b'<html><body>Service temporarily unavailable</body></html>', b'<error>Request blocked</error>'):
            with self.subTest(xml=xml), self.assertRaises(ValueError):
                discovery.parse_feed(xml)

    def test_external_declarations_are_rejected(self):
        for xml in (b'<!DOCTYPE rss SYSTEM "https://remote.example/entity"><rss/>', b'<!doctype rss><rss/>', b'<!ENTITY unsafe "test"><rss/>'):
            with self.subTest(xml=xml), self.assertRaises(ValueError):
                discovery.parse_feed(xml)

    def test_invalid_xml_is_rejected(self):
        with self.assertRaises(ET.ParseError):
            discovery.parse_feed(b'<rss><channel>')

    def test_feed_entry_limit_is_bounded(self):
        items = ''.join(f'<item><title>Boxing news {index}</title><link>https://boxing.example/{index}</link></item>' for index in range(130))
        parsed = discovery.parse_feed(f'<rss><channel>{items}</channel></rss>'.encode())
        self.assertEqual(len(parsed), 100)

    def test_non_boxing_and_betting_topics_are_filtered(self):
        for title in ("Une affiche UFC", "Championnat de MMA", "Résultat kickboxing", "Calendrier Muay Thaï", "Pronostic du combat", "Un décès dans la boxe"):
            with self.subTest(title=title):
                self.assertTrue(discovery.skip_item(title))
        self.assertFalse(discovery.skip_item("Boxe anglaise : une victoire au championnat de France"))


class DownloadTests(unittest.TestCase):
    def test_download_uses_timeout_and_identified_user_agent(self):
        with patch.object(discovery, "urlopen", return_value=BytesIO(RSS)) as opening:
            result = discovery.load_rss("https://boxing.example/feed")
        self.assertEqual(len(result), 1)
        request = opening.call_args.args[0]
        self.assertEqual(request.full_url, "https://boxing.example/feed")
        self.assertIn("ActuBoxeBot", request.get_header("User-agent"))
        self.assertEqual(opening.call_args.kwargs["timeout"], 20)

    def test_oversized_download_is_rejected_before_parsing(self):
        response = MagicMock()
        response.__enter__.return_value = response
        response.read.return_value = b"x" * 2_000_001
        with patch.object(discovery, "urlopen", return_value=response), patch.object(discovery, "parse_feed") as parse:
            with self.assertRaisesRegex(ValueError, "volumineux"):
                discovery.load_rss("https://boxing.example/feed")
            response.read.assert_called_once_with(2_000_001)
            parse.assert_not_called()


if __name__ == "__main__":
    unittest.main()
