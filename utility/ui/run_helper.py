"""Runs the pipeline as a subprocess and streams its log into the page.

Shared by all three creation modes. A subprocess rather than an import: the
render is long and would freeze the interface, and running it the same way the
command line does means the seven-stage checkpoint behaves identically.
"""

from __future__ import annotations

import os
import subprocess
import sys

import streamlit as st

from utility.ui import gallery_manager

PROJECT_ROOT = gallery_manager.project_root()

STAGE_LABELS = {
    "1_script": "Script",
    "2_voiceover": "Voiceover",
    "3_timed_captions": "Captions",
    "4_background_music": "Music and effects",
    "5_ai_video_broll": "Footage",
    "6_render": "Render",
    "7_metadata": "Upload packages",
}


def run_pipeline(topic: str, overrides: dict) -> bool:
    """Generate one video. Returns True when it finished.

    The pipeline runs in a separate process so a long render cannot block the
    browser, and so its log can be streamed into the page while it works.
    """
    environment = os.environ.copy()
    environment.update({k: str(v) for k, v in overrides.items() if v is not None})

    progress = st.progress(0.0, text="Starting...")
    log_box = st.empty()
    lines: list = []
    stages = list(STAGE_LABELS)

    process = subprocess.Popen(
        [sys.executable, "-u", "-c",
         "import sys; sys.path.insert(0, '.'); "
         "from utility.pipeline_runner import run; run(sys.argv[1])",
         topic],
        cwd=PROJECT_ROOT, env=environment,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, bufsize=1,
    )
    for line in process.stdout:
        line = line.rstrip()
        lines.append(line)
        for index, key in enumerate(stages):
            if f"STAGE {index + 1}" in line:
                progress.progress((index + 1) / len(stages),
                                  text=STAGE_LABELS[key])
        log_box.code("\n".join(lines[-25:]))
    process.wait()

    if process.returncode == 0:
        progress.progress(1.0, text="Finished")
        st.success("Done. It is in the Gallery tab.")
        st.balloons()
        return True

    progress.empty()
    st.error(
        "The run stopped. Nothing was lost: the checkpoint is saved, so "
        "starting the same topic again picks up from the stage that failed."
    )
    with st.expander("Full log", expanded=True):
        st.code("\n".join(lines[-60:]))
    return False
