---
name: video-content-analysis
description: Use when asked to watch a reel/TikTok. Frames+transcript.
---

# Video content analysis

I cannot play video. I analyze a local file via (a) a Whisper transcript and (b) sampled frames read as images. Say this plainly to the user: motion between frames is missed; speech and on-screen text are the reliable parts.

## 1. Get the file local (pick the first that fits)
- **Drive inbox (verified route):** user uploads to a Drive folder (no size limit, works from phone, avoids Discord's ~10 MB free upload cap). List with `google_api.py drive search "'<folderId>' in parents and trashed=false" --raw-query --max 50` (returns id/name/modifiedTime; filenames are opaque hashes, so identify videos by content), download with `google_api.py drive download <fileId> --output <path>`. For several videos, loop download into one scratch dir as v1..vN.mp4 and process them in one batch.
  - A folder link alone grants nothing: a 404 "File not found" means the folder is not shared with the authorized account. Find the account with `drive.about().get(fields="user(emailAddress)")` and ask the user to share the folder (Editor) with that address. Never assume the authorized account is the user's own.
  - The user must ping in chat after uploading; do not poll.
- **Discord attachment:** works if small enough; analyze the cached local path.
- **Public link:** `yt-dlp` (install: `uv tool install yt-dlp`; the exe lands in `~/.local/bin`, which may not be on PATH, so call it by full path). Instagram often needs cookies; fall back to the Drive route. (Not yet exercised end to end.)

## 2. Analyze (work in scratch dir, not the Drive folder)
Raw social videos can be 100+ MB for ~2.5 min; do not feed them whole to `video_analyze`. Derive small artifacts instead:
```
ffmpeg -v error -y -i in.mp4 -vf "scale=360:-2,fps=1/10" -q:v 5 a_%02d.jpg   # 1 frame / 10 s
ffmpeg -v error -y -i in.mp4 -vn -ac 1 -ar 16000 a.wav
ffmpeg -v error -y -framerate 1 -i a_%02d.jpg -vf tile=4x4 -frames:v 1 a_sheet.jpg  # contact sheet
```
- Use the `%02d` sequence pattern for ffmpeg input; `-pattern_type glob` fails on Windows builds.
- Transcribe: `WhisperModel("base",device="cpu",compute_type="int8").transcribe("a.wav", vad_filter=True)` from `faster_whisper` (CPU is fine; ~2.5 min audio finishes inside a tool timeout). Run it from a script file with `python -I`, load the model once and loop all clips, and redirect output to a file (`> tr.txt`) then `read_file` it: piping through `tail` or reading the background-completion notification truncates long transcripts.
- A multi-video ffmpeg+Whisper run exceeds the 600 s foreground cap and is auto-promoted to a background process; wait on it with `process_manage` (a deferred tool: call it via `tool_call`, it is not a direct tool). Wait is clamped to ~180 s per call, so re-wait.
- Clips that are consecutive parts of one talk (transcript ends mid-sentence, same speaker/setting) should be rated and reported together as a series.
- Read each contact sheet once with `vision_analyze` (one call per ~16 frames instead of 16 calls). Tighten fps or crop with `region` only if on-screen text (whiteboards, slides) must be read.
- Burned-in captions in frames corroborate the transcript; mention if they agree.

## 3. Report
Give: what the video is (setting, speaker, source watermark), a structured summary, limits (sampling gaps, unreadable small text), and rough token cost (a two-video run was ~10-15k tokens). Offer follow-ups rather than doing them unasked.

When the user asks which videos are "worth looking into": rate each out of 10 with pros and cons and a one-line verdict, judged against the user's actual setup (Hermes multi-profile agents, 8 GB RAM / no GPU PC, hosted APIs), then end with a short ordered "what I'd do". Flag engagement-bait roundups and claims that cannot run on the user's hardware.

## 4. Follow-ups on tools a video mentions
Video spoken names are often garbled by Whisper (e.g. a product heard as "pits a bot" was really Pizza Bot; "Artemis", "Terneri Bonsai" were right only after searching). Resolve each name with `web_search`, confirm it is real from the project's own repo/blog, then rate it per tool. When asked to summarize docs, `web_extract` the repo README / launch post; extracted pages are truncated head+tail, so `search_files`/`read_file` the saved cache path for the omitted middle. Say plainly that ratings come from docs and search results, not from installing or testing.
