"""
Prose stays readable in Outlook's dark mode, measured under a model of it (v0.9.0).

The owner found the gallery's prose dark on dark in new Outlook's dark mode: the skeleton forced
it back to the light theme's type while the client darkened its ground. The check applies
``qa.darkmode``'s model to every email and holds prose on a ground the model recolours to WCAG
AA; a mid-tone ground the model leaves alone is the owner's to judge. Its negative control
puts the old forcing block back and asserts the check finds what the owner saw.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest

from qa import screenshots
from qa.darkmode import prose_contrast
from qa.fixtures import all_fixtures

pytestmark = pytest.mark.skipif(
    not screenshots.available(), reason='measuring a render needs the "[qa]" extra and a Chromium'
)

#: WCAG AA for body text.
AA = 4.5

#: The block the skeleton carried until v0.9.0, in the default theme's colours.
FORCING = (
    "[data-ogsc] .email-container, [data-ogsb] .email-container "
    "{ background-color:#FFFFFF !important; }"
    "[data-ogsc] .body-text, [data-ogsb] .body-text { color:#3B3B3B !important; }"
)


@pytest.fixture(scope="module")
def browser() -> Iterator[Any]:
    sync_playwright = screenshots._load_playwright()
    with sync_playwright() as playwright:
        launched = screenshots._launch(playwright)
        yield launched
        launched.close()


def _html(name: str) -> str:
    email = all_fixtures()[name]()
    return screenshots.inline_cid_images(email.render(), email)


def _low(runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The runs under AA on a ground the model recoloured."""
    return [run for run in runs if run["recoloured"] and run["ratio"] < AA]


@pytest.mark.parametrize("name", list(all_fixtures()))
def test_prose_meets_aa_in_outlooks_dark_mode(browser, name):
    low = _low(prose_contrast(browser, _html(name)))
    assert not low, f"{name}: prose under {AA}:1 in dark mode: {low[:3]}"


def test_the_check_measures_prose_across_the_gallery(browser):
    """An email with no prose passes trivially; the gallery as a whole must not."""
    measured = [
        name
        for name in all_fixtures()
        if any(run["recoloured"] for run in prose_contrast(browser, _html(name)))
    ]
    assert len(measured) >= 20, measured


def test_the_check_finds_prose_forced_dark_on_a_darkened_ground(browser):
    # Into the head's last style element: the first is Outlook's own, inside [if mso].
    html = _html("house_daily_note").replace("</head>", f"<style>{FORCING}</style></head>", 1)
    low = _low(prose_contrast(browser, html))
    assert any("Semiconductors carried the tape" in run["text"] for run in low)
    assert min(run["ratio"] for run in low) < 1.6


def test_light_mode_prose_is_untouched_by_the_model(browser):
    runs = prose_contrast(browser, _html("house_daily_note"), dark=False)
    assert runs and min(run["ratio"] for run in runs) >= AA
