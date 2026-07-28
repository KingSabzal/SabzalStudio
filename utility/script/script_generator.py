import json
from utility.config import get_config
from utility.script.video_styles import get_style


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

# Below this a video is a vertical Short and is written to different rules.
SHORTS_MAX_SECONDS = 120


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
    provider = config.get_llm_provider()

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

    if provider == 'gemini':
        content = _call_gemini(client, topic, prompt)
    else:
        content = _call_openai_groq(client, model, topic, prompt)

    try:
        # Remove any common prefix that might be added by LLMs (content:, content =, content=, content: , etc.)
        text = content
        for prefix in ['content:', 'content =', 'content =', 'content: ', 'content=']:
            if text.startswith(prefix):
                text = text[len(prefix):].strip()
                break

        # Try to find complete JSON object or array
        json_start = text.find('{')
        json_end = text.rfind('}')

        if json_start == -1 or json_end == -1:
            raise ValueError("No valid JSON found in response")

        script_text = text[json_start:json_end+1]
        script = json.loads(script_text)["script"]
        script = clean_markdown(script)

        actual = len(script.split())
        drift = (actual - word_count) / word_count * 100 if word_count else 0
        print(f"[Script] {actual} words written ({drift:+.0f}% against target)")

        return script
    except Exception as e:
        print(f"Error: {e}")
        raise


def _call_openai_groq(client, model, topic, prompt):
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": topic}
        ]
    )
    return response.choices[0].message.content


def _call_gemini(client, topic, prompt):
    response = client.generate_content(
        contents=[
            {"role": "user", "parts": [{"text": f"{prompt}\n\nTopic: {topic}"}]}
        ],
        generation_config={
            "temperature": 0.7,
            "top_p": 0.8,
            "max_output_tokens": 8192,
        }
    )
    text = response.text
    
    if text.startswith('```json'):
        text = text[7:]
    if text.startswith('```'):
        text = text[3:]
    if text.endswith('```'):
        text = text[:-3]
    
    return text.strip()
