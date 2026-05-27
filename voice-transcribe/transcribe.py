#!/usr/bin/env python3
"""Whisper large-v3 语音转写 — faster-whisper 加速版"""

import sys
import os
import time

from faster_whisper import WhisperModel


def format_timestamp(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"


def transcribe(filepath, model_size="large-v3", language=None):
    if not os.path.isfile(filepath):
        print(f"[错误] 文件不存在: {filepath}")
        sys.exit(1)

    base = os.path.splitext(filepath)[0]

    print(f"[加载] 模型: {model_size} (float16, CUDA)")
    model = WhisperModel(model_size, device="cuda", compute_type="float16")

    print(f"[转录] {filepath}")
    t0 = time.time()

    segments_gen, info = model.transcribe(
        filepath,
        language=language,
        beam_size=5,
        vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=500),
    )

    print(f"[检测] 语言: {info.language} (概率 {info.language_probability:.2%})")
    segments = list(segments_gen)
    elapsed = time.time() - t0

    full_text = "".join(seg.text for seg in segments)

    # ---- 纯文本 ----
    txt_path = f"{base}.txt"
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(full_text)
    print(f"[输出] {txt_path}")

    # ---- SRT 字幕 ----
    srt_path = f"{base}.srt"
    with open(srt_path, "w", encoding="utf-8") as f:
        for i, seg in enumerate(segments, 1):
            start = format_timestamp(seg.start)
            end = format_timestamp(seg.end)
            f.write(f"{i}\n{start} --> {end}\n{seg.text.strip()}\n\n")
    print(f"[输出] {srt_path}")

    print(f"\n完成: {len(full_text)} 字, {len(segments)} 句, 耗时 {elapsed:.1f}s")
    return full_text


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法:")
        print("  python transcribe.py <音频文件>              默认自动检测语言")
        print("  python transcribe.py <音频文件> zh           指定中文")
        print("  python transcribe.py <音频文件> auto medium  自动检测 + medium 模型")
        sys.exit(1)

    audio_file = sys.argv[1]
    lang = sys.argv[2] if len(sys.argv) > 2 else None
    mdl = sys.argv[3] if len(sys.argv) > 3 else "large-v3"

    transcribe(audio_file, mdl, lang)
