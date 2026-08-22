from html.parser import HTMLParser
import json
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
CANONICAL = "https://pipeliner.github.io/hypothesisctl/"


class LandingParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.anchors = set()
        self.canonical = None
        self.external_resources = []
        self.forms = 0
        self.json_ld = []
        self.meta = {}
        self.scripts = []
        self.title_parts = []
        self._in_title = False
        self._json_ld_parts = None

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == "title":
            self._in_title = True
        elif tag == "meta":
            key = values.get("name") or values.get("property")
            if key:
                self.meta[key] = values.get("content")
        elif tag == "link":
            if values.get("rel") == "canonical":
                self.canonical = values.get("href")
            if values.get("rel") == "stylesheet":
                self.external_resources.append(values.get("href"))
        elif tag == "a":
            self.anchors.add(values.get("href"))
        elif tag in {"img", "iframe"}:
            self.external_resources.append(values.get("src"))
        elif tag == "form":
            self.forms += 1
        elif tag == "script":
            self.scripts.append(values)
            if values.get("src"):
                self.external_resources.append(values["src"])
            if values.get("type") == "application/ld+json" and "src" not in values:
                self._json_ld_parts = []

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        elif tag == "script" and self._json_ld_parts is not None:
            self.json_ld.append(json.loads("".join(self._json_ld_parts)))
            self._json_ld_parts = None

    def handle_data(self, data):
        if self._in_title:
            self.title_parts.append(data)
        if self._json_ld_parts is not None:
            self._json_ld_parts.append(data)


class DiscoverySiteTest(unittest.TestCase):
    def parsed_page(self):
        page = (ROOT / "docs/index.html").read_text(encoding="utf-8")
        parser = LandingParser()
        parser.feed(page)
        parser.close()
        return page, parser

    def test_landing_page_has_unique_machine_readable_identity(self):
        _, page = self.parsed_page()
        self.assertEqual("".join(page.title_parts).strip(), "hypothesisctl — fail-closed evidence gates")
        self.assertEqual(page.canonical, CANONICAL)
        self.assertIn("fail-closed", page.meta["description"].lower())
        self.assertEqual(page.meta["og:url"], CANONICAL)
        self.assertEqual(page.meta["og:type"], "website")
        self.assertEqual(len(page.json_ld), 1)
        software = page.json_ld[0]
        self.assertEqual(software["@type"], "SoftwareApplication")
        self.assertEqual(software["name"], "hypothesisctl")
        self.assertEqual(software["url"], CANONICAL)
        self.assertEqual(software["offers"]["price"], "0")

    def test_page_links_real_adoption_and_safety_artifacts(self):
        _, page = self.parsed_page()
        required = {
            "https://github.com/Pipeliner/hypothesisctl",
            "https://github.com/Pipeliner/hypothesisctl/releases/tag/v0.2.1",
            "https://github.com/Pipeliner/hypothesisctl/blob/main/examples/agent-completion.json",
            "https://github.com/Pipeliner/hypothesisctl/blob/main/SECURITY.md",
            "https://github.com/Pipeliner/hypothesisctl/blob/main/LICENSE",
        }
        self.assertTrue(required.issubset(page.anchors))

    def test_page_has_no_executable_or_remote_resource_ingress(self):
        text, page = self.parsed_page()
        self.assertEqual(page.external_resources, [])
        self.assertEqual(page.forms, 0)
        self.assertEqual(page.scripts, [{"type": "application/ld+json"}])
        lowered = text.lower()
        for forbidden in ("google-analytics", "gtag(", "segment.com", "hotjar", "cookie"):
            self.assertNotIn(forbidden, lowered)

    def test_public_action_guidance_uses_the_isolated_entrypoint_commit(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        page, _ = self.parsed_page()
        fixed = "413f5377325082381b740ebc652c301f21d6a1d4"
        vulnerable = "1722321620d8c297562bcf20ec1bd63057407df1"
        self.assertIn(fixed, readme)
        self.assertIn(fixed, page)
        self.assertNotIn(vulnerable, readme)
        self.assertNotIn(vulnerable, page)
        self.assertIn("isolated mode", page)

    def test_robots_and_sitemap_cover_exactly_the_canonical_page(self):
        robots = (ROOT / "docs/robots.txt").read_text(encoding="utf-8")
        self.assertEqual(
            robots,
            f"User-agent: *\nAllow: /\nSitemap: {CANONICAL}sitemap.xml\n",
        )
        root = ET.parse(ROOT / "docs/sitemap.xml").getroot()
        namespace = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        locations = [item.text for item in root.findall("sm:url/sm:loc", namespace)]
        self.assertEqual(locations, [CANONICAL])

    def test_discovery_contract_preserves_claim_boundaries(self):
        contract = (ROOT / "DISCOVERY.md").read_text(encoding="utf-8")
        for phrase in (
            "no JavaScript execution",
            "does not prove that evidence bytes",
            "not called adopted without traffic or star evidence",
            "repository-native branch source",
        ):
            self.assertIn(phrase, contract)


if __name__ == "__main__":
    unittest.main()
