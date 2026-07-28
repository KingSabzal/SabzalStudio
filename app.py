"""SabzalStudio.

Start it with:

    streamlit run app.py

This file exists only to launch the interface. The interface itself lives in
utility/ui, and the pipeline it drives lives in utility/pipeline_runner.
"""

import os
import sys

# Bundle ffmpeg onto the path before anything imports MoviePy or Whisper, both
# of which shell out to it. A copy is placed in bin/ on first run so there is
# nothing for the user to install separately.
import imageio_ffmpeg

_ROOT = os.path.dirname(os.path.abspath(__file__))
_BIN = os.path.join(_ROOT, "bin")
os.makedirs(_BIN, exist_ok=True)
_FFMPEG = os.path.join(_BIN, "ffmpeg.exe")

if not os.path.exists(_FFMPEG):
    import shutil

    shutil.copy2(imageio_ffmpeg.get_ffmpeg_exe(), _FFMPEG)

if _BIN not in os.environ["PATH"]:
    os.environ["PATH"] = _BIN + os.pathsep + os.environ["PATH"]

if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def _started_by_streamlit() -> bool:
    """Whether this file is being served by Streamlit.

    Run with plain python it would execute every widget call outside a
    session, which produces a wall of confusing warnings and no interface.
    Better to say what to type instead.
    """
    try:
        from streamlit.runtime import exists
        return bool(exists())
    except Exception:
        return False


def _main() -> None:
    if not _started_by_streamlit():
        print("SabzalStudio is an interface. Start it with:\n")
        print("    streamlit run app.py\n")
        raise SystemExit(1)

    import runpy

    runpy.run_path(
        os.path.join(_ROOT, "utility", "ui", "main.py"),
        run_name="__main__",
    )


_main()
