from __future__ import annotations

from pathlib import Path

from scripts.common import read_json, write_json

DEFAULT_SCENE_MIN_LENGTH_SECONDS = 3.0


def build_scenes_payload(
    source_video: Path,
    min_scene_len: float,
    scene_cuts: list[float],
) -> dict[str, object]:
    return {
        "source_video": str(source_video),
        "min_scene_len": min_scene_len,
        "scene_cuts": scene_cuts,
    }


def can_reuse_scenes_payload(
    source_video: Path,
    output_path: Path,
    min_scene_len: float,
) -> bool:
    if not output_path.exists():
        return False

    payload = read_json(output_path)
    return (
        payload.get("source_video") == str(source_video)
        and payload.get("min_scene_len") == min_scene_len
    )


def detect_scenes(
    source_video: Path,
    output_path: Path,
    force: bool = False,
    min_scene_len: float = DEFAULT_SCENE_MIN_LENGTH_SECONDS,
) -> dict[str, object]:
    if not force and can_reuse_scenes_payload(source_video, output_path, min_scene_len):
        return read_json(output_path)

    try:
        import scenedetect
    except ImportError:
        raise RuntimeError(
            "PySceneDetect is required but not installed. "
            "Install it with: pip install scenedetect"
        )

    from scenedetect import AdaptiveDetector as ScDetector
    from scenedetect import detect

    detector = ScDetector(min_scene_len=min_scene_len)
    scene_list = detect(str(source_video), detector)

    scene_cuts: list[float] = []
    for start, end in scene_list:
        scene_cuts.append(round(start.get_seconds(), 3))
        scene_cuts.append(round(end.get_seconds(), 3))

    deduped: list[float] = []
    for t in scene_cuts:
        if not deduped or t - deduped[-1] > 0.001:
            deduped.append(t)

    payload = build_scenes_payload(source_video, min_scene_len, deduped)
    write_json(output_path, payload)
    return payload
