"""Render contract: the brief Artifact template is self-contained (no external/webfont deps) and wired.

Enforces the hard-won rendering lesson — the inline widget broke because of an icon webfont and external
deps; the Artifact card must never depend on anything the CSP would block or that could fail to load.
"""
import os
import re
import unittest

from _util import REPO

TEMPLATE = os.path.join(REPO, "skills", "team-brief", "assets", "brief-card.template.html")
RENDER_REF = os.path.join(REPO, "skills", "team-brief", "references", "render-artifact.md")
SKILL = os.path.join(REPO, "skills", "team-brief", "SKILL.md")
OUTPUT_STYLE = os.path.join(REPO, "skills", "team-brief", "references", "output-style.md")

# Patterns that would make the card depend on something external / fragile.
FORBIDDEN = [
    (r"<link\b", "external <link> (stylesheet/font) — inline it instead"),
    (r"<script\b[^>]*\bsrc=", "external <script src> — inline it instead"),
    (r"@import\b", "@import of an external stylesheet"),
    (r"fonts\.googleapis|fonts\.gstatic", "Google Fonts webfont URL"),
    (r"cdn\.|unpkg\.com|jsdelivr\.net|cdnjs", "CDN asset URL"),
    (r'class="ti\b|class="ti ', "Tabler icon webfont (the class that rendered as empty boxes)"),
    (r"@font-face[^}]*url\(\s*['\"]?https?:", "@font-face loading a remote font URL"),
]


class TestRenderContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = open(TEMPLATE, encoding="utf-8").read()

    def test_template_exists(self):
        self.assertTrue(os.path.isfile(TEMPLATE), "brief-card.template.html missing")

    def test_template_is_self_contained(self):
        # comments can't load resources — strip them so documentation prose doesn't trip the scan
        live = re.sub(r"<!--.*?-->", "", self.html, flags=re.DOTALL)
        for pat, why in FORBIDDEN:
            self.assertIsNone(re.search(pat, live, re.IGNORECASE),
                              f"brief-card.template.html must be self-contained: found {why}")

    def test_template_is_theme_aware(self):
        # must define tokens and honor both the media query and the data-theme override
        self.assertIn("prefers-color-scheme:dark", self.html.replace(" ", ""))
        self.assertIn('data-theme="dark"', self.html)
        self.assertIn('data-theme="light"', self.html)

    def test_template_has_the_card_contract(self):
        for needed in ("Top of mind", "FYI", "On your calendar", 'class="src"',
                       'class="chip open"', 'class="chip act"'):
            self.assertIn(needed, self.html, f"template missing card element: {needed!r}")

    def test_skill_and_output_style_point_to_the_artifact_renderer(self):
        self.assertTrue(os.path.isfile(RENDER_REF), "render-artifact.md missing")
        self.assertIn("render-artifact.md", open(SKILL, encoding="utf-8").read(),
                      "SKILL.md must reference the Artifact renderer")
        self.assertIn("render-artifact.md", open(OUTPUT_STYLE, encoding="utf-8").read(),
                      "output-style.md must mark itself the fallback and point to render-artifact.md")


if __name__ == "__main__":
    unittest.main()
