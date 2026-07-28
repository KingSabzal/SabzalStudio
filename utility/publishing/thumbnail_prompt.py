"""Builds a complete image-generation prompt for a 2026-standard thumbnail.

The pipeline produces a video, not a thumbnail. What it can produce is a
prompt precise enough that any image model, or a human designer, can make the
thumbnail without guessing. That is what this module writes.

Everything here comes from published 2026 thumbnail research rather than
taste. The numbers that drive the prompt:

* 1280x720, 16:9, under 2 MB. YouTube began rolling out 50 MB support in
  early 2026 for TV screens, but 2 MB stays the safe target.
* A thumbnail is judged at roughly 168x94 in a mobile feed. Over 70% of views
  are mobile, so every element has to survive that size.
* Text: three to five words. Around 73% of top performers use two or three.
  Fewer than four words measures about 30% higher CTR than text-heavy designs.
* Faces: expressive faces beat neutral or absent ones by 25-42% across several
  analyses. But an unknown face can lower CTR, so a face is only requested
  when it genuinely carries meaning, and a faceless composition is specified
  otherwise.
* Contrast: 4.5:1 minimum, the accessibility standard. Complementary pairs
  (blue/orange, yellow/violet, red/cyan) maximise separation. YouTube's own
  red and white are avoided because they blend into the interface.
* Composition: one dominant subject, two to three visual elements at most,
  around 40% negative space, subject on a rule-of-thirds intersection.
* The bottom right corner holds the duration badge, and the bottom 15% can be
  covered by interface on some surfaces. Nothing important goes there.
* Curiosity gap: show the reaction, not the cause. Partially obscured or
  withheld elements measure around 43% higher CTR.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List

# Canvas and delivery
THUMBNAIL_WIDTH = 1280
THUMBNAIL_HEIGHT = 720
THUMBNAIL_ASPECT = "16:9"
THUMBNAIL_MAX_BYTES = 2 * 1024 * 1024
MOBILE_PREVIEW = (168, 94)

# Text rules
TEXT_WORDS_MIN = 2
TEXT_WORDS_MAX = 5
TEXT_AREA_SHARE = (0.20, 0.30)
MIN_CONTRAST_RATIO = 4.5
NEGATIVE_SPACE_SHARE = 0.40

# Zones that platform interface can cover, as shares of the frame.
DURATION_BADGE_ZONE = "bottom right corner, roughly 20% wide by 15% tall"
UNSAFE_BOTTOM_SHARE = 0.15

# Complementary pairs that separate well in a feed. YouTube red and white are
# deliberately absent: they blend into the interface in both light and dark mode.
COLOR_PAIRS = {
    "electric": ("#0B3D91 deep blue", "#FF7A00 vivid orange"),
    "alert": ("#111111 near black", "#FFD400 signal yellow"),
    "clinical": ("#0E1B24 dark teal", "#00E5FF cyan"),
    "organic": ("#1B3A1F forest green", "#FFB300 amber"),
    "danger": ("#1A0000 blood black", "#FF2A2A alarm red"),
    "regal": ("#2B1B4A deep violet", "#FFC93C gold"),
    "cold": ("#0A1A2F midnight", "#8FE3FF ice blue"),
}

# Which palette and emotional register suits each script style, and whether a
# human face genuinely helps. A face is only worth requesting when a reaction
# is part of the story: on concept-led content it can cost CTR.
STYLE_THUMBNAIL: Dict[str, Dict[str, Any]] = {
    "facts":         {"palette": "alert",    "emotion": "surprise",  "face": True},
    "true_crime":    {"palette": "danger",   "emotion": "concern",   "face": False},
    "mystery":       {"palette": "cold",     "emotion": "concern",   "face": False},
    "history":       {"palette": "regal",    "emotion": "awe",       "face": False},
    "biography":     {"palette": "regal",    "emotion": "resolve",   "face": True},
    "science":       {"palette": "clinical", "emotion": "curiosity", "face": False},
    "space":         {"palette": "cold",     "emotion": "awe",       "face": False},
    "ocean":         {"palette": "cold",     "emotion": "awe",       "face": False},
    "nature":        {"palette": "organic",  "emotion": "awe",       "face": False},
    "animals":       {"palette": "organic",  "emotion": "delight",   "face": False},
    "technology":    {"palette": "clinical", "emotion": "curiosity", "face": False},
    "finance":       {"palette": "electric", "emotion": "resolve",   "face": True},
    "health":        {"palette": "organic",  "emotion": "resolve",   "face": True},
    "psychology":    {"palette": "regal",    "emotion": "curiosity", "face": True},
    "travel":        {"palette": "electric", "emotion": "delight",   "face": False},
    "survival":      {"palette": "danger",   "emotion": "concern",   "face": True},
    "disaster":      {"palette": "danger",   "emotion": "shock",     "face": False},
    "news":          {"palette": "electric", "emotion": "concern",   "face": False},
    "explainer":     {"palette": "clinical", "emotion": "curiosity", "face": False},
    "tutorial":      {"palette": "clinical", "emotion": "resolve",   "face": True},
    "listicle":      {"palette": "alert",    "emotion": "delight",   "face": False},
    "countdown":     {"palette": "alert",    "emotion": "surprise",  "face": False},
    "comparison":    {"palette": "electric", "emotion": "curiosity", "face": False},
    "myth_busting":  {"palette": "alert",    "emotion": "surprise",  "face": True},
    "mistakes":      {"palette": "danger",   "emotion": "concern",   "face": True},
    "motivational":  {"palette": "regal",    "emotion": "resolve",   "face": True},
    "story":         {"palette": "cold",     "emotion": "concern",   "face": True},
    "case_study":    {"palette": "electric", "emotion": "resolve",   "face": False},
    "opinion":       {"palette": "regal",    "emotion": "resolve",   "face": True},
    "what_if":       {"palette": "cold",     "emotion": "awe",       "face": False},
}

DEFAULT_THUMBNAIL = {"palette": "alert", "emotion": "curiosity", "face": False}

# How each emotion should be described to an image model. Vague words like
# "emotional" produce nothing; these describe the face muscle by muscle.
EMOTION_DIRECTION = {
    "surprise": ("eyes wide and eyebrows genuinely raised, mouth slightly open, "
                 "caught mid-reaction rather than posed"),
    "shock":    ("pupils dilated, jaw dropped, head pulled back slightly, "
                 "the split second after seeing something unexpected"),
    "concern":  ("brows drawn together, jaw set, eyes fixed and serious, "
                 "the look of someone delivering bad news carefully"),
    "curiosity": ("head tilted a few degrees, one eyebrow lifted, eyes narrowed "
                  "in thought, leaning slightly toward the subject"),
    "awe":      ("chin lifted, eyes open and reflecting light, lips parted, "
                 "looking at something far larger than themselves"),
    "resolve":  ("direct eye contact with the lens, chin level, mouth closed "
                 "and firm, calm and certain rather than aggressive"),
    "delight":  ("genuine smile reaching the eyes with crow's feet visible, "
                 "shoulders relaxed, warm and unforced"),
}

_WORD_RE = re.compile(r"[A-Za-z0-9']+")


def _normalise(name: str) -> str:
    return str(name or "").strip().lower().replace(" ", "_").replace("-", "_")


def profile_for_style(style_name: str) -> Dict[str, Any]:
    """The palette, emotion and face decision that suit a script style."""
    return dict(STYLE_THUMBNAIL.get(_normalise(style_name), DEFAULT_THUMBNAIL))


def trim_text(text: str, max_words: int = TEXT_WORDS_MAX) -> str:
    """Cut thumbnail text down to the researched word budget."""
    words = _WORD_RE.findall(str(text or ""))
    return " ".join(words[:max_words]).upper()


def checklist() -> List[str]:
    """The 2026 rules the finished image has to satisfy, for a reviewer."""
    return [
        f"{THUMBNAIL_WIDTH}x{THUMBNAIL_HEIGHT} pixels, {THUMBNAIL_ASPECT}, "
        f"under {THUMBNAIL_MAX_BYTES // (1024 * 1024)} MB, JPG or PNG",
        f"Still readable shrunk to {MOBILE_PREVIEW[0]}x{MOBILE_PREVIEW[1]} "
        f"(the real mobile feed size)",
        f"{TEXT_WORDS_MIN}-{TEXT_WORDS_MAX} words of text, no more",
        f"Text covers {int(TEXT_AREA_SHARE[0] * 100)}-{int(TEXT_AREA_SHARE[1] * 100)}% "
        f"of the frame, bold sans-serif at weight 700 or heavier",
        f"At least {MIN_CONTRAST_RATIO}:1 contrast between text and what is behind it",
        f"Around {int(NEGATIVE_SPACE_SHARE * 100)}% negative space, "
        f"two to three visual elements at most",
        "One dominant subject on a rule-of-thirds intersection, not dead centre",
        f"Nothing important in the {DURATION_BADGE_ZONE}",
        f"Nothing important in the bottom {int(UNSAFE_BOTTOM_SHARE * 100)}% of the frame",
        "Passes a greyscale test: the subject still separates from the background",
        "Thumbnail text does not repeat the title word for word",
        "The promise is honest: the video actually delivers what this implies",
    ]


def build_prompt(
    topic: str,
    style_name: str,
    thumbnail_text: str = "",
    title: str = "",
    script: str = "",
    subject_hint: str = "",
) -> Dict[str, Any]:
    """Write the full thumbnail brief.

    Returns the image-generation prompt, a negative prompt, the design
    decisions behind it and the review checklist, so the choices can be
    inspected rather than taken on trust.
    """
    profile = profile_for_style(style_name)
    dark, accent = COLOR_PAIRS[profile["palette"]]
    emotion = profile["emotion"]
    direction = EMOTION_DIRECTION.get(emotion, EMOTION_DIRECTION["curiosity"])
    text = trim_text(thumbnail_text or title or topic)
    subject = subject_hint.strip() or topic.strip()

    if profile["face"]:
        subject_block = (
            f"A single human face in close-up, framed head and shoulders, "
            f"filling 40 to 60% of the frame height, positioned on the left or "
            f"right third rather than the centre. Expression: {direction}. "
            f"The expression must be authentic, not a theatrical open-mouthed "
            f"pose. The face looks toward the empty side of the frame where the "
            f"text sits, so the viewer's eye follows the gaze onto the words. "
            f"Behind the person, clearly separated by depth of field: {subject}."
        )
    else:
        subject_block = (
            f"No human face. One dominant subject: {subject}, shot close and "
            f"filling roughly half the frame, placed on a rule-of-thirds "
            f"intersection. Because there is no face to carry the emotion, the "
            f"{emotion} has to come from the lighting and the framing: strong "
            f"directional light, deep shadow, and a background thrown out of "
            f"focus so the subject separates hard from it."
        )

    prompt = (
        f"A professional YouTube thumbnail, {THUMBNAIL_WIDTH}x{THUMBNAIL_HEIGHT} "
        f"pixels, {THUMBNAIL_ASPECT}, photorealistic and sharply lit.\n\n"
        f"SUBJECT\n{subject_block}\n\n"
        f"COLOUR\nTwo colours dominate. Background: {dark}. Accent used for the "
        f"text and one highlight only: {accent}. These are complementary, so "
        f"they separate at any size. Roughly 60% background, 30% subject, 10% "
        f"accent. No YouTube red or plain white as a main colour, because both "
        f"disappear into the interface.\n\n"
        f"TEXT\nExactly these words, nothing else: \"{text}\". Heavy sans-serif, "
        f"weight 700 or above, all capitals, in {accent} with a thick contrasting "
        f"outline so it holds against anything behind it. The block occupies "
        f"{int(TEXT_AREA_SHARE[0] * 100)} to {int(TEXT_AREA_SHARE[1] * 100)}% of "
        f"the frame, sitting in the upper or middle area on the opposite side "
        f"from the subject.\n\n"
        f"COMPOSITION\nTwo to three elements at most. Around "
        f"{int(NEGATIVE_SPACE_SHARE * 100)}% of the frame stays empty so it does "
        f"not read as clutter at small size. Leave the {DURATION_BADGE_ZONE} "
        f"clear for the duration badge, and keep everything important out of the "
        f"bottom {int(UNSAFE_BOTTOM_SHARE * 100)}% where interface can cover it.\n\n"
        f"CURIOSITY\nShow the reaction or the result, never the explanation. "
        f"Something is deliberately withheld, so the only way to resolve it is "
        f"to watch.\n\n"
        f"QUALITY\nMust stay legible shrunk to {MOBILE_PREVIEW[0]}x"
        f"{MOBILE_PREVIEW[1]} pixels, which is the size most viewers actually "
        f"see. Contrast between text and background at least "
        f"{MIN_CONTRAST_RATIO}:1. In greyscale the subject must still separate "
        f"from the background."
    )

    negative = (
        "cluttered composition, more than five words of text, small or thin "
        "text, decorative or script fonts, low contrast, muddy colours, "
        "washed-out lighting, a neutral or blank expression, a tiny distant "
        "face, watermarks, logos, borders, frames, collage or split-screen "
        "with many panels, text in the bottom right corner, important detail "
        "at the frame edges, blurry or low resolution output, extra fingers, "
        "distorted faces, unreadable garbled lettering, stock-photo blandness"
    )

    return {
        "prompt": prompt,
        "negative_prompt": negative,
        "text": text,
        "specification": {
            "width": THUMBNAIL_WIDTH,
            "height": THUMBNAIL_HEIGHT,
            "aspect_ratio": THUMBNAIL_ASPECT,
            "max_bytes": THUMBNAIL_MAX_BYTES,
            "mobile_preview": f"{MOBILE_PREVIEW[0]}x{MOBILE_PREVIEW[1]}",
        },
        "decisions": {
            "style": _normalise(style_name),
            "palette": profile["palette"],
            "background_colour": dark,
            "accent_colour": accent,
            "emotion": emotion,
            "uses_face": profile["face"],
            "face_rationale": (
                "A reaction is part of this story, and an expressive face "
                "measures 25-42% better than none."
                if profile["face"] else
                "Concept-led content. An unrecognised face can lower CTR here, "
                "so the composition carries the weight instead."
            ),
        },
        "checklist": checklist(),
    }


def to_text(brief: Dict[str, Any]) -> str:
    """The brief as plain text, for a file or the console."""
    lines = [
        "THUMBNAIL BRIEF",
        "=" * 60,
        "",
        "PROMPT",
        brief["prompt"],
        "",
        "NEGATIVE PROMPT",
        brief["negative_prompt"],
        "",
        "DESIGN DECISIONS",
    ]
    for key, value in brief["decisions"].items():
        lines.append(f"  {key.replace('_', ' ')}: {value}")
    lines += ["", "CHECKLIST BEFORE UPLOADING"]
    for item in brief["checklist"]:
        lines.append(f"  [ ] {item}")
    return "\n".join(lines)
