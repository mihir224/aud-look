#!/usr/bin/env python3
"""Generate the high-level aud-look workflow diagram used by the submission."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "assets" / "high-level-workflow.png"

WIDTH = 2600
HEIGHT = 1180
BACKGROUND = "#F7FAFC"
NAVY = "#102A43"
TEAL = "#0B7285"
BLUE = "#2F6F9F"
LIGHT_BLUE = "#EAF4F8"
LIGHT_TEAL = "#E6F5F7"
LIGHT_GRAY = "#EEF2F6"
MID_GRAY = "#66788A"
WHITE = "#FFFFFF"

REGULAR_FONT = Path("/System/Library/Fonts/Supplemental/Arial.ttf")
BOLD_FONT = Path("/System/Library/Fonts/Supplemental/Arial Bold.ttf")


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(BOLD_FONT if bold else REGULAR_FONT), size)


def centered_lines(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    lines: list[str],
    text_font: ImageFont.FreeTypeFont,
    fill: str,
    gap: int = 12,
) -> None:
    x1, y1, x2, y2 = box
    heights = []
    for line in lines:
        bounds = draw.textbbox((0, 0), line, font=text_font)
        heights.append(bounds[3] - bounds[1])
    total_height = sum(heights) + gap * max(0, len(lines) - 1)
    y = y1 + (y2 - y1 - total_height) / 2
    for line, line_height in zip(lines, heights):
        bounds = draw.textbbox((0, 0), line, font=text_font)
        line_width = bounds[2] - bounds[0]
        draw.text(((x1 + x2 - line_width) / 2, y), line, font=text_font, fill=fill)
        y += line_height + gap


def card(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    stage: str,
    title: str,
    details: list[str],
    accent: str = TEAL,
    background: str = WHITE,
) -> None:
    x1, y1, x2, y2 = box
    draw.rounded_rectangle(box, radius=30, fill=background, outline="#C5D3DF", width=4)
    draw.rounded_rectangle((x1, y1, x2, y1 + 18), radius=9, fill=accent)
    draw.rounded_rectangle((x1 + 24, y1 + 35, x1 + 93, y1 + 104), radius=18, fill=accent)
    centered_lines(draw, (x1 + 24, y1 + 35, x1 + 93, y1 + 104), [stage], font(28, True), WHITE)
    draw.text((x1 + 24, y1 + 126), title, font=font(34, True), fill=NAVY)
    centered_lines(draw, (x1 + 20, y1 + 180, x2 - 20, y2 - 24), details, font(25), MID_GRAY, gap=10)


def arrow(
    draw: ImageDraw.ImageDraw,
    start: tuple[int, int],
    end: tuple[int, int],
    color: str = BLUE,
    width: int = 10,
) -> None:
    sx, sy = start
    ex, ey = end
    draw.line((sx, sy, ex - 22, ey), fill=color, width=width)
    draw.polygon([(ex, ey), (ex - 28, ey - 18), (ex - 28, ey + 18)], fill=color)


def elbow_arrow(
    draw: ImageDraw.ImageDraw,
    start: tuple[int, int],
    bend_x: int,
    end: tuple[int, int],
    color: str,
) -> None:
    sx, sy = start
    ex, ey = end
    draw.line((sx, sy, bend_x, sy, bend_x, ey, ex - 22, ey), fill=color, width=10, joint="curve")
    draw.polygon([(ex, ey), (ex - 28, ey - 18), (ex - 28, ey + 18)], fill=color)


def build() -> None:
    image = Image.new("RGB", (WIDTH, HEIGHT), BACKGROUND)
    draw = ImageDraw.Draw(image)

    draw.text((70, 55), "aud-look workflow", font=font(64, True), fill=NAVY)
    draw.text(
        (70, 137),
        "From podcast audio to precise, speaker-attributed search evidence",
        font=font(31),
        fill=MID_GRAY,
    )

    audio = (60, 410, 325, 700)
    transcribe = (390, 410, 700, 700)
    cache = (765, 410, 1075, 700)
    lexical = (1140, 220, 1510, 520)
    semantic = (1140, 590, 1510, 890)
    union = (1575, 410, 1865, 700)
    rerank = (1930, 410, 2220, 700)
    evidence = (2285, 380, 2550, 730)

    card(draw, audio, "1", "Audio corpus", ["6 podcast clips", "52m 29s total"])
    card(draw, transcribe, "2", "Transcription", ["Gemini verbatim words", "speaker labels", "word timestamps"], BLUE)
    card(draw, cache, "3", "Canonical cache", ["checksum-keyed JSON", "reusable offline"], NAVY, LIGHT_GRAY)
    card(draw, lexical, "4A", "Lexical branch", ["speaker utterances", "PostgreSQL FTS", "reviewed entity aliases"], BLUE, LIGHT_BLUE)
    card(draw, semantic, "4B", "Semantic branch", ["conversation chunks", "local BGE embeddings", "pgvector cosine search"], TEAL, LIGHT_TEAL)
    card(draw, union, "5", "Candidate union", ["expand to utterances", "deduplicate", "preserve provenance"], NAVY, LIGHT_GRAY)
    card(draw, rerank, "6", "Local reranking", ["target-only scoring", "cross-encoder"], TEAL)
    card(draw, evidence, "7", "Ranked evidence", ["episode + speaker", "timestamp + text", "FastAPI + Streamlit"], NAVY, LIGHT_GRAY)

    arrow(draw, (audio[2], 555), (transcribe[0], 555))
    arrow(draw, (transcribe[2], 555), (cache[0], 555))
    elbow_arrow(draw, (cache[2], 555), 1105, (lexical[0], 370), BLUE)
    elbow_arrow(draw, (cache[2], 555), 1105, (semantic[0], 740), TEAL)
    elbow_arrow(draw, (lexical[2], 370), 1540, (union[0], 520), BLUE)
    elbow_arrow(draw, (semantic[2], 740), 1540, (union[0], 590), TEAL)
    arrow(draw, (union[2], 555), (rerank[0], 555))
    arrow(draw, (rerank[2], 555), (evidence[0], 555))

    draw.rounded_rectangle((690, 970, 1910, 1085), radius=25, fill=NAVY)
    centered_lines(
        draw,
        (715, 985, 1885, 1070),
        ["Retrieve with conversational context  |  Return precise utterance evidence"],
        font(30, True),
        WHITE,
    )

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    image.save(OUTPUT, "PNG", optimize=True)
    print(OUTPUT)


if __name__ == "__main__":
    build()
