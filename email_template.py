"""Turns Gemini's revision notes into a styled HTML email (plus a plain-text fallback)."""
import re
from html import escape

LABELS = {
    "KEY CONCEPT": "💡 Key concept",
    "STEPS": "🪜 Steps",
    "MEMORY TIP": "🧠 Memory tip",
}
FIELD_PATTERN = re.compile(r"^(TOPIC|KEY CONCEPT|STEPS|MEMORY TIP)\s*:\s*(.*)$", re.IGNORECASE)


def parse_notes(text):
    """Parse Gemini's TOPIC / KEY CONCEPT / STEPS / MEMORY TIP blocks into dicts."""
    blocks = []
    for raw_block in re.split(r"^\s*-{3,}\s*$", text or "", flags=re.MULTILINE):
        fields, current = {}, None
        for line in raw_block.strip().splitlines():
            line = line.strip().replace("**", "")
            if line.startswith("```"):
                continue
            match = FIELD_PATTERN.match(line)
            if match:
                current = match.group(1).upper()
                fields[current] = match.group(2).strip()
            elif current and line:
                fields[current] += "\n" + line
        if fields.get("TOPIC"):
            blocks.append(fields)
    return blocks


def _is_empty(value):
    return not value or value.strip().strip(".").upper() in {"N/A", "NA", "NONE", "-"}


def _to_html_text(value):
    return escape(value).replace("\n", "<br>")


def build_email(user_name, summary):
    """Returns (plain_text, html). Falls back to simple paragraphs if parsing finds nothing."""
    notes = parse_notes(summary)
    name = escape(user_name)

    # ---- plain text version ----
    plain = [f"Hi {user_name},", "", "Here are your Snap & Study revision notes:", ""]
    if notes:
        for number, note in enumerate(notes, 1):
            plain.append(f"({number}) {note['TOPIC']}")
            for key, label in LABELS.items():
                if not _is_empty(note.get(key)):
                    plain.append(f"{label}: {note[key]}")
            plain.append("")
    else:
        plain += [(summary or "").strip(), ""]
    plain += ["Happy studying!", "- Snap & Study"]

    # ---- HTML version (inline styles only, so email clients render it) ----
    cards = []
    if notes:
        for number, note in enumerate(notes, 1):
            rows = ""
            for key, label in LABELS.items():
                if _is_empty(note.get(key)):
                    continue
                rows += (
                    f'<p style="margin:12px 0 2px;font-size:12px;font-weight:bold;'
                    f'color:#4f46e5;text-transform:uppercase;letter-spacing:0.5px;">{label}</p>'
                    f'<p style="margin:0;font-size:15px;line-height:1.55;color:#1f2937;">'
                    f'{_to_html_text(note[key])}</p>'
                )
            cards.append(
                '<div style="background:#f5f7ff;border-left:4px solid #4f46e5;'
                'border-radius:8px;padding:16px 18px;margin:0 0 16px;">'
                f'<h2 style="margin:0;font-size:18px;color:#111827;">{number}. '
                f'{_to_html_text(note["TOPIC"])}</h2>{rows}</div>'
            )
    else:
        cards.append(
            '<div style="background:#f5f7ff;border-radius:8px;padding:16px 18px;'
            'font-size:15px;line-height:1.55;color:#1f2937;">'
            f'{_to_html_text((summary or "").strip())}</div>'
        )

    html = (
        '<!DOCTYPE html><html><body style="margin:0;padding:24px 12px;background:#eef0f6;'
        'font-family:Segoe UI,Helvetica,Arial,sans-serif;">'
        '<div style="max-width:600px;margin:0 auto;background:#ffffff;border-radius:12px;'
        'overflow:hidden;">'
        '<div style="background:#4f46e5;padding:24px;color:#ffffff;">'
        '<div style="font-size:24px;font-weight:bold;">📚 Snap &amp; Study</div>'
        '<div style="font-size:14px;opacity:0.9;margin-top:4px;">Your revision notes</div></div>'
        '<div style="padding:24px;">'
        f'<p style="margin:0 0 18px;font-size:15px;color:#1f2937;">Hi {name}, here is a '
        "quick recap of what you studied:</p>"
        f'{"".join(cards)}'
        '<p style="margin:20px 0 0;font-size:14px;color:#6b7280;">Happy studying! 🚀</p></div>'
        '<div style="background:#f9fafb;padding:12px 24px;font-size:12px;color:#9ca3af;">'
        "Sent by Snap &amp; Study</div></div></body></html>"
    )
    return "\n".join(plain), html