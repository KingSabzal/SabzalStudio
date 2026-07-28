"""Build MoviePy caption clips from a caption style preset.

The original renderer made one plain TextClip per word. This keeps the same
TextClip and ImageMagick machinery, and adds what a style needs: word,
phrase, line and karaoke grouping, a box behind the text, upper case, sane
wrapping, per style placement, and three cheap entrance animations.

The animations are built from static clips on purpose. Anything that resizes
or repaints a clip on every frame makes the render several times slower, and
this project is meant to stay fast.
"""

import os
import subprocess
import tempfile

# Must come before MoviePy: it resizes through PIL constants that Pillow 10
# removed, and both the 'pop' animation and the safe-box clamp below resize.
from utility.core import pillow_compat  # noqa: F401

from moviepy.editor import ColorClip, CompositeVideoClip, ImageClip, TextClip

from utility.captions.caption_layout import (
    group_captions,
    position_for,
    resolve_font,
    safe_box,
    safe_width,
    wrap_text,
)
from utility.captions.caption_styles import GROUP_KARAOKE
from utility.captions.emoji_bank import DEFAULT_PER_MINUTE, annotate
from utility.render import emoji_renderer

# Presets are written for a 1080 pixel wide frame.
REFERENCE_WIDTH = 1080

# How long an entrance animation lasts.
ANIMATION_SECONDS = 0.09
# How much bigger a popping caption starts.
POP_SCALE = 1.14
# How far a rising caption travels, as a share of frame height.
RISE_RATIO = 0.02

# MoviePy hands the caption text to ImageMagick as an @file argument. Recent
# ImageMagick packages ship a policy that forbids @ arguments, and the whole
# render then dies on the first caption. When that happens the text is drawn
# by calling the same binary directly with the text inline, which the policy
# allows. Decided once per process.
_direct_draw = None


def _scaled(value, frame_width):
    return max(1, int(round(value * frame_width / REFERENCE_WIDTH)))


def _magick_binary():
    return os.environ.get("IMAGEMAGICK_BINARY", "convert")


def _draw_with_magick(text, font, font_size, color, stroke_color, stroke_width):
    """Render text to a PNG by calling ImageMagick with the text inline.

    This is the path used when the ImageMagick policy blocks @file arguments.
    """
    out = tempfile.NamedTemporaryFile(suffix=".png", delete=False).name
    cmd = [_magick_binary(), "-background", "transparent", "-fill", color,
           "-font", font, "-pointsize", str(int(font_size))]
    if stroke_width:
        cmd += ["-stroke", stroke_color, "-strokewidth", "%.1f" % stroke_width]
    cmd += [f"label:{text}", "-type", "truecolormatte", f"PNG32:{out}"]

    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0 or not os.path.exists(out):
        raise OSError(result.stderr.decode("utf8", "replace").strip()
                      or "ImageMagick produced no output")
    return ImageClip(out, transparent=True)


def _make_text_clip(text, style, frame_width, font_path, size_override=None,
                    color_override=None):
    """One text clip, styled. Returns None when the text cannot be drawn."""
    global _direct_draw

    font_size = size_override or _scaled(style["font_size"], frame_width)
    stroke_width = _scaled(style["stroke_width"], frame_width) if style["stroke_width"] else 0
    color = color_override or style["color"]
    stroke_color = style["stroke_color"]

    if not _direct_draw:
        kwargs = {
            "txt": text,
            "font": font_path,
            "fontsize": font_size,
            "color": color,
            "method": "label",
        }
        if stroke_width:
            kwargs["stroke_color"] = stroke_color
            kwargs["stroke_width"] = stroke_width
        try:
            return TextClip(**kwargs)
        except Exception as error:
            if _direct_draw is None:
                print("[caption_renderer] MoviePy's TextClip was refused by the "
                      "ImageMagick security policy. Drawing captions by calling "
                      "ImageMagick directly instead.")
                _direct_draw = True
            else:
                print(f"[caption_renderer] Could not draw caption {text!r}: {error}")
                return None

    try:
        return _draw_with_magick(text, font_path, font_size, color,
                                 stroke_color, stroke_width)
    except Exception as error:
        print(f"[caption_renderer] Could not draw caption {text!r}: {error}")
        return None


def _boxed(clip, style, frame_width):
    """Put the text on a solid card when the style asks for one."""
    if not style.get("bg_color"):
        return clip

    pad = _scaled(style.get("box_padding", 18), frame_width)
    width = clip.w + pad * 2
    height = clip.h + pad * 2
    background = ColorClip(size=(width, height), color=_rgb(style["bg_color"]))
    background = background.set_duration(clip.duration or 1)
    return CompositeVideoClip([background, clip.set_position((pad, pad))],
                              size=(width, height))


def _rgb(color):
    """Accept '#RRGGBB' and a few plain names, return an (r, g, b) tuple."""
    named = {
        "black": (0, 0, 0),
        "white": (255, 255, 255),
        "red": (255, 0, 0),
        "green": (0, 128, 0),
        "blue": (0, 0, 255),
        "yellow": (255, 255, 0),
        "cyan": (0, 255, 255),
        "magenta": (255, 0, 255),
        "grey": (128, 128, 128),
        "gray": (128, 128, 128),
    }
    if isinstance(color, (tuple, list)):
        return tuple(color)
    value = str(color).strip()
    if value.startswith("#") and len(value) == 7:
        return tuple(int(value[i:i + 2], 16) for i in (1, 3, 5))
    return named.get(value.lower(), (0, 0, 0))


def _place(clip, style, frame_width, frame_height):
    x, y = position_for(None, frame_width, frame_height, clip.w, clip.h)
    return clip.set_position((x, y)), x, y


def _animate(clip, style, frame_width, frame_height, x, y, start, end):
    """Give a caption its entrance. Returns a list of clips to composite."""
    animation = style.get("animation", "none")
    duration = end - start
    if animation == "none" or duration <= ANIMATION_SECONDS * 2:
        return [clip.set_start(start).set_end(end).set_position((x, y))]

    lead = ANIMATION_SECONDS

    if animation == "fade":
        return [clip.set_start(start).set_end(end).set_position((x, y))
                    .crossfadein(lead)]

    if animation == "rise":
        travel = int(frame_height * RISE_RATIO)

        def rising(t):
            if t >= lead:
                return (x, y)
            return (x, int(y + travel * (1 - t / lead)))

        return [clip.set_start(start).set_end(end).set_position(rising)]

    if animation == "pop":
        # Two static clips instead of a per frame resize: a slightly larger
        # copy for a few frames, then the real one. Reads as a punch and
        # costs nothing to encode.
        #
        # The enlarged copy is bigger than the caption it replaces, so it has
        # to be re-checked against the safe box. Without this the punch frame
        # is the one that slides under the like and share buttons, and it is
        # easy to miss because it is only on screen for a few frames.
        big = clip.resize(POP_SCALE)
        left, top, right, bottom = safe_box(frame_width, frame_height)
        if big.w > (right - left) or big.h > (bottom - top):
            # No room to grow here; play it without the punch.
            return [clip.set_start(start).set_end(end).set_position((x, y))]

        bx = x - (big.w - clip.w) // 2
        by = y - (big.h - clip.h) // 2
        bx = max(left, min(bx, right - big.w))
        by = max(top, min(by, bottom - big.h))
        return [
            big.set_start(start).set_end(min(start + lead, end)).set_position((bx, by)),
            clip.set_start(min(start + lead, end)).set_end(end).set_position((x, y)),
        ]

    return [clip.set_start(start).set_end(end).set_position((x, y))]


def _fit_to_frame(text, style, frame_width, frame_height, font_path, max_chars,
                  reserve=0):
    """Draw the text so it cannot run off the sides of the frame.

    A character budget is only a guess: 'WWWW' is far wider than 'illi' at
    the same setting. So the clip is measured, and while it is too wide the
    text is wrapped onto more lines, and after that the point size is stepped
    down. Without this, long words in the loud presets bleed off both edges.
    """
    # The caption has to fit inside the safe box, not just inside the frame,
    # or a wide line runs under the like and share buttons.
    limit = min(
        int(frame_width * style.get("max_width_ratio", 0.86)),
        safe_width(frame_width, frame_height),
    )
    if style.get("bg_color"):
        limit -= _scaled(style.get("box_padding", 18), frame_width) * 2
    # An emoji is pasted beside the text after it is drawn, so its width has
    # to come out of the budget now. Otherwise the finished clip is wider than
    # the safe box and slides under the platform buttons.
    limit -= reserve

    wrapped = wrap_text(text, max_chars)
    clip = _make_text_clip(wrapped, style, frame_width, font_path)
    if clip is None or clip.w <= limit:
        return clip

    # Step 1: allow more lines by tightening the characters per line.
    chars = max_chars
    while clip.w > limit and chars > 6:
        chars = max(6, int(chars * 0.8))
        candidate = wrap_text(text, chars)
        if candidate == wrapped:
            break
        wrapped = candidate
        clip = _make_text_clip(wrapped, style, frame_width, font_path) or clip

    # Step 2: if a single word is still too wide, shrink the type.
    size = _scaled(style["font_size"], frame_width)
    while clip is not None and clip.w > limit and size > 20:
        size = int(size * 0.88)
        clip = _make_text_clip(wrapped, style, frame_width, font_path,
                               size_override=size)

    return clip


def _measure_space(style, frame_width, font_path, size=None):
    """Width of one space in the current style, in pixels."""
    with_gap = _make_text_clip("n n", style, frame_width, font_path, size_override=size)
    without_gap = _make_text_clip("nn", style, frame_width, font_path, size_override=size)
    if with_gap and without_gap and with_gap.w > without_gap.w:
        return with_gap.w - without_gap.w
    return _scaled(20, frame_width)


def _karaoke_clips(words, style, frame_width, frame_height, font_path, start, end):
    """A block of text that stays put while the spoken word lights up.

    Each word is drawn twice, once in the base colour and once in the
    highlight colour. The highlight copy is only on screen for that word's own
    time window, so the line reads ahead of the voice while the voice keeps
    its place.

    Words are packed onto as many lines as they need. Squeezing a long group
    onto one line would shrink the type until nobody could read it, which
    defeats the point of a caption.
    """
    highlight = style.get("highlight_color") or style["color"]
    limit = min(
        int(frame_width * style.get("max_width_ratio", 0.86)),
        safe_width(frame_width, frame_height),
    )
    size = _scaled(style["font_size"], frame_width)
    texts = [w.upper() if style.get("uppercase") else w for w, _, _ in words]

    # Only shrink for a single word that is wider than the frame on its own,
    # because no amount of wrapping can help that.
    while size > 24:
        widest = max(
            (_make_text_clip(t, style, frame_width, font_path, size_override=size)
             for t in texts),
            key=lambda c: c.w if c else 0, default=None,
        )
        if widest is None or widest.w <= limit:
            break
        size = int(size * 0.9)

    # ImageMagick will not draw a label made only of a space, so the gap
    # between words is measured as the difference between two real strings.
    space_width = _measure_space(style, frame_width, font_path, size)

    drawn = []
    for text, (_, word_start, word_end) in zip(texts, words, strict=False):
        base = _make_text_clip(text, style, frame_width, font_path,
                               size_override=size)
        if base is None:
            return []
        high = _make_text_clip(text, style, frame_width, font_path,
                               size_override=size,
                               color_override=highlight) or base
        drawn.append((base, high, word_start, word_end))

    # Pack into lines that fit the frame.
    lines, line, line_width = [], [], 0
    for item in drawn:
        needed = item[0].w + (space_width if line else 0)
        if line and line_width + needed > limit:
            lines.append((line, line_width))
            line, line_width = [], 0
            needed = item[0].w
        line.append(item)
        line_width += needed
    if line:
        lines.append((line, line_width))

    line_height = max(item[0].h for item in drawn)
    spacing = int(line_height * style.get("line_spacing", 1.0) * 1.1)
    block_height = spacing * (len(lines) - 1) + line_height
    widest_line = max(width for _, width in lines)
    _, block_y = position_for(None, frame_width, frame_height,
                              widest_line, block_height)

    left, _, right, _ = safe_box(frame_width, frame_height)

    clips = []
    for line_index, (line_items, width) in enumerate(lines):
        # Centre the line, but never start it left of the safe box, and never
        # let it run past the right edge into the button column.
        cursor = int((frame_width - width) / 2)
        cursor = max(left, min(cursor, max(left, right - width)))
        row_y = block_y + spacing * line_index
        for base, high, word_start, word_end in line_items:
            top = row_y + (line_height - base.h) // 2
            clips.append(base.set_start(start).set_end(end)
                             .set_position((cursor, top)))

            word_start = max(start, min(word_start, end))
            word_end = max(word_start + 0.05, min(word_end, end))
            hx = cursor - (high.w - base.w) // 2
            hy = row_y + (line_height - high.h) // 2
            clips.append(high.set_start(word_start).set_end(word_end)
                             .set_position((hx, hy)))

            cursor += base.w + space_width

    return clips


def _emoji_settings(style):
    """Whether this render carries emoji, and how many per minute."""
    raw = os.getenv("CAPTION_EMOJI", "off").strip().lower()
    on = raw in ("on", "true", "1", "yes")
    if on and not style.get("emoji", True):
        print(f"[caption_renderer] Preset '{style['name']}' is designed "
              f"without emoji; CAPTION_EMOJI is being ignored for it.")
        on = False
    if on and not emoji_renderer.available():
        on = False

    try:
        rate = int(os.getenv("CAPTION_EMOJI_PER_MINUTE", DEFAULT_PER_MINUTE))
    except ValueError:
        print(f"[caption_renderer] CAPTION_EMOJI_PER_MINUTE is not a number; "
              f"using {DEFAULT_PER_MINUTE}.")
        rate = DEFAULT_PER_MINUTE
    return on, rate


def _with_emoji(clip, emoji, style, frame_width):
    """Paste an emoji beside a finished caption clip.

    The emoji is sized to the text, not to the frame, so it sits on the same
    optical line whatever the preset's point size is.
    """
    if not emoji:
        return clip

    height = int(clip.h * 0.72)
    badge = emoji_renderer.clip(emoji, height)
    if badge is None:
        return clip

    gap = _scaled(14, frame_width)
    where = style.get("emoji_position", "right")

    if where == "above":
        width = max(clip.w, badge.w)
        total = badge.h + gap + clip.h
        return CompositeVideoClip(
            [badge.set_position(((width - badge.w) // 2, 0)),
             clip.set_position(((width - clip.w) // 2, badge.h + gap))],
            size=(width, total),
        ).set_duration(clip.duration or 1)

    width = clip.w + gap + badge.w
    height_total = max(clip.h, badge.h)
    text_y = (height_total - clip.h) // 2
    badge_y = (height_total - badge.h) // 2

    if where == "left":
        parts = [badge.set_position((0, badge_y)),
                 clip.set_position((badge.w + gap, text_y))]
    else:
        parts = [clip.set_position((0, text_y)),
                 badge.set_position((clip.w + gap, badge_y))]

    return CompositeVideoClip(parts, size=(width, height_total)).set_duration(
        clip.duration or 1
    )


def _clamp_to_safe(clip, frame_width, frame_height):
    """Last line of defence: shrink a finished clip that is still too wide.

    Everything upstream predicts how wide a caption will end up, and a
    prediction can be a few pixels out once an emoji and a box are added.
    Rather than trust the arithmetic, the assembled clip is measured and
    scaled down if it does not fit. This is measured, not estimated, so no
    caption can reach the frame wider than the safe box.
    """
    left, top, right, bottom = safe_box(frame_width, frame_height)
    max_w, max_h = right - left, bottom - top
    if clip.w <= max_w and clip.h <= max_h:
        return clip

    scale = min(max_w / clip.w, max_h / clip.h)
    return clip.resize(scale)


def build_caption_clips(timed_captions, style, frame_width, frame_height):
    """Every caption clip for one video, ready to composite.

    `timed_captions` is the word level list from the STT stage.
    `style` is a dictionary from utility.captions.caption_styles.get_style.
    """
    if not timed_captions:
        return []

    font_path = resolve_font(style["font"])
    print(f"[caption_renderer] Style '{style['name']}' using font: {font_path}")

    groups = group_captions(timed_captions, style)
    max_chars = int(style.get("max_chars", 28))

    emoji_on, emoji_rate = _emoji_settings(style)
    emoji_picks = annotate(groups, per_minute=emoji_rate, enabled=emoji_on)
    if emoji_on:
        chosen = sum(1 for e in emoji_picks if e)
        print(f"[caption_renderer] Emoji on: {chosen} of {len(groups)} groups "
              f"decorated, capped at {emoji_rate} per minute.")

    clips = []
    for index, ((start, end), payload) in enumerate(groups):
        end = max(end, start + 0.05)

        if style.get("group") == GROUP_KARAOKE:
            clips.extend(_karaoke_clips(payload, style, frame_width,
                                        frame_height, font_path, start, end))
            continue

        text = payload.upper() if style.get("uppercase") else payload

        emoji = emoji_picks[index]
        reserve = 0
        if emoji and style.get("emoji_position", "right") != "above":
            # A Noto glyph is close to square, drawn at 72% of the text height.
            reserve = int(_scaled(style["font_size"], frame_width) * 0.72) \
                + _scaled(14, frame_width)

        clip = _fit_to_frame(text, style, frame_width, frame_height, font_path,
                             max_chars, reserve=reserve)
        if clip is None:
            continue
        clip = clip.set_duration(end - start)
        clip = _with_emoji(clip, emoji, style, frame_width)
        clip = _boxed(clip, style, frame_width)
        clip = _clamp_to_safe(clip, frame_width, frame_height)
        _, x, y = _place(clip, style, frame_width, frame_height)
        clips.extend(_animate(clip, style, frame_width, frame_height, x, y, start, end))

    print(f"[caption_renderer] Built {len(clips)} caption clips "
          f"from {len(groups)} groups.")
    return clips


def frame_size_from(clips, orientation_landscape=False):
    """Work out the frame the captions have to fit.

    The background clips decide it. When there are none, fall back to the
    standard size for the configured orientation.
    """
    for clip in clips:
        size = getattr(clip, "size", None)
        if size and size[0] and size[1]:
            return int(size[0]), int(size[1])
    return (1920, 1080) if orientation_landscape else (1080, 1920)


def caption_style_from_env(video_style=None):
    """Resolve the caption style, honouring CAPTION_STYLE and any overrides."""
    from utility.captions.caption_styles import get_style, style_for_video_style

    requested = os.getenv("CAPTION_STYLE", "auto").strip()
    if not requested or requested.lower() == "auto":
        requested = style_for_video_style(video_style)
        print(f"[caption_renderer] CAPTION_STYLE is auto; "
              f"'{video_style}' scripts get '{requested}'.")

    style = get_style(requested)

    # The original per setting variables still work, as overrides on top of
    # the chosen preset, so an existing .env keeps behaving the way it did.
    overrides = {
        "font_size": ("CAPTION_FONT_SIZE", int),
        "color": ("CAPTION_FONT_COLOR", str),
        "stroke_width": ("CAPTION_STROKE_WIDTH", int),
        "stroke_color": ("CAPTION_STROKE_COLOR", str),
    }
    applied = []
    for key, (env_name, cast) in overrides.items():
        raw = os.getenv(env_name)
        if raw is None or not str(raw).strip():
            continue
        try:
            style[key] = cast(str(raw).strip())
            applied.append(f"{env_name}={raw.strip()}")
        except ValueError:
            print(f"[caption_renderer] Ignoring {env_name}={raw!r}: not a {cast.__name__}.")

    if applied:
        # An .env written for the old single style project sets all of these,
        # which would quietly flatten every preset back to the old look. Say
        # so plainly rather than letting the style appear not to work.
        print(f"[caption_renderer] Preset '{style['name']}' is being overridden by "
              f"{', '.join(applied)}. Clear these in .env to see the preset as "
              f"it was designed.")

    font_face = os.getenv("CAPTION_FONT_FACE", "").strip()
    if font_face:
        style["font"] = [font_face] + list(style["font"])

    return style
