import json
from pathlib import Path
from types import SimpleNamespace
import sys

import pytest

from scripts.detect_scenes import (
    build_scenes_payload,
    can_reuse_scenes_payload,
    detect_scenes,
)


def test_build_scenes_payload_includes_source_and_cuts():
    scene_cuts = [0.0, 5.0, 10.0, 15.0]
    payload = build_scenes_payload(Path("/tmp/video.mp4"), 3.0, scene_cuts)

    assert payload["source_video"] == "/tmp/video.mp4"
    assert payload["min_scene_len"] == 3.0
    assert payload["scene_cuts"] == scene_cuts


def test_can_reuse_scenes_payload_matches_exact_context():
    output_path = Path("/tmp/fake_output/scenes.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps({"source_video": "/tmp/video.mp4", "min_scene_len": 3.0, "scene_cuts": []}),
        encoding="utf-8",
    )

    assert can_reuse_scenes_payload(Path("/tmp/video.mp4"), output_path, 3.0) is True


def test_can_reuse_scenes_payload_rejects_different_source():
    output_path = Path("/tmp/fake_output/scenes_diff.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps({"source_video": "/tmp/other.mp4", "min_scene_len": 3.0, "scene_cuts": []}),
        encoding="utf-8",
    )

    assert can_reuse_scenes_payload(Path("/tmp/video.mp4"), output_path, 3.0) is False


def test_can_reuse_scenes_payload_rejects_different_min_scene_len():
    output_path = Path("/tmp/fake_output/scenes_len.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps({"source_video": "/tmp/video.mp4", "min_scene_len": 5.0, "scene_cuts": []}),
        encoding="utf-8",
    )

    assert can_reuse_scenes_payload(Path("/tmp/video.mp4"), output_path, 3.0) is False


def test_can_reuse_scenes_payload_handles_missing_file():
    output_path = Path("/tmp/fake_output/nonexistent.json")
    assert can_reuse_scenes_payload(Path("/tmp/video.mp4"), output_path, 3.0) is False


def test_detect_scenes_reuses_existing_output_when_not_forced(tmp_path: Path, monkeypatch):
    source = tmp_path / "video.mp4"
    source.write_text("fake video", encoding="utf-8")
    output_path = tmp_path / "scenes.json"
    output_path.write_text(
        json.dumps({"source_video": str(source), "min_scene_len": 3.0, "scene_cuts": [0.0, 5.0]}),
        encoding="utf-8",
    )

    def unexpected_detect():
        raise AssertionError("scenedetect should not be loaded for safe reuse")

    monkeypatch.setitem(sys.modules, "scenedetect", SimpleNamespace(detect=unexpected_detect))

    payload = detect_scenes(source, output_path, force=False)

    assert payload["scene_cuts"] == [0.0, 5.0]


def test_detect_scenes_reruns_when_forced(tmp_path: Path, monkeypatch):
    source = tmp_path / "video.mp4"
    source.write_text("fake video", encoding="utf-8")
    output_path = tmp_path / "scenes.json"
    output_path.write_text(
        json.dumps({"source_video": str(source), "min_scene_len": 3.0, "scene_cuts": [0.0, 5.0]}),
        encoding="utf-8",
    )

    def fake_detect(video_path, detector):
        assert str(video_path) == str(source)

        class FakeTC:
            def __init__(self, secs):
                self._secs = secs

            def get_seconds(self):
                return self._secs

        return [
            (FakeTC(0.0), FakeTC(10.0)),
            (FakeTC(10.0), FakeTC(20.0)),
        ]

    monkeypatch.setitem(sys.modules, "scenedetect", SimpleNamespace(AdaptiveDetector=lambda **kw: None, detect=fake_detect))

    payload = detect_scenes(source, output_path, force=True)

    assert payload["scene_cuts"] == [0.0, 10.0, 20.0]
