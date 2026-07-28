"""Turn word level transcript timings into the caption chunks a style wants.

Whisper gives one entry per word. A caption style decides whether the viewer
sees one word, a short phrase, a whole line, or a line with the spoken word
highlighted. This module does that regrouping, and it resolves the font names
a style asks for against the fonts actually installed.
"""

import os
import subprocess

from utility.captions.caption_styles import (
    GROUP_KARAOKE,
    GROUP_LINE,
    GROUP_PHRASE,
    GROUP_WORD,
)

# Sentence enders. A caption group never runs past one of these, because
# reading a chunk that spans two sentences is what makes captions feel wrong.
_SENTENCE_END = ('.', '!', '?')
_CLAUSE_END = (',', ';', ':', '-')

# A group is also cut when the speaker pauses this long, so the text on
# screen keeps step with the voice.
PAUSE_SPLIT_SECONDS = 0.45

# Nothing readable stays on screen for less than this.
MIN_GROUP_SECONDS = 0.30


def _ends_sentence(word):
    return word.rstrip().endswith(_SENTENCE_END)


def _ends_clause(word):
    return word.rstrip().endswith(_CLAUSE_END)


def group_captions(timed_captions, style):
    """Regroup word level captions to suit a style.

    `timed_captions` is what the STT stage returns: [((start, end), word), ...]

    For the word, phrase and line modes the result has the same shape, with
    longer text per entry: [((start, end), "text"), ...]

    For karaoke the result is [((start, end), [(word, start, end), ...]), ...]
    so the renderer can light up one word at a time inside a line that stays.
    """
    words = [((float(s), float(e)), str(w)) for (s, e), w in timed_captions if str(w).strip()]
    if not words:
        return []

    mode = style.get("group", GROUP_PHRASE)

    if mode == GROUP_WORD:
        return [((s, e), w) for (s, e), w in words]

    max_words = int(style.get("max_words", 3))
    max_chars = int(style.get("max_chars", 28))
    groups = _chunk(words, max_words, max_chars)

    if mode == GROUP_KARAOKE:
        return [
            ((g[0][0][0], g[-1][0][1]), [(w, s, e) for (s, e), w in g])
            for g in groups
        ]

    if mode in (GROUP_PHRASE, GROUP_LINE):
        return [
            ((g[0][0][0], g[-1][0][1]), " ".join(w for _, w in g))
            for g in groups
        ]

    raise ValueError(f"Unknown caption grouping mode: {mode}")


def _chunk(words, max_words, max_chars):
    """Split the word list into groups, respecting punctuation and pauses."""
    groups = []
    current = []
    current_chars = 0

    for i, ((start, end), word) in enumerate(words):
        added = len(word) + (1 if current else 0)

        too_long = current and (
            len(current) >= max_words or current_chars + added > max_chars
        )
        if too_long:
            groups.append(current)
            current, current_chars = [], 0

        current.append(((start, end), word))
        current_chars += added

        # Cut after a full stop, and after a comma when the group is already
        # more than half full, so groups break where a reader would breathe.
        cut = _ends_sentence(word)
        if not cut and _ends_clause(word) and len(current) >= max(2, max_words // 2):
            cut = True

        # Cut on a real gap in the speech.
        if not cut and i + 1 < len(words):
            gap = words[i + 1][0][0] - end
            if gap >= PAUSE_SPLIT_SECONDS:
                cut = True

        if cut:
            groups.append(current)
            current, current_chars = [], 0

    if current:
        groups.append(current)

    return _merge_flashes(groups)


def _merge_flashes(groups):
    """Fold away groups too short to read into the group before them."""
    merged = []
    for group in groups:
        duration = group[-1][0][1] - group[0][0][0]
        if merged and duration < MIN_GROUP_SECONDS:
            merged[-1].extend(group)
        else:
            merged.append(list(group))
    return merged


def wrap_text(text, max_chars):
    """Break a caption over lines so no line is wider than max_chars."""
    words = text.split()
    if not words:
        return text

    lines, line = [], ""
    for word in words:
        candidate = f"{line} {word}".strip()
        if line and len(candidate) > max_chars:
            lines.append(line)
            line = word
        else:
            line = candidate
    if line:
        lines.append(line)
    return "\n".join(lines)


# --------------------------------------------------------------------------
# Fonts
# --------------------------------------------------------------------------

_font_cache = {}


def _fc_match(request):
    """Ask fontconfig for the file and family it would use for a request."""
    try:
        out = subprocess.run(
            ["fc-match", "-f", "%{family}\t%{file}", request],
            capture_output=True, text=True, timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None, None
    if out.returncode != 0 or "\t" not in out.stdout:
        return None, None
    family, path = out.stdout.split("\t", 1)
    return family.strip(), path.strip()


def _squash(name):
    """'Playfair Display' and 'PlayfairDisplay' become the same key."""
    return "".join(ch for ch in str(name).lower() if ch.isalnum())


def fonts_dir():
    """Where the project's own caption fonts live."""
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.normpath(os.path.join(here, "..", "..", "assets", "fonts"))


def bundled_fonts():
    """Family name -> file path, for every font shipped with the project."""
    directory = fonts_dir()
    if not os.path.isdir(directory):
        return {}
    found = {}
    for name in sorted(os.listdir(directory)):
        if not name.lower().endswith((".ttf", ".otf")):
            continue
        if "emoji" in name.lower():
            continue  # not a text font
        path = os.path.join(directory, name)
        stem = os.path.splitext(name)[0]        # 'PlayfairDisplay-Bold'
        family, _, weight = stem.partition("-")  # 'PlayfairDisplay', 'Bold'

        # Key on the squashed name so 'Playfair Display' and 'PlayfairDisplay'
        # both land here, and so does 'Roboto Mono' for 'RobotoMono'.
        base = _squash(family)
        for key in (_squash(stem), f"{base}{_squash(weight)}"):
            if key:
                found[key] = path
        # A bare family name resolves to the first weight seen, which is
        # alphabetical, so Montserrat-Black wins over Montserrat-Bold. Prefer
        # the Regular or Bold cut for a bare request instead.
        if base not in found or weight.lower() in ("regular", "bold"):
            if base not in found or weight.lower() == "regular":
                found[base] = path
            else:
                found.setdefault(base, path)
    return found


def resolve_font(candidates):
    """Return a font file for the first candidate that can be found.

    A style lists the fonts it wants, best first. The project's own
    assets/fonts directory is searched before anything else, because those
    files are committed and always present, which is what makes a preset look
    the same on every machine. Only if none of them match does this fall back
    to fontconfig and whatever the operating system happens to have.
    """
    if isinstance(candidates, str):
        candidates = [candidates]
    key = tuple(candidates)
    if key in _font_cache:
        return _font_cache[key]

    override = os.getenv("CAPTION_FONT_FILE", "").strip()
    if override and os.path.exists(override):
        _font_cache[key] = override
        return override

    bundled = bundled_fonts()

    fallback = None
    for candidate in candidates:
        if os.path.exists(candidate):
            _font_cache[key] = candidate
            return candidate

        wanted = candidate.split(":")[0].strip().lower()

        # The project's own fonts first.
        hit = bundled.get(_squash(wanted))
        if hit:
            _font_cache[key] = hit
            return hit

        # Then whatever the system offers, accepted only on an exact family
        # match, because fc-match always answers with something.
        family, path = _fc_match(candidate)
        if not path:
            continue
        if fallback is None:
            fallback = path
        if family and family.split(",")[0].strip().lower() == wanted:
            _font_cache[key] = path
            return path

    result = fallback or (candidates[-1] if candidates else "DejaVu-Sans-Bold")
    _font_cache[key] = result
    return result


# --------------------------------------------------------------------------
# Safe zones
# --------------------------------------------------------------------------
#
# A 1080x1920 frame is not 1080x1920 of usable space. Every platform paints
# its own interface on top: the profile row and back button at the top, the
# caption text, audio label and subscribe button at the bottom, and a column
# of like, comment and share buttons down the right.
#
# The numbers below are the union of the 2026 published safe zones, so one
# render is clear on all three platforms at once:
#
#     TikTok           top 108   bottom 320   left 60   right 120
#     Instagram Reels  top 210   bottom 310   left  0   right  84
#     YouTube Shorts   top 120   bottom 300   left  0   right  96
#     ------------------------------------------------------------
#     union            top 260   bottom 320   left 90   right 120
#
# The top figure is 260 rather than 210 to leave a little air under the
# Instagram profile row instead of touching it.
#
# Written as ratios of a 1080x1920 frame so they hold in landscape too.
SAFE_TOP_RATIO = 260 / 1920      # 0.1354
SAFE_BOTTOM_RATIO = 320 / 1920   # 0.1667
SAFE_LEFT_RATIO = 90 / 1080      # 0.0833
SAFE_RIGHT_RATIO = 120 / 1080    # 0.1111

# Captions sit at this share of the way down the safe box. 0.80 puts the text
# at roughly 69% of a 1080x1920 frame, which is the band viewers read.
CAPTION_ANCHOR = 0.80


def safe_zone_enabled():
    """Whether captions are kept clear of the platform interface."""
    return os.getenv("CAPTION_SAFE_ZONE", "on").strip().lower() not in (
        "off", "false", "0", "no"
    )


def safe_box(frame_width, frame_height):
    """The rectangle a caption may occupy: (left, top, right, bottom)."""
    if not safe_zone_enabled():
        margin = int(frame_width * 0.04)
        return margin, 0, frame_width - margin, frame_height
    return (
        int(frame_width * SAFE_LEFT_RATIO),
        int(frame_height * SAFE_TOP_RATIO),
        int(frame_width * (1 - SAFE_RIGHT_RATIO)),
        int(frame_height * (1 - SAFE_BOTTOM_RATIO)),
    )


def safe_width(frame_width, frame_height):
    """How wide a caption may be without running under the side buttons."""
    left, _, right, _ = safe_box(frame_width, frame_height)
    return right - left


def position_for(name, frame_width, frame_height, clip_width, clip_height):
    """Pixel position for a caption inside a frame.

    There is one caption position: bottom centre. The project used to offer
    five, and that was a choice with no upside. Centre of frame covers the
    subject's face, top competes with the profile row, and the left and right
    variants push text into the button column on one side or the other.
    Bottom centre is where viewers look for captions on every platform, and
    it is the position the 2026 A/B data favours over top alignment.

    `name` is still accepted so old presets and an old .env do not break, but
    every value resolves to the same place.
    """
    left, top, right, bottom = safe_box(frame_width, frame_height)
    usable_height = max(1, bottom - top)

    # Sit at 80% down the safe box. Inside a 1080x1920 frame that puts the
    # middle of the text around 69% of the frame height: clear of the face in
    # the upper half, and clear of the caption bar and subscribe button that
    # occupy the bottom 320 pixels.
    y = int(top + usable_height * CAPTION_ANCHOR - clip_height / 2)
    y = max(top, min(y, bottom - clip_height))
    y = max(0, min(y, max(0, frame_height - clip_height)))

    x = int((frame_width - clip_width) / 2)
    x = max(left, min(x, max(left, right - clip_width)))
    return x, y
