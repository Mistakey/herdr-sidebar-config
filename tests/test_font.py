from __future__ import annotations

import tempfile
import tomllib
import unittest
from fractions import Fraction
from pathlib import Path

try:
    from fontTools.pens.boundsPen import BoundsPen
    from fontTools.ttLib import TTFont
except ImportError:  # Build-only checks run in the font virtual environment.
    TTFont = None


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_GLYPHS = [
    "claude",
    "codex",
    "opencode",
    "omp",
    "cline",
    "mastracode",
    "kimi",
    "kilo",
    "maki",
    "agy",
    "pi",
]
EXPECTED_CMAP = {0xE1A0 + offset: name for offset, name in enumerate(EXPECTED_GLYPHS)}


class FontSourceTests(unittest.TestCase):
    def test_codepoints_and_svg_sources_match(self) -> None:
        with (ROOT / "font" / "codepoints.toml").open("rb") as config_file:
            glyphs = tomllib.load(config_file)["glyphs"]
        svg_names = {path.stem for path in (ROOT / "assets" / "svg").glob("*.svg")}

        self.assertEqual(list(glyphs), EXPECTED_GLYPHS)
        self.assertEqual([int(value, 16) for value in glyphs.values()], list(EXPECTED_CMAP))
        self.assertEqual(set(glyphs), svg_names)


@unittest.skipIf(TTFont is None, "fontTools is a build-only dependency")
class FontTests(unittest.TestCase):
    def test_sidebar_pi_matches_peer_size_and_alignment(self):
        with TTFont(ROOT / "dist/HerdrSidebarLogos-Regular.ttf") as font:
            self.assertEqual(font.getBestCmap()[0xE1AA], "pi")
            pi = font["glyf"]["pi"]
            width, height = pi.xMax - pi.xMin, pi.yMax - pi.yMin
            center_y = (pi.yMin + pi.yMax) / 2
            self.assertEqual((width, height, center_y), (760, 760, 365))
            self.assertEqual(font["hmtx"].metrics["pi"], (600, pi.xMin))
            self.assertEqual((pi.xMin + pi.xMax) / 2, 300)
            glyphs = font.getGlyphSet()
            for name in ("claude", "codex"):
                with self.subTest(glyph=name):
                    # Measure the visible curves rather than off-curve control points.
                    pen = BoundsPen(glyphs)
                    glyphs[name].draw(pen)
                    left, bottom, right, top = pen.bounds
                    self.assertAlmostEqual(width, right - left, delta=1)
                    self.assertAlmostEqual(height, top - bottom, delta=1)
                    self.assertAlmostEqual(center_y, (bottom + top) / 2, delta=1)
                    self.assertEqual(font["hmtx"].metrics["pi"][0], font["hmtx"].metrics[name][0])

    def test_sidebar_pi_preserves_the_harness_pixel_outline(self):
        with (
            TTFont(ROOT / "dist/HerdrHarnessLogos-Regular.ttf") as harness,
            TTFont(ROOT / "dist/HerdrSidebarLogos-Regular.ttf") as sidebar,
        ):
            base, enlarged = harness["glyf"]["pi"], sidebar["glyf"]["pi"]
            self.assertEqual(base.xMax - base.xMin, 460)
            self.assertEqual(base.yMax - base.yMin, 460)
            self.assertEqual((base.yMin + base.yMax) / 2, 300)
            self.assertEqual(harness["hmtx"].metrics["pi"], (600, 0))

            def outline(font, glyph):
                coordinates, ends, flags = glyph.getCoordinates(font["glyf"])
                width, height = glyph.xMax - glyph.xMin, glyph.yMax - glyph.yMin
                normalized = [(Fraction(x - glyph.xMin, width), Fraction(y - glyph.yMin, height))
                              for x, y in coordinates]
                return normalized, list(ends), list(flags)

            self.assertEqual(outline(harness, base), outline(sidebar, enlarged))

    def test_sidebar_font_matches_sources(self):
        from tools.build_sidebar_font import build
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "sidebar.ttf"
            build(output)
            self.assertEqual(output.read_bytes(), (ROOT / "dist/HerdrSidebarLogos-Regular.ttf").read_bytes())
            font = TTFont(output)
            self.assertEqual(font.getBestCmap(), EXPECTED_CMAP)
            self.assertEqual(font["name"].getDebugName(1), "Herdr Sidebar Logos")
            for name in ("claude", "codex"):
                self.assertEqual(font["hmtx"].metrics[name][0], 600)
                self.assertGreater(font["glyf"][name].numberOfContours, 0)

    def test_committed_font_contract(self) -> None:
        font = TTFont(ROOT / "dist" / "HerdrHarnessLogos-Regular.ttf")
        self.assertTrue(
            {"head", "hhea", "maxp", "OS/2", "hmtx", "cmap", "glyf", "loca", "name", "post"}.issubset(
                font.keys()
            )
        )
        self.assertFalse({"SVG ", "COLR", "CPAL", "CBDT", "fvar"}.intersection(font.keys()))
        cmap = font.getBestCmap()
        self.assertEqual(cmap, EXPECTED_CMAP)
        self.assertEqual(font.getGlyphOrder(), [".notdef", *EXPECTED_GLYPHS])
        self.assertEqual(font["post"].isFixedPitch, 1)
        for name in cmap.values():
            self.assertEqual(font["hmtx"].metrics[name][0], 600)
            self.assertGreater(font["glyf"][name].numberOfContours, 0)

    def test_build_is_deterministic(self) -> None:
        from tools.build_font import build

        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "first.ttf"
            second = Path(directory) / "second.ttf"
            build(first)
            build(second)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            self.assertEqual(
                first.read_bytes(),
                (ROOT / "dist" / "HerdrHarnessLogos-Regular.ttf").read_bytes(),
            )


if __name__ == "__main__":
    unittest.main()
