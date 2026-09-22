#!/usr/bin/env python3
"""Generate a static top-languages SVG from public GitHub repos.

The public github-readme-stats instance is often paused or rate-limited.
This card lives in the profile repo, so GitHub serves it directly.
"""

from __future__ import annotations

import json
import os
import ssl
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path

OWNER = os.environ.get("GITHUB_OWNER", "Brenoh1810")
OUTPUT = Path(os.environ.get("TOP_LANGS_OUTPUT", "assets/top-langs.svg"))
MAX_LANGS = int(os.environ.get("TOP_LANGS_COUNT", "6"))
API = "https://api.github.com"

# GitHub Linguist colors (subset) plus a fallback.
LANG_COLORS = {
    "HTML": "#e34c26",
    "Python": "#3572A5",
    "CSS": "#563d7e",
    "Jupyter Notebook": "#DA5B0B",
    "JavaScript": "#f1e05a",
    "TypeScript": "#3178c6",
    "Java": "#b07219",
    "Mako": "#7e858d",
    "PowerShell": "#012456",
    "Other": "#8b949e",
}

# Radical theme, aligned with the streak card.
THEME = {
    "bg": "#141321",
    "title": "#fe428e",
    "text": "#a9fef7",
    "muted": "#7ee8e0",
}


def token() -> str:
    return os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN") or ""


def api_get(path: str):
    req = urllib.request.Request(
        f"{API}{path}",
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "profile-top-langs",
            "X-GitHub-Api-Version": "2022-11-28",
            **({"Authorization": f"Bearer {token()}"} if token() else {}),
        },
    )
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
        return json.loads(resp.read().decode())


def list_owned_repos() -> list[dict]:
    repos = []
    page = 1
    while True:
        batch = api_get(f"/users/{OWNER}/repos?per_page=100&page={page}&type=owner")
        if not batch:
            break
        repos.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return [r for r in repos if not r.get("fork") and not r.get("private")]


def language_totals() -> Counter[str]:
    totals: Counter[str] = Counter()
    for repo in list_owned_repos():
        try:
            langs = api_get(f"/repos/{OWNER}/{repo['name']}/languages")
        except urllib.error.HTTPError:
            continue
        totals.update(langs)
    return totals


def ranked_languages(totals: Counter[str]) -> list[tuple[str, int, float]]:
    total = sum(totals.values()) or 1
    top = totals.most_common(MAX_LANGS)
    shown_bytes = sum(n for _, n in top)
    rows = [(name, n, 100.0 * n / total) for name, n in top]
    leftover = total - shown_bytes
    if leftover > 0 and len(totals) > MAX_LANGS:
        rows.append(("Other", leftover, 100.0 * leftover / total))
    return rows


def color_for(name: str) -> str:
    return LANG_COLORS.get(name, "#58a6ff")


def escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def render_svg(rows: list[tuple[str, int, float]]) -> str:
    width = 495
    bar_x, bar_y, bar_w, bar_h = 25, 58, 445, 10
    row_h = 22
    list_y = 86
    height = list_y + ((len(rows) + 1) // 2) * row_h + 22

    segments = []
    x = bar_x
    for name, _bytes, pct in rows:
        w = max(bar_w * pct / 100.0, 0)
        segments.append(
            f'<rect x="{x:.2f}" y="{bar_y}" width="{w:.2f}" height="{bar_h}" fill="{color_for(name)}"/>'
        )
        x += w

    items = []
    cols = 2
    col_w = bar_w / cols
    for i, (name, _bytes, pct) in enumerate(rows):
        col, row = i % cols, i // cols
        ix = bar_x + col * col_w
        iy = list_y + row * row_h
        items.append(
            f"""
      <circle cx="{ix + 6:.1f}" cy="{iy + 6:.1f}" r="5" fill="{color_for(name)}"/>
      <text x="{ix + 18:.1f}" y="{iy + 10:.1f}" class="lang">{escape(name)} {pct:.1f}%</text>"""
        )

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="Linguagens mais usadas">
  <style>
    .title {{ font: 600 16px 'Segoe UI', Ubuntu, Sans-Serif; fill: {THEME['title']}; }}
    .lang {{ font: 400 13px 'Segoe UI', Ubuntu, Sans-Serif; fill: {THEME['text']}; }}
  </style>
  <rect width="{width}" height="{height}" rx="8" fill="{THEME['bg']}"/>
  <text x="25" y="36" class="title">Linguagens mais usadas</text>
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
    rows = ranked_languages(language_totals())
    if not rows:
        raise SystemExit("No language data found")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(render_svg(rows), encoding="utf-8")
    print(f"Wrote {OUTPUT} with {len(rows)} languages")
    for name, n, pct in rows:
        print(f"  {name:20} {n:8}  {pct:5.1f}%")


if __name__ == "__main__":
    main()
