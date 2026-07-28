"""Make MoviePy 1.0.3 work with Pillow 10 and newer.

MoviePy 1.0.3 resizes frames through ``PIL.Image.ANTIALIAS``. That constant,
along with the other bare resampling names, was deprecated in Pillow 2.7 and
finally **removed in Pillow 10**. Nothing in MoviePy guards against it, so on a
modern install every ``clip.resize(...)`` dies with:

    AttributeError: module 'PIL.Image' has no attribute 'ANTIALIAS'

That is not a corner case here. The default script style is ``facts``, which
maps to the ``hormozi_yellow`` caption preset, whose entrance animation is
``pop`` -- and ``pop`` resizes. ``_clamp_to_safe``, the last line of defence
that stops a caption spilling out of the safe box, resizes too. So the default
path crashes.

Three fixes were possible:

1. Pin ``pillow<10``. Rejected: Pillow 9 has known CVEs and has no wheels for
   recent Python, so it would trade this crash for a build failure.
2. Add ``opencv-python``, which MoviePy prefers over PIL when present.
   Rejected: a ~60 MB dependency to work around three missing aliases.
3. Restore the aliases. Chosen. They were only ever names for the enum values
   that Pillow still ships, so this is the same code path the old constant
   selected, not an approximation.

Import this module before anything imports MoviePy. It is safe to import more
than once and does nothing on a Pillow that still has the constants.
"""

from __future__ import annotations

# Old name -> the enum member that replaced it in Pillow 9.1+.
_RESAMPLING_ALIASES = {
    "NEAREST": "NEAREST",
    "BOX": "BOX",
    "BILINEAR": "BILINEAR",
    "HAMMING": "HAMMING",
    "BICUBIC": "BICUBIC",
    "LANCZOS": "LANCZOS",
    # ANTIALIAS was renamed rather than removed: it always meant Lanczos.
    "ANTIALIAS": "LANCZOS",
    "CUBIC": "BICUBIC",
    "LINEAR": "BILINEAR",
}

_applied = False


def apply() -> bool:
    """Restore the removed Pillow resampling constants. True when patched."""
    global _applied
    if _applied:
        return True

    try:
        from PIL import Image
    except ImportError:  # Pillow is optional for the non-rendering code paths.
        return False

    resampling = getattr(Image, "Resampling", None)
    if resampling is None:
        # Pillow older than 9.1: the bare constants are the only ones there are.
        _applied = True
        return True

    for old_name, member in _RESAMPLING_ALIASES.items():
        if not hasattr(Image, old_name):
            setattr(Image, old_name, getattr(resampling, member))

    _applied = True
    return True


# Applied on import so a caller only has to import the module.
apply()
