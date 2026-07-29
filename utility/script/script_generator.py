from utility.config import get_config
from utility.llm.llm_router import extract_json
from utility.script.video_styles import get_style

# How many times to ask the model again when its reply is not usable JSON.
MAX_ATTEMPTS = 3

# Prefixes some models put in front of their reply before the JSON starts.
_REPLY_PREFIXES = ("content:", "content =", "content=", "output:", "json:")


def _script_from_reply(content):
    """Pull the narration text out of whatever the model replied with.

    The previous implementation sliced between the first '{' and the last '}'
    and handed that to json.loads. That fails on the two things models actually
    do: adding a sentence after the JSON ("Hope this helps!"), and returning two
    objects in a row. Both leave a trailing fragment inside the slice, so
    json.loads raises "Extra data" and the whole run dies.

    utility.llm.llm_router.extract_json already solves this properly: it walks
    the string tracking brace depth, collects every balanced candidate, tries
    the longest first and repairs common model mistakes such as a trailing
    comma. Reusing it removes a second, weaker parser from the codebase.
    """
    text = str(content or "").strip()
    lowered = text.lower()
    for prefix in _REPLY_PREFIXES:
        if lowered.startswith(prefix):
            text = text[len(prefix):].strip()
            break

    data = extract_json(text)
    if data is None:
        raise ValueError("No JSON object found in the model response.")
    if not isinstance(data, dict):
        raise ValueError(f"Expected a JSON object, got {type(data).__name__}.")

    script = data.get("script")
    if not isinstance(script, str) or not script.strip():
        raise ValueError("The JSON had no usable 'script' field.")
    return script.strip()


def clean_markdown(text):
    """Remove markdown formatting from text to prevent TTS issues."""
    import re
    
    # Remove bold formatting (**text**)
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    
    # Remove italic formatting (*text* or _text_)
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    text = re.sub(r'_(.*?)_', r'\1', text)
    
    # Remove code formatting (`text` or ```text```)
    text = re.sub(r'`(.*?)`', r'\1', text)
    text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
    
    # Remove headers (# text)
    text = re.sub(r'^#+\s+', '', text, flags=re.MULTILINE)
    
    # Remove links [text](url) -> text
    text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', text)
    
    # Clean up extra whitespace
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()


# Speech runs at roughly 140 words a minute, so the word count follows the
# requested duration instead of being fixed. The original prompt asked for about
# 140 words no matter what, which made every video the same length.
WORDS_PER_MINUTE = 140

# YouTube counts anything up to three minutes as a Short, and Instagram and
# TikTok both take vertical video of that length too. This was 120, which left
# a gap: a 150-second video was written to long-form rules and rendered
# landscape even though every platform would still have filed it as a Short.
SHORTS_MAX_SECONDS = 180

# What the two automatic modes are allowed to produce.
#
# The footage is stock. A four-minute video needs roughly eighty clips, and
# there are not eighty distinct relevant clips in the free catalogues for any
# given topic -- so the same shots repeat, and a repetitive long video is worse
# than no video. Short form is also where this kind of footage genuinely works,
# because no single shot is on screen long enough to be studied.
#
# So Trends and From-a-link stay inside the Shorts window and stay vertical.
# The Manual tab is untouched: there the user has decided, and may well have a
# reason.
AUTO_MODE_MIN_SECONDS = 30
AUTO_MODE_MAX_SECONDS = 170   # a little under the 180 limit, for safety


def clamp_auto_duration(seconds):
    """Hold an automatically chosen duration inside the Shorts window."""
    try:
        seconds = int(float(seconds))
    except (TypeError, ValueError):
        seconds = 60
    return max(AUTO_MODE_MIN_SECONDS, min(seconds, AUTO_MODE_MAX_SECONDS))


def words_for_duration(seconds):
    """How many spoken words fit in the requested number of seconds."""
    return max(20, int(round(seconds / 60.0 * WORDS_PER_MINUTE)))


def _hook_rule(seconds):
    """The opening requirement, which differs sharply by format.

    On a swipeable feed the keep-or-swipe decision is reflexive and happens at or
    before one second, so a Short's hook is effectively its first spoken words.
    The older "first three seconds" advice came from long-form discovery and is
    too slow for a Short.
    """
    if seconds < SHORTS_MAX_SECONDS:
        return (
            "HOOK: the first five to eight words ARE the hook. On a swipe feed the "
            "viewer decides within one second. Open with the surprising claim, the "
            "result or the strange fact itself. No greeting, no channel name, no "
            "'in this video', no scene setting, not one warm-up word."
        )
    return (
        "HOOK: the first ten seconds must do three things at once. Confirm the "
        "viewer is in the right place, make clear why this matters now, and open "
        "one curiosity loop that hints at the payoff without giving it away. Never "
        "open with a greeting or 'in this video'."
    )


def _ending_rule(seconds):
    """How the script should close.

    A Short that loops back to its opening line gets rewatched without the viewer
    deciding to, which is the strongest positive signal a Short can produce. A
    long video instead wants the viewer to keep watching something else, so it
    ends by opening a door rather than closing one.
    """
    if seconds < SHORTS_MAX_SECONDS:
        return (
            "ENDING: the last sentence must lead back into the first, so the video "
            "reads as one continuous thought when it repeats. Do not end with "
            "'thanks for watching' or anything that signals the video is over."
        )
    return (
        "ENDING: leave one specific question raised and unanswered so the viewer "
        "wants another video immediately. Do not send them off the platform."
    )


def build_prompt(topic, style, duration_seconds, word_count):
    """Assemble the system prompt from the style and the requested length."""
    return f"""You are a professional short-form video scriptwriter working to 2026 standards.

STYLE: {style['description']}
STRUCTURE: {style['structure']}
TONE: {style['tone']}

TARGET LENGTH: about {word_count} words, which is roughly {int(duration_seconds)} \
seconds of narration at a natural speaking pace.

{_hook_rule(duration_seconds)}
Hook approach for this style: {style['hook']}

{_ending_rule(duration_seconds)}

RULES:
- Write for the ear, not the page. This will be read aloud by a synthetic voice.
  Short sentences. Fragments are fine. Average under 15 words per sentence.
- Every sentence must carry information or move the story. No filler, no
  throat-clearing, no "let's dive in", no "buckle up".
- Treat the word count as a ceiling, not a quota. If the material runs out,
  finish early. A shorter script that satisfies beats a padded one, because the
  ranking model estimates whether a viewer would rate the video highly rather
  than counting minutes.
- Never repeat a point or restate the hook to reach the length.
- Do not write scene directions, speaker labels, timestamps or stage notes. The
  output is spoken words only.
- Write in English.

Output strictly a single parsable JSON object with one key, 'script', and nothing
else:
{{"script": "the narration text"}}"""


def generate_script(topic, style_name=None, duration_seconds=None):
    """Generate a narration script for a topic.

    style_name and duration_seconds fall back to the configured defaults, so the
    original single-argument call still works.
    """
    config = get_config()
    client = config.get_llm_client()
    model = config.get_llm_model()

    if style_name is None:
        style_name = config.get_video_style()
    if duration_seconds is None:
        duration_seconds = config.get_video_duration()

    style = get_style(style_name)
    word_count = words_for_duration(duration_seconds)

    print(
        f"[Script] style='{style_name}' duration={int(duration_seconds)}s "
        f"target={word_count} words"
    )

    prompt = build_prompt(topic, style, duration_seconds, word_count)

    # Each attempt is a fresh request. A model that wrapped its JSON in prose
    # once will usually not do it again, and dropping the temperature makes it
    # markedly less likely, so a retry is worth far more than a cleverer parser.
    last_error = None
    temperature = 0.7
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            content = _call_model(client, model, topic, prompt,
                                  temperature=temperature)

            script = _script_from_reply(content)
            script = clean_markdown(script)

            actual = len(script.split())
            drift = (actual - word_count) / word_count * 100 if word_count else 0
            print(f"[Script] {actual} words written ({drift:+.0f}% against target)")

            return script
        except Exception as e:
            last_error = e
            print(f"[Script] Attempt {attempt}/{MAX_ATTEMPTS} failed: {e}")
            # A lower temperature makes the model follow the JSON instruction
            # far more closely, which is almost always what went wrong.
            temperature = 0.3

    raise RuntimeError(
        f"The model did not return a usable script after {MAX_ATTEMPTS} "
        f"attempts. Last error: {last_error}"
    )


def _call_model(client, model, topic, prompt, temperature=0.7):
    """One request through the router's OpenAI-shaped client.

    A ``provider == 'gemini'`` branch used to sit alongside this, calling
    ``client.generate_content(contents=[...], generation_config={...})``. It was
    unreachable -- 'gemini' is not one of the four providers the config accepts
    -- and it would have raised TypeError if it ever had run, because the
    compatibility client's generate_content takes a single prompt string.
    """
    response = client.chat.completions.create(
        model=model,
        temperature=temperature,
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": topic}
        ]
    )
    return response.choices[0].message.content
