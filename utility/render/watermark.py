"""A faint, always moving handle watermark.

A watermark that sits in one corner is trivial to crop out. One that never
stops moving has to be tracked frame by frame, so a reposter either leaves it
in or spends real effort removing it.

The mark drifts like the old DVD screensaver: constant velocity, bouncing off
the edges of the frame. It is deliberately low contrast, because a watermark
that competes with the content costs more views than the credit is worth.

Two things keep it from becoming a nuisance:

  * it never enters the caption band, so the text is always readable
  * it is drawn once as a single image and moved with a position function,
    so it costs one still image per render rather than work on every frame
"""

import os

from utility.captions.caption_layout import (
    CAPTION_ANCHOR,
    resolve_font,
    safe_box,
)

# Presets are written for a 1080 pixel wide frame.
REFERENCE_WIDTH = 1080

DEFAULT_OPACITY = 0.28
DEFAULT_SIZE = 34          # point size at 1080 wide
DEFAULT_SPEED = 60.0       # pixels per second at 1080 wide

# How much of the frame height the caption band occupies, as a share either
# side of the caption anchor. The mark steers around this.
_CAPTION_BAND = 0.09

_FONT = ["Montserrat Bold", "Roboto Bold", "DejaVu Sans:bold"]


def _scaled(value, frame_width):
    return max(1, int(round(value * frame_width / REFERENCE_WIDTH)))


def enabled():
    """Whether a watermark should be drawn at all."""
    if os.getenv("WATERMARK", "off").strip().lower() not in (
        "on", "true", "1", "yes"
    ):
        return False
    return bool(handle())


def handle():
    """The handle to draw, normalised to start with '@'."""
    raw = os.getenv("WATERMARK_HANDLE", "").strip()
    if not raw:
        return ""
    return raw if raw.startswith("@") else "@" + raw


def _opacity():
    try:
        value = float(os.getenv("WATERMARK_OPACITY", DEFAULT_OPACITY))
    except ValueError:
        print(f"[watermark] WATERMARK_OPACITY is not a number; "
              f"using {DEFAULT_OPACITY}.")
        return DEFAULT_OPACITY
    return min(1.0, max(0.05, value))


def _speed():
    try:
        value = float(os.getenv("WATERMARK_SPEED", DEFAULT_SPEED))
    except ValueError:
        print(f"[watermark] WATERMARK_SPEED is not a number; "
              f"using {DEFAULT_SPEED}.")
        return DEFAULT_SPEED
    return min(400.0, max(5.0, value))


def _size():
    try:
        value = int(os.getenv("WATERMARK_SIZE", DEFAULT_SIZE))
    except ValueError:
        print(f"[watermark] WATERMARK_SIZE is not a number; "
              f"using {DEFAULT_SIZE}.")
        return DEFAULT_SIZE
    return min(120, max(12, value))


def _draw(text, frame_width):
    """The handle as a still transparent clip, or None."""
    from utility.render.caption_renderer import _make_text_clip

    style = {
        "font_size": _size(),
        "color": "white",
        "stroke_color": "black",
        "stroke_width": 2,
    }
    return _make_text_clip(text, style, frame_width, resolve_font(_FONT))


def _bounce(value, span):
    """Fold a distance travelled into a there-and-back path of length span.

    Travelling 2*span returns to the start, so the mark bounces between the
    walls forever without ever needing per frame state.
    """
    if span <= 0:
        return 0.0
    cycle = value % (2 * span)
    return cycle if cycle <= span else (2 * span - cycle)


def build(frame_width, frame_height, duration):
    """The moving watermark clip, or None when it is switched off.

    `duration` is how long the finished video runs.
    """
    if not enabled():
        return None

    text = handle()
    mark = _draw(text, frame_width)
    if mark is None:
        print("[watermark] The handle could not be drawn; skipping watermark.")
        return None

    mark = mark.set_opacity(_opacity()).set_duration(duration)

    left, top, right, bottom = safe_box(frame_width, frame_height)
    span_x = max(1, right - left - mark.w)
    span_y = max(1, bottom - top - mark.h)

    # The band the captions live in. The mark is pushed out of it rather than
    # stopped, so it keeps moving but never sits on top of the text.
    band_half = frame_height * _CAPTION_BAND
    band_centre = top + (bottom - top) * CAPTION_ANCHOR
    band_top = band_centre - band_half - mark.h
    band_bottom = band_centre + band_half

    speed = _speed() * frame_width / REFERENCE_WIDTH
    # A different rate on each axis, so the path does not repeat quickly and
    # the mark actually reaches every part of the frame.
    speed_x = speed
    speed_y = speed * 0.61803  # an irrational ratio keeps the path from looping

    def position(t):
        x = left + _bounce(speed_x * t, span_x)
        y = top + _bounce(speed_y * t, span_y)

        if band_top < y < band_bottom:
            # Inside the caption band. Send it to whichever side of the band
            # is nearer, so the deflection looks like part of the drift.
            if y - band_top < band_bottom - y:
                y = band_top
            else:
                y = band_bottom
            y = max(top, min(y, bottom - mark.h))
        return (x, y)

    print(f"[watermark] '{text}' drifting at {speed:.0f} px/s, "
          f"opacity {_opacity():.2f}, steering around the caption band.")
    return mark.set_position(position)
