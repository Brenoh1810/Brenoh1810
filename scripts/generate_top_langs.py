#!/usr/bin/env python3
"""Generate a curated languages card for the profile README.

This is not GitHub linguist data. Public repos miss work/private code,
so the list below is the stack you want to show.
"""

from __future__ import annotations

from pathlib import Path

OUTPUT = Path("assets/top-langs.svg")

# Edit this list to add or remove what you use at work or in studies.
LANGUAGES = [
    ("TypeScript", "#3178c6"),
    ("JavaScript", "#f1e05a"),
    ("Node.js", "#339933"),
    ("Python", "#3572A5"),
    ("Java", "#b07219"),
    ("SQL", "#00758f"),
    ("HTML", "#e34c26"),
    ("CSS", "#563d7e"),
]

THEME = {
    "bg": "#141321",
    "title": "#fe428e",
    "text": "#a9fef7",
}


def escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def render_svg(languages: list[tuple[str, str]]) -> str:
    width = 495
    bar_x, bar_y, bar_w, bar_h = 25, 58, 445, 10
    row_h = 22
    list_y = 86
    cols = 2
    height = list_y + ((len(languages) + 1) // cols) * row_h + 22
    segment_w = bar_w / len(languages)

    segments = []
    for i, (_name, color) in enumerate(languages):
        segments.append(
            f'<rect x="{bar_x + i * segment_w:.2f}" y="{bar_y}" width="{segment_w:.2f}" height="{bar_h}" fill="{color}"/>'
        )

    items = []
    col_w = bar_w / cols
    for i, (name, color) in enumerate(languages):
        col, row = i % cols, i // cols
        ix = bar_x + col * col_w
        iy = list_y + row * row_h
        items.append(
            f"""
      <circle cx="{ix + 6:.1f}" cy="{iy + 6:.1f}" r="5" fill="{color}"/>
      <text x="{ix + 18:.1f}" y="{iy + 10:.1f}" class="lang">{escape(name)}</text>"""
        )

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="Linguagens que uso">
  <style>
    .title {{ font: 600 16px 'Segoe UI', Ubuntu, Sans-Serif; fill: {THEME['title']}; }}
    .lang {{ font: 400 13px 'Segoe UI', Ubuntu, Sans-Serif; fill: {THEME['text']}; }}
  </style>
  <rect width="{width}" height="{height}" rx="8" fill="{THEME['bg']}"/>
  <text x="25" y="36" class="title">Linguagens que uso</text>
  <rect x="{bar_x}" y="{bar_y}" width="{bar_w}" height="{bar_h}" rx="5" fill="#1f1e30"/>
  <clipPath id="bar">
    <rect x="{bar_x}" y="{bar_y}" width="{bar_w}" height="{bar_h}" rx="5"/>
  </clipPath>
  <g clip-path="url(#bar)">
    {''.join(segments)}
  </g>
  {''.join(items)}
</svg>
"""


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(render_svg(LANGUAGES), encoding="utf-8")
    print(f"Wrote {OUTPUT}")
    for name, _color in LANGUAGES:
        print(f"  {name}")


if __name__ == "__main__":
    main()
