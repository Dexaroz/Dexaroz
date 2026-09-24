"""Render Dexaroz's pinned public repositories as a self-hosted SVG."""

import html
import json
import os
import textwrap
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


QUERY = """query {
  user(login: "Dexaroz") {
    pinnedItems(first: 4, types: REPOSITORY) {
      nodes {
        ... on Repository {
          name
          nameWithOwner
          description
          stargazerCount
          pushedAt
          primaryLanguage { name }
          repositoryTopics(first: 2) { nodes { topic { name } } }
        }
      }
    }
  }
}"""


def safe(value):
    return html.escape("".join(c for c in str(value or "") if c.isprintable()))


def clip(value, length):
    return value[: length - 1] + "…" if len(value) > length else value


def project_card(repo, x, y):
    name = safe(clip(repo["name"], 31))
    owner = safe(clip(repo["nameWithOwner"], 45))
    description = " ".join((repo.get("description") or "No description provided.").split())
    lines = textwrap.wrap(description, width=48, max_lines=2, placeholder="…")
    description_svg = "".join(
        f'<text x="{x + 16}" y="{y + 86 + i * 19}" class="body">{safe(line)}</text>'
        for i, line in enumerate(lines)
    )
    language = (repo.get("primaryLanguage") or {}).get("name") or "Code"
    topics = [node["topic"]["name"] for node in (repo.get("repositoryTopics") or {}).get("nodes", [])]
    tags = clip(" · ".join([language, *topics]), 45)
    pushed = (repo.get("pushedAt") or "")[:10]
    stars = int(repo["stargazerCount"])
    return f"""
    <g>
      <rect x="{x}" y="{y}" width="422" height="174" rx="13" class="card"/>
      <circle cx="{x + 16}" cy="{y + 17}" r="3" fill="#89a99a"/>
      <text x="{x + 29}" y="{y + 21}" class="meta">{owner}</text>
      <line x1="{x}" y1="{y + 33}" x2="{x + 422}" y2="{y + 33}" stroke="#3d5261"/>
      <text x="{x + 16}" y="{y + 61}" class="name">{name}</text>
      {description_svg}
      <rect x="{x + 16}" y="{y + 120}" width="{max(58, len(tags) * 7.2 + 20):.0f}" height="22" rx="11" fill="#263a49"/>
      <text x="{x + 27}" y="{y + 135}" class="meta">{safe(tags)}</text>
      <text x="{x + 16}" y="{y + 160}" class="meta">★ {stars}   ·   pushed {safe(pushed)}</text>
    </g>"""


def render(repos):
    if not repos:
        raise ValueError("No pinned repositories returned; keeping the previous image")
    rows = (len(repos) + 1) // 2
    height = 70 + rows * 188 + 16
    checked = datetime.now(timezone.utc).strftime("%Y-%m")
    cards = "".join(project_card(repo, 18 + (i % 2) * 442, 70 + (i // 2) * 188) for i, repo in enumerate(repos))
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="900" height="{height}" viewBox="0 0 900 {height}" role="img" aria-labelledby="title description">
  <title id="title">Dexaroz pinned projects</title>
  <desc id="description">Public repositories pinned on Dexaroz's GitHub profile, updated by GitHub Actions.</desc>
  <style>
    .card {{ fill: #1a2630; stroke: #4a6070; }}
    .meta {{ fill: #a9c4d2; font: 12px Consolas, monospace; }}
    .name {{ fill: #f2f5f6; font: bold 18px Consolas, monospace; }}
    .body {{ fill: #c4d0d8; font: 13px Consolas, monospace; }}
  </style>
  <rect width="900" height="{height}" rx="18" fill="#141b23"/>
  <rect x=".5" y=".5" width="899" height="{height - 1}" rx="18" fill="none" stroke="#586b79"/>
  <text x="20" y="31" class="meta">PROJECTS.LIST</text>
  <text x="165" y="31" class="meta">~/projects.sh --pinned</text>
  <text x="878" y="31" text-anchor="end" class="meta">{len(repos)} pinned · checked {checked}</text>
  <line x1="18" y1="46" x2="882" y2="46" stroke="#4a6070"/>
{cards}
</svg>
"""


def main():
    token = os.environ["GITHUB_TOKEN"]
    request = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY}).encode(),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json", "User-Agent": "dexaroz-profile"},
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        result = json.load(response)
    if result.get("errors"):
        raise RuntimeError(result["errors"])
    repos = result["data"]["user"]["pinnedItems"]["nodes"]
    output = Path(__file__).resolve().parents[1] / "assets" / "projects.svg"
    output.write_text(render(repos), encoding="utf-8")


if __name__ == "__main__":
    main()
