"""Caption style presets.

The original project drew every caption the same way: one small white word
with a black outline, glued to the bottom of the frame. That is the look of
2019. Short form video in 2026 uses captions as a design element, and the
look changes with the kind of video: a true crime story is not lettered like
a comedy skit.

This module holds 27 presets. Each one decides three things:

  * how many words appear on screen at a time (`group`, `max_words`,
    `max_chars`)
  * how the text looks (font, size, colour, outline, box, case)
  * how it enters (`animation`)

Captions always sit at bottom centre. The project used to offer five
positions and none of the other four were a good idea: centre of frame covers
the subject, top competes with the profile row, and the left and right
variants push text towards the button column.

Sizes are written for a 1080 pixel wide frame and are scaled by the renderer
for any other width, so a preset looks the same in 9:16 and in 16:9.

Fonts are given as a candidate list, most wanted first. The renderer resolves
the list against the fonts actually installed on the machine, so a preset
never fails just because a designer font is missing.
"""

# Grouping modes
GROUP_WORD = "word"        # one word at a time
GROUP_PHRASE = "phrase"    # two to four words, the modern default
GROUP_LINE = "line"        # a readable line, up to max_words
GROUP_KARAOKE = "karaoke"  # a line stays, the spoken word lights up

# Font candidate lists. The first name in each list is a font committed to
# assets/fonts, so a preset renders identically on every machine; the rest are
# system fallbacks in case the bundled file is ever removed.
#
# The families were chosen from what short form creators actually use in 2026:
# Montserrat Black is the Hormozi caption face, Anton and Oswald are the
# condensed faces that keep a long word on one line, and Bangers is the free
# stand-in for the Komika Axis look on entertainment content.
_BLACK = ["Montserrat Black", "Montserrat Bold", "Anton",
          "Liberation Sans Bold", "DejaVu Sans:bold"]
_HEAVY = ["Anton", "Oswald Bold", "Impact", "Archivo Black",
          "Liberation Sans Bold", "DejaVu Sans:bold"]
_CONDENSED = ["Oswald Bold", "Anton", "Liberation Sans Narrow Bold",
              "DejaVu Sans:bold"]
_COMIC = ["Bangers", "Komika Axis", "Anton", "DejaVu Sans:bold"]
_SANS_BOLD = ["Montserrat Bold", "Roboto Bold", "Open Sans Bold",
              "Liberation Sans Bold", "DejaVu Sans:bold"]
_SANS = ["Roboto", "Open Sans", "Liberation Sans", "DejaVu Sans"]
_SERIF = ["Playfair Display", "Georgia", "Liberation Serif", "DejaVu Serif"]
_MONO = ["Roboto Mono", "JetBrains Mono", "Liberation Mono", "DejaVu Sans Mono"]
_ROUND = ["Nunito Bold", "Quicksand Bold", "Comfortaa", "DejaVu Sans:bold"]

_DEFAULTS = {
    "description": "",
    "group": GROUP_PHRASE,
    "max_words": 3,
    "max_chars": 28,
    "font": _SANS_BOLD,
    "font_size": 78,
    "color": "white",
    "stroke_color": "black",
    "stroke_width": 4,
    "bg_color": None,        # None means no box behind the text
    "box_padding": 18,
    "uppercase": False,
    "animation": "none",     # none | fade | pop | rise
    "highlight_color": None,  # karaoke only
    "line_spacing": 1.0,
    "max_width_ratio": 0.86,  # text is wrapped inside this share of the frame
    "emoji": True,            # may this preset carry an emoji at all
    "emoji_position": "right",  # right | left | above
}


CAPTION_STYLES = {
    # ------------------------------------------------------------------ #
    # Group 1 - plain and safe
    # ------------------------------------------------------------------ #
    "clean_white": {
        "description": "The original look. White text, thin black outline, "
                       "one short phrase at the bottom. Costs the least to "
                       "render and never fights the footage.",
        "group": GROUP_PHRASE,
        "max_words": 3,
        "max_chars": 24,
        "font_size": 76,
        "stroke_width": 3,
    },
    "minimal_thin": {
        "description": "Light weight, wide letter feel, no outline. For calm "
                       "footage where the caption should whisper.",
        "font": _SANS,
        "group": GROUP_LINE,
        "max_words": 6,
        "max_chars": 40,
        "font_size": 62,
        "stroke_width": 0,
        "animation": "fade",
        "emoji": False,
    },
    "podcast_clean": {
        "description": "Sentence case, five to seven words per line, sitting "
                       "just above the lower third. The look of clipped "
                       "interview shows.",
        "group": GROUP_LINE,
        "max_words": 7,
        "max_chars": 44,
        "font_size": 64,
        "stroke_width": 3,
    },

    # ------------------------------------------------------------------ #
    # Group 2 - loud short form, the 2026 mainstream
    # ------------------------------------------------------------------ #
    "hormozi_yellow": {
        "description": "One giant uppercase word at a time in yellow with a "
                       "heavy black outline. The highest retention caption "
                       "style on short form and the reason viewers keep "
                       "watching with the sound off.",
        "group": GROUP_WORD,
        "font": _BLACK,
        "font_size": 118,
        "color": "#FFD400",
        "stroke_width": 9,
        "uppercase": True,
        "animation": "pop",
    },
    "hormozi_green": {
        "description": "The same one word beat, in signal green. Reads well "
                       "over warm or sandy footage where yellow disappears.",
        "group": GROUP_WORD,
        "font": _BLACK,
        "font_size": 118,
        "color": "#39FF6A",
        "stroke_width": 9,
        "uppercase": True,
        "animation": "pop",
    },
    "beasty": {
        "description": "Huge white uppercase with a very thick outline, "
                       "punched in the middle of the frame. Built for fast "
                       "cuts and loud energy.",
        "group": GROUP_WORD,
        "font": _HEAVY,
        "font_size": 126,
        "color": "white",
        "stroke_width": 10,
        "uppercase": True,
        "animation": "pop",
    },
    "karaoke_highlight": {
        "description": "A full line stays on screen and the word being "
                       "spoken lights up. Viewers can read ahead, which is "
                       "why it holds attention on longer sentences.",
        "group": GROUP_KARAOKE,
        "font": _SANS_BOLD,
        "max_words": 4,
        "max_chars": 30,
        "font_size": 76,
        "color": "white",
        "highlight_color": "#FFD400",
        "stroke_width": 6,
        "uppercase": True,
    },
    "karaoke_pink": {
        "description": "Karaoke timing with a hot pink highlight. Suits "
                       "beauty, fashion and lifestyle footage.",
        "group": GROUP_KARAOKE,
        "font": _SANS_BOLD,
        "max_words": 4,
        "max_chars": 30,
        "font_size": 76,
        "color": "white",
        "highlight_color": "#FF3FA4",
        "stroke_width": 6,
        "uppercase": True,
    },
    "tiktok_classic": {
        "description": "White text inside a solid black box, three words at "
                       "a time. The most copied caption on the platform "
                       "because it is readable over anything.",
        "group": GROUP_PHRASE,
        "max_words": 3,
        "max_chars": 22,
        "font_size": 68,
        "stroke_width": 0,
        "bg_color": "black",
        "box_padding": 20,
    },
    "tiktok_white_box": {
        "description": "Black text in a white box. The inverse card, for "
                       "dark or night footage.",
        "group": GROUP_PHRASE,
        "max_words": 3,
        "max_chars": 22,
        "font_size": 68,
        "color": "black",
        "stroke_width": 0,
        "bg_color": "white",
        "box_padding": 20,
    },
    "reels_bold": {
        "description": "Two words at a time, extra bold, rising slightly as "
                       "they appear. Tuned for Instagram Reels safe areas.",
        "group": GROUP_PHRASE,
        "max_words": 2,
        "max_chars": 18,
        "font": _HEAVY,
        "font_size": 96,
        "stroke_width": 7,
        "uppercase": True,
        "animation": "rise",
    },
    "shorts_pop": {
        "description": "YouTube Shorts pacing: short phrases that pop in "
                       "with a red keyline, kept clear of the title overlay.",
        "group": GROUP_PHRASE,
        "max_words": 3,
        "max_chars": 22,
        "font": _HEAVY,
        "font_size": 92,
        "color": "white",
        "stroke_color": "#FF0033",
        "stroke_width": 7,
        "uppercase": True,
        "animation": "pop",
    },

    # ------------------------------------------------------------------ #
    # Group 3 - genre looks
    # ------------------------------------------------------------------ #
    "true_crime_slate": {
        "description": "Cold grey white on a heavy outline, small and low. "
                       "Deliberately unexcited, which is what makes a crime "
                       "story feel like evidence.",
        "group": GROUP_LINE,
        "max_words": 6,
        "max_chars": 38,
        "font": _SANS_BOLD,
        "font_size": 64,
        "color": "#DCE3EA",
        "stroke_width": 5,
        "emoji": False,
    },
    "horror_red": {
        "description": "Blood red uppercase with a black outline, centred. "
                       "For scares, unsolved cases and creepy facts.",
        "group": GROUP_WORD,
        "font": _CONDENSED,
        "font_size": 104,
        "color": "#D40000",
        "stroke_width": 8,
        "uppercase": True,
        "animation": "pop",
    },
    "documentary_serif": {
        "description": "Serif type, sentence case, generous line length. "
                       "Reads as authored rather than posted.",
        "group": GROUP_LINE,
        "max_words": 8,
        "max_chars": 48,
        "font": _SERIF,
        "font_size": 62,
        "stroke_width": 3,
        "emoji": False,
    },
    "news_lower_third": {
        "description": "White text in a dark band across the lower third, "
                       "the broadcast convention. Best for updates and "
                       "explainers.",
        "group": GROUP_LINE,
        "max_words": 8,
        "max_chars": 46,
        "font": _SANS_BOLD,
        "font_size": 60,
        "stroke_width": 0,
        "bg_color": "#0B1F3A",
        "box_padding": 24,
        "emoji": False,
    },
    "sports_impact": {
        "description": "Compressed uppercase in stadium white with a thick "
                       "outline, slammed in the centre. For highlights and "
                       "records.",
        "group": GROUP_WORD,
        "font": _CONDENSED,
        "font_size": 122,
        "stroke_width": 10,
        "uppercase": True,
        "animation": "pop",
    },
    "finance_ticker": {
        "description": "Monospace numbers and terms in market green on a "
                       "near black bar. Numbers stay legible, which matters "
                       "when the script is full of them.",
        "group": GROUP_PHRASE,
        "max_words": 4,
        "max_chars": 30,
        "font": _MONO,
        "font_size": 60,
        "color": "#22E06B",
        "stroke_width": 0,
        "bg_color": "#06110B",
        "box_padding": 18,
        "emoji": False,
    },
    "edu_chalk": {
        "description": "Soft chalk white on a slate coloured card, unhurried "
                       "line lengths. For teaching and how it works videos.",
        "group": GROUP_LINE,
        "max_words": 7,
        "max_chars": 42,
        "font": _ROUND,
        "font_size": 62,
        "color": "#F2F5EA",
        "stroke_width": 0,
        "bg_color": "#2C3A34",
        "box_padding": 22,
    },
    "storytime_bubble": {
        "description": "Rounded friendly type in a white bubble with black "
                       "text. The look of a personal story told to camera.",
        "group": GROUP_PHRASE,
        "max_words": 4,
        "max_chars": 26,
        "font": _ROUND,
        "font_size": 68,
        "color": "#1A1A1A",
        "stroke_width": 0,
        "bg_color": "#FFFFFF",
        "box_padding": 24,
        "animation": "fade",
    },
    "comic_pop": {
        "description": "Cyan uppercase with a fat outline that pops in on "
                       "every phrase. Comedy, reactions and skits.",
        "group": GROUP_PHRASE,
        "max_words": 2,
        "max_chars": 18,
        "font": _COMIC,
        "font_size": 100,
        "color": "#00E5FF",
        "stroke_width": 9,
        "uppercase": True,
        "animation": "pop",
    },
    "motivational_upper": {
        "description": "All caps, centred, rising into place. Built for "
                       "short declarative lines that end in a full stop.",
        "group": GROUP_PHRASE,
        "max_words": 3,
        "max_chars": 24,
        "font": _HEAVY,
        "font_size": 96,
        "stroke_width": 7,
        "uppercase": True,
        "animation": "rise",
    },

    # ------------------------------------------------------------------ #
    # Group 4 - colour led
    # ------------------------------------------------------------------ #
    "neon_cyan": {
        "description": "Electric cyan on deep navy outline. Reads as tech, "
                       "future and space.",
        "group": GROUP_PHRASE,
        "max_words": 3,
        "max_chars": 22,
        "font": _SANS_BOLD,
        "font_size": 84,
        "color": "#3DF5FF",
        "stroke_color": "#04121F",
        "stroke_width": 8,
        "uppercase": True,
        "animation": "fade",
    },
    "neon_pink": {
        "description": "Magenta on black, the night city palette. Music, "
                       "nightlife and fashion cuts.",
        "group": GROUP_PHRASE,
        "max_words": 3,
        "max_chars": 22,
        "font": _SANS_BOLD,
        "font_size": 84,
        "color": "#FF2FD6",
        "stroke_width": 8,
        "uppercase": True,
        "animation": "fade",
    },
    "gold_luxury": {
        "description": "Warm gold serif, small and low, no shouting. "
                       "Watches, cars, wealth and history.",
        "group": GROUP_LINE,
        "max_words": 6,
        "max_chars": 36,
        "font": _SERIF,
        "font_size": 64,
        "color": "#E8C579",
        "stroke_width": 4,
        "animation": "fade",
    },
    "pastel_soft": {
        "description": "Soft cream text on a muted plum card. Gentle enough "
                       "for wellness, sleep and ASMR footage.",
        "group": GROUP_LINE,
        "max_words": 6,
        "max_chars": 36,
        "font": _ROUND,
        "font_size": 62,
        "color": "#FFF4E6",
        "stroke_width": 0,
        "bg_color": "#4A3550",
        "box_padding": 22,
        "animation": "fade",
    },
    "terminal_green": {
        "description": "Monospace phosphor green, no outline, lower left. "
                       "Hacking, code and anything that should look like a "
                       "console.",
        "group": GROUP_PHRASE,
        "max_words": 4,
        "max_chars": 32,
        "font": _MONO,
        "font_size": 60,
        "color": "#33FF66",
        "stroke_width": 0,
        "emoji": False,
    },
}


# Every style a script style can ask for. Used by pick_style_for_video_style.
STYLE_FOR_VIDEO_STYLE = {
    "facts": "hormozi_yellow",
    "true_crime": "true_crime_slate",
    "horror": "horror_red",
    "space": "neon_cyan",
    "science": "neon_cyan",
    "history": "gold_luxury",
    "documentary": "documentary_serif",
    "news": "news_lower_third",
    "finance": "finance_ticker",
    "money": "finance_ticker",
    "business": "finance_ticker",
    "education": "edu_chalk",
    "how_to": "edu_chalk",
    "tutorial": "edu_chalk",
    "story": "storytime_bubble",
    "storytime": "storytime_bubble",
    "case_study": "podcast_clean",
    "interview": "podcast_clean",
    "comedy": "comic_pop",
    "motivation": "motivational_upper",
    "sports": "sports_impact",
    "fitness": "sports_impact",
    "animals": "storytime_bubble",
    "technology": "terminal_green",
    "tech": "terminal_green",
    "fashion": "karaoke_pink",
    "beauty": "karaoke_pink",
    "music": "neon_pink",
    "travel": "minimal_thin",
    "food": "tiktok_classic",
    "health": "pastel_soft",
    "wellness": "pastel_soft",
    "mystery": "true_crime_slate",
}

DEFAULT_STYLE = "clean_white"


def _normalise(name):
    """Accept 'Hormozi Yellow', 'hormozi-yellow' and 'HORMOZI_YELLOW'."""
    return str(name or "").strip().lower().replace(" ", "_").replace("-", "_")


def list_styles():
    """Every preset name, sorted."""
    return sorted(CAPTION_STYLES)


def style_exists(name):
    return _normalise(name) in CAPTION_STYLES


def get_style(name=None):
    """Return a complete style dictionary.

    Missing keys are filled from the defaults, so a preset only has to state
    what makes it different. An unknown name falls back to the plain style
    and says so instead of failing the render.
    """
    key = _normalise(name)
    if key and key not in CAPTION_STYLES:
        print(
            f"[caption_styles] Unknown caption style '{name}'. "
            f"Using '{DEFAULT_STYLE}'. Known styles: {', '.join(list_styles())}"
        )
        key = DEFAULT_STYLE
    if not key:
        key = DEFAULT_STYLE

    style = dict(_DEFAULTS)
    style.update(CAPTION_STYLES[key])
    style["name"] = key
    return style


def style_for_video_style(video_style):
    """The caption preset that suits a script style.

    Used when CAPTION_STYLE is left at 'auto', so a true crime script is not
    lettered like a comedy skit.
    """
    key = _normalise(video_style)
    return STYLE_FOR_VIDEO_STYLE.get(key, DEFAULT_STYLE)


def describe(name):
    """One line describing a preset, for menus and logs."""
    style = get_style(name)
    return f"{style['name']}: {style['description']}"
