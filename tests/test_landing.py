"""Landing-page formatting regressions: hero centering, control groups, OG art."""
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent

sys.path.insert(0, str(REPO / "tools"))
import make_landing  # noqa: E402  (stdlib-only module)


def _landing_html() -> str:
    return (REPO / "docs" / "index.html").read_text()


def test_hero_keeps_centered_margins():
    # .hero must not override .wrap's auto side-margins (page went left-aligned).
    m = re.search(r"\.hero\{([^}]*)\}", _landing_html())
    assert m, ".hero rule missing from landing page"
    assert "margin:24pxauto8px" in m.group(1).replace(" ", "")


def test_mood_and_event_controls_are_separate_groups():
    html = _landing_html()
    assert 'id="moods"' in html and 'id="kinds"' in html
    # active highlight must apply to the mood row only (kinds used to stick).
    assert "querySelectorAll('#moods button')" in html


def test_og_text_fits_canvas_and_font_covers_it():
    for x, y, text, scale, _rgb in make_landing.OG_TEXTS:
        w, h = make_landing.text_extent(text, scale)
        assert x + w <= make_landing.OG_W, f"overflows right: {text!r}"
        assert y + h <= make_landing.OG_H, f"overflows bottom: {text!r}"
        for ch in text.upper():
            assert ch in make_landing.FONT, f"missing glyph: {ch!r}"
    g = make_landing.OG_MATRIX
    dots_right = g["origin_x"] + 12 * g["pitch"] + g["led"] + g["glow"]
    text_left = min(x for x, *_rest in make_landing.OG_TEXTS)
    assert dots_right < text_left, "LED dots overlap the text block"
