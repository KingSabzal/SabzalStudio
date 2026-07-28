"""Registry of approved media sources. Zero-attribution licences only.

Every source listed here is CC0, Public Domain, Pexels, Pixabay or Mixkit
licensed and needs no credit in the finished video. Paid services and AI video
generators are deliberately absent: paid video generators, paid music
services and the paid stock libraries are all forbidden by this project's
rules.

Each entry carries a `status` field recording what the source did when it was
last probed live. A source marked `blocked` or `dead` is still tried, because
these sites change their minds often and a source that refuses a request today
may answer tomorrow, but the field means nobody has to guess which parts of
the chain are actually carrying the work.
"""

from __future__ import annotations

from typing import Any, Dict, List

# Status values, from the live probe of 2026-07-28:
#   live    - answered with usable results
#   blocked - answered, but refused this client (403 and similar)
#   dead    - did not answer, or answered with nothing usable
STATUS_LIVE = "live"
STATUS_BLOCKED = "blocked"
STATUS_DEAD = "dead"

VIDEO_SOURCES: List[Dict[str, Any]] = [
    {"priority": 1, "id": "pexels", "name": "Pexels", "kind": "api",
     "endpoint": "https://api.pexels.com/videos/search", "license": "Pexels License",
     "needs_key": True, "key_field": "pexels_api_key", "status": STATUS_LIVE,
     "signup": "https://www.pexels.com/api/new/"},
    {"priority": 2, "id": "pixabay", "name": "Pixabay", "kind": "api",
     "endpoint": "https://pixabay.com/api/videos/", "license": "Pixabay License",
     "needs_key": True, "key_field": "pixabay_api_key", "status": STATUS_LIVE,
     "signup": "https://pixabay.com/api/key/"},
    {"priority": 3, "id": "mixkit", "name": "Mixkit", "kind": "scrape",
     "endpoint": "https://mixkit.co/free-stock-video/{query}/", "license": "Mixkit License",
     "needs_key": False, "status": STATUS_LIVE},
    {"priority": 4, "id": "coverr", "name": "Coverr", "kind": "scrape",
     "endpoint": "https://coverr.co/s?q={query}", "license": "Coverr (CC0-like)",
     "needs_key": False, "status": STATUS_LIVE},
    {"priority": 5, "id": "dareful", "name": "Dareful", "kind": "scrape",
     "endpoint": "http://dareful.com/?s={query}", "license": "CC0",
     "needs_key": False, "status": STATUS_LIVE},
    {"priority": 6, "id": "lifeofvids", "name": "Life of Vids", "kind": "scrape",
     "endpoint": "https://www.lifeofvids.com/?s={query}", "license": "Public Domain",
     "needs_key": False, "status": STATUS_DEAD},
    {"priority": 7, "id": "splitshire", "name": "SplitShire", "kind": "scrape",
     "endpoint": "https://www.splitshire.com/?s={query}", "license": "CC0",
     "needs_key": False, "status": STATUS_DEAD},
    {"priority": 8, "id": "videvo", "name": "Videvo (free only)", "kind": "scrape",
     "endpoint": "https://www.videvo.net/search/{query}/?filter=free",
     "license": "Videvo free / CC0", "needs_key": False, "status": STATUS_BLOCKED},
    {"priority": 9, "id": "openverse_video", "name": "Openverse", "kind": "api",
     "endpoint": "https://api.openverse.org/v1/images/", "license": "CC0 / Public Domain",
     "needs_key": False, "status": STATUS_LIVE},
    {"priority": 18, "id": "archive", "name": "Internet Archive / Prelinger", "kind": "api",
     "endpoint": "https://archive.org/advancedsearch.php", "license": "Public Domain",
     "needs_key": False, "status": STATUS_LIVE},
]

IMAGE_SOURCES: List[Dict[str, Any]] = [
    {"priority": 1, "id": "pexels_img", "name": "Pexels Photos", "kind": "api",
     "endpoint": "https://api.pexels.com/v1/search", "license": "Pexels License",
     "needs_key": True, "key_field": "pexels_api_key", "status": STATUS_LIVE},
    {"priority": 2, "id": "pixabay_img", "name": "Pixabay Photos", "kind": "api",
     "endpoint": "https://pixabay.com/api/", "license": "Pixabay License",
     "needs_key": True, "key_field": "pixabay_api_key", "status": STATUS_LIVE},
    {"priority": 9, "id": "nasa", "name": "NASA Images", "kind": "api",
     "endpoint": "https://images-api.nasa.gov/search", "license": "Public Domain",
     "needs_key": False, "status": STATUS_LIVE},
    {"priority": 10, "id": "smithsonian", "name": "Smithsonian Open Access", "kind": "api",
     "endpoint": "https://api.si.edu/openaccess/api/v1.0/search", "license": "CC0",
     "needs_key": False, "status": STATUS_BLOCKED},
    {"priority": 11, "id": "met", "name": "Met Museum", "kind": "api",
     "endpoint": "https://collectionapi.metmuseum.org/public/collection/v1/search",
     "license": "CC0 (Open Access)", "needs_key": False, "status": STATUS_LIVE},
    {"priority": 12, "id": "rijksmuseum", "name": "Rijksmuseum", "kind": "api",
     "endpoint": "https://www.rijksmuseum.nl/api/en/collection", "license": "Public Domain",
     "needs_key": False, "status": STATUS_DEAD},
    {"priority": 13, "id": "openverse_img", "name": "Openverse", "kind": "api",
     "endpoint": "https://api.openverse.org/v1/images/", "license": "CC0 / Public Domain",
     "needs_key": False, "status": STATUS_LIVE},
    {"priority": 14, "id": "wikimedia", "name": "Wikimedia Commons", "kind": "api",
     "endpoint": "https://commons.wikimedia.org/w/api.php", "license": "Public Domain / CC0",
     "needs_key": False, "status": STATUS_LIVE},
    {"priority": 15, "id": "loc", "name": "Library of Congress", "kind": "api",
     "endpoint": "https://www.loc.gov/photos/", "license": "Public Domain",
     "needs_key": False, "status": STATUS_LIVE},
    {"priority": 16, "id": "nypl", "name": "NYPL Digital Collections", "kind": "api",
     "endpoint": "https://api.nypl.org/api/v1/items/search", "license": "Public Domain",
     "needs_key": False, "status": STATUS_DEAD},
    # NOAA, USGS and the National Park Service publish enormous public domain
    # photo libraries, but all three render their galleries with JavaScript, so
    # a plain HTTP fetch returns markup with no image in it. Their collections
    # are reachable through Openverse and Wikimedia instead, which is how the
    # three entries below actually deliver the same material.
    {"priority": 17, "id": "noaa", "name": "NOAA (via Openverse)", "kind": "api",
     "endpoint": "https://api.openverse.org/v1/images/", "license": "Public Domain",
     "needs_key": False, "status": STATUS_LIVE},
    {"priority": 18, "id": "usgs", "name": "USGS (via Openverse)", "kind": "api",
     "endpoint": "https://api.openverse.org/v1/images/", "license": "Public Domain",
     "needs_key": False, "status": STATUS_LIVE},
    {"priority": 19, "id": "nps", "name": "National Park Service (via Openverse)",
     "kind": "api", "endpoint": "https://api.openverse.org/v1/images/",
     "license": "Public Domain", "needs_key": False, "status": STATUS_LIVE},
    {"priority": 20, "id": "flickr_commons", "name": "Flickr Commons", "kind": "api",
     "endpoint": "https://api.openverse.org/v1/images/", "license": "CC0 / Public Domain",
     "needs_key": False, "status": STATUS_LIVE},
    {"priority": 21, "id": "smithsonian_ov", "name": "Smithsonian (via Openverse)",
     "kind": "api", "endpoint": "https://api.openverse.org/v1/images/",
     "license": "CC0", "needs_key": False, "status": STATUS_LIVE},
]

MUSIC_SOURCES: List[Dict[str, Any]] = [
    {"priority": 1, "id": "pixabay_music", "name": "Pixabay Music", "kind": "api",
     "endpoint": "https://pixabay.com/api/", "license": "Pixabay License",
     "needs_key": True, "key_field": "pixabay_api_key", "status": STATUS_LIVE},
    {"priority": 2, "id": "mixkit_music", "name": "Mixkit Music", "kind": "scrape",
     "endpoint": "https://mixkit.co/free-stock-music/{query}/", "license": "Mixkit License",
     "needs_key": False, "status": STATUS_LIVE},
    {"priority": 3, "id": "openverse_music", "name": "Openverse Audio", "kind": "api",
     "endpoint": "https://api.openverse.org/v1/audio/", "license": "CC0 / Public Domain",
     "needs_key": False, "status": STATUS_LIVE},
    {"priority": 4, "id": "freepd", "name": "FreePD", "kind": "scrape",
     "endpoint": "https://freepd.com/", "license": "CC0",
     "needs_key": False, "status": STATUS_DEAD},
    {"priority": 5, "id": "wikimedia_audio", "name": "Wikimedia Audio", "kind": "api",
     "endpoint": "https://api.openverse.org/v1/audio/", "license": "CC0 / Public Domain",
     "needs_key": False, "status": STATUS_LIVE},
    # The YouTube Audio Library is genuinely free and genuinely useful, but it
    # sits behind a Google sign-in: requesting it unauthenticated redirects to
    # accounts.google.com. It cannot be reached by an automated pipeline, so it
    # is recorded here for completeness and never called.
    {"priority": 9, "id": "yt_audio_library", "name": "YouTube Audio Library",
     "kind": "manual", "endpoint": "https://studio.youtube.com/channel/UC/music",
     "license": "YouTube Audio Library (no attribution tracks only)",
     "needs_key": False, "status": STATUS_BLOCKED,
     "note": "Requires a Google sign-in; download tracks by hand if you want them."},
]

SFX_SOURCES: List[Dict[str, Any]] = [
    {"priority": 1, "id": "pixabay_sfx", "name": "Pixabay Sound Effects", "kind": "api",
     "endpoint": "https://pixabay.com/api/", "license": "Pixabay License",
     "needs_key": True, "key_field": "pixabay_api_key", "status": STATUS_LIVE},
    {"priority": 2, "id": "mixkit_sfx", "name": "Mixkit Sound Effects", "kind": "scrape",
     "endpoint": "https://mixkit.co/free-sound-effects/{query}/", "license": "Mixkit License",
     "needs_key": False, "status": STATUS_LIVE},
    {"priority": 3, "id": "openverse_sfx", "name": "Openverse Audio", "kind": "api",
     "endpoint": "https://api.openverse.org/v1/audio/", "license": "CC0 / Public Domain",
     "needs_key": False, "status": STATUS_LIVE},
    {"priority": 4, "id": "freepd_sfx", "name": "FreePD SFX", "kind": "scrape",
     "endpoint": "https://freepd.com/", "license": "CC0",
     "needs_key": False, "status": STATUS_DEAD},
    {"priority": 5, "id": "freesound", "name": "Freesound (via Openverse)",
     "kind": "api", "endpoint": "https://api.openverse.org/v1/audio/",
     "license": "CC0", "needs_key": False, "status": STATUS_LIVE},
    {"priority": 9, "id": "yt_audio_library_sfx", "name": "YouTube Audio Library SFX",
     "kind": "manual", "endpoint": "https://studio.youtube.com/channel/UC/music",
     "license": "YouTube Audio Library", "needs_key": False, "status": STATUS_BLOCKED,
     "note": "Requires a Google sign-in; not reachable by an automated pipeline."},
]


# --------------------------------------------------------------------------
# Style -> visual and musical character
# --------------------------------------------------------------------------
#
# The script styles from stage 3 describe how a script is written, not how it
# should look or sound. These two tables add that: what a shot for this style
# should show, and what the music under it should feel like. Without them
# every style would search the same generic footage.

STYLE_VISUALS: Dict[str, List[str]] = {
    "facts": ["macro detail", "slow motion", "abstract texture"],
    "true_crime": ["empty street night", "rain window", "old documents"],
    "mystery": ["fog forest", "abandoned building", "dark corridor"],
    "history": ["ancient ruins", "old map", "archive footage"],
    "biography": ["portrait silhouette", "old photographs", "city archive"],
    "science": ["laboratory", "microscope", "particle simulation"],
    "space": ["galaxy stars", "planet surface", "rocket launch"],
    "ocean": ["underwater", "deep sea", "ocean waves"],
    "nature": ["forest canopy", "wildlife", "mountain landscape"],
    "animals": ["wildlife closeup", "animal in nature", "birds flying"],
    "technology": ["circuit board", "server room", "code screen"],
    "finance": ["stock chart", "city skyline business", "banknotes"],
    "health": ["running outdoors", "fresh food", "medical closeup"],
    "psychology": ["human eye closeup", "crowd slow motion", "abstract brain"],
    "travel": ["aerial landscape", "street market", "coastline drone"],
    "survival": ["wilderness", "campfire night", "storm weather"],
    "disaster": ["storm clouds", "flood water", "wildfire"],
    "news": ["city traffic", "crowd walking", "newsroom"],
    "explainer": ["clean workspace", "abstract geometry", "hands demonstrating"],
    "tutorial": ["hands working", "workshop table", "close up process"],
    "listicle": ["fast cuts objects", "flat lay", "colourful abstract"],
    "countdown": ["fast motion city", "abstract numbers", "dramatic reveal"],
    "comparison": ["split composition", "two objects", "balance scale"],
    "myth_busting": ["question mark abstract", "laboratory test", "old book"],
    "mistakes": ["frustrated person", "broken object", "warning sign"],
    "motivational": ["sunrise runner", "mountain summit", "training gym"],
    "story": ["cinematic portrait", "quiet room", "walking alone"],
    "case_study": ["office meeting", "data charts", "modern building"],
    "opinion": ["person thinking", "city bench", "abstract light"],
    "what_if": ["surreal landscape", "futuristic city", "abstract cosmos"],
}

STYLE_MUSIC_MAPPING: Dict[str, List[str]] = {
    "facts": ["upbeat", "curious", "electronic"],
    "true_crime": ["dark", "suspense", "tension"],
    "mystery": ["mysterious", "suspense", "ambient dark"],
    "history": ["cinematic", "orchestral", "documentary"],
    "biography": ["emotional", "piano", "inspiring"],
    "science": ["ambient", "curious", "electronic"],
    "space": ["ambient", "cosmic", "cinematic"],
    "ocean": ["ambient", "calm", "underwater"],
    "nature": ["ambient", "calm", "acoustic"],
    "animals": ["playful", "light", "acoustic"],
    "technology": ["electronic", "modern", "corporate"],
    "finance": ["corporate", "modern", "confident"],
    "health": ["uplifting", "calm", "acoustic"],
    "psychology": ["ambient", "thoughtful", "minimal"],
    "travel": ["uplifting", "acoustic", "adventure"],
    "survival": ["tension", "dramatic", "cinematic"],
    "disaster": ["dramatic", "tension", "epic"],
    "news": ["corporate", "neutral", "documentary"],
    "explainer": ["corporate", "light", "modern"],
    "tutorial": ["light", "corporate", "acoustic"],
    "listicle": ["upbeat", "energetic", "pop"],
    "countdown": ["energetic", "building", "epic"],
    "comparison": ["modern", "corporate", "curious"],
    "myth_busting": ["curious", "quirky", "electronic"],
    "mistakes": ["tension", "quirky", "modern"],
    "motivational": ["epic", "inspiring", "uplifting"],
    "story": ["emotional", "cinematic", "piano"],
    "case_study": ["corporate", "confident", "modern"],
    "opinion": ["thoughtful", "minimal", "ambient"],
    "what_if": ["cinematic", "cosmic", "mysterious"],
}

DEFAULT_VISUALS = ["cinematic background", "abstract texture", "slow motion"]
DEFAULT_MOODS = ["ambient", "cinematic"]


def _normalise(name: str) -> str:
    return str(name or "").strip().lower().replace(" ", "_").replace("-", "_")


def music_moods_for_style(style_name: str) -> List[str]:
    """Music mood keywords for a script style."""
    return STYLE_MUSIC_MAPPING.get(_normalise(style_name), list(DEFAULT_MOODS))


def visual_keywords_for_style(style_name: str) -> List[str]:
    """Visual keywords describing what a shot for this style should show."""
    return STYLE_VISUALS.get(_normalise(style_name), list(DEFAULT_VISUALS))


def all_sources() -> Dict[str, List[Dict[str, Any]]]:
    """Every registered source, grouped by media type."""
    return {
        "video": VIDEO_SOURCES,
        "image": IMAGE_SOURCES,
        "music": MUSIC_SOURCES,
        "sfx": SFX_SOURCES,
    }


def live_sources() -> Dict[str, List[str]]:
    """The sources that answered when they were last probed."""
    return {
        kind: [s["name"] for s in group if s["status"] == STATUS_LIVE]
        for kind, group in all_sources().items()
    }


from utility.core.user_agents import default_agent, headers_for  # noqa: E402

USER_AGENT = default_agent()
HEADERS = headers_for(USER_AGENT)
