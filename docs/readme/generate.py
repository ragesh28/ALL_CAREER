"""Render the self-contained illustrations embedded in the README."""

from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent
WIDTH = 1040
INK = "#101e1a"
PANEL = "#1a2c25"
LINE = "#345348"
TEXT = "#eef7ed"
MUTED = "#b5c9bd"
MINT = "#bcf2a6"

STYLE = """
  text { font-family: 'Segoe UI', system-ui, sans-serif; }
  .arrive { animation: arrive 850ms cubic-bezier(.22,.78,.25,1) 160ms both; }
  .later { animation-delay: 480ms; }
  .signal {
    stroke-dasharray: 7 93;
    opacity: 0;
    animation: send 1550ms cubic-bezier(.22,.78,.25,1) 350ms 2;
  }
  .signal-later { animation-delay: 680ms; }
  .highlight { animation: highlight 1.3s cubic-bezier(.22,.78,.25,1) 540ms both; }
  @keyframes arrive {
    from { opacity: .35; transform: translateY(9px); }
    to { opacity: 1; transform: translateY(0); }
  }
  @keyframes send {
    0% { opacity: 0; stroke-dashoffset: 7; }
    12%, 78% { opacity: 1; }
    100% { opacity: 0; stroke-dashoffset: -100; }
  }
  @keyframes highlight {
    0% { opacity: .3; }
    45%, 100% { opacity: 1; }
  }
  @media (prefers-reduced-motion: reduce) {
    .arrive, .signal, .highlight { animation: none; }
  }
"""


def svg(title, height, body):
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{height}" viewBox="0 0 {WIDTH} {height}" role="img">
  <title>{escape(title)}</title>
  <defs>
    <linearGradient id="surface" x2="1" y2="1" gradientUnits="objectBoundingBox">
      <stop stop-color="#0b1716"/>
      <stop offset="1" stop-color="#1b3329"/>
    </linearGradient>
    <pattern id="dots" width="18" height="18" patternUnits="userSpaceOnUse">
      <circle cx="2" cy="2" r="1" fill="#476759" opacity=".45"/>
    </pattern>
  </defs>
  <style>{STYLE.rstrip()}
  </style>
  <rect x="0.5" y="0.5" width="{WIDTH - 1}" height="{height - 1}" rx="27" fill="url(#surface)" stroke="{LINE}"/>
{body}
</svg>
"""


def text(x, y, value, size, color=TEXT, weight=400, attrs=""):
    return f'  <text x="{x}" y="{y}" fill="{color}" font-size="{size}" font-weight="{weight}" {attrs}>{escape(value)}</text>'


def rect(x, y, width, height, radius, fill, stroke=None):
    outline = f' stroke="{stroke}"' if stroke else ""
    return f'  <rect x="{x}" y="{y}" width="{width}" height="{height}" rx="{radius}" fill="{fill}"{outline}/>'


def frame(contents):
    return "\n".join(contents)


def overview():
    paths = [
        "M709 100 H743 Q767 100 767 125 V158 Q767 182 791 182 H805",
        "M709 180 H805",
        "M709 260 H743 Q767 260 767 235 V205 Q767 182 791 182 H805",
    ]
    parts = [
        rect(515, 29, 498, 294, 22, "url(#dots)"),
        '<g class="arrive">',
        text(53, 70, "ALL CAREER", 17, MINT, 700, 'letter-spacing="2.5"'),
        text(49, 150, "Find the jobs", 64, TEXT, 700, 'letter-spacing="-3.5"'),
        text(50, 215, "that fit.", 64, MINT, 700, 'letter-spacing="-3.5"'),
        text(54, 264, "Stay on top of new openings across India.", 19, MUTED, 500),
        text(54, 289, "See the date posted and experience together.", 19, MUTED, 500),
        "</g>",
    ]
    for index, (y, label, subtitle) in enumerate([
        (100, "Job boards", "LinkedIn · Naukri · Indeed"),
        (180, "Career sites", "Company openings"),
        (260, "Telegram & flyers", "Public hiring posts"),
    ]):
        parts += [
            rect(540, y - 29, 170, 58, 11, PANEL, LINE),
            text(553, y - 4, label, 15, TEXT, 650),
            text(553, y + 15, subtitle, 12, MUTED),
            f'  <path d="{paths[index]}" fill="none" stroke="#577a64" stroke-width="1.2"/>',
            f'  <path class="signal{" signal-later" if index == 2 else ""}" d="{paths[index]}" pathLength="100" fill="none" stroke="{MINT}" stroke-width="2.7" stroke-linecap="round"/>',
        ]
    parts += [
        '<g class="arrive later">',
        rect(804, 117, 190, 130, 16, "#1f3b2c", "#648b6b"),
        text(822, 145, "EXAMPLE JOB CARD", 11, MINT, 650, 'letter-spacing="1"'),
        text(822, 179, "Software Engineer", 17, TEXT, 700),
        text(822, 202, "Chennai · Naukri", 14, MUTED),
        text(822, 225, "2 days ago · 0–2 years", 13, MINT, 600),
        "</g>",
    ]
    return svg("All Career brings job listings together", 352, frame(parts))


def job_card():
    parts = [
        rect(36, 42, 378, 200, 18, INK, LINE),
        text(59, 78, "INSIDE THE LISTING", 14, MUTED, 650, 'letter-spacing="1.4"'),
        text(59, 129, "“Minimum 3 years of experience", 19, TEXT, 500),
        text(59, 156, "building and testing web apps.”", 19, TEXT, 500),
        text(59, 202, "Posted two days ago", 16, MUTED),
        '  <path d="M423 142 H501 M492 134 L501 142 492 150" fill="none" stroke="#88a895" stroke-width="1.5"/>',
        f'  <path class="signal" d="M423 142 H501" pathLength="100" fill="none" stroke="{MINT}" stroke-width="2.5"/>',
        '<g class="arrive later">',
        rect(522, 32, 482, 220, 20, PANEL, "#517861"),
        text(549, 76, "ALL CAREER  /  EXAMPLE", 13, MINT, 650, 'letter-spacing="1.4"'),
        text(548, 121, "Software Engineer", 32, TEXT, 700, 'letter-spacing="-1.25"'),
        text(550, 149, "Chennai · Naukri", 16, MUTED),
        rect(548, 170, 200, 57, 10, "#203c2c"),
        rect(754, 170, 224, 57, 10, "#203c2c"),
        '<g class="highlight">',
        text(562, 191, "Posted", 13, MUTED, 500),
        text(562, 214, "2 days ago", 18, MINT, 700),
        text(769, 191, "Experience", 13, MUTED, 500),
        text(769, 214, "Minimum 3 years", 18, MINT, 700),
        "</g>",
        "</g>",
    ]
    return svg("Job card with posting date and required experience", 284, frame(parts))


def shared_filters():
    parts = [
        text(40, 57, "Same link. Same filters.", 34, TEXT, 700, 'letter-spacing="-1.1"'),
        text(42, 91, "Save the search or share it with someone.", 16, MUTED),
        rect(42, 118, 955, 75, 14, INK, LINE),
    ]
    for index, (x, width, label) in enumerate([
        (61, 115, "Chennai"),
        (187, 107, "Naukri"),
        (305, 110, "0 years"),
        (426, 216, "Software Technical"),
    ]):
        parts += [
            f'  <g class="arrive" style="animation-delay:{140 + index * 120}ms">',
            rect(x, 137, width, 36, 8, "#294739", "#49725a"),
            text(x + 13, 160, label, 16, TEXT, 600),
            "</g>",
        ]
    parts += [
        '<g class="arrive later">',
        rect(796, 134, 182, 42, 21, MINT),
        text(816, 161, "Try this search", 16, "#172b12", 700),
        '  <path d="M946 158 l8 -8 m-7 0 h7 v7" fill="none" stroke="#172b12" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>',
        "</g>",
    ]
    return svg("A shareable All Jobs filter selection", 220, frame(parts))


if __name__ == "__main__":
    for name, artwork in [
        ("overview.svg", overview()),
        ("job-card.svg", job_card()),
        ("shared-filters.svg", shared_filters()),
    ]:
        (HERE / name).write_bytes(artwork.encode("utf-8"))
