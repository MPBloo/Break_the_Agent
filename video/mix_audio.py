#!/usr/bin/env python3
"""Assemble the film and lay the voice-over on it.

    python video/mix_audio.py            # -> video/out/break_the_agent_film.mp4

Each section's video is in video/out/ and its voice-over in video/audio/vo_<section>.mp3 (ElevenLabs,
voice Adam Stone). OFFSET is when the voice starts within its section, chosen so the words land on the
picture (for M2, "water never falls straight" on the first miss and "the right point" on the second pass).
The voice is normalised to -16 LUFS, the usual level for web video.
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
AUDIO = os.path.join(HERE, "audio")

# section, video file, voice file, voice offset in the section (s)
SECTIONS = [
    ("M1", "m1_break_the_agent.mp4", "vo_m1.mp3", 1.6),
    ("M2", "m2_fire_and_water.mp4", "vo_m2.mp3", 6.0),
    ("M3", "m3_the_problem.mp4", "vo_m3.mp3", 0.0),
    ("M4", "m4_what_it_learns.mp4", "vo_m4.mp3", 1.5),
    ("S5", "s5_environment.mp4", "vo_s5.mp3", 0.5),
    ("S6", "s6_reward_reference.mp4", "vo_s6.mp3", 0.5),
    ("S7", "s7_results.mp4", "vo_s7.mp3", 0.5),
    ("S8", "s8_why_agents_fail.mp4", "vo_s8.mp3", 0.8),
    ("S9", "s9_reward_integrity.mp4", "vo_s9.mp3", 0.5),
    ("S10", "s10_one_command.mp4", "vo_s10.mp3", 0.6),
]


def duration(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                       capture_output=True, text=True, check=True)
    return float(r.stdout)


def main():
    t, starts = 0.0, []
    for name, video, voice, off in SECTIONS:
        dv, da = duration(os.path.join(OUT, video)), duration(os.path.join(AUDIO, voice))
        starts.append(t + off)
        print(f"{name:4s} {int(t // 60)}:{t % 60:05.2f}  video {dv:6.2f} s  voice {da:6.2f} s from +{off:.1f} s"
              + ("   (voice runs past the section)" if off + da > dv + 1.0 else ""))
        t += dv
    print(f"total {int(t // 60)}:{t % 60:05.2f}")

    film = os.path.join(OUT, "film_silent.mp4")
    inputs = []
    for _, video, _, _ in SECTIONS:
        inputs += ["-i", os.path.join(OUT, video)]
    n = len(SECTIONS)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex",
                    "".join(f"[{i}:v]" for i in range(n)) + f"concat=n={n}:v=1:a=0[v]", "-map", "[v]",
                    "-c:v", "libx264", "-crf", "19", "-preset", "medium", "-pix_fmt", "yuv420p", "-r", "60",
                    "-movflags", "+faststart", film], check=True)

    ain, parts = [], []
    for i, ((_, _, voice, _), start) in enumerate(zip(SECTIONS, starts)):
        ain += ["-i", os.path.join(AUDIO, voice)]
        ms = int(round(start * 1000))
        parts.append(f"[{i + 1}:a]aresample=48000,aformat=channel_layouts=stereo,adelay={ms}|{ms}[a{i}]")
    mix = ";".join(parts) + ";" + "".join(f"[a{i}]" for i in range(n)) + \
        f"amix=inputs={n}:normalize=0:dropout_transition=0,loudnorm=I=-16:TP=-1.5:LRA=11,apad[aout]"
    final = os.path.join(OUT, "break_the_agent_film.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", film, *ain, "-filter_complex", mix,
                    "-map", "0:v", "-map", "[aout]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
                    "-shortest", "-movflags", "+faststart", final], check=True)
    print("->", final)


if __name__ == "__main__":
    sys.exit(main())
