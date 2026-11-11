"""A filled ground no type reads on is refused when its section is added (v0.9.0)."""

from __future__ import annotations

import pytest

from inkfold.builder import Email, FullWidth, TextBlock
from inkfold.builder.exceptions import ValidationError
from inkfold.builder.filters import contrast_ratio
from inkfold.builder.surfaces import Callout
from inkfold.builder.theming import DEFAULT_THEME
from inkfold.config import Config, config_override
from qa.fixtures import all_fixtures

GOLD, DEEP_GOLD, PALE_GOLD = "#B8860B", "#8B6508", "#D4A93A"
THEME = DEFAULT_THEME.derive(tones={"gold": GOLD, "deep": DEEP_GOLD, "pale": PALE_GOLD})


def _email(config: Config | None = None) -> Email:
    return Email(
        {"email_subject": "s", "firm_name": "f", "campaign_name": "c", "theme": THEME},
        config=config,
    )


def _solid(tone: str) -> FullWidth:
    return FullWidth(Callout(TextBlock("<p>12 March 2019</p>"), tone=tone, fill="solid"))


class TestTheContrastRatio:
    def test_black_on_white_is_21_and_a_colour_on_itself_is_1(self):
        assert contrast_ratio("#000000", "#FFFFFF") == pytest.approx(21)
        assert contrast_ratio(GOLD, GOLD) == pytest.approx(1)

    def test_the_owners_gold_reads_under_aa_either_way(self):
        assert contrast_ratio(GOLD, DEFAULT_THEME.text.primary) == pytest.approx(3.44, abs=0.01)
        assert contrast_ratio(GOLD, DEFAULT_THEME.text.on_dark) == pytest.approx(3.25, abs=0.01)


class TestASolidBox:
    def test_a_mid_tone_fill_is_refused_naming_its_colour_and_both_types(self):
        email = _email()
        with pytest.raises(ValidationError) as caught:
            email.add_section(_solid("gold"))
        message = str(caught.value)
        assert GOLD in message and "3.44:1" in message and "3.25:1" in message
        assert "Config.min_text_contrast" in message
        assert email.render().count("12 March 2019") == 0, "the refused section was kept"

    @pytest.mark.parametrize(("tone", "ink"), [("deep", "#FFFFFF"), ("pale", "#3B3B3B")])
    def test_a_fill_dark_or_light_enough_takes_the_type_that_reads(self, tone, ink):
        html = _email().add_section(_solid(tone)).render()
        prose = html[html.index('class="body-text"') : html.index("12 March 2019")]
        assert f"color: {ink};" in prose


class TestASectionsGround:
    def test_a_mid_tone_background_is_refused(self):
        with pytest.raises(ValidationError, match="FullWidth.*fills with #B8860B"):
            _email().add_section(FullWidth(TextBlock("<p>x</p>"), background_color=GOLD))

    def test_a_callers_text_colour_is_held_to_the_floor_on_its_ground(self):
        section = FullWidth(TextBlock("<p>x</p>"), background_color="#2C3E50", text_color="#5B8A9A")
        with pytest.raises(ValidationError, match=r"sets #5B8A9A on #2C3E50: 2\.\d+:1"):
            _email().add_section(section)

    def test_a_readable_pair_passes(self):
        section = FullWidth(TextBlock("<p>x</p>"), background_color="#2C3E50", text_color="#FFFFFF")
        _email().add_section(section)


class TestTheFloorIsTunable:
    def test_a_documents_own_config_relaxes_it(self):
        _email(Config(min_text_contrast=3.0)).add_section(_solid("gold"))

    def test_a_context_override_relaxes_it(self):
        with config_override(Config(min_text_contrast=3.0)):
            _email().add_section(_solid("gold"))

    @pytest.mark.parametrize("value", [0.5, 22])
    def test_it_is_a_contrast_ratio(self, value):
        with pytest.raises(ValueError, match="min_text_contrast"):
            Config(min_text_contrast=value)


def test_every_email_in_the_gallery_builds_under_the_floor():
    """The gallery is held to it by building at all; this names the claim."""
    for build in all_fixtures().values():
        build()
