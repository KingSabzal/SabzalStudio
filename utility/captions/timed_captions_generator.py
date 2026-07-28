from utility.config import get_config


def generate_timed_captions(audio_filename):
    """Transcribe the voiceover into word level timings.

    Whisper is the only provider. It runs locally, needs no account and no
    key. The paid Deepgram provider was removed.
    """
    config = get_config()
    stt_provider = config.get_stt_provider()

    if stt_provider == 'whisper':
        from utility.stt.whisper_stt import generate_timed_captions as whisper_captions
        return whisper_captions(audio_filename)

    raise ValueError(
        f"Unknown STT provider: {stt_provider}. Only 'whisper' is supported."
    )
