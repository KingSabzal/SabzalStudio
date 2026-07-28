"""Checkpointing: one file per topic, so runs cannot destroy each other.

There used to be a single ``pipeline_checkpoint.json``. Two runs at once
overwrote each other's state, and whichever finished first deleted the file the
other was relying on to resume.
"""

import utility.pipeline_manager as pm
from utility.pipeline_manager import PipelineManager


def _isolate(tmp_path, monkeypatch):
    monkeypatch.setattr(pm, "project_root", lambda: str(tmp_path))


def test_two_topics_keep_separate_checkpoints(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)

    first = PipelineManager("deep sea creatures")
    first.set_stage("3_timed_captions")
    first.update_data("script", "first script")

    second = PipelineManager("the roman empire")
    second.set_stage("5_ai_video_broll")
    second.update_data("script", "second script")

    assert first.checkpoint_file != second.checkpoint_file
    assert PipelineManager("deep sea creatures").get_stage() == "3_timed_captions"
    assert PipelineManager("the roman empire").get_stage() == "5_ai_video_broll"


def test_finishing_one_run_leaves_the_other_alone(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)

    finished = PipelineManager("topic one")
    unfinished = PipelineManager("topic two")
    unfinished.set_stage("4_background_music")

    finished.clear()

    remaining = [state["topic"] for _path, state in pm.list_checkpoints()]
    assert remaining == ["topic two"]


def test_resuming_restores_every_field(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)

    original = PipelineManager("a topic")
    original.update_data("script", "the script")
    original.update_data("timed_captions", [[[0.0, 1.0], "word"]])
    original.set_stage("6_render")

    resumed = PipelineManager("a topic")
    assert resumed.get_stage() == "6_render"
    assert resumed.get_data("script") == "the script"
    assert resumed.get_data("timed_captions") == [[[0.0, 1.0], "word"]]


def test_checkpoint_names_are_filesystem_safe(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)

    hostile = 'a/b\\c:d*e?f"g<h>i|j' + "k" * 300
    manager = PipelineManager(hostile)
    manager.set_stage("2_voiceover")

    name = manager.checkpoint_file.rsplit("/", 1)[-1]
    assert not set(name) & set('/\\:*?"<>|')
    assert len(name) < 120
    assert PipelineManager(hostile).get_stage() == "2_voiceover"


def test_an_old_shared_checkpoint_is_adopted(tmp_path, monkeypatch):
    """Upgrading must not throw away a run that was already in progress."""
    import json

    _isolate(tmp_path, monkeypatch)
    legacy = tmp_path / pm.LEGACY_CHECKPOINT_FILE
    legacy.write_text(json.dumps({
        "topic": "an old run", "current_stage": "5_ai_video_broll",
        "script": "carried over",
    }), encoding="utf-8")

    adopted = PipelineManager("an old run")
    assert adopted.get_stage() == "5_ai_video_broll"
    assert adopted.get_data("script") == "carried over"
    assert not legacy.exists()
