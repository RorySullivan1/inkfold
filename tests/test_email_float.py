"""A wrapped figure floats in an email too (v0.9.0), and kitchen_sink's hosted images load."""

from __future__ import annotations

import pytest

from inkfold.builder import EmailBuilder, FullWidth, ImageBlock, TextBlock
from inkfold.builder.images import EmailImage
from qa.fixtures import _hosted, all_fixtures
from qa.fixtures._png import solid_png

PROSE = "<p>The long end did the work this quarter.</p>"


def _email(wrap: str = "right"):
    figure = ImageBlock(
        EmailImage.attached(solid_png(120, 80, (1, 2, 3)), alt="A", width=120), wrap=wrap
    )
    return (
        EmailBuilder()
        .metadata({"email_subject": "s", "firm_name": "f", "campaign_name": "c"})
        .section(FullWidth(content=TextBlock(PROSE, figure=figure)))
        .build()
    )


class TestAWrappedFigureInAnEmail:
    @pytest.mark.parametrize("side", ["left", "right"])
    def test_it_floats_by_a_tables_align_before_the_prose(self, side):
        html = _email(side).render()
        table = html.index(f'class="email-float" align="{side}"')
        assert table < html.index("The long end did the work")
        assert 'role="presentation" class="email-float"' in html

    def test_its_width_is_the_figure_and_the_gutter(self):
        assert 'width="136"' in _email().render()  # 120px + the standard 16px gutter

    def test_a_phone_stacks_it_and_only_an_email_with_one_carries_the_rule(self):
        assert ".email-float { float:none !important;" in _email().render()
        assert ".email-float" not in _email(wrap="").render()
        assert ".email-float" not in all_fixtures()["minimal"]().render()


class TestTheHostedImages:
    def test_the_committed_files_are_the_constants(self):
        for name, data in _hosted.IMAGES.items():
            assert (_hosted.FOLDER / name).read_bytes() == data, "run python -m qa.fixtures._hosted"

    def test_kitchen_sink_fetches_all_three_from_the_repository(self):
        html = all_fixtures()["kitchen_sink"]().render()
        for name in _hosted.IMAGES:
            assert _hosted.url(name) in html
        assert "cdn.example.com" not in html

    def test_an_unknown_name_is_refused(self):
        with pytest.raises(KeyError, match="no hosted fixture image"):
            _hosted.url("nope.png")
