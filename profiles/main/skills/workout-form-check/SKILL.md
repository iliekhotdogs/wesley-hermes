---
name: workout-form-check
description: Use to review exercise/lifting form from a workout video.
---

# Workout form check

Repurposes the video-content-analysis pipeline (yt-dlp + ffmpeg frame sampling + vision_analyze) to critique exercise form instead of summarizing a reel. Lives only in main's profile — same host-tool dependency as video-content-analysis; do not delegate to builder/Docker specialists (no yt-dlp/ffmpeg there, MAIN_REQUIRED on install).

## 1. Get the video local
Same routes as video-content-analysis step 1: Drive inbox folder, Discord attachment, or public Instagram/YouTube link via `~/.local/bin/yt-dlp.exe -o in.mp4 "<url>"` (full path, not on PATH). Use a fresh scratch dir. On Windows pass absolute `C:/...` paths to yt-dlp/ffmpeg — resolve with `pwd -W` first.

## 2. Sample frames
```
ffmpeg -v error -y -i in.mp4 -vf "scale=480:-2,fps=2" -q:v 4 f_%03d.jpg   # 2 frames/sec, denser than reel-summary sampling since form faults are brief
ffmpeg -v error -y -framerate 2 -i f_%03d.jpg -vf tile=4x4 -frames:v 1 sheet1.jpg   # repeat per 16-frame batch if the rep is long
```
Denser sampling than general reel analysis (fps=2 not fps=1/10) because form faults (knee cave, rounded back, bar path) can appear for under a second.

## 3. Identify the exercise and ask vision_analyze targeted questions
First pass: show one representative frame, ask "what exercise is this and what is the camera angle (front/side/3-4)?" Use the answer to pick the right fault checklist:
- Squat: knee valgus (knees caving in), heel rise, excessive forward lean, depth (hip crease vs knee), bar path over midfoot.
- Deadlift: rounded lower back, bar drifting away from shins, hips rising before chest, lockout hyperextension.
- Bench press: elbow flare angle, bar path (straight line vs arcing), wrist position, feet/leg drive.
- Overhead press: lower back arch (compensating), bar path in front vs overhead, elbow flare.
- If exercise doesn't match a known checklist, ask vision_analyze generically for joint alignment, range of motion, and any asymmetry between left/right sides.

Read each contact sheet once with vision_analyze (one call per ~16 frames), asking it to flag the specific checklist items frame-by-frame with approximate rep-number/frame-position references, not a generic paragraph.

## 4. Synthesize one structured report
Format:
- **Exercise & angle identified**
- **What looked correct** (2-3 specific observations, e.g. "neutral spine maintained through the pull")
- **Faults found**, each with a frame/rep reference and why it's a fault
- **2-3 concrete correction cues** (short, actionable, e.g. "screw feet into the floor to stop knee cave")

Disclose sampling gaps (frames are sparse snapshots, not continuous video) only if they'd change the verdict — same disclosure norm as video-content-analysis. Do not give generic textbook fitness advice disconnected from what the actual frames show; every claim should be traceable to a specific observed frame.
