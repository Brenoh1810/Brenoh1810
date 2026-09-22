#!/usr/bin/env python3
"""Generate a top-languages SVG from GitHub repos.

Public tokens only see public repos. To include private/work repos, set
GH_TOKEN to a PAT with `repo` scope (and SSO authorized for company orgs).
"""

from __future__ import annotations

import json
import os
import ssl
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path

OWNER = os.environ.get("GITHUB_OWNER", "Brenoh1810")
OUTPUT = Path(os.environ.get("TOP_LANGS_OUTPUT", "assets/top-langs.svg"))
MAX_LANGS = int(os.environ.get("TOP_LANGS_COUNT", "6"))
INCLUDE_ORG_REPOS = os.environ.get("INCLUDE_ORG_REPOS", "true").lower() in {
    "1",
    "true",
    "yes",
}
API = "https://api.github.com"

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
    "C#": "#178600",
    "Go": "#00ADD8",
    "PHP": "#4F5D95",
    "Ruby": "#701516",
    "Kotlin": "#A97BFF",
    "Other": "#8b949e",
}

THEME = {
    "bg": "#141321",
    "title": "#fe428e",
    "text": "#a9fef7",
}


def user_pat() -> str:
    """Only the repo secret PRIVATE_REPO_TOKEN. GITHUB_TOKEN cannot see private repos."""
    return os.environ.get("GH_TOKEN", "").strip()


def api_get(path: str, auth: str = ""):
    req = urllib.request.Request(
        f"{API}{path}",
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "profile-top-langs",
            "X-GitHub-Api-Version": "2022-11-28",
            **({"Authorization": f"Bearer {auth}"} if auth else {}),
        },
    )
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
        return json.loads(resp.read().decode())


def paginate(path: str, auth: str = "") -> list:
    items = []
    parsed = urllib.parse.urlparse(path)
    query = urllib.parse.parse_qs(parsed.query)
    query["per_page"] = ["100"]
    page = 1
    while True:
        query["page"] = [str(page)]
        next_path = urllib.parse.urlunparse(
            parsed._replace(query=urllib.parse.urlencode(query, doseq=True))
        )
        batch = api_get(next_path, auth=auth)
        if not batch:
            break
        items.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return items


def describe_pat(pat: str) -> str:
    if pat.startswith("ghp_"):
        return "classic PAT"
    if pat.startswith("github_pat_"):
        return "fine-grained PAT"
    return f"value that does not look like a GitHub token (starts with {pat[:6]!r})"


def owner_pat() -> str:
    pat = user_pat()
    if not pat:
        print("PRIVATE_REPO_TOKEN is empty; counting public repos only")
        return ""
    try:
        me = api_get("/user", auth=pat)
    except urllib.error.HTTPError as exc:
        print(
            f"PRIVATE_REPO_TOKEN was rejected ({exc.code} {exc.reason}). "
            "The secret Value must be the token itself, like ghp_... or github_pat_..., "
            "not the token name. GitHub shows that string only once when you create it. "
            f"Current secret looks like a {describe_pat(pat)}."
        )
        return ""
    login = me.get("login", "")
    if login.lower() != OWNER.lower():
        print(f"Token belongs to {login}, expected {OWNER}; counting public repos only")
        return ""
    print(
        f"Authenticated as {login}; counting public and private repos"
        + (" plus org repos" if INCLUDE_ORG_REPOS else "")
    )
    return pat


def list_repos() -> tuple[list[dict], str]:
    pat = owner_pat()
    if pat:
        affiliation = "owner,organization_member" if INCLUDE_ORG_REPOS else "owner"
        repos = paginate(f"/user/repos?affiliation={affiliation}&visibility=all", auth=pat)
    else:
        repos = paginate(f"/users/{OWNER}/repos?type=owner")

    return [r for r in repos if not r.get("fork")], pat


def language_totals(repos: list[dict], auth: str = "") -> Counter[str]:
    totals: Counter[str] = Counter()
    public = private = skipped = 0
    for repo in repos:
        if repo.get("private"):
            private += 1
        else:
            public += 1
        full_name = repo.get("full_name") or f"{OWNER}/{repo['name']}"
        try:
            langs = api_get(f"/repos/{full_name}/languages", auth=auth)
        except urllib.error.HTTPError:
            skipped += 1
            continue
        totals.update(langs)
    print(
        f"Counted {public} public and {private} private/non-public repos"
        + (f" ({skipped} skipped)" if skipped else "")
    )
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
    repos, pat = list_repos()
    rows = ranked_languages(language_totals(repos, auth=pat))
    if not rows:
        raise SystemExit("No language data found")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(render_svg(rows), encoding="utf-8")
    print(f"Wrote {OUTPUT} with {len(rows)} languages")
    for name, n, pct in rows:
        print(f"  {name:20} {n:8}  {pct:5.1f}%")


if __name__ == "__main__":
    main()
