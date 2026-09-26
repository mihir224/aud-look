#!/usr/bin/env python3
"""Build the submission PDF from docs/submission.md."""

from __future__ import annotations

import html
import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    LongTable,
    PageBreak,
    PageTemplate,
    Paragraph,
    Preformatted,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs" / "submission.md"
OUTPUT = ROOT / "output" / "pdf" / "aud-look-submission.pdf"

NAVY = colors.HexColor("#102A43")
TEAL = colors.HexColor("#0B7285")
BLUE = colors.HexColor("#2F6F9F")
LIGHT_BLUE = colors.HexColor("#EAF4F8")
LIGHT_GRAY = colors.HexColor("#F4F6F8")
MID_GRAY = colors.HexColor("#66788A")
TEXT = colors.HexColor("#243B53")
WHITE = colors.white


def inline_markup(text: str) -> str:
    escaped = html.escape(text.strip())
    escaped = re.sub(r"`([^`]+)`", r'<font name="Courier">\1</font>', escaped)
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", escaped)
    return escaped


def make_styles():
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="CoverTitle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=28,
            leading=33,
            textColor=WHITE,
            alignment=TA_LEFT,
            spaceAfter=8 * mm,
        )
    )
    styles.add(
        ParagraphStyle(
            name="CoverSubtitle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=14,
            leading=19,
            textColor=colors.HexColor("#D9EDF2"),
            spaceAfter=4 * mm,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Section",
            parent=styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=17,
            leading=21,
            textColor=NAVY,
            spaceBefore=7 * mm,
            spaceAfter=3 * mm,
            keepWithNext=True,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Subsection",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=12.5,
            leading=16,
            textColor=TEAL,
            spaceBefore=5 * mm,
            spaceAfter=2 * mm,
            keepWithNext=True,
        )
    )
    styles.add(
        ParagraphStyle(
            name="BodyCustom",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=9.4,
            leading=14,
            textColor=TEXT,
            spaceAfter=2.6 * mm,
        )
    )
    styles.add(
        ParagraphStyle(
            name="BulletCustom",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=8.8,
            leading=12.2,
            textColor=TEXT,
            leftIndent=5 * mm,
            firstLineIndent=-4 * mm,
        )
    )
    styles.add(
        ParagraphStyle(
            name="TableHeader",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=7.7,
            leading=9.5,
            textColor=WHITE,
            alignment=TA_LEFT,
        )
    )
    styles.add(
        ParagraphStyle(
            name="TableCell",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=7.5,
            leading=9.4,
            textColor=TEXT,
            alignment=TA_LEFT,
        )
    )
    styles.add(
        ParagraphStyle(
            name="CodeCustom",
            parent=styles["Code"],
            fontName="Courier",
            fontSize=7.7,
            leading=10.5,
            textColor=NAVY,
            backColor=LIGHT_GRAY,
            borderColor=colors.HexColor("#CBD5E1"),
            borderWidth=0.5,
            borderPadding=7,
            spaceBefore=2 * mm,
            spaceAfter=4 * mm,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Small",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=11,
            textColor=MID_GRAY,
        )
    )
    return styles


STYLES = make_styles()


def header_footer(canvas, doc):
    canvas.saveState()
    width, height = A4
    if doc.page > 1:
        canvas.setStrokeColor(colors.HexColor("#D9E2EC"))
        canvas.line(19 * mm, height - 16 * mm, width - 19 * mm, height - 16 * mm)
        canvas.setFont("Helvetica-Bold", 7.5)
        canvas.setFillColor(NAVY)
        canvas.drawString(19 * mm, height - 12 * mm, "AUD-LOOK")
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(MID_GRAY)
    canvas.drawString(19 * mm, 11 * mm, "Hackathon submission - Multimodal AI: Audio Search")
    canvas.drawRightString(width - 19 * mm, 11 * mm, f"Page {doc.page}")
    canvas.restoreState()


def cover_story():
    title_box = Table(
        [[Paragraph("aud-look", STYLES["CoverTitle"])],
         [Paragraph("Local hybrid search over diarized podcast conversations", STYLES["CoverSubtitle"])],
         [Paragraph("Multimodal AI: Audio Search | September 2026", STYLES["CoverSubtitle"])]],
        colWidths=[166 * mm],
        rowHeights=[50 * mm, 18 * mm, 14 * mm],
    )
    title_box.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), NAVY),
                ("BOX", (0, 0), (-1, -1), 0, NAVY),
                ("LEFTPADDING", (0, 0), (-1, -1), 12 * mm),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12 * mm),
                ("TOPPADDING", (0, 0), (-1, -1), 8 * mm),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5 * mm),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    cards = [
        ("6", "episodes"),
        ("52:29", "audio corpus"),
        ("0.833", "holdout Recall@5"),
        ("565 ms", "warm p95"),
    ]
    card_table = Table(
        [[Paragraph(f'<b><font size="18" color="#0B7285">{value}</font></b><br/><font size="8" color="#66788A">{label}</font>', STYLES["Small"]) for value, label in cards]],
        colWidths=[41.5 * mm] * 4,
        rowHeights=[28 * mm],
    )
    card_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), LIGHT_BLUE),
                ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#B8D8E3")),
                ("INNERGRID", (0, 0), (-1, -1), 0.6, WHITE),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    summary = Paragraph(
        "A reproducible Python/PostgreSQL system combining literal search, local semantic embeddings, "
        "candidate fusion, and local cross-encoder reranking. Results retain the source file, speaker, "
        "timestamp, and transcript evidence required for an auditable audio-search experience.",
        STYLES["BodyCustom"],
    )
    return [
        Spacer(1, 15 * mm),
        title_box,
        Spacer(1, 15 * mm),
        card_table,
        Spacer(1, 13 * mm),
        summary,
        Spacer(1, 24 * mm),
        Paragraph("Submission contents", STYLES["Subsection"]),
        Paragraph(
            "Engineering design and rationale; success criteria and measured achievement; evaluation methodology; "
            "production considerations; limitations; reproduction instructions; and AI-usage disclosure.",
            STYLES["BodyCustom"],
        ),
        PageBreak(),
    ]


def column_widths(rows: list[list[str]], available: float) -> list[float]:
    columns = len(rows[0])
    if columns == 5:
        weights = [1.75, 0.7, 0.75, 0.8, 2.25]
    elif columns == 6:
        weights = [1.55, 0.8, 0.8, 0.8, 0.8, 0.95]
    elif columns == 4:
        weights = [2.0, 1.35, 2.1, 0.85]
    elif columns == 2:
        weights = [1.35, 4.65]
    else:
        weights = [1.0] * columns
    total = sum(weights)
    return [available * weight / total for weight in weights]


def markdown_table(rows: list[list[str]], available: float):
    data = []
    for row_index, row in enumerate(rows):
        style = STYLES["TableHeader"] if row_index == 0 else STYLES["TableCell"]
        data.append([Paragraph(inline_markup(cell), style) for cell in row])
    table = LongTable(data, colWidths=column_widths(rows, available), repeatRows=1, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_GRAY]),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#CBD5E1")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return table


def markdown_list(items: list[str], available: float, numbered: bool = False):
    data = []
    for index, item in enumerate(items, 1):
        marker = f"{index}." if numbered else "&bull;"
        data.append(
            [
                Paragraph(marker, STYLES["BulletCustom"]),
                Paragraph(inline_markup(item), STYLES["BulletCustom"]),
            ]
        )
    table = LongTable(data, colWidths=[5 * mm, available - 5 * mm], hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 1),
                ("TOPPADDING", (0, 0), (-1, -1), 1.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5),
            ]
        )
    )
    return table


def parse_markdown(text: str, available: float):
    lines = text.splitlines()
    story = []
    index = 1 if lines and lines[0].startswith("# ") else 0
    paragraph_lines: list[str] = []

    def flush_paragraph():
        if paragraph_lines:
            story.append(Paragraph(inline_markup(" ".join(paragraph_lines)), STYLES["BodyCustom"]))
            paragraph_lines.clear()

    while index < len(lines):
        line = lines[index].rstrip()
        if not line:
            flush_paragraph()
            index += 1
            continue
        if line.startswith("```"):
            flush_paragraph()
            code: list[str] = []
            index += 1
            while index < len(lines) and not lines[index].startswith("```"):
                code.append(lines[index])
                index += 1
            story.append(Preformatted("\n".join(code), STYLES["CodeCustom"]))
            index += 1
            continue
        if line.startswith("### "):
            flush_paragraph()
            story.append(Paragraph(inline_markup(line[4:]), STYLES["Subsection"]))
            index += 1
            continue
        if line.startswith("## "):
            flush_paragraph()
            story.append(Paragraph(inline_markup(line[3:]), STYLES["Section"]))
            index += 1
            continue
        if line.startswith("| ") and index + 1 < len(lines) and re.match(r"^\|[-:| ]+\|$", lines[index + 1]):
            flush_paragraph()
            table_rows = [[cell.strip() for cell in line.strip("|").split("|")]]
            index += 2
            while index < len(lines) and lines[index].startswith("|"):
                table_rows.append([cell.strip() for cell in lines[index].strip("|").split("|")])
                index += 1
            story.extend([markdown_table(table_rows, available), Spacer(1, 4 * mm)])
            continue
        if line.startswith("- "):
            flush_paragraph()
            items = []
            while index < len(lines) and lines[index].startswith("- "):
                items.append(lines[index][2:])
                index += 1
            story.append(markdown_list(items, available))
            story.append(Spacer(1, 2 * mm))
            continue
        if re.match(r"^\d+\. ", line):
            flush_paragraph()
            items = []
            while index < len(lines) and re.match(r"^\d+\. ", lines[index]):
                match = re.match(r"^(\d+)\. (.*)", lines[index])
                items.append(match.group(2))
                index += 1
            story.append(markdown_list(items, available, numbered=True))
            story.append(Spacer(1, 2 * mm))
            continue
        paragraph_lines.append(line)
        index += 1
    flush_paragraph()
    return story


def build_pdf():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    width, height = A4
    left = right = 19 * mm
    top = 21 * mm
    bottom = 17 * mm
    frame = Frame(left, bottom, width - left - right, height - top - bottom, id="normal")
    document = BaseDocTemplate(
        str(OUTPUT),
        pagesize=A4,
        leftMargin=left,
        rightMargin=right,
        topMargin=top,
        bottomMargin=bottom,
        title="aud-look - Effective Retrieval from Audio Transcripts",
        author="aud-look project",
        subject="Hackathon engineering design, evaluation, limitations, and AI-usage disclosure",
    )
    document.addPageTemplates([PageTemplate(id="submission", frames=[frame], onPage=header_footer)])
    available = width - left - right
    story = cover_story() + parse_markdown(SOURCE.read_text(encoding="utf-8"), available)
    document.build(story)
    print(OUTPUT)


if __name__ == "__main__":
    build_pdf()
