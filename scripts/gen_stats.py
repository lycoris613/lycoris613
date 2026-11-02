"""Render GitHub stats / top-languages cards as local SVGs (no third-party host)."""
import json
import os
import sys
import urllib.request
from html import escape

USER = os.environ["USERNAME"]
TOKEN = os.environ["GITHUB_TOKEN"]
OUT = "assets"

BG, BORDER, TITLE, TEXT, ICON = "#05010f", "#7b2ff7", "#00e5ff", "#d7d2ff", "#ff2bd6"
PALETTE = ["#00e5ff", "#7b2ff7", "#ff2bd6", "#f5e663", "#3b0a5c"]

QUERY = """
query($login: String!) {
  user(login: $login) {
    repositoriesContributedTo(first: 1, contributionTypes: [COMMIT, ISSUE, PULL_REQUEST, REPOSITORY]) { totalCount }
    pullRequests { totalCount }
    issues { totalCount }
    contributionsCollection { totalCommitContributions restrictedContributionsCount }
    repositories(ownerAffiliations: OWNER, isFork: false, privacy: PUBLIC, first: 100) {
      totalCount
      nodes {
        stargazerCount
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name color } }
        }
      }
    }
  }
}
"""


def gql():
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": USER}}).encode(),
        headers={"Authorization": f"bearer {TOKEN}", "User-Agent": "profile-stats"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        body = json.load(r)
    if "errors" in body:
        sys.exit(json.dumps(body["errors"]))
    return body["data"]["user"]


def card(width, height, title, inner):
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
<rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="6" fill="{BG}" stroke="{BORDER}"/>
<text x="25" y="35" font-family="Segoe UI, Ubuntu, sans-serif" font-size="18" font-weight="600" fill="{TITLE}">{escape(title)}</text>
{inner}
</svg>
"""


def stats_svg(u):
    c = u["contributionsCollection"]
    stars = sum(r["stargazerCount"] for r in u["repositories"]["nodes"])
    rows = [
        ("Total Stars", stars),
        ("Commits (last year)", c["totalCommitContributions"] + c["restrictedContributionsCount"]),
        ("Pull Requests", u["pullRequests"]["totalCount"]),
        ("Issues", u["issues"]["totalCount"]),
        ("Public Repos", u["repositories"]["totalCount"]),
        ("Contributed To", u["repositoriesContributedTo"]["totalCount"]),
    ]
    inner = ""
    for i, (label, val) in enumerate(rows):
        y = 70 + i * 22
        inner += (
            f'<circle cx="32" cy="{y - 5}" r="4" fill="{ICON}"/>'
            f'<text x="46" y="{y}" font-family="Segoe UI, Ubuntu, sans-serif" font-size="14" fill="{TEXT}">{label}:</text>'
            f'<text x="250" y="{y}" font-family="Segoe UI, Ubuntu, sans-serif" font-size="14" font-weight="700" fill="{TEXT}">{val:,}</text>\n'
        )
    return card(350, 200, f"{USER}'s GitHub Stats", inner)


def langs_svg(u):
    totals = {}
    for r in u["repositories"]["nodes"]:
        for e in r["languages"]["edges"]:
            n = e["node"]
            t = totals.setdefault(n["name"], [0, n["color"] or "#8888aa"])
            t[0] += e["size"]
    top = sorted(totals.items(), key=lambda kv: -kv[1][0])[:6]
    whole = sum(v[0] for _, v in top) or 1
    inner, bar_x = "", 25
    for name, (size, color) in top:
        w = 300 * size / whole
        inner += f'<rect x="{bar_x:.1f}" y="52" width="{w:.1f}" height="8" fill="{color}"/>'
        bar_x += w
    for i, (name, (size, color)) in enumerate(top):
        x, y = 25 + (i % 2) * 150, 85 + (i // 2) * 25
        inner += (
            f'<circle cx="{x + 5}" cy="{y - 5}" r="5" fill="{color}"/>'
            f'<text x="{x + 17}" y="{y}" font-family="Segoe UI, Ubuntu, sans-serif" font-size="13" fill="{TEXT}">'
            f'{escape(name)} {100 * size / whole:.1f}%</text>\n'
        )
    return card(350, 200, "Top Languages", inner)


if __name__ == "__main__":
    user = gql()
    os.makedirs(OUT, exist_ok=True)
    for name, svg in (("stats.svg", stats_svg(user)), ("top-langs.svg", langs_svg(user))):
        with open(os.path.join(OUT, name), "w", encoding="utf-8") as f:
            f.write(svg)
