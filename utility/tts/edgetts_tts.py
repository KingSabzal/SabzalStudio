"""EdgeTTS narration with emotion, natural pauses and fallbacks.

The original version was three lines: hand the whole script to EdgeTTS and save
the result. That works, but it produces one flat reading of the entire script,
and if the voice or the service fails the whole run dies.

Two things changed.

**Delivery.** The script is split into sentences and each is synthesised with its
own speed, pitch and volume, chosen from the sentiment of that sentence. Real
silence of a chosen length is inserted between them. A sentence about a death is
now slower and lower than the sentence after it, which is most of the difference
between narration and a screen reader.

**Resilience.** A failure no longer ends the run. The chain tries the chosen
voice, then the same voice without emotion, then similar voices, then a plain
single-shot call, and finally Google Translate TTS. Each step is a real attempt
rather than a retry of the thing that just failed.
"""

import asyncio
import os
import subprocess
import tempfile
from typing import Dict, List

import edge_tts

from utility.tts.prosody import build_segments
from utility.tts.voices import DEFAULT_VOICE, describe, sibling_voices

# A synthesised file smaller than this contains no speech.
MIN_AUDIO_BYTES = 1024


def _ffmpeg() -> str:
    """The bundled ffmpeg, so nothing has to be installed separately."""
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"


def _valid(path: str) -> bool:
    """True when a file exists and actually holds audio."""
    return os.path.exists(path) and os.path.getsize(path) > MIN_AUDIO_BYTES


def _run_async(coroutine):
    """Run a coroutine whether or not a loop is already running.

    asyncio.run refuses to start inside a notebook kernel, where a loop is
    always active. Without this the whole voice stage fails there and drops to
    the lowest quality fallback.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coroutine)

    try:
        import nest_asyncio

        nest_asyncio.apply()
        return asyncio.run(coroutine)
    except ImportError:
        pass

    import concurrent.futures

    def worker():
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coroutine)
        finally:
            loop.close()

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(worker).result()


async def _speak(text: str, path: str, voice: str, prosody: Dict[str, str]) -> None:
    """One EdgeTTS request."""
    await edge_tts.Communicate(text, voice, **prosody).save(path)


def _silence(path: str, milliseconds: int) -> bool:
    """Create a silent mp3 of the requested length."""
    if milliseconds <= 0:
        return False
    result = subprocess.run(
        [_ffmpeg(), "-loglevel", "error", "-f", "lavfi",
         "-i", "anullsrc=r=24000:cl=mono",
         "-t", f"{milliseconds / 1000:.3f}", "-q:a", "9", path, "-y"],
        capture_output=True,
    )
    return result.returncode == 0 and os.path.exists(path)


def _concat(parts: List[str], destination: str) -> bool:
    """Join audio pieces in order.

    Re-encoding rather than copying: the segments come from separate requests
    and stream copying them produces timestamp warnings and occasional glitches
    at the joins.
    """
    listing = destination + ".txt"
    with open(listing, "w", encoding="utf-8") as handle:
        for part in parts:
            handle.write(f"file '{os.path.abspath(part)}'\n")

    result = subprocess.run(
        [_ffmpeg(), "-loglevel", "error", "-f", "concat", "-safe", "0",
         "-i", listing, "-c:a", "libmp3lame", "-q:a", "2", destination, "-y"],
        capture_output=True,
    )
    try:
        os.remove(listing)
    except OSError:
        pass
    return result.returncode == 0 and _valid(destination)


async def _expressive(text: str, output: str, voice: str) -> bool:
    """Synthesise sentence by sentence with emotion and pauses."""
    segments = build_segments(text)
    workdir = tempfile.mkdtemp(prefix="tts_")
    pieces: List[str] = []

    try:
        for index, segment in enumerate(segments):
            part = os.path.join(workdir, f"{index:03d}.mp3")
            await _speak(segment["text"], part, voice, segment["prosody"])
            if not _valid(part):
                return False
            pieces.append(part)

            gap = int(segment["pause_ms"])
            if gap > 0:
                quiet = os.path.join(workdir, f"{index:03d}_gap.mp3")
                if _silence(quiet, gap):
                    pieces.append(quiet)

        if len(pieces) == 1:
            # A single sentence needs no stitching.
            import shutil

            shutil.copy2(pieces[0], output)
            return _valid(output)

        return _concat(pieces, output)
    finally:
        import shutil

        shutil.rmtree(workdir, ignore_errors=True)


async def _plain(text: str, output: str, voice: str) -> bool:
    """One request for the whole script, with no emotion or pauses."""
    await _speak(text, output, voice, {})
    return _valid(output)


def _google_translate(text: str, output: str) -> bool:
    """Last resort, and the only one that does not need EdgeTTS.

    Noticeably more robotic, so it is genuinely a fallback rather than an
    alternative. Long text is split because the endpoint truncates.
    """
    try:
        import requests
    except ImportError:
        return False

    chunks: List[str] = []
    current = ""
    for word in text.split():
        if len(current) + len(word) + 1 > 190:
            chunks.append(current)
            current = word
        else:
            current = f"{current} {word}".strip()
    if current:
        chunks.append(current)

    workdir = tempfile.mkdtemp(prefix="gtts_")
    parts: List[str] = []
    try:
        for index, chunk in enumerate(chunks):
            part = os.path.join(workdir, f"{index:03d}.mp3")
            response = requests.get(
                "https://translate.google.com/translate_tts",
                params={"ie": "UTF-8", "q": chunk, "tl": "en",
                        "client": "tw-ob", "ttsspeed": "1"},
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=25,
            )
            if response.status_code != 200 or len(response.content) < MIN_AUDIO_BYTES:
                return False
            with open(part, "wb") as handle:
                handle.write(response.content)
            parts.append(part)

        if len(parts) == 1:
            import shutil

            shutil.copy2(parts[0], output)
            return _valid(output)
        return _concat(parts, output)
    except Exception:
        return False
    finally:
        import shutil

        shutil.rmtree(workdir, ignore_errors=True)


async def generate_audio(text: str, outputFilename: str,
                         voice: str = DEFAULT_VOICE,
                         expressive: bool = True) -> str:
    """Narrate *text* into *outputFilename*.

    Returns the voice actually used, which will differ from the one requested if
    a fallback was needed. Raises only when every option has failed.
    """
    voice = voice or DEFAULT_VOICE

    attempts = []
    if expressive:
        attempts.append(
            (f"{voice} with emotion", lambda: _expressive(text, outputFilename, voice))
        )
    attempts.append(
        (f"{voice} plain", lambda: _plain(text, outputFilename, voice))
    )
    for alternative in sibling_voices(voice, limit=3):
        attempts.append(
            (f"{alternative} plain",
             lambda v=alternative: _plain(text, outputFilename, v))
        )

    last_error = None
    for label, attempt in attempts:
        try:
            if await attempt():
                if not label.startswith(voice):
                    print(f"[TTS] Fell back to {label}")
                else:
                    print(f"[TTS] {describe(voice)} ({label.split()[-1]})")
                return label.split()[0]
        except Exception as exc:
            last_error = exc
            print(f"[TTS] {label} failed: {type(exc).__name__}: {str(exc)[:90]}")
        # A partial file from a failed attempt would fool the next check.
        if os.path.exists(outputFilename) and not _valid(outputFilename):
            os.remove(outputFilename)

    print("[TTS] Every EdgeTTS option failed. Trying Google Translate TTS.")
    if _google_translate(text, outputFilename):
        print("[TTS] Google Translate TTS succeeded. Quality is noticeably lower.")
        return "google-translate"

    raise RuntimeError(
        f"Voice synthesis failed for every option. Last error: {last_error}"
    )


def generate_audio_sync(text: str, outputFilename: str,
                        voice: str = DEFAULT_VOICE,
                        expressive: bool = True) -> str:
    """Blocking wrapper, for callers that are not already async."""
    return _run_async(generate_audio(text, outputFilename, voice, expressive))
