"""Pure logic that decides what the viewer sees and what the file is called."""

import pytest

from utility.core.naming import output_stem, slugify_title, unique_path
from utility.media.media_manager import is_allowed_url, merge_empty_intervals


# ----------------------------------------------------------------------
# Gap filling. A segment with no clip becomes a black flash while the
# narration keeps talking, so no interval may leave here without a URL.
# ----------------------------------------------------------------------

def test_a_gap_in_the_middle_borrows_the_previous_clip():
    merged = merge_empty_intervals([
        [(0.0, 2.0), "a.mp4"],
        [(2.0, 4.0), None],
        [(4.0, 6.0), "b.mp4"],
    ])
    assert all(url for _interval, url in merged)


def test_a_gap_at_the_very_start_is_filled_forwards():
    """The old copy of this function left a leading gap unfilled: the video
    opened on black."""
    merged = merge_empty_intervals([
        [(0.0, 2.0), None],
        [(2.0, 4.0), "b.mp4"],
    ])
    assert all(url for _interval, url in merged)
    assert merged[0][1] == "b.mp4"


def test_several_leading_gaps_are_all_covered():
    merged = merge_empty_intervals([
        [(0.0, 1.0), None],
        [(1.0, 2.0), None],
        [(2.0, 3.0), "c.mp4"],
    ])
    assert all(url for _interval, url in merged)
    covered = merged[-1][0][1]
    assert covered == 3.0


def test_nothing_at_all_is_reported_rather_than_guessed():
    assert merge_empty_intervals(None) is None


# ----------------------------------------------------------------------
# Licensing guard
# ----------------------------------------------------------------------

@pytest.mark.parametrize("url", [
    "https://cdn.shutterstock.com/clip.mp4",
    "https://www.gettyimages.com/x.mp4",
    "https://stock.adobe.com/x.mp4",
    "https://example.com/ai-generated-clip.mp4",
    "https://example.com/paywall-promo.mp4",
    "",
])
def test_paid_and_ai_sources_are_refused(url):
    assert not is_allowed_url(url)


@pytest.mark.parametrize("url", [
    "https://player.vimeo.com/external/123.hd.mp4",
    "https://assets.mixkit.co/videos/preview/mixkit-forest-1234-large.mp4",
    "https://cdn.coverr.co/videos/coverr-a-river-1234/1080p.mp4",
])
def test_free_sources_are_allowed(url):
    assert is_allowed_url(url)


# ----------------------------------------------------------------------
# File naming
# ----------------------------------------------------------------------

def test_a_title_becomes_a_readable_file_name():
    assert slugify_title("Why Cats Purr: 5 Reasons!") == "Why-Cats-Purr-5-Reasons"


def test_accents_and_emoji_do_not_reach_the_filesystem():
    assert slugify_title("Café Déjà Vu 🎬") == "Cafe-Deja-Vu"


def test_windows_reserved_names_are_escaped():
    assert slugify_title("CON").upper() != "CON"


def test_an_empty_title_still_produces_a_name():
    assert slugify_title("!!!", fallback="video") == "video"
    assert output_stem("", "a topic") == "a-topic"
    assert output_stem("", "") == "video"


def test_names_do_not_collide(tmp_path):
    first = unique_path(str(tmp_path), "clip", ".mp4")
    open(first, "w").close()
    second = unique_path(str(tmp_path), "clip", ".mp4")
    assert first != second
    assert second.endswith("clip-2.mp4")
