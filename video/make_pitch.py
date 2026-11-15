#!/usr/bin/env python3
"""The 2-minute pitch video (Junction submission: strictly 2:00 or less).

    python video/make_pitch.py      # -> video/out/break_the_agent_pitch_2min.mp4

Full motion design: shots cut from M1 (the closing title), M2 (the Canadair), M3 (the task and the score), and
five scenes made for the pitch (p_intro, p_air, p_results, p_why, p_holds). The voice-over (ElevenLabs, Adam Stone) is one
take, video/audio/vo_pitch.mp3, cut at its pauses into 16 phrases, each placed on its picture.
"""
import os
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
VOICE = os.path.join(HERE, "audio", "vo_pitch.mp3")

SOURCES = ["m1_break_the_agent.mp4", "m2_fire_and_water.mp4", "m3_the_problem.mp4",
           "p_results.mp4", "p_why.mp4", "p_holds.mp4", "p_intro.mp4", "p_air.mp4"]
M1, M2, M3, PR, PW, PH, PI, PA = range(8)

# (source, start, end) in the source's own time
SHOTS = [
    (PI, 0.0, 16.8),    # the problem: agents write code... can they learn a system they cannot see? BLIND DROP
    (M2, 9.0, 19.5),    # the Canadair drops, misses: wind, heat, drag
    (PA, 0.0, 6.0),     # THE AIR IS UNKNOWN: the six hidden numbers, named
    (M3, 13.0, 19.5),   # 1 CALIBRATE: ten noisy test drops
    (M3, 23.2, 28.8),   # 2 BUILD A MODEL: calculations run down
    (M3, 29.0, 36.8),   # 3 COMMIT: five blind drops
    (M3, 36.8, 39.3),   # the score: 1 at the centre, 0 at 6 m
    (PR, 0.0, 25.0),    # results, then the same fire side by side
    (PW, 0.0, 12.5),    # where the points are lost, the main mistake
    (PH, 0.0, 16.0),    # the reward holds, one command, Harbor
    (M1, 24.5, 30.0),   # title, Junction 2026, the drop puts out the ember
]

# (start, end) of each phrase in vo_pitch.mp3, and where it plays in the pitch
PHRASES = [
    (0.00, 9.04, 0.9),     # AI agents can write code... one shot?
    (9.67, 11.86, 12.4),   # We built an environment to find out.
    (12.50, 15.20, 17.3),  # A Canadair drops water on a wildfire.
    (15.68, 23.60, 20.4),  # But water never falls straight... the air is unknown.
    (24.18, 32.77, 33.5),  # ten noisy test drops... 120 calculations to fit a model.
    (33.28, 39.13, 45.6),  # Then five fires, one blind drop each. It never sees where the water lands.
    (39.72, 42.13, 53.3),  # The environment scores the real impacts.
    (42.56, 45.47, 56.1),  # Our reference uses the same tools and budgets.
    (45.99, 52.36, 59.5),  # Claude Sonnet 5.5 scores 0.73...
    (52.88, 58.70, 66.4),  # Opus 5.5 comes close...
    (59.19, 66.10, 72.7),  # On the same fire...
    (66.72, 70.80, 81.0),  # We replay counterfactuals...
    (71.37, 77.53, 85.7),  # The models' main mistake...
    (78.06, 87.78, 93.5),  # The reward holds...
    (88.26, 93.03, 103.8), # One command... Harbor.
    (93.67, 97.88, 109.6), # Break the Agent: learn an unknown system, then commit.
]


def main():
    total = sum(e - s for _, s, e in SHOTS)
    assert total <= 119.5, total
    inputs = []
    for f in SOURCES:
        inputs += ["-i", os.path.join(OUT, f)]
    inputs += ["-i", VOICE]
    vi = len(SOURCES)
    parts = [f"[{src}:v]trim=start={s}:end={e},setpts=PTS-STARTPTS,fps=60[v{i}]" for i, (src, s, e) in enumerate(SHOTS)]
    parts.append("".join(f"[v{i}]" for i in range(len(SHOTS))) + f"concat=n={len(SHOTS)}:v=1:a=0[v]")
    parts.append(f"[{vi}:a]aresample=48000,aformat=channel_layouts=stereo,asplit={len(PHRASES)}" +
                 "".join(f"[s{i}]" for i in range(len(PHRASES))))
    for i, (a, b, at) in enumerate(PHRASES):
        ms = int(round(at * 1000))
        parts.append(f"[s{i}]atrim=start={max(0, a - 0.05)}:end={b + 0.12},asetpts=PTS-STARTPTS,"
                     f"afade=t=in:d=0.03,afade=t=out:st={b + 0.12 - max(0, a - 0.05) - 0.06}:d=0.06,adelay={ms}|{ms}[p{i}]")
    parts.append("".join(f"[p{i}]" for i in range(len(PHRASES))) +
                 f"amix=inputs={len(PHRASES)}:normalize=0:dropout_transition=0,loudnorm=I=-16:TP=-1.5:LRA=11,apad[a]")
    out = os.path.join(OUT, "break_the_agent_pitch_2min.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", ";".join(parts),
                    "-map", "[v]", "-map", "[a]", "-t", f"{total:.3f}", "-c:v", "libx264", "-crf", "18", "-preset", "medium",
                    "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", out],
                   check=True)
    print(f"{total:.1f} s -> {out}")


if __name__ == "__main__":
    main()
