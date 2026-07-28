"""Emotion and pacing for narration.

A neural voice reading flat text sounds like a neural voice reading flat text.
It is technically clear and completely lifeless, because it delivers a sentence
about a child dying exactly the same way as a sentence about a discount.

Two things fix most of that, and neither needs a paid service.

**Emotion.** The sentiment of the writing is detected and turned into speed,
pitch and volume adjustments. Sad writing is slowed and lowered; excitement is
raised and quickened. EdgeTTS accepts these per request, so the change is real
rather than cosmetic.

**Pauses.** Human narrators stop. They stop hard after a revelation, briefly
between clauses, and they never run a list together at one speed. Silence is
inserted as real audio between sentences, at the places a person would
naturally breathe: after the hook, before a contrast, and at the end of a beat.

Detection is deliberately lexical rather than a machine-learning model. A model
would be more accurate on ambiguous prose, but it would also add a heavy
dependency and seconds of startup for a task where the writing is short, plain
and written by another model that follows instructions.
"""

import re
from typing import Dict, List, Tuple

# ----------------------------------------------------------------------
# Emotion vocabulary
# ----------------------------------------------------------------------
# Weighted so a single strong word outranks several mild ones. "Massacre" should
# dominate a sentence, "quiet" should only nudge it.
EMOTION_WORDS: Dict[str, Dict[str, float]] = {
    "sad": {
        "died": 3, "death": 3, "killed": 3, "murdered": 3, "dead": 2.5,
        "tragedy": 3, "tragic": 3, "grief": 3, "mourning": 3, "funeral": 2.5,
        "lost": 1.5, "loss": 2, "alone": 2, "lonely": 2, "abandoned": 2.5,
        "suffering": 2.5, "pain": 2, "cried": 2, "tears": 2, "sorrow": 3,
        "never returned": 3, "disappeared": 2, "vanished": 2, "gone": 1.5,
        "failed": 1.5, "destroyed": 2, "ruined": 2, "collapsed": 2,
        "victim": 2.5, "victims": 2.5, "buried": 2, "starved": 3,
    },
    "tense": {
        "suddenly": 2.5, "without warning": 3, "trapped": 3, "escape": 2,
        "danger": 2.5, "dangerous": 2.5, "threat": 2.5, "attack": 2.5,
        "screaming": 3, "panic": 3, "terrified": 3, "fear": 2.5, "afraid": 2,
        "desperate": 2.5, "survival": 2, "survive": 2, "critical": 2,
        "seconds": 1.5, "running out": 2.5, "too late": 3, "last chance": 3,
        "collapse": 2, "emergency": 2.5, "warning": 2, "closing in": 3,
    },
    "excited": {
        "incredible": 2.5, "amazing": 2.5, "astonishing": 3, "extraordinary": 3,
        "unbelievable": 3, "stunning": 2.5, "spectacular": 2.5, "remarkable": 2,
        "breakthrough": 2.5, "revolutionary": 2.5, "record": 2, "fastest": 2,
        "largest": 2, "biggest": 2, "first ever": 2.5, "never before": 2.5,
        "discovered": 2, "finally": 2, "success": 2, "triumph": 2.5,
        "wait until": 2.5, "get this": 2.5, "here is the best part": 3,
    },
    "curious": {
        "why": 1.5, "how": 1.2, "what if": 2.5, "mystery": 2.5, "strange": 2,
        "puzzling": 2.5, "unexplained": 3, "nobody knows": 3, "unknown": 2,
        "secret": 2, "hidden": 2, "question": 1.5, "wondered": 2,
        "turns out": 2, "it appears": 1.5, "scientists": 1.2, "theory": 1.5,
    },
    "serious": {
        "however": 1.2, "research": 1.5, "study": 1.5, "evidence": 2,
        "data": 1.5, "according to": 1.5, "official": 2, "government": 1.5,
        "investigation": 2, "report": 1.5, "confirmed": 2, "documented": 2,
        "billion": 1.5, "million": 1.2, "percent": 1.2,
    },
}

# How each emotion changes delivery. Values stay conservative on purpose: pushed
# further, EdgeTTS starts to sound like a cartoon rather than a person.
EMOTION_PROSODY: Dict[str, Dict[str, str]] = {
    "sad":     {"rate": "-10%", "pitch": "-6Hz",  "volume": "-4%"},
    "tense":   {"rate": "+6%",  "pitch": "+3Hz",  "volume": "+3%"},
    "excited": {"rate": "+9%",  "pitch": "+8Hz",  "volume": "+5%"},
    "curious": {"rate": "-3%",  "pitch": "+2Hz",  "volume": "+0%"},
    "serious": {"rate": "-5%",  "pitch": "-2Hz",  "volume": "+0%"},
    "neutral": {"rate": "+0%",  "pitch": "+0Hz",  "volume": "+0%"},
}

# Pause lengths in milliseconds, chosen to match how people actually speak.
PAUSE_AFTER_HOOK = 420        # let the opening claim land
PAUSE_SENTENCE = 260          # ordinary full stop
PAUSE_PARAGRAPH = 520         # a change of subject
PAUSE_BEFORE_CONTRAST = 340   # "but", "however" - the turn needs room
PAUSE_AFTER_QUESTION = 400    # give the viewer a beat to wonder
PAUSE_AROUND_NUMBER = 180     # a statistic reads better isolated
PAUSE_BEFORE_REVEAL = 480     # the payoff

# Words that signal the sentence is about to turn.
CONTRAST_WORDS = (
    "but", "however", "yet", "although", "though", "instead", "despite",
    "nevertheless", "still", "except", "unless", "whereas",
)

# Phrases that announce a payoff, which deserves a real silence before it.
REVEAL_PHRASES = (
    "turns out", "the truth is", "here is why", "here's why", "the answer is",
    "what happened next", "the reason is", "and then", "until", "finally",
    "the problem is", "the catch is", "nobody expected",
)


def split_sentences(text: str) -> List[str]:
    """Split narration into sentences, keeping their punctuation."""
    parts = re.split(r"(?<=[.!?])\s+", (text or "").strip())
    return [p.strip() for p in parts if p.strip()]


def detect_emotion(sentence: str) -> Tuple[str, float]:
    """Return the dominant emotion of a sentence and how strongly it registers.

    Scores are normalised by a fixed divisor rather than by sentence length, so
    a long sentence with one sad word is not treated as intensely sad.
    """
    lowered = " " + re.sub(r"[^\w\s]", " ", (sentence or "").lower()) + " "
    scores: Dict[str, float] = {}

    for emotion, vocabulary in EMOTION_WORDS.items():
        total = 0.0
        for phrase, weight in vocabulary.items():
            if " " in phrase:
                if phrase in lowered:
                    total += weight
            elif f" {phrase} " in lowered:
                total += weight
        if total:
            scores[emotion] = total

    if not scores:
        return "neutral", 0.0

    best = max(scores, key=scores.get)
    return best, min(scores[best] / 6.0, 1.0)


def scale_prosody(emotion: str, intensity: float) -> Dict[str, str]:
    """Blend the emotion's prosody towards neutral according to intensity.

    A sentence that is faintly sad should not be delivered like a eulogy, so the
    adjustment is scaled rather than applied at full strength every time.
    """
    target = EMOTION_PROSODY.get(emotion, EMOTION_PROSODY["neutral"])
    if emotion == "neutral" or intensity <= 0:
        return dict(EMOTION_PROSODY["neutral"])

    # Never fall below a third of the effect, or the emotion is inaudible.
    factor = max(0.34, min(intensity, 1.0))
    out = {}
    for key, value in target.items():
        number = float(re.sub(r"[^\d.+-]", "", value) or 0)
        unit = "Hz" if "Hz" in value else "%"
        out[key] = f"{number * factor:+.0f}{unit}"
    return out


def _needs_reveal_pause(sentence: str) -> bool:
    """True when a sentence announces a payoff."""
    lowered = sentence.lower()
    return any(phrase in lowered for phrase in REVEAL_PHRASES)


def _starts_with_contrast(sentence: str) -> bool:
    """True when a sentence opens on a turn, which deserves room before it."""
    words = re.sub(r"[^\w\s]", "", sentence.strip().lower()).split()
    return bool(words) and words[0] in CONTRAST_WORDS


def pause_after(sentences: List[str], index: int) -> int:
    """Milliseconds of silence to place after sentence *index*.

    Human narrators do not pause uniformly. They stop hard after the opening
    claim, leave room for a question to register, and hesitate before a reveal.
    """
    if index >= len(sentences) - 1:
        return 0

    current = sentences[index]
    following = sentences[index + 1]

    if index == 0:
        return PAUSE_AFTER_HOOK              # the opening claim needs to land
    if current.rstrip().endswith("?"):
        return PAUSE_AFTER_QUESTION
    if _needs_reveal_pause(following):
        return PAUSE_BEFORE_REVEAL
    if _starts_with_contrast(following):
        return PAUSE_BEFORE_CONTRAST
    if (index + 1) % 4 == 0:
        return PAUSE_PARAGRAPH               # a breath every few sentences
    return PAUSE_SENTENCE


def build_segments(text: str) -> List[Dict[str, object]]:
    """Break narration into segments, each with its own delivery and pause.

    EdgeTTS applies rate, pitch and volume per request and does not support
    SSML: passing markup to Communicate makes it read the tags aloud, which
    turned a nine second clip into seventy six in testing. Emotion is therefore
    applied by synthesising each sentence separately with its own settings, and
    the pauses are real silence inserted between the pieces.
    """
    sentences = split_sentences(text)
    if not sentences:
        sentences = [(text or "").strip()]

    segments = []
    for index, sentence in enumerate(sentences):
        emotion, intensity = detect_emotion(sentence)
        segments.append({
            "text": sentence,
            "emotion": emotion,
            "intensity": round(intensity, 2),
            "prosody": scale_prosody(emotion, intensity),
            "pause_ms": pause_after(sentences, index),
        })
    return segments


def analyse(text: str) -> List[Dict[str, object]]:
    """Per-sentence emotion report, for logging and for checking the result."""
    report = []
    for sentence in split_sentences(text):
        emotion, intensity = detect_emotion(sentence)
        report.append({
            "sentence": sentence,
            "emotion": emotion,
            "intensity": round(intensity, 2),
            "prosody": scale_prosody(emotion, intensity),
        })
    return report


def dominant_emotion(text: str) -> str:
    """The overall emotional colour of a whole script."""
    counts: Dict[str, float] = {}
    for entry in analyse(text):
        if entry["emotion"] != "neutral":
            counts[entry["emotion"]] = counts.get(entry["emotion"], 0) + entry["intensity"]
    return max(counts, key=counts.get) if counts else "neutral"
