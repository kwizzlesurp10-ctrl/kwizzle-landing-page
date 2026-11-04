from __future__ import annotations

import io
import re
from typing import Iterable

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
)

from api.pack_pipeline.schema import ArchitectedPrompt, PackPipelineInput

EMERALD = colors.HexColor("#10b981")
SLATE = colors.HexColor("#0f172a")
MUTED = colors.HexColor("#64748b")


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "PackTitle",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=26,
            textColor=SLATE,
            spaceAfter=12,
        ),
        "h1": ParagraphStyle(
            "H1",
            parent=base["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=18,
            textColor=SLATE,
            spaceBefore=18,
            spaceAfter=8,
        ),
        "h2": ParagraphStyle(
            "H2",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=14,
            textColor=EMERALD,
            spaceBefore=14,
            spaceAfter=6,
        ),
        "body": ParagraphStyle(
            "Body",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=10,
            leading=14,
            textColor=SLATE,
            alignment=TA_LEFT,
        ),
        "mono": ParagraphStyle(
            "Mono",
            parent=base["Code"],
            fontName="Courier",
            fontSize=8,
            leading=10,
            textColor=SLATE,
        ),
        "muted": ParagraphStyle(
            "Muted",
            parent=base["BodyText"],
            fontName="Helvetica-Oblique",
            fontSize=9,
            textColor=MUTED,
        ),
    }


def _escape_pdf(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\n", "<br/>")
    )


def _slot_names(template: str) -> list[str]:
    return list(dict.fromkeys(re.findall(r"\[([A-Z0-9_]+)\]", template)))


def _cover_page(story: list, pack: PackPipelineInput, sty: dict[str, ParagraphStyle]) -> None:
    story.append(Spacer(1, 2.2 * inch))
    story.append(Paragraph(_escape_pdf(pack.brand_name), sty["muted"]))
    story.append(Spacer(1, 0.3 * inch))
    story.append(Paragraph(_escape_pdf(pack.pack_title), sty["title"]))
    if pack.pack_subtitle:
        story.append(Paragraph(_escape_pdf(pack.pack_subtitle), sty["h2"]))
    story.append(Spacer(1, 0.4 * inch))
    story.append(Paragraph(_escape_pdf(f"Niche: {pack.niche}"), sty["body"]))
    story.append(
        Paragraph(
            _escape_pdf(f"{len(pack.prompts)} architected multi-step prompts"),
            sty["body"],
        )
    )
    story.append(PageBreak())


def _usage_guide(story: list, sty: dict[str, ParagraphStyle]) -> None:
    story.append(Paragraph("Usage guide", sty["h1"]))
    bullets = [
        "Copy the prompt template into your AI tool (ChatGPT, Claude, etc.).",
        "Replace every [SLOT] placeholder using the slot table under each prompt.",
        "Keep Constraints and Format sections intact — they stabilize output quality.",
        "Compare your output to the worked example; adjust slots, not the core structure.",
        "Use the quick-reference section at the end for daily lookup.",
    ]
    story.append(
        ListFlowable(
            [ListItem(Paragraph(_escape_pdf(b), sty["body"])) for b in bullets],
            bulletType="bullet",
            leftIndent=18,
        )
    )
    story.append(PageBreak())


def _prompt_section(
    story: list,
    prompt: ArchitectedPrompt,
    index: int,
    sty: dict[str, ParagraphStyle],
) -> None:
    story.append(Paragraph(f"Prompt {index}: {_escape_pdf(prompt.title)}", sty["h1"]))
    story.append(Paragraph("Role", sty["h2"]))
    story.append(Paragraph(_escape_pdf(prompt.role), sty["body"]))
    story.append(Paragraph("Goal", sty["h2"]))
    story.append(Paragraph(_escape_pdf(prompt.goal), sty["body"]))
    story.append(Paragraph("Constraints", sty["h2"]))
    story.append(
        ListFlowable(
            [
                ListItem(Paragraph(_escape_pdf(c), sty["body"]))
                for c in prompt.constraints
            ],
            bulletType="bullet",
            leftIndent=18,
        )
    )
    story.append(Paragraph("Format", sty["h2"]))
    story.append(Paragraph(_escape_pdf(prompt.format_spec), sty["body"]))
    story.append(Paragraph("Template", sty["h2"]))
    story.append(Preformatted(prompt.template, sty["mono"]))
    slot_names = _slot_names(prompt.template)
    merged_slots = {s.name: s for s in prompt.slots}
    if slot_names or prompt.slots:
        story.append(Paragraph("Slots", sty["h2"]))
        rows: list[str] = []
        for name in slot_names:
            slot = merged_slots.get(name)
            if slot:
                ex = f" (e.g. {slot.example})" if slot.example else ""
                rows.append(f"[{name}] — {slot.description}{ex}")
            else:
                rows.append(f"[{name}] — (document your value before running)")
        for slot in prompt.slots:
            if slot.name not in slot_names:
                ex = f" (e.g. {slot.example})" if slot.example else ""
                rows.append(f"[{slot.name}] — {slot.description}{ex}")
        story.append(
            ListFlowable(
                [ListItem(Paragraph(_escape_pdf(r), sty["body"])) for r in rows],
                bulletType="bullet",
                leftIndent=18,
            )
        )
    story.append(Paragraph("Worked example output", sty["h2"]))
    story.append(Preformatted(prompt.example_output, sty["mono"]))
    story.append(PageBreak())


def _quick_reference(
    story: list,
    prompts: Iterable[ArchitectedPrompt],
    sty: dict[str, ParagraphStyle],
) -> None:
    story.append(Paragraph("Quick reference", sty["h1"]))
    story.append(Paragraph(_escape_pdf("One-line index of every prompt in this pack."), sty["muted"]))
    story.append(Spacer(1, 0.2 * inch))
    for idx, prompt in enumerate(prompts, start=1):
        slots = ", ".join(f"[{n}]" for n in _slot_names(prompt.template)[:6])
        line = f"{idx}. {prompt.title}"
        if slots:
            line += f" — slots: {slots}"
        story.append(Paragraph(_escape_pdf(line), sty["body"]))
        story.append(Spacer(1, 0.08 * inch))


def build_pack_pdf(pack: PackPipelineInput) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
        title=pack.pack_title,
        author=pack.brand_name,
    )
    sty = _styles()
    story: list = []
    _cover_page(story, pack, sty)
    _usage_guide(story, sty)
    for idx, prompt in enumerate(pack.prompts, start=1):
        _prompt_section(story, prompt, idx, sty)
    _quick_reference(story, pack.prompts, sty)
    doc.build(story)
    return buffer.getvalue()
