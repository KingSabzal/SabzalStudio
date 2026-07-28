"""Narration entry point.

ElevenLabs was removed: it is a paid service, and the project should not need a
subscription to produce a video. EdgeTTS is free and, with per-sentence emotion
and real pauses, close enough in quality that the difference does not justify
the cost. Google Translate TTS remains underneath as a last resort.
"""

from utility.config import get_config
from utility.tts.voices import DEFAULT_VOICE, describe, pick_voice, voice_exists


async def generate_audio(text, outputFilename, voice=None, style=None, topic=None):
    """Narrate text to a file and return the voice that was used.

    When no voice is configured, one is chosen from the script style so a
    channel does not use the same narrator for every video. The topic seeds that
    choice, which keeps it stable across a resumed run.
    """
    from utility.tts.edgetts_tts import generate_audio as edgetts_audio

    config = get_config()

    if not voice:
        voice = config.get_tts_voice()

    if voice and voice.lower() == "auto":
        voice = pick_voice(style or config.get_video_style(), seed=topic)
        print(f"[TTS] Auto-selected {voice} ({describe(voice)})")
    elif not voice_exists(voice):
        print(f"[TTS] '{voice}' is not in the catalogue. Using {DEFAULT_VOICE}.")
        voice = DEFAULT_VOICE

    return await edgetts_audio(text, outputFilename, voice)
