"""Per-topic checkpointing, so an interrupted run resumes instead of restarting.

Each topic gets its own checkpoint file, named after a hash of the topic. There
used to be a single ``pipeline_checkpoint.json`` shared by everything, which had
two consequences:

* two runs at once trampled each other's state, and whichever finished first
  deleted the other's checkpoint;
* starting a different topic threw away the unfinished one without asking.

The path is also absolute now. It was relative before, so the file landed in
whatever directory the process happened to start in and a run launched from
elsewhere could not find its own checkpoint.
"""

import hashlib
import json
import os
import re

CHECKPOINT_PREFIX = "pipeline_checkpoint"
LEGACY_CHECKPOINT_FILE = "pipeline_checkpoint.json"


def project_root():
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.normpath(os.path.join(here, ".."))


def checkpoint_path(topic=None):
    """The checkpoint file for a topic.

    A short hash keeps the name filesystem-safe whatever the topic contains,
    and a readable slug is kept in front of it so the folder stays legible.
    """
    if not topic:
        return os.path.join(project_root(), LEGACY_CHECKPOINT_FILE)
    digest = hashlib.sha256(topic.strip().lower().encode("utf-8")).hexdigest()[:10]
    slug = re.sub(r"[^A-Za-z0-9]+", "-", topic.strip())[:40].strip("-").lower()
    name = f"{CHECKPOINT_PREFIX}.{slug}-{digest}.json" if slug \
        else f"{CHECKPOINT_PREFIX}.{digest}.json"
    return os.path.join(project_root(), name)


def list_checkpoints():
    """Every saved checkpoint, newest first, as (path, state) pairs."""
    root = project_root()
    found = []
    try:
        names = os.listdir(root)
    except OSError:
        return found
    for name in names:
        if not name.startswith(CHECKPOINT_PREFIX) or not name.endswith(".json"):
            continue
        path = os.path.join(root, name)
        try:
            with open(path, "r", encoding="utf-8") as handle:
                state = json.load(handle)
            if isinstance(state, dict) and state.get("topic"):
                found.append((path, state))
        except (OSError, json.JSONDecodeError):
            continue
    found.sort(key=lambda item: os.path.getmtime(item[0]), reverse=True)
    return found


class PipelineManager:
    def __init__(self, topic=None):
        self.state = {
            "current_stage": "1_script",
            "topic": topic or "",
            "script": "",
            "voiceover_path": "",
            "voice_used": "",
            "timed_captions": [],
            "background_music_url": "",
            "background_music_path": "",
            "background_video_urls": [],
            "sfx_items": [],
            "video_path": "",
            "metadata": {},
            "metadata_path": ""
        }
        self.checkpoint_file = checkpoint_path(topic)

        if os.path.exists(self.checkpoint_file):
            self.load_state()
            # A hash collision or a hand-edited file could carry another topic.
            if topic and self.state["topic"] != topic:
                self.state["topic"] = topic
                self.state["current_stage"] = "1_script"
            self.save_state()
            return

        # An older install has one shared checkpoint. Adopt it when it belongs
        # to this topic, so an upgrade does not discard work in progress.
        legacy = os.path.join(project_root(), LEGACY_CHECKPOINT_FILE)
        if topic and os.path.exists(legacy) and legacy != self.checkpoint_file:
            try:
                with open(legacy, "r", encoding="utf-8") as handle:
                    saved = json.load(handle)
                if isinstance(saved, dict) and saved.get("topic") == topic:
                    for key, value in saved.items():
                        if key in self.state:
                            self.state[key] = value
                    print(f"[PipelineManager] Adopted the shared checkpoint for "
                          f"'{topic}' at stage '{self.state['current_stage']}'.")
                    os.remove(legacy)
            except (OSError, json.JSONDecodeError):
                pass

        self.save_state()

    def load_state(self):
        if os.path.exists(self.checkpoint_file):
            try:
                with open(self.checkpoint_file, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                    # Merge keys to ensure compatibility
                    for k, v in saved.items():
                        if k in self.state:
                            self.state[k] = v
                print(f"[PipelineManager] Loaded existing checkpoint. Current stage: {self.state['current_stage']}")
            except Exception as e:
                print(f"[PipelineManager] Error loading checkpoint: {e}. Starting fresh.")

    def save_state(self):
        try:
            # Write beside the target and rename, so an interrupted save cannot
            # leave a half-written checkpoint that fails to parse next time.
            temporary = self.checkpoint_file + ".tmp"
            with open(temporary, "w", encoding="utf-8") as f:
                json.dump(self.state, f, indent=2, ensure_ascii=False)
            os.replace(temporary, self.checkpoint_file)
            print(f"[PipelineManager] Checkpoint saved: stage='{self.state['current_stage']}'")
        except Exception as e:
            print(f"[PipelineManager] Error saving checkpoint: {e}")

    def clear(self):
        """Delete this run's checkpoint. Called once the run has completed."""
        for path in (self.checkpoint_file, self.checkpoint_file + ".tmp"):
            try:
                os.remove(path)
            except OSError:
                pass

    def get_stage(self):
        return self.state["current_stage"]

    def set_stage(self, stage_name):
        self.state["current_stage"] = stage_name
        self.save_state()

    def update_data(self, key, value):
        if key in self.state:
            self.state[key] = value
            self.save_state()
        else:
            raise KeyError(f"Key '{key}' is not a valid pipeline state variable.")

    def get_data(self, key):
        return self.state.get(key)
