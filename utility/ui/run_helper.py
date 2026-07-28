"""Runs the pipeline as a subprocess and streams its log into the page.

Shared by all three creation modes. A subprocess rather than an import: the
render is long and would freeze the interface, and running it the same way the
command line does means the seven-stage checkpoint behaves identically.
"""

from __future__ import annotations

import os
import signal
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

# The runner prints this immediately before each stage. The interface watches
# for it to advance the progress bar, which makes it a contract between the two
# rather than incidental log text: changing the wording in one place without the
# other silently breaks the progress bar.
STAGE_MARKER = "--- STAGE"

# Where the interface remembers a running process, so a rerun of the script
# (which Streamlit does constantly) can still find and stop it.
_PROCESS_KEY = "_pipeline_process"


def _terminate(process: subprocess.Popen) -> None:
    """Stop a running pipeline and everything it started.

    The render spawns ffmpeg children. Killing only the parent leaves those
    encoding away with nobody reading their output, so the whole process group
    goes at once. SIGTERM first so the runner can write its checkpoint.
    """
    if process.poll() is not None:
        return
    try:
        if os.name == "nt":
            process.send_signal(signal.CTRL_BREAK_EVENT)
        else:
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
    except (ProcessLookupError, PermissionError, OSError):
        process.terminate()

    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        try:
            if os.name == "nt":
                process.kill()
            else:
                os.killpg(os.getpgid(process.pid), signal.SIGKILL)
        except (ProcessLookupError, PermissionError, OSError):
            process.kill()


def stop_running_pipeline() -> bool:
    """Stop a pipeline left running by an earlier interaction. True if it did."""
    process = st.session_state.get(_PROCESS_KEY)
    if process is None:
        return False
    _terminate(process)
    st.session_state.pop(_PROCESS_KEY, None)
    return True


def run_pipeline(topic: str, overrides: dict) -> bool:
    """Generate one video. Returns True when it finished.

    The pipeline runs in a separate process so a long render cannot block the
    browser, and so its log can be streamed into the page while it works.
    """
    environment = os.environ.copy()
    environment.update({k: str(v) for k, v in overrides.items() if v is not None})

    # A previous run that was never stopped would otherwise carry on rendering
    # in the background, competing for CPU and writing to the same checkpoint.
    stop_running_pipeline()

    progress = st.progress(0.0, text="Starting...")
    stop_slot = st.empty()
    log_box = st.empty()
    lines: list = []
    stages = list(STAGE_LABELS)

    # Put the child in its own process group so ffmpeg and every other
    # grandchild can be signalled together.
    if os.name == "nt":
        creation_flags = subprocess.CREATE_NEW_PROCESS_GROUP
        preexec = None
    else:
        creation_flags = 0
        preexec = os.setsid

    process = subprocess.Popen(
        [sys.executable, "-u", "-c",
         "import sys; sys.path.insert(0, '.'); "
         "from utility.pipeline_runner import run; run(sys.argv[1])",
         topic],
        cwd=PROJECT_ROOT, env=environment,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, bufsize=1,
        creationflags=creation_flags, preexec_fn=preexec,
    )
    st.session_state[_PROCESS_KEY] = process

    cancelled = False
    if stop_slot.button("Stop this run", key=f"stop_{process.pid}"):
        # Streamlit reruns the script on a click, so this is reached on the
        # rerun rather than mid-loop; the guard below covers the running case.
        cancelled = True

    try:
        for line in process.stdout:
            line = line.rstrip()
            lines.append(line)
            if STAGE_MARKER in line:
                for index, key in enumerate(stages):
                    if f"{STAGE_MARKER} {index + 1}" in line:
                        progress.progress((index + 1) / len(stages),
                                          text=STAGE_LABELS[key])
                        break
            log_box.code("\n".join(lines[-25:]))
        process.wait()
    except BaseException:
        # Covers the browser tab closing, a Streamlit rerun and Ctrl-C alike:
        # never leave the render orphaned.
        _terminate(process)
        st.session_state.pop(_PROCESS_KEY, None)
        raise
    finally:
        if process.stdout:
            process.stdout.close()

    st.session_state.pop(_PROCESS_KEY, None)
    stop_slot.empty()

    if cancelled:
        progress.empty()
        st.warning("The run was stopped. The checkpoint is saved.")
        return False

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
