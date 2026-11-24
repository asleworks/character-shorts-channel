#!/usr/bin/env python3
"""Assemble illustrated or infographic scenes and narration into a vertical short."""
import argparse
from bisect import bisect_right
from dataclasses import dataclass
from difflib import SequenceMatcher
from functools import lru_cache
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unicodedata

from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageOps

WIDTH, HEIGHT, FPS, POSE_FPS = 1080, 1920, 30, 12
LEAD, HOLD = 0.2, 0.5
SUBTITLE_Y = round(HEIGHT * 0.76)
PAPER, INK = "#f8f2e2", "#1c1510"
LANCZOS = Image.Resampling.LANCZOS


@dataclass(frozen=True)
class Scene:
    key: str
    dialogue: str
    image: Path | None
    screen_text: tuple[str, ...]
    number: str | None = None


@dataclass(frozen=True)
class Word:
    text: str
    start: float
    end: float


@dataclass(frozen=True)
class Caption:
    frame: int
    text: str


def read_scenes(path):
    rows = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(rows, list) or not rows:
        raise ValueError("scenes.json must contain a nonempty array of scenes.")
    scenes = []
    keys = set()
    for row in rows:
        key, dialogue = (row[field] for field in ("key", "dialogue"))
        labels = row.get("screen_text", [])
        if not all(isinstance(value, str) and value.strip() for value in (key, dialogue)):
            raise ValueError("Each scene needs a nonempty key and dialogue.")
        if key in keys:
            raise ValueError(f"Duplicate scene key: {key}")
        if not isinstance(labels, list) or not all(isinstance(label, str) for label in labels):
            raise ValueError(f"{key}: screen_text must be an array of strings.")
        kind = row.get("type", "image")
        if kind == "image":
            image = row.get("image")
            if not isinstance(image, str) or not image.strip():
                raise ValueError(f"{key}: image scenes need a nonempty image path.")
            scene = Scene(key, dialogue, path.parent / image, tuple(labels))
        elif kind == "card":
            if not 1 <= len(labels) <= 3 or not all(label.strip() for label in labels):
                raise ValueError(f"{key}: card scenes need one to three nonempty screen_text lines.")
            number = row.get("number")
            if number is not None and (not isinstance(number, str) or not number.strip()):
                raise ValueError(f"{key}: card number must be a nonempty string.")
            scene = Scene(key, dialogue, None, tuple(labels), number)
        else:
            raise ValueError(f"{key}: scene type must be image or card.")
        keys.add(key)
        scenes.append(scene)
    return scenes


def call(*args):
    result = subprocess.run(args, capture_output=True)
    if result.returncode:
        raise ValueError(result.stderr.decode(errors="replace").strip() or f"{args[0]} failed.")
    return result.stdout


def media_info(path):
    return json.loads(call("ffprobe", "-v", "error", "-show_format",
                           "-show_streams", "-of", "json", str(path)))


def read_words(path, audio, duration, model_name, language):
    if path:
        data = json.loads(path.read_text(encoding="utf-8"))
    else:
        import numpy as np
        from faster_whisper import WhisperModel

        print("Transcribing narration with faster-whisper…", flush=True)
        pcm = call("ffmpeg", "-v", "error", "-nostdin", "-i", str(audio),
                   "-map", "0:a:0", "-ar", "16000", "-ac", "1", "-f", "f32le", "pipe:1")
        model = WhisperModel(model_name, device="cpu", compute_type="int8")
        segments, _ = model.transcribe(np.frombuffer(pcm, dtype="<f4"), language=language,
                                       word_timestamps=True, condition_on_previous_text=False)
        data = [{"w": word.word, "s": word.start, "e": word.end}
                for segment in segments for word in segment.words or []]

    words = []
    for item in data:
        text = item["w"].strip()
        start, end = float(item["s"]), float(item["e"])
        if not math.isfinite(start) or not math.isfinite(end) or not 0 <= start <= end:
            raise ValueError("Word times must be finite, nonnegative and in seconds.")
        if words and start < words[-1].start:
            raise ValueError("Sort the word timing JSON by start time.")
        if text and end > start and start < duration:
            words.append(Word(text, start, min(end, duration)))
    if not words:
        raise ValueError("No spoken word timings were found in the narration.")
    return words


def word_chars(tokens):
    chars, owners = [], []
    for index, token in enumerate(tokens):
        normalized = unicodedata.normalize("NFC", token).casefold()
        letters = [char for char in normalized if char.isalnum()]
        chars.extend(letters)
        owners.extend((index, offset, len(letters)) for offset in range(len(letters)))
    return chars, owners


def align(script, heard):
    expected, expected_owners = word_chars(script)
    observed, observed_owners = word_chars([word.text for word in heard])
    blocks = SequenceMatcher(None, expected, observed, autojunk=False).get_matching_blocks()
    matched = sum(block.size for block in blocks)
    if not expected or matched / len(expected) < 0.82:
        raise ValueError("Narration and dialogue diverge. Check the script and word timing JSON.")

    anchors = [None] * len(script)
    used = set()
    for left, right, size in blocks:
        for shift in range(size):
            index, script_offset, _ = expected_owners[left + shift]
            heard_index, offset, length = observed_owners[right + shift]
            token = heard[heard_index]
            used.add(heard_index)
            if anchors[index] is None:
                fraction = max(0, offset - script_offset) / length
                anchors[index] = token.start + (token.end - token.start) * fraction

    # Use surrounding anchors for missed script words without importing ASR text.
    known = [(-1, 0.0)] + [(i, t) for i, t in enumerate(anchors) if t is not None]
    known.append((len(anchors), max(word.end for word in heard)))
    inferred = sum(time is None for time in anchors)
    for (left, start), (right, stop) in zip(known, known[1:]):
        for index in range(left + 1, right):
            anchors[index] = start + (stop - start) * (index - left) / (right - left)
    return anchors, matched / len(expected), inferred, len(heard) - len(used)


def find_font(supplied):
    if supplied:
        ImageFont.truetype(str(supplied), 48)
        return str(supplied), 0

    apple = Path("/System/Library/Fonts/AppleSDGothicNeo.ttc")
    candidates = [(str(apple), 6)] if apple.is_file() else []
    if shutil.which("fc-list"):
        entries = call("fc-list", "--format", "%{file}\t%{index}\n", ":lang=ko").decode().splitlines()
        entries.sort(key=lambda value: ("noto" not in value.lower(), "bold" not in value.lower()))
        candidates.extend((path, int(index)) for path, index in (entry.rsplit("\t", 1) for entry in entries))
    for base in (Path("/usr/share/fonts"), Path.home() / "Library/Fonts",
                 Path.home() / ".local/share/fonts"):
        candidates.extend((str(path), 0) for path in base.rglob("*NotoSans*KR*") if path.is_file())
        candidates.extend((str(path), 0) for path in base.rglob("*NotoSansCJK*") if path.is_file())

    for path, index in candidates:
        try:
            font = ImageFont.truetype(path, 48, index=index)
        except OSError:
            continue
        if bytes(font.getmask("한")) != bytes(font.getmask("글")):
            return path, index
    raise ValueError("No Korean font found. Supply --font with a Noto Sans KR .ttf or .otf file.")


def phrase_groups(tokens, font, end_punctuation=True):
    """Yield contiguous original words that fit on one line."""
    line = []
    for token in tokens:
        combined = " ".join(line + [token])
        korean = re.search(r"[가-힣]", combined) is not None
        too_wide = font.getlength(combined) > WIDTH * 0.86 or (korean and len(combined) > 14)
        if line and too_wide:
            yield line
            line = []
        line.append(token)
        if end_punctuation and token.endswith((".", "?", "!", "…")):
            yield line
            line = []
    if line:
        yield line


def frame_at(seconds):
    return math.ceil(seconds * FPS - 1e-7)


def schedule(scenes, words, font, duration):
    tokens = [scene.dialogue.split() for scene in scenes]
    anchors, coverage, inferred, unused = align([word for line in tokens for word in line], words)
    cuts, onsets, captions = [], [], []
    offset = 0
    for scene, line in zip(scenes, tokens):
        onset = anchors[offset] + LEAD
        cut = frame_at(onset)
        if cuts and cut <= cuts[-1]:
            raise ValueError(f"{scene.key}: two scenes start on the same frame. Check word timings.")
        cuts.append(cut)
        onsets.append(onset)
        for group in phrase_groups(line, font):
            caption = Caption(frame_at(anchors[offset] + LEAD), " ".join(group))
            if captions and caption.frame <= captions[-1].frame:
                raise ValueError(f"{scene.key}: caption starts overlap. Check word timings.")
            captions.append(caption)
            offset += len(group)
    if cuts[-1] >= frame_at(duration + LEAD):
        raise ValueError("The last scene begins after the narration.")
    if " ".join(caption.text for caption in captions).split() != [t for line in tokens for t in line]:
        raise ValueError("Subtitle text does not match the script.")
    return cuts, onsets, captions, (coverage, inferred, unused)


def scene_art(path):
    with Image.open(path) as source:
        image = ImageOps.exif_transpose(source).convert("RGBA")
    white = Image.new("RGBA", image.size, "white")
    white.alpha_composite(image)
    r, g, b = white.convert("RGB").split()
    near_white = ImageChops.darker(ImageChops.darker(r, g), b).point(
        lambda pixel: 255 if pixel >= 246 else 0
    )
    # Clear only white connected to the frame edge. Keep whites enclosed by the art.
    border = ImageOps.expand(near_white, border=1, fill=255)
    ImageDraw.floodfill(border, (0, 0), 128)
    mask = border.crop((1, 1, image.width + 1, image.height + 1)).point(
        lambda pixel: 0 if pixel == 128 else 255
    )
    if mask.getbbox():
        white.putalpha(mask)
        white = white.crop(mask.getbbox())
    white.thumbnail((WIDTH, HEIGHT), LANCZOS)
    return white


class Layout:
    def __init__(self, font_path, font_index):
        self.font_path = font_path
        self.font_index = font_index

    @lru_cache(maxsize=96)
    def font(self, size):
        return ImageFont.truetype(self.font_path, size, index=self.font_index)

    def text(self, canvas, text, x, y, size, max_width, outline=0):
        draw = ImageDraw.Draw(canvas)
        for point_size in range(size, 0, -1):
            font = self.font(point_size)
            stroke = round(outline * point_size / size)
            box = draw.textbbox((0, 0), text, font=font, stroke_width=stroke)
            if box[2] - box[0] <= max_width:
                draw.text((x - (box[0] + box[2]) / 2, y - (box[1] + box[3]) / 2), text,
                          font=font, fill=INK, stroke_width=stroke, stroke_fill="white")
                return
        raise ValueError("On-screen text is too long to fit.")

    def background(self, scene, art, zoom):
        if art is None:
            return self.card_background(scene)
        canvas = Image.new("RGBA", (WIDTH, HEIGHT), PAPER)
        scale = zoom * min(WIDTH * 0.84 / art.width, HEIGHT * 0.46 / art.height)
        size = (max(1, round(art.width * scale)), max(1, round(art.height * scale)))
        image = art.resize(size, LANCZOS)
        canvas.alpha_composite(image, ((WIDTH - image.width) // 2, 1370 - image.height))
        spacing = min(110, 420 / max(1, len(scene.screen_text)))
        for index, label in enumerate(scene.screen_text):
            self.text(canvas, label, WIDTH // 2, 240 + spacing * index,
                      min(96, round(spacing * 0.88)), WIDTH * 0.88, outline=5)
        return canvas

    def card_background(self, scene):
        canvas = Image.new("RGBA", (WIDTH, HEIGHT), PAPER)
        draw = ImageDraw.Draw(canvas)
        center_x = WIDTH // 2
        draw.rounded_rectangle((100, 250, 980, 1290), radius=64, fill="#fffdf6",
                               outline=INK, width=5)
        draw.ellipse((355, 335, 725, 705), fill="#ffce65", outline=INK, width=5)
        if scene.number is None:
            draw.polygon(((540, 405), (655, 520), (540, 635), (425, 520)), fill=INK)
            draw.ellipse((512, 492, 568, 548), fill="#ffce65")
        else:
            self.text(canvas, scene.number, center_x, 520, 166, 286)

        title, *details = scene.screen_text
        self.text(canvas, title, center_x, 850, 110, 756)
        if details:
            draw.line((210, 953, 870, 953), fill=INK, width=4)
        for index, label in enumerate(details):
            self.text(canvas, label, center_x, 1040 + 105 * index, 64, 756)
        return canvas


def loudness(path, prefilter=None):
    filters = "loudnorm=I=-14:TP=-1:LRA=11:print_format=json"
    if prefilter:
        filters = f"{prefilter},{filters}"
    result = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-nostdin", "-i", str(path),
                             "-vn", "-af", filters, "-f", "null", "-"], capture_output=True)
    log = result.stderr.decode(errors="replace")
    match = re.search(r'\{\s*"input_i".*?\}', log, re.S)
    if result.returncode or not match:
        raise ValueError(f"FFmpeg could not measure audio loudness: {log.strip()}")
    metrics = json.loads(match.group())
    integrated, peak = float(metrics["input_i"]), float(metrics["input_tp"])
    if not math.isfinite(integrated) or not math.isfinite(peak):
        raise ValueError("The narration is silent or too short to measure.")
    return integrated, peak


def punch_zoom(age, duration):
    if duration <= 4:
        return 1.0
    t = max(0, min(1, (age - min(2.45, duration * 0.52)) / 0.34))
    return 1 + 0.06 * t * t * (3 - 2 * t)


def master_audio(source, duration, track):
    stereo = "aformat=sample_rates=48000:channel_layouts=stereo"
    integrated, _ = loudness(source, stereo)
    gain = -14.05 - integrated
    limit = -1.8
    for _ in range(5):
        filters = (f"{stereo},volume={gain:.4f}dB,"
                   f"alimiter=limit={10 ** (limit / 20):.6f}:level=0:latency=1,"
                   f"adelay={round(LEAD * 1000)}:all=1,apad")
        call("ffmpeg", "-v", "error", "-nostdin", "-y", "-i", str(source),
             "-vn", "-map_metadata", "-1", "-af", filters, "-t", f"{duration:.6f}",
             "-c:a", "aac", "-b:a", "192k", str(track))
        actual, peak = loudness(track)
        if abs(actual + 14) <= 0.25 and peak <= -1:
            return
        limit -= max(0, peak + 1.15)
        gain += -14.05 - actual
    raise ValueError(f"Could not master audio to −14 LUFS / −1 dBTP ({actual:.2f} / {peak:.2f}).")


def encode(video, track, scenes, art, layout, cuts, captions, frames, audio_end):
    cmd = [
        "ffmpeg", "-v", "error", "-nostdin", "-y",
        "-f", "rawvideo", "-pixel_format", "rgb24", "-video_size", f"{WIDTH}x{HEIGHT}",
        "-framerate", str(FPS), "-i", "pipe:0", "-i", str(track),
        "-map", "0:v:0", "-map", "1:a:0", "-map_metadata", "-1",
        "-vf", "scale=out_color_matrix=bt709,format=yuv420p",
        "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "17",
        "-c:a", "copy", "-movflags", "+faststart", str(video),
    ]
    scene_frames = [0, *cuts[1:], frames]
    caption_frames = [caption.frame for caption in captions]
    previous_pose, previous_overlay = None, None
    with subprocess.Popen(cmd, stdin=subprocess.PIPE) as encoder:
        try:
            with encoder.stdin:
                for frame in range(frames):
                    at = min(frame, audio_end - 1)
                    index = bisect_right(scene_frames, at) - 1
                    age = max(0, at - cuts[index]) * POSE_FPS // FPS
                    duration = (min(scene_frames[index + 1], audio_end) - cuts[index]) / FPS
                    zoom = punch_zoom(age / POSE_FPS, duration) if art[index] is not None else 1.0
                    pose = index, zoom
                    if pose != previous_pose:
                        background = layout.background(scenes[index], art[index], zoom)
                        previous_pose = pose
                    caption_index = bisect_right(caption_frames, at) - 1
                    overlay = pose, caption_index
                    if overlay != previous_overlay:
                        canvas = background.copy()
                        if caption_index >= 0:
                            layout.text(canvas, captions[caption_index].text, WIDTH // 2,
                                        SUBTITLE_Y, 84, WIDTH * 0.88, outline=9)
                        raw = canvas.convert("RGB").tobytes()
                        previous_overlay = overlay
                    encoder.stdin.write(raw)
        except BrokenPipeError:
            raise ValueError("FFmpeg closed the video stream. See its output above.") from None
        if encoder.wait():
            raise ValueError("FFmpeg could not encode the MP4.")


def scene_sheet(video, path, scenes, cuts, audio_end, layout):
    starts = [0, *cuts[1:]]
    ends = starts[1:] + [audio_end]
    samples = [start + int((end - start) * 0.63) for start, end in zip(starts, ends)]
    select = "+".join(f"eq(n\\,{frame})" for frame in samples)
    tile_w, tile_h = 234, 416
    raw = call("ffmpeg", "-v", "error", "-nostdin", "-i", str(video), "-an",
               "-vf", f"select={select},scale={tile_w}:{tile_h}", "-fps_mode", "vfr",
               "-pix_fmt", "rgb24", "-f", "rawvideo", "pipe:1")
    tile_bytes = tile_w * tile_h * 3
    if len(raw) != len(scenes) * tile_bytes:
        raise ValueError("Could not decode one frame per scene from the final MP4.")
    columns = min(4, len(scenes))
    cell_h = tile_h + 32
    sheet = Image.new("RGB", (columns * tile_w, math.ceil(len(scenes) / columns) * cell_h), INK)
    draw = ImageDraw.Draw(sheet)
    for index, (scene, frame) in enumerate(zip(scenes, samples)):
        x, y = (index % columns) * tile_w, (index // columns) * cell_h
        tile = Image.frombytes("RGB", (tile_w, tile_h), raw[index * tile_bytes:(index + 1) * tile_bytes])
        sheet.paste(tile, (x, y))
        draw.text((x + 8, y + tile_h + 5), f"{scene.key}  {frame / FPS:.2f}s",
                  font=layout.font(17), fill="white")
    sheet.save(path, quality=90, optimize=True)


def markdown_cell(value):
    return " ".join(value.split()).replace("|", "\\|")


def write_report(path, scenes, cuts, onsets, captions, frames, metrics, alignment, font_name):
    integrated, peak = metrics
    coverage, inferred, unused = alignment
    lines = [
        "# 렌더 검수", "",
        "[MP4](short.mp4) · [장면 시트](sheet_scenes.jpg)", "",
        f"- H.264 · {WIDTH}×{HEIGHT} · {FPS}fps · {frames / FPS:.2f}초 · {len(scenes)}컷.",
        f"- 최종 MP4 음량 {integrated:.2f} LUFS / 최고 {peak:.2f} dBTP.",
        f"- 자막 {len(captions)}줄을 대본과 대조했습니다. 글꼴은 {font_name}입니다.",
        f"- 타이밍 대조에서 정규화한 대본 글자의 {coverage:.1%}가 일치했습니다. "
        f"대본 단어 {inferred}개의 타이밍을 보간했고 매칭 없이 남은 ASR 단어는 {unused}개입니다.",
        "- 장면 시트는 최종 MP4에서 디코딩했습니다. 재생하면서 발화와 컷 전환, "
        "자막과 화면 문구, 캐릭터와 그림 오류를 확인하세요.",
        "", "| 장면 | 컷 시작(초) | 첫 단어(초) | 자막 순서 | 화면 문구 |",
        "|---|---:|---:|---|---|",
    ]
    for index, (scene, cut, onset) in enumerate(zip(scenes, cuts, onsets)):
        stop = cuts[index + 1] if index + 1 < len(cuts) else frames
        script = " / ".join(c.text for c in captions if cut <= c.frame < stop)
        labels = " / ".join(([scene.number] if scene.number is not None else [])
                            + list(scene.screen_text)) or "—"
        cut_start = (cut if index else 0) / FPS
        lines.append(f"| {markdown_cell(scene.key)} | {cut_start:.3f} | {onset:.3f} | "
                     f"{markdown_cell(script)} | {markdown_cell(labels)} |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenes", type=Path, required=True, help="ordered scenes.json")
    parser.add_argument("--audio", type=Path, required=True, help="narration audio, e.g. MP3 or WAV")
    parser.add_argument("--words", type=Path, help="JSON word timings [{w, s, e}], in seconds")
    parser.add_argument("--out", type=Path, required=True, help="output directory")
    parser.add_argument("--font", type=Path, help="path to a Korean font such as Noto Sans KR")
    parser.add_argument("--language", help="faster-whisper language code, e.g. ko")
    parser.add_argument("--whisper-model", default="small", help="faster-whisper model name or path")
    args = parser.parse_args()

    try:
        for program in ("ffmpeg", "ffprobe"):
            if not shutil.which(program):
                raise ValueError(f"Install {program} and add it to PATH.")
        scenes = read_scenes(args.scenes)
        art = [scene_art(scene.image) if scene.image is not None else None for scene in scenes]
        layout = Layout(*find_font(args.font))
        info = media_info(args.audio)
        if not any(stream["codec_type"] == "audio" for stream in info["streams"]):
            raise ValueError("Narration input contains no audio stream.")
        duration = float(info["format"]["duration"])
        if not math.isfinite(duration) or duration <= 0:
            raise ValueError("The narration must have a positive duration.")
        words = read_words(args.words, args.audio, duration, args.whisper_model, args.language)
        cuts, onsets, captions, alignment = schedule(scenes, words, layout.font(84), duration)
        audio_end = frame_at(duration + LEAD)
        frames = audio_end + round(HOLD * FPS)

        args.out.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix=".render-", dir=args.out) as temporary:
            scratch = Path(temporary)
            track, video = scratch / "master.m4a", scratch / "short.mp4"
            sheet, report = scratch / "sheet_scenes.jpg", scratch / "REPORT.md"
            master_audio(args.audio, frames / FPS, track)
            print(f"Encoding {len(scenes)} scenes at {WIDTH}×{HEIGHT}…", flush=True)
            encode(video, track, scenes, art, layout, cuts, captions, frames, audio_end)
            streams = media_info(video)["streams"]
            picture = next(stream for stream in streams if stream["codec_type"] == "video")
            if (picture["codec_name"], picture["width"], picture["height"], picture["r_frame_rate"],
                    int(picture["nb_frames"])) != ("h264", WIDTH, HEIGHT, f"{FPS}/1", frames):
                raise ValueError("Unexpected codec, frame size, frame rate or frame count.")
            metrics = loudness(video)
            if abs(metrics[0] + 14) > 0.25 or metrics[1] > -1:
                raise ValueError(f"Final MP4 loudness failed verification: {metrics}")
            scene_sheet(video, sheet, scenes, cuts, audio_end, layout)
            write_report(report, scenes, cuts, onsets, captions, frames, metrics, alignment,
                         " ".join(layout.font(84).getname()))
            for file in (video, sheet, report):
                file.replace(args.out / file.name)
    except (OSError, ValueError, KeyError, TypeError, StopIteration) as error:
        parser.exit(1, f"render: {error}\n")
    print(f"Saved {args.out / 'short.mp4'}", flush=True)


if __name__ == "__main__":
    main()
