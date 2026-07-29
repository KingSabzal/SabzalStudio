"""Word-level transcription of the narration, locally, with Whisper.

Runs on the machine, needs no account and no key. The output is the
``[((start, end), word), ...]`` list every later stage is built around: the
caption renderer groups it into presets, and the footage stage uses the same
timings to decide what each shot has to cover.
"""

import contextlib
import os
import re

from whisper_timestamped import load_model, transcribe_timestamped


def _attention_weights_available():
    """Force Whisper to compute attention weights, which word timing needs.

    openai-whisper 20240930 and later default to PyTorch's fused
    scaled_dot_product_attention. It is faster, but it never materialises the
    attention matrix, so ``qkv_attention`` returns ``qk = None``.

    whisper-timestamped derives each word's start and end from exactly those
    weights. It installs a forward hook that reads ``w.shape``, so against a
    modern whisper every transcription dies with:

        AttributeError: 'NoneType' object has no attribute 'shape'

    Upstream anticipated this and ships ``whisper.model.disable_sdpa()``, a
    context manager that switches back to the explicit path for the duration
    of a call. Using it costs a little speed on the transcription stage and
    nothing anywhere else, and it is the supported way to ask for the weights
    rather than a monkey-patch of our own.

    Returns a null context on older whisper builds, which never used SDPA and
    therefore always produced the weights.
    """
    try:
        from whisper.model import disable_sdpa

        return disable_sdpa()
    except ImportError:
        return contextlib.nullcontext()


# Model size, overridable so a slower machine can drop to 'tiny' and a fast one
# can gain accuracy with 'small'. 'base' stays the default: it is the size the
# caption timings were tuned against.
DEFAULT_MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "base").strip() or "base"

# Loading a model reads several hundred megabytes from disk and rebuilds it on
# the device. It used to happen on every call, which cost that much again for
# each video in a batch. The model is stateless once loaded, so it is cached.
_MODEL_CACHE = {}


def _device():
    """Use the GPU when there is one; fp16 is only valid there."""
    try:
        import torch

        if torch.cuda.is_available():
            return "cuda"
    except Exception:  # noqa: BLE001 - torch is optional at import time here
        pass
    return "cpu"


def get_model(model_size=None):
    """Load a Whisper model, reusing it across calls in this process."""
    size = model_size or DEFAULT_MODEL_SIZE
    device = _device()
    key = (size, device)
    if key not in _MODEL_CACHE:
        print(f"[Whisper] Loading the '{size}' model on {device}. "
              f"The first run downloads it.")
        _MODEL_CACHE[key] = load_model(size, device=device)
    return _MODEL_CACHE[key]


def generate_timed_captions(audio_filename, model_size=None):
    """Transcribe a narration file into word-level timings."""
    model = get_model(model_size)
    # fp16 is a GPU feature. Forcing it off everywhere left CUDA machines
    # running in fp32, which is roughly twice as slow for no gain in accuracy.
    use_fp16 = _device() == "cuda"

    # Without this the fused attention path returns no weights and
    # whisper-timestamped cannot time the words. See the note above.
    with _attention_weights_available():
        gen = transcribe_timestamped(model, audio_filename, verbose=False,
                                     fp16=use_fp16)

    return getCaptionsWithTime(gen)


def cleanWord(word):

    return re.sub(r'[^\w\s\-_%\']', '', word)


def getCaptionsWithTime(whisper_analysis, maxCaptionSize=15, considerPunctuation=False):

    CaptionsPairs = []
    last_end = 0

    for segment in whisper_analysis['segments']:
        for word_info in segment['words']:
            clean_word = cleanWord(word_info['text'])
            if clean_word:
                start = word_info['start']
                end = word_info['end']

                # Fix all timestamp issues including multiple words with same end time
                # Check if there's any problem: zero duration, backwards, or overlap
                if start >= end or start < last_end or end <= last_end:
                    # Set start from last_end to ensure sequential order
                    start = last_end
                    # Set end slightly forward to ensure minimum duration
                    end = last_end + 0.3

                # Update last_end for next word
                last_end = end

                CaptionsPairs.append(((start, end), clean_word))

    return CaptionsPairs
