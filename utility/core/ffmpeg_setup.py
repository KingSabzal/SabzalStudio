"""Put the bundled ffmpeg on PATH, once, for the whole project.

Whisper and MoviePy both shell out to a plain ``ffmpeg`` command rather than
asking imageio-ffmpeg where its binary lives, so it has to be reachable by name.

This used to be done twice, differently:

* ``app.py`` copied it to ``<project>/bin/ffmpeg.exe``
* ``utility/pipeline_runner.py`` copied it to ``<project>/utility/bin/ffmpeg.exe``

That produced two copies of an ~80 MB binary in different places, and both used
the ``.exe`` suffix on every platform. On Linux and macOS a file called
``ffmpeg.exe`` is not what a subprocess looking for ``ffmpeg`` will find, so the
copy was dead weight there and the system ffmpeg was used instead -- or nothing
was, if none was installed.

One location, and the right name for the platform.
"""

from __future__ import annotations

import os
import shutil
import sys

_done = False


def project_root() -> str:
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.normpath(os.path.join(here, "..", ".."))


def bin_dir() -> str:
    return os.path.join(project_root(), "bin")


def _binary_name() -> str:
    return "ffmpeg.exe" if sys.platform == "win32" else "ffmpeg"


def ensure_ffmpeg(verbose: bool = False) -> str:
    """Copy the bundled ffmpeg into bin/ and put bin/ on PATH. Returns its path.

    Safe to call repeatedly and from either process; the copy only happens the
    first time.
    """
    global _done

    target_dir = bin_dir()
    target = os.path.join(target_dir, _binary_name())

    if _done and os.path.exists(target):
        return target

    try:
        import imageio_ffmpeg

        source = imageio_ffmpeg.get_ffmpeg_exe()
    except Exception as error:  # noqa: BLE001 - fall back to a system install
        existing = shutil.which("ffmpeg")
        if existing:
            _done = True
            return existing
        raise RuntimeError(
            f"No ffmpeg is available: imageio-ffmpeg could not provide one "
            f"({error}) and none is on PATH. Run "
            f"`pip install -r requirements.txt`."
        ) from error

    if not os.path.exists(target):
        os.makedirs(target_dir, exist_ok=True)
        if verbose:
            print(f"[ffmpeg] Placing the bundled binary at {target}")
        shutil.copy2(source, target)
        if sys.platform != "win32":
            # copy2 keeps the mode, but be certain it is executable.
            os.chmod(target, 0o755)

    path_entries = os.environ.get("PATH", "").split(os.pathsep)
    if target_dir not in path_entries:
        os.environ["PATH"] = target_dir + os.pathsep + os.environ.get("PATH", "")

    _done = True
    return target
