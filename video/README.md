# Video

Silent video sections, rendered from code: each page draws every frame as a pure function of time,
so a render is identical on every run. Sound (music, voice-over) is added afterwards in an editor.

```bash
node video/render.js video/m1_break_the_agent.html video/out/m1_break_the_agent.mp4      # 1920x1080, 60 fps
node video/render.js video/m1_break_the_agent.html video/out/stills --stills 1,5,12       # PNG stills
```

Needs Node, Playwright with Chromium, and ffmpeg. To join sections:
`ffmpeg -i video/out/m1_break_the_agent.mp4 -i video/out/m2_fire_and_water.mp4 -filter_complex "[0:v][1:v]concat=n=2:v=1:a=0[v]" -map "[v]" video/out/m1_m2.mp4`. Rendered files go to `video/out/` (not committed).
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

## M2 · The fire and the water (45 s, film time 0:30 to 1:15) · pixel art

Drawn at 320x180 and scaled 6x without smoothing. The fire is a cellular automaton; the water follows the
same kind of physics as the environment (gravity, drag, wind, the updraft above the fire). The second
release point is computed by bisection, as the reference solution does.

| Local time | Film time | What happens | Cue for the sound |
|---|---|---|---|
| 0.0 | 0:30.0 | A single small flame (picks up from the ember of M1), stepped zoom out | crackle |
| 1.2 to 7.2 | 0:31.2 | The flame spreads into a burning hillside; smoke | fire bed, wind |
| 7.5 | 0:37.5 | The water bomber enters from the left, descends to the lake | propeller in |
| 8.5 to 11.8 | 0:38.5 | Skims and scoops (spray) | water rush |
| 11.8 to 13.4 | 0:41.8 | Climbs toward the fire | engine strain |
| 13.45 | 0:43.45 | First release, right above the fire | release swoosh |
| 15.0 | 0:45.0 | The water lands beside the fire, grey steam; the fire keeps burning | hiss, "miss" |
| 16.2 / 17.0 / 17.8 | 0:46.2 | Labels WIND, HEAT, DRAG appear | three ticks |
| 24.0 to 25.4 | 0:54.0 | Rewind (rows slip, "REWIND") | tape rewind |
| 25.4 to 29.6 | 0:55.4 | Replay: dashed straight line (what you would expect) and the real curved path | |
| 26.0 | 0:56.0 | "WATER NEVER FALLS STRAIGHT" | hit |
| 29.6 to 30.0 | 0:59.6 | Quick dip to black | |
| 30.0 | 1:00.0 | Second pass enters from the left | propeller in |
| 34.8 | 1:04.8 | Release, earlier and upwind | release swoosh |
| 36.3 | 1:06.3 | The water lands on the fire; it goes out from the centre; white steam | big hiss, relief |
| 36.6 | 1:06.6 | "RELEASE AT THE RIGHT POINT" | hit |
| 40.0 | 1:10.0 | Freeze; a pixel grid appears, the picture fades | music thins |
| 42.6 to 44.2 | 1:12.6 | A wide square grid remains: the start of M3 | |
