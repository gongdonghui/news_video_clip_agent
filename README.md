# news_video_clip_agent

A local video clipping pipeline for segmenting long-form news videos into shorter, focused clips.

The goal is not a general-purpose NLE, but to automatically break a ~20-30 minute news program into a set of shorter, self-contained, distributable clips, along with subtitles and structured metadata.

## Key Features

- Read local video and extract metadata via ffprobe
- Extract mono 16kHz WAV audio
- Generate timestamped transcription using local `mlx_whisper`
- Prioritize DeepSeek for semantic news clip segmentation
- Snap clip boundaries to natural speech pauses near semantic edges
- Fall back to local heuristic grouping when no LLM is available
- Export `clip_plan.json`, `clip_plan.csv`, `clip_plan.md`
- Execute FFmpeg accurate-encode clips
- Export per-clip `.srt` / `.vtt` subtitles
- Isolated output directory per input video to avoid cross-contamination
- PID-based pipeline lock prevents concurrent runs on the same input

## Current Clipping Strategy

The project is optimized for `news` mode. Core strategy:

1. **Transcribe first, don't cut by shot**  
   Entry point: [scripts/transcribe.py](scripts/transcribe.py:1). Uses local `mlx_whisper` to produce a timestamped transcript of the full video.

2. **DeepSeek semantic clip selection (preferred)**  
   Entry point: [scripts/analyze_clips.py](scripts/analyze_clips.py:1).  
   Prompt focuses on:
   - English news
   - Target duration `15-45s`
   - Prefer broadcaster-led clips centered on the anchor
   - Allow brief reporter/soundbite continuation
   - Favor tighter, shorter clips over long packages

3. **Fall back to local heuristic grouping when DeepSeek fails**  
   Logic in [scripts/build_clip_plan.py](scripts/build_clip_plan.py:1).  
   Groups transcript segments by duration thresholds and inter-segment gaps, not by shot boundaries.

4. **Pause-aware boundary snapping**  
   Logic in [scripts/detect_pauses.py](scripts/detect_pauses.py:1).  
   Uses `ffmpeg silencedetect` to find speech pauses and snaps clip endpoints to natural silence, avoiding cuts mid-sentence.

5. **Uniform padding and export**  
   Orchestrated in [scripts/run_pipeline.py](scripts/run_pipeline.py:1):
   - Add `0.5s` padding before clip start
   - Add `1.0s` padding after clip end
   - Output clips, subtitles, and clip plan artifacts

## Suitable Content

- English TV news broadcasts
- Anchor-led evening news with reporter packages
- Current-affairs programs needing fast clip extraction

Less suitable:

- Long-form interview conversations
- Lecture recordings
- Documentaries relying heavily on visual language
- Content requiring shot-level, character-level, or emotion-driven fine editing

## Tech Stack

- Python 3.11+
- FFmpeg / ffprobe
- `mlx_whisper`
- DeepSeek Chat Completions API

## Project Structure

```text
news_video_clip_agent/
├── README.md
├── AGENTS.md
├── .env
├── docs/
├── scripts/
│   ├── analyze_clips.py
│   ├── build_clip_plan.py
│   ├── common.py
│   ├── cut_clips.py
│   ├── detect_pauses.py
│   ├── export_clip_subtitles.py
│   ├── extract_audio.py
│   ├── probe_video.py
│   ├── run_pipeline.py
│   └── transcribe.py
├── tests/
├── temp/
└── output/
```

- `temp/` — intermediate artifacts, not committed by default
- `output/<run_id>/` — per-input-video output directory

## Configuration

Set environment variables in `.env` or export them in your shell:

```bash
# Required for DeepSeek semantic analysis (falls back to heuristic if missing)
DEEPSEEK_API_KEY=your_key

# Optional overrides
DEEPSEEK_MODEL=deepseek-chat
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
WHISPER_MODEL=mlx-community/whisper-large-v3-mlx
```

## Setup

Verify your local environment:

```bash
ffmpeg -version
ffprobe -version
python3 --version
```

## Usage

Generate clip plan only (no cuts):

```bash
python3 scripts/run_pipeline.py \
  --input ~/Downloads/l13.mp4 \
  --mode news \
  --language en \
  --plan-only
```

Generate plan and execute cuts:

```bash
python3 scripts/run_pipeline.py \
  --input ~/Downloads/l13.mp4 \
  --mode news \
  --language en \
  --execute
```

Force rebuild all intermediate artifacts:

```bash
python3 scripts/run_pipeline.py \
  --input ~/Downloads/l13.mp4 \
  --mode news \
  --language en \
  --plan-only \
  --force
```

## Output

Each run produces an isolated directory:

```text
output/<run_id>/
├── clips/
├── subtitles/
├── metadata/
└── logs/
```

Contents:

- `metadata/source_probe.json` — video metadata
- `metadata/transcript.json` — timestamped transcription
- `metadata/pauses.json` — silence detection results
- `metadata/clip_plan.json` — structured clip plan
- `metadata/clip_plan.csv` — tabular clip plan
- `metadata/clip_plan.md` — human-readable clip plan
- `subtitles/source.srt` / `source.vtt` — full-video subtitles
- `subtitles/<clip_id>.srt` / `<clip_id>.vtt` — per-clip relative-time subtitles
- `clips/<clip_id>.mp4` — exported video clips

## Data Flow

```text
source video
  -> ffprobe
  -> extract audio
  -> mlx_whisper transcript
  -> ffmpeg silencedetect
  -> DeepSeek semantic clip selection
     or fallback local grouping
  -> pause-aware boundary snapping
  -> clip plan artifacts
  -> ffmpeg cut
  -> clip subtitles
```

## Current Strategy Strengths

- Practical for news programs, especially anchor-centric structures
- Local transcription — no Whisper cloud API dependency
- Pause-aware boundaries feel more natural than pure transcript grouping
- DeepSeek failures don't halt the pipeline
- Reusable transcript, pause, and clip plan artifacts keep re-run costs low

## Current Limitations

- No shot-cut detection via `PySceneDetect`
- No speaker diarization — can't label anchor vs. reporter vs. interviewee
- DeepSeek and fallback produce different clip distributions
- No clip budget constraint — a ~20 min news segment may yield 10 or 30+ clips
- DeepSeek responses get basic validation only, no aggressive post-pass merging

## Tests

Run all tests:

```bash
pytest -q
```

Focused test runs:

```bash
pytest tests/test_analyze_clips.py -q
pytest tests/test_build_clip_plan.py -q
pytest tests/test_run_pipeline.py -q
```

## Future Directions

- Add `clip budget` to constrain target clip count by total duration
- Post-pass merging for overly fragmented adjacent clips
- Integrate `PySceneDetect` for shot-boundary assistance
- Add speaker diarization to distinguish anchor / reporter / interviewee
- Generate thumbnails and burned-in subtitles
- Support additional video genres beyond news
