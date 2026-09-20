"""Safety and layout contracts for original editorial illustrations."""

from pathlib import Path
import re
import tempfile
import unittest
import xml.etree.ElementTree as ET

from news_images import render_news_image


SVG = "{http://www.w3.org/2000/svg}"


class NewsImageTests(unittest.TestCase):
    def render(self, **overrides):
        article = {
            "slug": "exemple-boxe",
            "title": "Duel de boxe à Toulouse",
            "image_brief": {
                "kind": "fight", "kicker": "À L’AFFICHE",
                "headline": "Le prochain rendez-vous de la boxe",
                "facts": ["Toulouse", "Samedi 19 septembre", "Super-légers"],
            },
        }
        article.update(overrides)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "nested" / "image.svg"
            render_news_image(article, path)
            source = path.read_text(encoding="utf-8")
        return source, ET.fromstring(source)

    def test_markup_cannot_create_svg_elements_or_urls(self):
        malicious = '<script>alert("x")</script> & <image href="evil"/>\x00\u202e\uffff'
        source, root = self.render(title=malicious, image_brief={
            "headline": malicious, "kicker": malicious, "facts": [malicious],
        })
        self.assertNotIn("<script>", source)
        self.assertNotIn("\x00", source)
        self.assertNotIn("\u202e", source)
        self.assertNotIn("\uffff", source)
        self.assertIn("&lt;script&gt;", source)
        self.assertEqual(root.find(f"{SVG}title").text, malicious[:-3])
        self.assertFalse(root.findall(f".//{SVG}script"))
        self.assertFalse(root.findall(f".//{SVG}image"))

    def test_long_text_stays_within_explicit_line_and_width_limits(self):
        _, root = self.render(image_brief={
            "headline": "W" * 900,
            "kicker": "Un titre très long " * 50,
            "facts": ["Information détaillée " * 100] * 6,
        })
        title = root.find(f'.//{SVG}text[@data-role="headline"]')
        lines = title.findall(f"{SVG}tspan")
        self.assertEqual(len(lines), 3)
        self.assertTrue(lines[-1].text.endswith("…"))
        self.assertTrue(all(float(line.attrib["textLength"]) <= 626 for line in lines))
        facts = root.findall(f'.//{SVG}text[@data-role="fact"]')
        self.assertEqual(len(facts), 3)
        for fact in facts:
            self.assertLessEqual(len(fact), 2)
            for span in fact:
                self.assertLessEqual(float(span.attrib["textLength"]), 595)
                self.assertLess(float(span.attrib["y"]), 588)

    def test_no_external_resources_for_any_topic_kind(self):
        variants = []
        for kind in ("fight", "results", "championship", "club"):
            source, root = self.render(image_brief={"kind": kind, "facts": []})
            variants.append(source)
            self.assertEqual(root.attrib["viewBox"], "0 0 1200 675")
            self.assertEqual(root.attrib["width"], "1200")
            self.assertEqual(root.attrib["height"], "675")
            self.assertIn("Illustration Actu Boxe", source)
            for node in root.iter():
                self.assertNotIn(node.tag, {f"{SVG}a", f"{SVG}image", f"{SVG}script"})
                for key, value in node.attrib.items():
                    self.assertFalse(key.endswith("href"))
                    self.assertFalse(value.startswith(("http:", "https:", "data:")))
            self.assertTrue(all(ref.startswith("#") for ref in re.findall(r"url\(([^)]+)\)", source)))
        self.assertEqual(len(set(variants)), 4)

    def test_render_is_deterministic_and_missing_brief_invents_no_facts(self):
        first, _ = self.render()
        second, _ = self.render()
        self.assertEqual(first, second)
        _, root = self.render(image_brief=None)
        self.assertEqual(len(root.findall(f'.//{SVG}text[@data-role="fact"]')), 0)
        title = root.find(f'.//{SVG}text[@data-role="headline"]')
        self.assertEqual(" ".join(span.text for span in title), "Duel de boxe à Toulouse")

    def test_rejects_malformed_brief_instead_of_treating_string_as_facts(self):
        with self.assertRaises(ValueError):
            self.render(image_brief="not an object")
        with self.assertRaises(ValueError):
            self.render(image_brief={"facts": "not a list"})


if __name__ == "__main__":
    unittest.main()
