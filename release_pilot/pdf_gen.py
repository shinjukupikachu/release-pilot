"""Generate PDF release notes using fpdf2."""

from __future__ import annotations

import re
from pathlib import Path

from fpdf import FPDF

_UNICODE_MAP = {
    "—": "-",  # em dash
    "–": "-",  # en dash
    "→": "->",  # right arrow
    "←": "<-",  # left arrow
    "‘": "'",  # left single quote
    "’": "'",  # right single quote
    "“": '"',  # left double quote
    "”": '"',  # right double quote
    "…": "...",  # ellipsis
    "•": "*",  # bullet
    "✓": "[ok]",
    "✔": "[ok]",
    "✗": "[x]",
    "✘": "[x]",
    # emoji replacements used in internal announcement
    "✨": "[Feature]",  # ✨
    "\U0001f41b": "[Bug]",  # 🐛
    "⚡": "[Perf]",  # ⚡
    "\U0001f512": "[Sec]",  # 🔒
    "⚠️": "[!]",  # ⚠️ (combined)
    "⚠": "[!]",  # ⚠
    "️": "",  # variation selector
    "\U0001f4cb": "",  # 📋
    "\U0001f4e3": "",  # 📢
    "\U0001f4e4": "",  # 📤
    "✅": "[ok]",  # ✅
    "❌": "[x]",  # ❌
    "⚙️": "",  # ⚙️
    "⚙": "",  # ⚙
}


def _sanitize(text: str) -> str:
    """Replace non-Latin1 characters so core Helvetica fonts can encode them."""
    for ch, repl in _UNICODE_MAP.items():
        text = text.replace(ch, repl)
    # Strip any remaining non-Latin1 chars
    return "".join(c if ord(c) < 256 else "?" for c in text)


# ── Markdown → HTML (subset fpdf2 understands) ────────────────────────────────


def _inline(text: str) -> str:
    """Convert inline markdown to HTML: bold, italic, code, links."""
    text = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"\*(.*?)\*", r"<i>\1</i>", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)
    # escape bare & that aren't already entities
    text = re.sub(r"&(?!amp;|lt;|gt;|quot;)", "&amp;", text)
    return text


def _md_to_html(text: str) -> str:
    """Convert a markdown document to minimal HTML for fpdf2's write_html."""
    if not text:
        return ""
    lines = text.splitlines()
    parts: list[str] = []
    in_list = False

    def close_list():
        nonlocal in_list
        if in_list:
            parts.append("</ul>")
            in_list = False

    for line in lines:
        if line.startswith("# "):
            close_list()
            parts.append(f"<h1>{_inline(line[2:].strip())}</h1>")
        elif line.startswith("## "):
            close_list()
            parts.append(f"<h2>{_inline(line[3:].strip())}</h2>")
        elif line.startswith("### "):
            close_list()
            parts.append(f"<h3>{_inline(line[4:].strip())}</h3>")
        elif re.match(r"^[-*] ", line):
            if not in_list:
                parts.append("<ul>")
                in_list = True
            # Handle indented sub-bullets
            content = _inline(line[2:].strip())
            parts.append(f"<li>{content}</li>")
        elif re.match(r"^  [-*] ", line):
            if not in_list:
                parts.append("<ul>")
                in_list = True
            content = _inline(line[4:].strip())
            parts.append(f"<li>{content}</li>")
        elif line.strip() == "":
            close_list()
            parts.append("<br/>")
        elif line.startswith("---") or line.startswith("==="):
            close_list()
            parts.append("<hr/>")
        else:
            close_list()
            parts.append(f"<p>{_inline(line.strip())}</p>")

    close_list()
    return "\n".join(parts)


# ── PDF class ─────────────────────────────────────────────────────────────────


class _ReleasePDF(FPDF):
    def __init__(self, version: str):
        super().__init__()
        self._version = version
        self.set_margins(20, 20, 20)
        self.set_auto_page_break(auto=True, margin=20)

    def header(self):
        self.set_fill_color(20, 20, 20)
        self.set_text_color(255, 255, 255)
        self.set_font("Helvetica", "B", 10)
        self.cell(
            0,
            9,
            _sanitize(f"  NyankoOS Release Notes - {self._version}"),
            fill=True,
            ln=True,
        )
        self.set_text_color(0, 0, 0)
        self.ln(3)

    def footer(self):
        self.set_y(-14)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(130)
        self.cell(
            0,
            8,
            _sanitize(f"Page {self.page_no()} | NyankoOS {self._version}"),
            align="C",
        )
        self.set_text_color(0)

    def section_title(self, title: str):
        self.set_font("Helvetica", "B", 14)
        self.set_fill_color(240, 240, 240)
        self.cell(0, 9, _sanitize(f"  {title}"), fill=True, ln=True)
        self.ln(2)

    def readiness_badge(self, score: int, recommendation: str, bump: str):
        color = {
            "READY": (0, 160, 80),
            "HOLD": (220, 140, 0),
            "BLOCKED": (200, 40, 40),
        }.get(recommendation, (80, 80, 80))
        self.set_font("Helvetica", "B", 11)
        self.set_fill_color(*color)
        self.set_text_color(255, 255, 255)
        label = _sanitize(f"  {recommendation}  Score: {score}/100  Bump: {bump}  ")
        self.cell(0, 8, label, fill=True, ln=True)
        self.set_text_color(0)
        self.ln(4)

    def write_md(self, markdown_text: str):
        html = _md_to_html(_sanitize(markdown_text))
        self.write_html(html)
        self.ln(4)


# ── Public API ────────────────────────────────────────────────────────────────


def generate(
    version: str,
    customer_notes: str | None,
    marketing_notes: str | None,
    internal_announcement: str | None,
    readiness_score: int,
    recommendation: str,
    suggested_bump: str,
    output_path: Path,
) -> None:
    """Render a PDF and write it to output_path. Creates parent dirs as needed."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    pdf = _ReleasePDF(version)

    # ── Page 1: Customer Release Notes ────────────────────────────────────
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 20)
    pdf.cell(0, 12, _sanitize(f"Release Notes - {version}"), ln=True)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(100)
    pdf.cell(0, 5, "Customer-facing release notes", ln=True)
    pdf.set_text_color(0)
    pdf.ln(3)
    pdf.readiness_badge(readiness_score, recommendation, suggested_bump)
    pdf.write_md(customer_notes or "_No customer notes generated._")

    # ── Page 2: Marketing Summary ──────────────────────────────────────────
    if marketing_notes and marketing_notes.strip():
        pdf.add_page()
        pdf.section_title("Marketing Summary")
        pdf.ln(2)
        pdf.write_md(marketing_notes)

    # ── Page 3: Internal Announcement ─────────────────────────────────────
    if internal_announcement and internal_announcement.strip():
        pdf.add_page()
        pdf.section_title("Internal Engineering Announcement")
        pdf.ln(2)
        pdf.write_md(internal_announcement)

    pdf.output(str(output_path))
