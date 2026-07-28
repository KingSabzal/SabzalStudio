"""Voice catalogue.

The original project used whatever single voice was named in EDGETTS_VOICE, with
a handful of examples in the comments. That is narrow for a tool meant to produce
many videos: the same voice on every upload is one of the things that makes a
channel sound automated.

Every identifier here was read from the live Microsoft catalogue rather than
typed from memory, so none of them is invented. The trait words are Microsoft's
own personality tags, which is what makes automatic selection possible: a mystery
script wants a voice tagged authoritative, not one tagged cheerful.
"""

import hashlib
from typing import Dict, List, Optional

# id -> what the voice sounds like and what it suits.
#
# ``traits``   Microsoft's personality tags, lightly normalised
# ``accent``   where the voice is from, so a channel can vary
# ``best_for`` the script styles this voice carries well
VOICES: Dict[str, Dict[str, object]] = {
    # ------------------------------------------------------------------
    # American - the widest range, and the default for most content
    # ------------------------------------------------------------------
    "en-US-AndrewNeural": {
        "gender": "male", "accent": "American",
        "traits": ["warm", "confident", "authentic", "honest"],
        "best_for": ["explainer", "story", "science", "history", "biography"],
    },
    "en-US-AndrewMultilingualNeural": {
        "gender": "male", "accent": "American",
        "traits": ["warm", "confident", "authentic", "honest"],
        "best_for": ["explainer", "biography", "case_study"],
    },
    "en-US-BrianNeural": {
        "gender": "male", "accent": "American",
        "traits": ["approachable", "casual", "sincere"],
        "best_for": ["tutorial", "opinion", "mistakes", "technology"],
    },
    "en-US-BrianMultilingualNeural": {
        "gender": "male", "accent": "American",
        "traits": ["approachable", "casual", "sincere"],
        "best_for": ["tutorial", "case_study", "technology"],
    },
    "en-US-ChristopherNeural": {
        "gender": "male", "accent": "American",
        "traits": ["reliable", "authoritative"],
        "best_for": ["news", "true_crime", "disaster", "finance"],
    },
    "en-US-EricNeural": {
        "gender": "male", "accent": "American",
        "traits": ["rational", "measured"],
        "best_for": ["science", "explainer", "finance", "health"],
    },
    "en-US-SteffanNeural": {
        "gender": "male", "accent": "American",
        "traits": ["rational", "steady"],
        "best_for": ["explainer", "case_study", "comparison"],
    },
    "en-US-GuyNeural": {
        "gender": "male", "accent": "American",
        "traits": ["passionate", "energetic"],
        "best_for": ["motivational", "facts", "countdown", "listicle"],
    },
    "en-US-RogerNeural": {
        "gender": "male", "accent": "American",
        "traits": ["lively", "bright"],
        "best_for": ["facts", "listicle", "what_if", "animals"],
    },
    "en-US-AriaNeural": {
        "gender": "female", "accent": "American",
        "traits": ["positive", "confident"],
        "best_for": ["explainer", "news", "listicle", "technology"],
    },
    "en-US-AvaNeural": {
        "gender": "female", "accent": "American",
        "traits": ["expressive", "caring", "pleasant", "friendly"],
        "best_for": ["story", "psychology", "health", "motivational"],
    },
    "en-US-AvaMultilingualNeural": {
        "gender": "female", "accent": "American",
        "traits": ["expressive", "caring", "pleasant", "friendly"],
        "best_for": ["story", "biography", "psychology"],
    },
    "en-US-EmmaNeural": {
        "gender": "female", "accent": "American",
        "traits": ["cheerful", "clear", "conversational"],
        "best_for": ["tutorial", "travel", "facts", "comparison"],
    },
    "en-US-EmmaMultilingualNeural": {
        "gender": "female", "accent": "American",
        "traits": ["cheerful", "clear", "conversational"],
        "best_for": ["tutorial", "explainer", "travel"],
    },
    "en-US-JennyNeural": {
        "gender": "female", "accent": "American",
        "traits": ["friendly", "considerate", "comforting"],
        "best_for": ["health", "psychology", "motivational", "story"],
    },
    "en-US-MichelleNeural": {
        "gender": "female", "accent": "American",
        "traits": ["friendly", "pleasant"],
        "best_for": ["listicle", "travel", "nature", "animals"],
    },
    "en-US-AnaNeural": {
        "gender": "female", "accent": "American",
        "traits": ["cute", "young"],
        "best_for": ["animals", "what_if"],
    },

    # ------------------------------------------------------------------
    # British and Irish - documentary weight
    # ------------------------------------------------------------------
    "en-GB-RyanNeural": {
        "gender": "male", "accent": "British",
        "traits": ["friendly", "measured"],
        "best_for": ["history", "mystery", "nature", "myth_busting"],
    },
    "en-GB-ThomasNeural": {
        "gender": "male", "accent": "British",
        "traits": ["calm", "considered"],
        "best_for": ["history", "science", "ocean", "space"],
    },
    "en-GB-SoniaNeural": {
        "gender": "female", "accent": "British",
        "traits": ["friendly", "warm"],
        "best_for": ["nature", "history", "story", "mystery"],
    },
    "en-GB-LibbyNeural": {
        "gender": "female", "accent": "British",
        "traits": ["friendly", "bright"],
        "best_for": ["explainer", "travel", "listicle"],
    },
    "en-GB-MaisieNeural": {
        "gender": "female", "accent": "British",
        "traits": ["young", "light"],
        "best_for": ["animals", "what_if", "facts"],
    },
    "en-IE-ConnorNeural": {
        "gender": "male", "accent": "Irish",
        "traits": ["friendly", "conversational"],
        "best_for": ["story", "opinion", "travel"],
    },
    "en-IE-EmilyNeural": {
        "gender": "female", "accent": "Irish",
        "traits": ["friendly", "warm"],
        "best_for": ["story", "history", "travel"],
    },

    # ------------------------------------------------------------------
    # Australian, New Zealand, Canadian
    # ------------------------------------------------------------------
    "en-AU-WilliamMultilingualNeural": {
        "gender": "male", "accent": "Australian",
        "traits": ["friendly", "relaxed"],
        "best_for": ["nature", "animals", "travel", "facts"],
    },
    "en-AU-NatashaNeural": {
        "gender": "female", "accent": "Australian",
        "traits": ["friendly", "positive"],
        "best_for": ["travel", "nature", "listicle", "health"],
    },
    "en-NZ-MitchellNeural": {
        "gender": "male", "accent": "New Zealand",
        "traits": ["friendly", "grounded"],
        "best_for": ["nature", "survival", "travel"],
    },
    "en-NZ-MollyNeural": {
        "gender": "female", "accent": "New Zealand",
        "traits": ["friendly", "clear"],
        "best_for": ["nature", "explainer", "travel"],
    },
    "en-CA-LiamNeural": {
        "gender": "male", "accent": "Canadian",
        "traits": ["friendly", "even"],
        "best_for": ["explainer", "technology", "case_study"],
    },
    "en-CA-ClaraNeural": {
        "gender": "female", "accent": "Canadian",
        "traits": ["friendly", "clear"],
        "best_for": ["explainer", "news", "health"],
    },

    # ------------------------------------------------------------------
    # South Asian and South East Asian
    # ------------------------------------------------------------------
    "en-IN-NeerjaExpressiveNeural": {
        "gender": "female", "accent": "Indian",
        "traits": ["expressive", "warm"],
        "best_for": ["story", "motivational", "psychology"],
    },
    "en-IN-NeerjaNeural": {
        "gender": "female", "accent": "Indian",
        "traits": ["friendly", "clear"],
        "best_for": ["explainer", "tutorial", "finance"],
    },
    "en-IN-PrabhatNeural": {
        "gender": "male", "accent": "Indian",
        "traits": ["friendly", "steady"],
        "best_for": ["explainer", "technology", "finance"],
    },
    "en-SG-LunaNeural": {
        "gender": "female", "accent": "Singaporean",
        "traits": ["friendly", "clear"],
        "best_for": ["explainer", "technology", "listicle"],
    },
    "en-SG-WayneNeural": {
        "gender": "male", "accent": "Singaporean",
        "traits": ["friendly", "even"],
        "best_for": ["explainer", "news", "technology"],
    },
    "en-PH-RosaNeural": {
        "gender": "female", "accent": "Filipino",
        "traits": ["friendly", "warm"],
        "best_for": ["story", "travel", "motivational"],
    },
    "en-PH-JamesNeural": {
        "gender": "male", "accent": "Filipino",
        "traits": ["friendly", "clear"],
        "best_for": ["explainer", "listicle", "travel"],
    },
    "en-HK-YanNeural": {
        "gender": "female", "accent": "Hong Kong",
        "traits": ["friendly", "clear"],
        "best_for": ["explainer", "news"],
    },
    "en-HK-SamNeural": {
        "gender": "male", "accent": "Hong Kong",
        "traits": ["friendly", "even"],
        "best_for": ["explainer", "technology"],
    },

    # ------------------------------------------------------------------
    # African
    # ------------------------------------------------------------------
    "en-ZA-LeahNeural": {
        "gender": "female", "accent": "South African",
        "traits": ["friendly", "warm"],
        "best_for": ["nature", "story", "history"],
    },
    "en-ZA-LukeNeural": {
        "gender": "male", "accent": "South African",
        "traits": ["friendly", "grounded"],
        "best_for": ["nature", "animals", "survival"],
    },
    "en-KE-AsiliaNeural": {
        "gender": "female", "accent": "Kenyan",
        "traits": ["friendly", "warm"],
        "best_for": ["story", "nature", "travel"],
    },
    "en-KE-ChilembaNeural": {
        "gender": "male", "accent": "Kenyan",
        "traits": ["friendly", "steady"],
        "best_for": ["nature", "history", "biography"],
    },
    "en-NG-EzinneNeural": {
        "gender": "female", "accent": "Nigerian",
        "traits": ["friendly", "clear"],
        "best_for": ["story", "explainer", "motivational"],
    },
    "en-NG-AbeoNeural": {
        "gender": "male", "accent": "Nigerian",
        "traits": ["friendly", "warm"],
        "best_for": ["story", "history", "biography"],
    },
    "en-TZ-ImaniNeural": {
        "gender": "female", "accent": "Tanzanian",
        "traits": ["friendly", "clear"],
        "best_for": ["nature", "story", "travel"],
    },
    "en-TZ-ElimuNeural": {
        "gender": "male", "accent": "Tanzanian",
        "traits": ["friendly", "steady"],
        "best_for": ["nature", "history", "survival"],
    },
}

DEFAULT_VOICE = "en-US-AndrewNeural"


def list_voices() -> List[str]:
    """Every voice identifier in the catalogue."""
    return sorted(VOICES)


def voice_exists(voice_id: str) -> bool:
    """True when the identifier is one we know about."""
    return (voice_id or "").strip() in VOICES


def describe(voice_id: str) -> str:
    """A one-line human description, for logs and documentation."""
    entry = VOICES.get(voice_id)
    if not entry:
        return voice_id
    return f"{entry['accent']} {entry['gender']}, {', '.join(entry['traits'][:3])}"


def voices_for_style(style: str) -> List[str]:
    """Voices whose tags suit a script style."""
    key = (style or "").strip().lower()
    return sorted(vid for vid, v in VOICES.items() if key in v["best_for"])


def pick_voice(style: str, seed: Optional[str] = None) -> str:
    """Choose a voice that suits the style.

    A channel that uses one voice for everything sounds automated, so the choice
    varies with the topic while staying inside the set that suits the style.

    The seed makes the choice repeatable. That matters because the pipeline can
    resume from a checkpoint: a video regenerated after a failure must not
    suddenly change narrator halfway through.
    """
    candidates = voices_for_style(style)
    if not candidates:
        return DEFAULT_VOICE
    if not seed:
        return candidates[0]

    # A stable digest, because Python's hash() is randomised per process and
    # would give a different voice on every run.
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    return candidates[int(digest, 16) % len(candidates)]


def sibling_voices(voice_id: str, limit: int = 4) -> List[str]:
    """Other voices with the same accent and gender.

    Used when a specific voice fails. Swapping to a similar one keeps the video
    sounding as intended, instead of dropping straight to a robotic fallback.
    """
    entry = VOICES.get(voice_id)
    if not entry:
        return [DEFAULT_VOICE]

    same = [
        vid for vid, v in VOICES.items()
        if vid != voice_id
        and v["accent"] == entry["accent"]
        and v["gender"] == entry["gender"]
    ]
    if len(same) < limit:
        same += [
            vid for vid, v in VOICES.items()
            if vid != voice_id and vid not in same and v["gender"] == entry["gender"]
        ]
    return same[:limit]
