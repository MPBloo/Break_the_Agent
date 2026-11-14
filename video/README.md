# Video

Silent video sections, rendered from code: each page draws every frame as a pure function of time,
so a render is identical on every run. Sound (music, voice-over) is added afterwards in an editor.

```bash
node video/render.js video/m1_break_the_agent.html video/out/m1_break_the_agent.mp4      # 1920x1080, 60 fps
node video/render.js video/m1_break_the_agent.html video/out/stills --stills 1,5,12       # PNG stills
```

Needs Node, Playwright with Chromium, and ffmpeg. Rendered files go to `video/out/` (not committed).
Fonts: Anton, Inter and JetBrains Mono, under the SIL Open Font License (`video/fonts/`).

## M1 · Break the Agent (30 s) · cut on a 124 BPM grid (one beat = 0.484 s)

| Time | What happens | Cue for the sound |
|---|---|---|
| 0.00 | Black, a thin line of light (closed eye) | intro swell |
| 0.48 | The eye snaps open (beat 1) | first hit |
| 2.00 | Push into the pupil | riser |
| 2.42 | "WRITES CODE" (beat 5) | hit |
| 3.39 | "PROVES THEOREMS" (beat 7) | hit |
| 4.35 | "BUILDS APPS" (beat 9) | hit |
| 5.32 | Pull back out of the pupil (beat 11) | whoosh |
| 6.00 | The pupil shows a burning forest | music drops to half |
| 6.77 / 7.26 / 7.74 | "NOW," / "A WORLD" / "IT HAS NEVER SEEN" (beats 14 to 16) | soft hits |
| 10.16 | Counter "10", then counts down every half beat | ticks |
| 12.58 | "ONE SHOT" stamp | big hit |
| 13.55 | "NO FEEDBACK" stamp | big hit |
| 15.00 | The eye returns, the iris cracks | tension |
| 15.48 | The iris shatters into letters (beat 32); hard colour cuts on every beat until 19.35 | drop |
| 17.42 | "WHERE DOES IT BREAK?" | |
| 20.00 | The shards fly back; letters land one by one until about 21.8 | build |
| 22.30 | Underline under AGENT | |
| 23.20 | Light sweep across the title | shimmer |
| 26.00 | Title shrinks; "Junction 2026 · AfterQuery challenge" | music settles |
| 27.55 | A drop of water falls | |
| 28.30 | The drop hits the ember and puts it out | splash, then silence |
| 29.00 to 30.00 | Hold on the final frame | |
