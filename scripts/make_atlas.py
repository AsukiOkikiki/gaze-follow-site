#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从图生视频短片抽取 121 帧，拼成 11×11 精灵图集 atlas.jpg（每格 256×370）。

用法:
  python make_atlas.py <video.mp4> [output.jpg]
依赖: ffmpeg 必须在 PATH 中可用。

几何必须与模板常量一致: COLS=11, ROWS=11, N=121, CELL=256, CELLH=370。
输出尺寸应为 2816×4070。
"""
import json
import subprocess
import sys
import pathlib


def ffprobe(video):
    out = subprocess.check_output([
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height,nb_frames,duration,r_frame_rate",
        "-of", "json", video,
    ])
    d = json.loads(out)
    st = d["streams"][0]
    num, den = (st.get("r_frame_rate") or "24/1").split("/")
    fps = float(num) / float(den or 1)
    dur = float(st.get("duration") or 0)
    nframes = int(st.get("nb_frames") or round(dur * fps))
    return fps, dur, nframes


def make(video, out):
    fps, dur, nframes = ffprobe(video)
    want = 121
    # 以 want/dur 重采样，得到约 121 帧（dur 为 0 时退回按帧数推算）
    if dur > 0:
        fr = want / dur
    else:
        fr = want / max(nframes, 1) * fps
    filt = "fps=%.5f,scale=256:370,tile=11x11" % fr
    subprocess.check_call([
        "ffmpeg", "-y", "-i", video,
        "-vf", filt,
        "-frames:v", "1", "-q:v", "3", out,
    ])
    p = pathlib.Path(out)
    print("atlas ->", p.resolve())
    print("expect 2816x4070 (11x11 x 256x370); want=%d frames, source=%d" % (want, nframes))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("usage: make_atlas.py <video.mp4> [output.jpg]")
    video = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else "atlas.jpg"
    make(video, out)
