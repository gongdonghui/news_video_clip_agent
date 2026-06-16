# PySceneDetect Integration for Shot-Boundary Assistance

## Summary

Add PySceneDetect content-aware shot detection as a peer signal alongside existing pause detection. Scene cuts and pauses are treated as equal boundary candidates — the nearest valid boundary wins when snapping clip endpoints.

## Decisions

| Decision | Choice |
|---|---|
| Role vs. pauses | Peer — nearest boundary among both signals wins |
| Dependency | Required — pipeline fails with clear error if missing |
| Detection mode | Content-aware (`detect-adaptive`) |
| Config | Module-level constants, with env var overrides |

## Architecture

### New: `scripts/detect_scenes.py`
- Runs `pyscenedetect detect-adaptive --min-scene-len <N>` on source video
- Parses output timecodes
- Follows same pattern as `detect_pauses.py`: force/reuse, metadata signature, `scenes.json` output

### Modified: `scripts/build_clip_plan.py`
- `find_pause_boundary()` → renamed to `find_nearest_boundary()` accepting both `pauses` and `scene_cuts`
- `snap_clip_end()` accepts both signals, picks nearest valid candidate within lookback/lookahead windows
- `normalize_clips()` and `build_fallback_clips()` signatures updated

### Modified: `scripts/run_pipeline.py`
- Calls `detect_scenes()` after `extract_audio()`
- Passes scene data alongside pause data to clip planning
- Scene signature included in clip plan context for reuse detection

## Data Flow

```
source video → detect_scenes → scenes.json
                           ↘
               detect_pauses → pauses.json
                           ↘
          normalize_clips(pauses, scenes) → clip_plan
```

## Boundary Snapping Logic

For a given clip's semantic end timestamp:
1. Collect all valid boundary candidates within `[end - 1.2s, end + 0.8s]` from both pauses and scenes
2. If candidates exist: pick the nearest one (ties broken by preferring the earlier candidate)
3. If no candidates: fall back to the raw semantic end
