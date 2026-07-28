"""How the pipeline behaves when a stage goes wrong.

Two failures used to be reported as success, or lose work:

* no footage reaching the render stage printed a message, left the stage
  unchanged and exited 0, so the interface showed "Done" and balloons for a run
  that produced no file;
* an error while writing the upload packages skipped moving the video into
  outputs/ and recording it, then wiped the checkpoint, so the render was
  stranded in the project root and the next run overwrote it.
"""

import pytest

import utility.pipeline_manager as pm
import utility.pipeline_runner as runner


class FakeConfig:
    def get_video_orientation(self):
        return False

    def get_video_style(self):
        return "facts"

    def get_sfx_enabled(self):
        return False

    def get_sfx_density(self):
        return "medium"


@pytest.fixture
def staged(tmp_path, monkeypatch):
    """A pipeline parked at the render stage with everything else in place."""
    monkeypatch.setattr(pm, "project_root", lambda: str(tmp_path))
    monkeypatch.setattr(runner, "get_config", lambda: FakeConfig())
    monkeypatch.setattr(runner, "MediaSourceManager", lambda *a, **k: object())

    outputs = tmp_path / "outputs"
    outputs.mkdir()
    monkeypatch.setattr(runner.gallery_manager, "outputs_dir", lambda: str(outputs))

    recorded = []
    monkeypatch.setattr(runner.gallery_manager, "record",
                        lambda **kw: recorded.append(kw))

    manager = pm.PipelineManager("a topic")
    manager.update_data("script", "the script")
    manager.update_data("timed_captions", [[[0.0, 1.0], "word"]])
    manager.update_data("voiceover_path", "voice.wav")
    manager.set_stage("6_render")
    return tmp_path, outputs, recorded


def test_no_footage_raises_instead_of_reporting_success(staged, monkeypatch):
    monkeypatch.setattr(runner, "merge_empty_intervals", lambda segments: [])

    with pytest.raises(RuntimeError, match="nothing to composite"):
        runner.run("a topic")


def test_a_renderer_that_produces_no_file_is_caught(staged, monkeypatch):
    monkeypatch.setattr(runner, "merge_empty_intervals",
                        lambda segments: [[[0.0, 1.0], "http://x/clip.mp4"]])
    monkeypatch.setattr(runner, "get_output_media",
                        lambda **kw: "does_not_exist.mp4")

    with pytest.raises(RuntimeError, match="no such file"):
        runner.run("a topic")


def test_the_video_survives_a_metadata_failure(staged, monkeypatch):
    """The whole point: a broken model call must not cost the user the render."""
    tmp_path, outputs, recorded = staged

    rendered = tmp_path / "rendered_video.mp4"
    rendered.write_bytes(b"video data")

    monkeypatch.setattr(runner, "merge_empty_intervals",
                        lambda segments: [[[0.0, 1.0], "http://x/clip.mp4"]])
    monkeypatch.setattr(runner, "get_output_media", lambda **kw: str(rendered))

    class ExplodingMetadata:
        def __init__(self, config):
            pass

        def generate(self, **kwargs):
            raise RuntimeError("the model is down")

    monkeypatch.setattr(runner, "MetadataGenerator", ExplodingMetadata)

    runner.run("a topic")

    # Moved into outputs/ and named from the topic rather than left behind.
    produced = list(outputs.glob("*.mp4"))
    assert len(produced) == 1
    assert produced[0].name == "a-topic.mp4"
    assert produced[0].read_bytes() == b"video data"
    assert not rendered.exists()

    # Still recorded, so it shows up in the gallery.
    assert len(recorded) == 1
    assert recorded[0]["topic"] == "a topic"


def test_a_completed_run_clears_only_its_own_checkpoint(staged, monkeypatch):
    tmp_path, outputs, _recorded = staged

    other = pm.PipelineManager("a different topic")
    other.set_stage("4_background_music")

    rendered = tmp_path / "rendered_video.mp4"
    rendered.write_bytes(b"video")
    monkeypatch.setattr(runner, "merge_empty_intervals",
                        lambda segments: [[[0.0, 1.0], "http://x/clip.mp4"]])
    monkeypatch.setattr(runner, "get_output_media", lambda **kw: str(rendered))

    class Metadata:
        def __init__(self, config):
            pass

        def generate(self, **kwargs):
            return {
                "youtube": {"title": "A Real Title", "thumbnail_text": "x"},
                "report": {"instagram_hashtag_count": 3,
                           "tiktok_hashtag_count": 3,
                           "corrections_applied": []},
            }

    monkeypatch.setattr(runner, "MetadataGenerator", Metadata)
    monkeypatch.setattr(runner, "to_text", lambda packages: "packages")

    runner.run("a topic")

    assert (outputs / "A-Real-Title.mp4").exists()
    remaining = [state["topic"] for _path, state in pm.list_checkpoints()]
    assert remaining == ["a different topic"]
