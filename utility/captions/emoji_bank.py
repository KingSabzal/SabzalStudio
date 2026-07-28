"""Emoji bank for captions.

Short form editors put an emoji next to the one word a viewer should
remember. Done well it gives the eye something to land on; done badly it
turns a caption into spam. So this module is built around restraint:

  * only one emoji per caption group, never more
  * a rate limit, so a fast talker does not get an emoji every half second
  * only concrete, picturable words, because an emoji next to an abstract
    word carries no meaning
  * a stop list of the words that are common but should never be decorated

The bank maps keyword -> emoji. Keywords are matched on the word stem, so
'exploding', 'explodes' and 'explosion' all reach the same entry.

Every emoji here is from Unicode 15.1 or earlier, which is what the bundled
Noto Color Emoji font can actually draw. Nothing is included that would
render as an empty box.
"""

import re

# --------------------------------------------------------------------------
# The bank, grouped by meaning so it stays maintainable.
# --------------------------------------------------------------------------

MONEY = {
    "money": "\U0001F4B0", "cash": "\U0001F4B5", "dollar": "\U0001F4B5",
    "dollars": "\U0001F4B5", "profit": "\U0001F4C8", "rich": "\U0001F911",
    "wealth": "\U0001F911", "wealthy": "\U0001F911", "millionaire": "\U0001F911",
    "billionaire": "\U0001F911", "billion": "\U0001F4B0", "million": "\U0001F4B0",
    "invest": "\U0001F4C8", "investment": "\U0001F4C8", "investor": "\U0001F4C8",
    "stock": "\U0001F4C9", "stocks": "\U0001F4C8", "market": "\U0001F4CA",
    "crypto": "\u20BF", "bitcoin": "\u20BF", "bank": "\U0001F3E6",
    "salary": "\U0001F4B8", "income": "\U0001F4B8", "revenue": "\U0001F4B9",
    "price": "\U0001F3F7\uFE0F", "cost": "\U0001F4B8", "expensive": "\U0001F4B8",
    "cheap": "\U0001F3F7\uFE0F", "free": "\U0001F381", "sale": "\U0001F6CD\uFE0F",
    "buy": "\U0001F6D2", "sell": "\U0001F91D", "business": "\U0001F4BC",
    "company": "\U0001F3E2", "startup": "\U0001F680", "deal": "\U0001F91D",
    "debt": "\U0001F4C9", "tax": "\U0001F9FE", "budget": "\U0001F9FE",
    "gold": "\U0001F947", "diamond": "\U0001F48E", "treasure": "\U0001F48E",
}

DANGER = {
    "danger": "\u26A0\uFE0F", "dangerous": "\u26A0\uFE0F", "warning": "\u26A0\uFE0F",
    "deadly": "\u2620\uFE0F", "death": "\U0001F480", "dead": "\U0001F480",
    "die": "\u2620\uFE0F", "died": "\U0001F480", "kill": "\u2620\uFE0F",
    "killed": "\u2620\uFE0F", "killer": "\U0001F52A", "murder": "\U0001F52A",
    "crime": "\U0001F6A8", "criminal": "\U0001F6A8", "police": "\U0001F693",
    "arrest": "\U0001F694", "prison": "\u26D3\uFE0F", "jail": "\u26D3\uFE0F",
    "gun": "\U0001F52B", "weapon": "\U0001F5E1\uFE0F", "knife": "\U0001F52A",
    "blood": "\U0001FA78", "poison": "\u2620\uFE0F", "toxic": "\u2622\uFE0F",
    "attack": "\u2694\uFE0F", "war": "\u2694\uFE0F", "fight": "\U0001F94A",
    "explode": "\U0001F4A5", "explosion": "\U0001F4A5", "bomb": "\U0001F4A3",
    "crash": "\U0001F4A5", "disaster": "\U0001F30A", "emergency": "\U0001F6A8",
    "trap": "\U0001FAA4", "threat": "\u26A0\uFE0F", "risk": "\u26A0\uFE0F",
    "scary": "\U0001F631", "terrifying": "\U0001F631", "horror": "\U0001F480",
    "nightmare": "\U0001F631", "ghost": "\U0001F47B", "monster": "\U0001F479",
    "evil": "\U0001F608", "curse": "\U0001F52E", "haunted": "\U0001F47B",
    "missing": "\U0001F50D", "disappeared": "\U0001F573\uFE0F", "vanished": "\U0001F573\uFE0F",
    "mystery": "\U0001F50D", "secret": "\U0001F92B", "hidden": "\U0001F576\uFE0F",
    "escape": "\U0001F3C3", "survive": "\U0001F64F", "survivor": "\U0001F64F",
}

SCIENCE = {
    "science": "\U0001F52C", "scientist": "\U0001F9D1\u200D\U0001F52C",
    "research": "\U0001F52C", "experiment": "\U0001F9EA", "lab": "\U0001F9EA",
    "chemical": "\u2697\uFE0F", "atom": "\u269B\uFE0F", "energy": "\u26A1",
    "electric": "\u26A1", "electricity": "\u26A1", "power": "\u26A1",
    "nuclear": "\u2622\uFE0F", "radiation": "\u2622\uFE0F", "laser": "\U0001F52B",
    "dna": "\U0001F9EC", "gene": "\U0001F9EC", "genetic": "\U0001F9EC",
    "cell": "\U0001F9A0", "bacteria": "\U0001F9A0", "virus": "\U0001F9A0",
    "microscope": "\U0001F52C", "telescope": "\U0001F52D", "discovery": "\U0001F4A1",
    "discovered": "\U0001F4A1", "invention": "\U0001F4A1", "theory": "\U0001F9E0",
    "evidence": "\U0001F50D", "proof": "\u2705", "data": "\U0001F4CA",
    "study": "\U0001F4DA", "temperature": "\U0001F321\uFE0F", "magnet": "\U0001F9F2",
    "gravity": "\U0001F34E", "physics": "\u269B\uFE0F", "math": "\U0001F522",
    "formula": "\U0001F9EE", "equation": "\U0001F9EE", "chemistry": "\u2697\uFE0F",
}

SPACE = {
    "space": "\U0001F30C", "universe": "\U0001F30C", "galaxy": "\U0001F30C",
    "star": "\u2B50", "stars": "\u2728", "sun": "\u2600\uFE0F",
    "moon": "\U0001F311", "planet": "\U0001FA90", "earth": "\U0001F30D",
    "mars": "\U0001F534", "jupiter": "\U0001FA90", "saturn": "\U0001FA90",
    "rocket": "\U0001F680", "launch": "\U0001F680", "astronaut": "\U0001F468\u200D\U0001F680",
    "nasa": "\U0001F680", "satellite": "\U0001F6F0\uFE0F", "orbit": "\U0001F6F0\uFE0F",
    "alien": "\U0001F47D", "ufo": "\U0001F6F8", "comet": "\u2604\uFE0F",
    "asteroid": "\u2604\uFE0F", "meteor": "\u2604\uFE0F", "blackhole": "\U0001F573\uFE0F",
    "cosmic": "\U0001F30C", "solar": "\u2600\uFE0F", "lunar": "\U0001F311",
    "telescope": "\U0001F52D", "spacecraft": "\U0001F680", "gravity": "\U0001F34E",
}

NATURE = {
    "ocean": "\U0001F30A", "sea": "\U0001F30A", "water": "\U0001F4A7",
    "wave": "\U0001F30A", "deep": "\U0001F30A", "underwater": "\U0001F41F",
    "fish": "\U0001F41F", "shark": "\U0001F988", "whale": "\U0001F40B",
    "octopus": "\U0001F419", "jellyfish": "\U0001FAB8", "coral": "\U0001FAB8",
    "mountain": "\u26F0\uFE0F", "volcano": "\U0001F30B", "earthquake": "\U0001F30D",
    "forest": "\U0001F332", "tree": "\U0001F333", "jungle": "\U0001F334",
    "desert": "\U0001F3DC\uFE0F", "ice": "\U0001F9CA", "snow": "\u2744\uFE0F",
    "storm": "\u26C8\uFE0F", "rain": "\U0001F327\uFE0F", "lightning": "\u26A1",
    "wind": "\U0001F4A8", "tornado": "\U0001F32A\uFE0F", "hurricane": "\U0001F32A\uFE0F",
    "fire": "\U0001F525", "flame": "\U0001F525", "burning": "\U0001F525",
    "glow": "\u2728", "glowing": "\u2728", "light": "\U0001F4A1",
    "dark": "\U0001F311", "darkness": "\U0001F311", "night": "\U0001F319",
    "cave": "\U0001F573\uFE0F", "island": "\U0001F3DD\uFE0F", "river": "\U0001F3DE\uFE0F",
    "flower": "\U0001F338", "plant": "\U0001F331", "seed": "\U0001F331",
}

ANIMALS = {
    "animal": "\U0001F43E", "dog": "\U0001F436", "cat": "\U0001F431",
    "bird": "\U0001F426", "eagle": "\U0001F985", "owl": "\U0001F989",
    "lion": "\U0001F981", "tiger": "\U0001F42F", "bear": "\U0001F43B",
    "wolf": "\U0001F43A", "fox": "\U0001F98A", "elephant": "\U0001F418",
    "snake": "\U0001F40D", "spider": "\U0001F577\uFE0F", "bee": "\U0001F41D",
    "ant": "\U0001F41C", "butterfly": "\U0001F98B", "frog": "\U0001F438",
    "turtle": "\U0001F422", "penguin": "\U0001F427", "monkey": "\U0001F412",
    "horse": "\U0001F434", "dinosaur": "\U0001F996", "dragon": "\U0001F409",
    "creature": "\U0001F9A0", "species": "\U0001F43E", "predator": "\U0001F988",
    "hunt": "\U0001F43E", "prey": "\U0001F43E", "egg": "\U0001F95A",
}

BODY_HEALTH = {
    "brain": "\U0001F9E0", "heart": "\u2764\uFE0F", "eye": "\U0001F440",
    "eyes": "\U0001F440", "blood": "\U0001FA78", "bone": "\U0001F9B4",
    "muscle": "\U0001F4AA", "strong": "\U0001F4AA", "strength": "\U0001F4AA",
    "sleep": "\U0001F634", "tired": "\U0001F634", "dream": "\U0001F4AD",
    "health": "\U0001F49A", "healthy": "\U0001F49A", "sick": "\U0001F912",
    "disease": "\U0001F9A0", "cancer": "\U0001F396\uFE0F", "medicine": "\U0001F48A",
    "pill": "\U0001F48A", "doctor": "\U0001F468\u200D\u2695\uFE0F", "hospital": "\U0001F3E5",
    "pain": "\U0001F915", "injury": "\U0001FA79", "cure": "\U0001F48A",
    "food": "\U0001F37D\uFE0F", "eat": "\U0001F37D\uFE0F", "hungry": "\U0001F37D\uFE0F",
    "coffee": "\u2615", "water": "\U0001F4A7", "sugar": "\U0001F36C",
    "exercise": "\U0001F3CB\uFE0F", "workout": "\U0001F3CB\uFE0F", "gym": "\U0001F3CB\uFE0F",
    "run": "\U0001F3C3", "running": "\U0001F3C3", "breathe": "\U0001FAC1",
}

TECH = {
    "technology": "\U0001F4BB", "computer": "\U0001F4BB", "phone": "\U0001F4F1",
    "internet": "\U0001F310", "online": "\U0001F310", "website": "\U0001F310",
    "code": "\U0001F4BB", "coding": "\U0001F4BB", "software": "\U0001F4BE",
    "app": "\U0001F4F1", "robot": "\U0001F916", "ai": "\U0001F916",
    "algorithm": "\U0001F9E0", "machine": "\u2699\uFE0F", "engine": "\u2699\uFE0F",
    "hack": "\U0001F5A5\uFE0F", "hacker": "\U0001F575\uFE0F", "password": "\U0001F510",
    "security": "\U0001F512", "encrypt": "\U0001F510", "privacy": "\U0001F512",
    "camera": "\U0001F4F7", "video": "\U0001F3AC", "screen": "\U0001F5A5\uFE0F",
    "battery": "\U0001F50B", "chip": "\U0001F9E0", "server": "\U0001F5A5\uFE0F",
    "network": "\U0001F310", "signal": "\U0001F4F6", "wifi": "\U0001F4F6",
    "car": "\U0001F697", "plane": "\u2708\uFE0F", "train": "\U0001F686",
    "engineer": "\U0001F477", "build": "\U0001F528", "built": "\U0001F528",
    "invention": "\U0001F4A1", "future": "\U0001F52E", "drone": "\U0001F681",
}

TIME_HISTORY = {
    "time": "\u23F1\uFE0F", "clock": "\U0001F551", "hour": "\u23F1\uFE0F",
    "minute": "\u23F1\uFE0F", "second": "\u23F1\uFE0F", "day": "\u2600\uFE0F",
    "year": "\U0001F4C5", "century": "\U0001F4C5", "ancient": "\U0001F3DB\uFE0F",
    "history": "\U0001F4DC", "historical": "\U0001F4DC", "past": "\u23EA",
    "future": "\u23E9", "old": "\U0001F4DC", "new": "\u2728",
    "king": "\U0001F451", "queen": "\U0001F451", "empire": "\U0001F3F0",
    "castle": "\U0001F3F0", "war": "\u2694\uFE0F", "battle": "\u2694\uFE0F",
    "soldier": "\U0001F396\uFE0F", "pyramid": "\U0001F3DB\uFE0F", "tomb": "\u26B0\uFE0F",
    "map": "\U0001F5FA\uFE0F", "explorer": "\U0001F9ED", "compass": "\U0001F9ED",
    "ship": "\U0001F6A2", "treasure": "\U0001F48E", "artifact": "\U0001F3FA",
    "legend": "\U0001F4DC", "myth": "\U0001F409", "civilization": "\U0001F3DB\uFE0F",
}

EMOTION_REACTION = {
    "amazing": "\U0001F929", "incredible": "\U0001F92F", "unbelievable": "\U0001F92F",
    "shocking": "\U0001F633", "shocked": "\U0001F633", "crazy": "\U0001F92A",
    "insane": "\U0001F92A", "wild": "\U0001F92A", "weird": "\U0001F914",
    "strange": "\U0001F914", "bizarre": "\U0001F914", "impossible": "\U0001F92F",
    "perfect": "\U0001F44C", "best": "\U0001F947", "worst": "\U0001F44E",
    "wrong": "\u274C", "right": "\u2705", "correct": "\u2705",
    "true": "\u2705", "false": "\u274C", "lie": "\U0001F925",
    "truth": "\U0001F50D", "fact": "\U0001F4CC", "myth": "\u274C",
    "win": "\U0001F3C6", "winner": "\U0001F3C6", "lose": "\U0001F614",
    "fail": "\u274C", "failure": "\u274C", "success": "\U0001F3C6",
    "happy": "\U0001F60A", "sad": "\U0001F622", "angry": "\U0001F620",
    "love": "\u2764\uFE0F", "hate": "\U0001F620", "fear": "\U0001F628",
    "laugh": "\U0001F602", "funny": "\U0001F602", "smile": "\U0001F60A",
    "cry": "\U0001F622", "shout": "\U0001F4E2", "scream": "\U0001F631",
    "surprise": "\U0001F381", "wow": "\U0001F92F", "boom": "\U0001F4A5",
}

ACTION_IDEA = {
    "idea": "\U0001F4A1", "think": "\U0001F914", "thought": "\U0001F4AD",
    "question": "\u2753", "answer": "\U0001F4A1", "problem": "\u26A0\uFE0F",
    "solution": "\u2705", "solve": "\u2705", "learn": "\U0001F4DA",
    "teach": "\U0001F9D1\u200D\U0001F3EB", "school": "\U0001F3EB", "student": "\U0001F393",
    "book": "\U0001F4D6", "read": "\U0001F4D6", "write": "\u270D\uFE0F",
    "listen": "\U0001F442", "watch": "\U0001F440", "look": "\U0001F440",
    "search": "\U0001F50D", "find": "\U0001F50D", "found": "\U0001F50D",
    "start": "\u25B6\uFE0F", "stop": "\U0001F6D1", "wait": "\u270B",
    "fast": "\u26A1", "slow": "\U0001F40C", "speed": "\U0001F4A8",
    "grow": "\U0001F331", "growth": "\U0001F4C8", "change": "\U0001F504",
    "repeat": "\U0001F501", "first": "\U0001F947", "last": "\U0001F3C1",
    "big": "\U0001F4CF", "huge": "\U0001F4CF", "giant": "\U0001F5FF",
    "small": "\U0001F50E", "tiny": "\U0001F50E", "world": "\U0001F30D",
    "people": "\U0001F465", "human": "\U0001F9CD", "child": "\U0001F9D2",
    "home": "\U0001F3E0", "city": "\U0001F3D9\uFE0F", "country": "\U0001F5FA\uFE0F",
    "trophy": "\U0001F3C6", "record": "\U0001F3C5", "champion": "\U0001F3C6",
    "goal": "\U0001F3AF", "target": "\U0001F3AF", "plan": "\U0001F4CB",
    "music": "\U0001F3B5", "song": "\U0001F3B5", "sound": "\U0001F50A",
    "game": "\U0001F3AE", "play": "\U0001F3AE", "sport": "\u26BD",
    "art": "\U0001F3A8", "movie": "\U0001F3AC", "story": "\U0001F4D6",
}

# One flat bank.
EMOJI_BANK = {}
for _group in (MONEY, DANGER, SCIENCE, SPACE, NATURE, ANIMALS, BODY_HEALTH,
               TECH, TIME_HISTORY, EMOTION_REACTION, ACTION_IDEA):
    EMOJI_BANK.update(_group)


# Words that are common enough to match something by accident, or so abstract
# that an emoji beside them means nothing. Never decorated.
STOP_WORDS = {
    "a", "an", "the", "and", "or", "but", "if", "then", "than", "so", "because",
    "as", "of", "at", "by", "for", "with", "about", "into", "to", "from", "in",
    "on", "off", "over", "under", "out", "up", "down", "is", "are", "was",
    "were", "be", "been", "being", "have", "has", "had", "do", "does", "did",
    "will", "would", "can", "could", "should", "may", "might", "must", "this",
    "that", "these", "those", "it", "its", "he", "she", "they", "them", "we",
    "you", "your", "i", "me", "my", "his", "her", "their", "our", "one", "two",
    "not", "no", "yes", "just", "only", "very", "really", "more", "most",
    "some", "any", "all", "every", "each", "other", "same", "own", "here",
    "there", "when", "where", "how", "why", "what", "who", "which", "now",
    "even", "also", "still", "back", "way", "thing", "things", "something",
    "nothing", "anything", "everything", "get", "got", "make", "made", "take",
    "took", "come", "came", "go", "went", "know", "knew", "see", "saw", "say",
    "said", "use", "used", "want", "need", "like", "let", "put", "keep",
}

# Suffixes stripped when looking a word up, longest first.
_SUFFIXES = ("iest", "ing", "ies", "est", "ed", "es", "ly", "er", "s")

_WORD_RE = re.compile(r"[a-z']+")

# Never more than this many emoji per minute of narration, however many
# keywords match. Roughly one every six seconds.
DEFAULT_PER_MINUTE = 10


def _stems(word):
    """The forms of a word worth looking up, most exact first."""
    word = _WORD_RE.sub(lambda m: m.group(0), word.lower().strip())
    word = re.sub(r"[^a-z]", "", word)
    if not word:
        return []

    forms = [word]
    for suffix in _SUFFIXES:
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            stem = word[: -len(suffix)]
            forms.append(stem)
            # 'studies' -> 'studi' -> 'study', 'running' -> 'runn' -> 'run'
            if suffix in ("ies", "iest"):
                forms.append(stem + "y")
            if len(stem) > 3 and stem[-1] == stem[-2]:
                forms.append(stem[:-1])
            if suffix in ("ed", "ing"):
                forms.append(stem + "e")
    return forms


def emoji_for_word(word):
    """The emoji for one word, or None."""
    plain = re.sub(r"[^a-z]", "", str(word).lower())
    if not plain or plain in STOP_WORDS or len(plain) < 3:
        return None
    for form in _stems(word):
        if form in STOP_WORDS:
            continue
        found = EMOJI_BANK.get(form)
        if found:
            return found
    return None


def pick_for_text(text):
    """The single best emoji for a caption group, or None.

    When several words match, the longest word wins. A long word is more
    specific, so 'explosion' beats 'big' in the same phrase.
    """
    best_word, best_emoji = None, None
    for word in str(text).split():
        found = emoji_for_word(word)
        if found and (best_word is None or len(word) > len(best_word)):
            best_word, best_emoji = word, found
    return best_emoji


def annotate(groups, per_minute=DEFAULT_PER_MINUTE, enabled=True):
    """Choose an emoji for each caption group, respecting the rate limit.

    `groups` is the output of caption_layout.group_captions:
    [((start, end), text_or_word_list), ...]

    Returns a list the same length, holding an emoji or None per group, so
    the caller can keep its own structure untouched.
    """
    if not enabled or not groups:
        return [None] * len(groups)

    picks = [None] * len(groups)
    if per_minute <= 0:
        return picks

    min_gap = 60.0 / per_minute
    last_at = None
    used = set()

    for index, ((start, _end), payload) in enumerate(groups):
        text = payload if isinstance(payload, str) else " ".join(
            w for w, _, _ in payload
        )
        emoji = pick_for_text(text)
        if not emoji:
            continue
        # Do not repeat the same emoji, it stops reading as emphasis.
        if emoji in used:
            continue
        if last_at is not None and start - last_at < min_gap:
            continue
        picks[index] = emoji
        used.add(emoji)
        last_at = start

    return picks


def bank_size():
    """How many keywords the bank holds."""
    return len(EMOJI_BANK)


def distinct_emoji():
    """How many different emoji the bank can produce."""
    return len(set(EMOJI_BANK.values()))
