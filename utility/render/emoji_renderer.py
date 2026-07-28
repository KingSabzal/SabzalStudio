"""Draw colour emoji for captions.

ImageMagick cannot render a CBDT colour emoji font. Tested on this project's
own environment, `magick -font NotoColorEmoji.ttf label:...` either fails
with "unable to read font" or produces a one pixel wide grey image. Pillow
reads the same font correctly when asked for `embedded_color=True`.

So the caption text keeps going through ImageMagick, exactly as the original
project did, and only the emoji is drawn here with Pillow and pasted beside
the text. Nothing else about the render path changes.
"""

import os
import tempfile

from PIL import Image, ImageDraw, ImageFont

# Noto Color Emoji is a bitmap font. Its strikes are authored at 109 pixels
# and FreeType will refuse any other size, so an emoji is always drawn at 109
# and then resampled to whatever the caption needs.
NATIVE_SIZE = 109

_EMOJI_FONT_FILE = "NotoColorEmoji.ttf"

_font = None
_font_missing = False
_cache = {}


def _fonts_dir():
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.normpath(os.path.join(here, "..", "..", "assets", "fonts"))


def emoji_font_path():
    """Where the bundled colour emoji font lives."""
    override = os.getenv("EMOJI_FONT_FILE", "").strip()
    if override:
        return override
    return os.path.join(_fonts_dir(), _EMOJI_FONT_FILE)


def available():
    """True when colour emoji can actually be drawn."""
    return _load_font() is not None


def _load_font():
    global _font, _font_missing
    if _font is not None or _font_missing:
        return _font

    path = emoji_font_path()
    if not os.path.exists(path):
        print(f"[emoji_renderer] No colour emoji font at {path}. "
              f"Captions will be rendered without emoji.")
        _font_missing = True
        return None
    try:
        _font = ImageFont.truetype(path, NATIVE_SIZE)
    except OSError as error:
        print(f"[emoji_renderer] Could not load {path}: {error}. "
              f"Captions will be rendered without emoji.")
        _font_missing = True
        return None
    return _font


def render(emoji, height):
    """Draw one emoji as a transparent PNG and return the file path.

    `height` is the pixel height wanted, normally the cap height of the
    caption text beside it. Returns None when emoji cannot be drawn.
    """
    height = max(8, int(height))
    key = (emoji, height)
    if key in _cache and os.path.exists(_cache[key]):
        return _cache[key]

    font = _load_font()
    if font is None:
        return None

    try:
        canvas = Image.new("RGBA", (NATIVE_SIZE * 3, NATIVE_SIZE * 2), (0, 0, 0, 0))
        draw = ImageDraw.Draw(canvas)
        draw.text((NATIVE_SIZE // 2, NATIVE_SIZE // 4), emoji,
                  font=font, embedded_color=True)

        box = canvas.getbbox()
        if not box:
            return None
        glyph = canvas.crop(box)

        scale = height / glyph.height
        width = max(1, int(round(glyph.width * scale)))
        glyph = glyph.resize((width, height), Image.LANCZOS)

        out = tempfile.NamedTemporaryFile(suffix=".png", delete=False).name
        glyph.save(out)
        _cache[key] = out
        return out
    except Exception as error:
        print(f"[emoji_renderer] Could not draw {emoji!r}: {error}")
        return None


def clip(emoji, height):
    """The emoji as a MoviePy ImageClip, or None."""
    path = render(emoji, height)
    if not path:
        return None
    from moviepy.editor import ImageClip
    return ImageClip(path, transparent=True)
