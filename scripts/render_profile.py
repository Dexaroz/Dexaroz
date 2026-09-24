"""Build the GitHub profile from profile.yml. Run with: python scripts/render_profile.py"""

import base64
import hashlib
import html
import os
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

import yaml

from update_projects import fetch, render as render_projects


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
TEMPLATES = ROOT / "templates"
KINDS = ("header", "link-website", "link-linkedin", "terminal", "skills", "projects")
FADE_DELAY = {"header": 0, "link-website": .15, "link-linkedin": .25, "terminal": .4, "skills": .65, "projects": .9}


def escaped(value):
    return html.escape(str(value), quote=True)


def template(name, **values):
    result = (TEMPLATES / f"{name}.svg").read_text(encoding="utf-8")
    for key, value in values.items():
        result = result.replace("{{" + key + "}}", escaped(value) if key not in {"AVATAR", "ASCII", "SKILLS_CONTENT"} else value)
    if "{{" in result:
        raise ValueError(f"Unfilled placeholder in {name}.svg")
    ET.fromstring(result)
    return result


def fade(svg, delay):
    """Animate an image on load; leave it visible when animation is unsupported."""
    anchor = next((tag for tag in ("</defs>", "</style>", "</desc>", "</title>") if tag in svg), None)
    if not anchor:
        raise ValueError("SVG has no metadata boundary")
    start = svg.index(anchor) + len(anchor)
    end = svg.rindex("</svg>")
    style = f'''\n  <style>
    @keyframes panel-fade {{ from {{ opacity: 0; }} to {{ opacity: 1; }} }}
    .panel-fade {{ animation: panel-fade .65s ease-out {delay:g}s both; }}
    @media (prefers-reduced-motion: reduce) {{ .panel-fade {{ animation: none; }} }}
  </style>
  <g class="panel-fade">'''
    result = svg[:start] + style + svg[start:end] + "\n  </g>\n" + svg[end:]
    ET.fromstring(result)
    return result


def valid_url(value):
    parsed = urllib.parse.urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
        raise ValueError(f"Expected a public HTTPS URL: {value}")
    return parsed.netloc.removeprefix("www.") + parsed.path.rstrip("/")


def ascii_svg(value):
    lines = value.splitlines()
    if len(lines) > 7 or any(len(line) > 43 for line in lines):
        raise ValueError("visual_map must fit within 7 lines of 43 characters")
    spans = "\n".join(f'    <tspan x="36" dy="{0 if i == 0 else 24}">{escaped(line)}</tspan>' for i, line in enumerate(lines))
    return f'<text x="36" y="116" xml:space="preserve" font-family="Consolas, monospace" font-size="15" fill="#ffeadb">\n{spans}\n  </text>'


def skill_icons(groups):
    entries = [tech for group in groups.values() for tech in group]
    ids = ",".join(tech["icon"] for tech in entries)
    cache = ASSETS / "skill-icons.svg"
    if cache.exists() and cache.read_text(encoding="utf-8").startswith(f"<!-- icons: {ids} -->\n"):
        svg = cache.read_text(encoding="utf-8").split("\n", 1)[1]
    else:
        url = "https://skillicons.dev/icons?" + urllib.parse.urlencode({"i": ids, "theme": "dark", "perline": len(entries)})
        with urllib.request.urlopen(url, timeout=30) as response:
            svg = response.read().decode("utf-8").strip()
        ET.fromstring(svg)
        cache.write_text(f"<!-- icons: {ids} -->\n{svg}\n", encoding="utf-8")
    svg = re.sub(r"(?m)^[ \t]+$", "", svg)
    icon = ET.fromstring(svg)
    icon.attrib.update(x="70", y="88", width="760", height="66")
    icon_svg = ET.tostring(icon, encoding="unicode")
    labels = {"languages": "LANGUAGES", "frontend": "FRONTEND", "backend": "BACKEND & APIs"}
    offset = 0
    total = len(entries)
    parts = [icon_svg]
    for key, group in groups.items():
        center = 70 + 760 * (offset + len(group) / 2) / total
        parts.append(f'<text x="{center:.1f}" y="182" text-anchor="middle" font-family="Segoe UI, Arial, sans-serif" font-size="11" font-weight="700" letter-spacing="1.5" fill="#d8c7bd">{escaped(labels[key])}</text>')
        offset += len(group)
        if offset < total:
            x = 70 + 760 * offset / total
            parts.append(f'<path d="M{x:.1f} 91v91" stroke="#765b4c" stroke-opacity=".55"/>')
    return "\n  ".join(parts)


def read_config():
    config = yaml.safe_load((ROOT / "profile.yml").read_text(encoding="utf-8"))
    profile, links, groups, projects = (config[key] for key in ("profile", "links", "technologies", "projects"))
    if not re.fullmatch(r"[A-Za-z0-9-]{1,39}", profile["handle"]):
        raise ValueError("Invalid GitHub handle")
    if list(groups) != ["languages", "frontend", "backend"] or not all(groups.values()):
        raise ValueError("technologies must have languages, frontend and backend lists")
    entries = [tech for group in groups.values() for tech in group]
    if len(entries) > 15 or any(not re.fullmatch(r"[a-z0-9]{1,20}", tech["icon"]) for tech in entries):
        raise ValueError("Use up to 15 valid Skill Icons IDs")
    if any(len(" · ".join(tech["name"] for tech in group)) > 34 for group in groups.values()):
        raise ValueError("A technology group is too long for the terminal panel")
    if projects["source"] != "pinned" or not 1 <= projects["count"] <= 6:
        raise ValueError("projects must use 1 to 6 pinned repositories")
    for url in links.values():
        valid_url(url)
    avatar = (ROOT / profile["avatar"]).resolve()
    if not avatar.is_relative_to(ASSETS.resolve()) or not avatar.is_file() or avatar.suffix.lower() not in {".jpg", ".jpeg", ".png"}:
        raise ValueError("avatar must be an existing JPG or PNG within assets/")
    return config, avatar


def build(config, avatar):
    profile, links, groups, projects = (config[key] for key in ("profile", "links", "technologies", "projects"))
    name, handle = profile["name"], profile["handle"]
    mime = "image/png" if avatar.suffix.lower() == ".png" else "image/jpeg"
    avatar_data = f"data:{mime};base64,{base64.b64encode(avatar.read_bytes()).decode()}"
    panels = {
        "header": template("header", NAME=name, HANDLE=handle, HANDLE_UPPER=handle.upper(), ROLE=profile["role"], AVATAR=avatar_data),
        "link-website": template("link-website", WEBSITE_DISPLAY=valid_url(links["website"])),
        "link-linkedin": template("link-linkedin", LINKEDIN_DISPLAY=valid_url(links["linkedin"])),
        "terminal": template("terminal", NAME=name, HANDLE=handle, HANDLE_LOWER=handle.lower(), ASCII=ascii_svg(config["visual_map"]), TAGLINE="> " + profile["tagline"], TERMINAL_ROLE=profile["role"].split("|")[0].strip(), LANGUAGES=" · ".join(t["name"] for t in groups["languages"]), FRONTEND=" · ".join(t["name"] for t in groups["frontend"]), BACKEND=" · ".join(t["name"] for t in groups["backend"])),
        "skills": template("skills", NAME=name, SKILLS_DESCRIPTION="Skill Icons for " + ", ".join(t["name"] for group in groups.values() for t in group) + ".", SKILLS_CONTENT=skill_icons(groups)),
    }
    panels["projects"] = render_projects(fetch(handle, projects["count"], os.environ["GITHUB_TOKEN"]), handle)
    return {kind: fade(svg, FADE_DELAY[kind]) for kind, svg in panels.items()}


def main():
    config, avatar = read_config()
    panels = build(config, avatar)
    paths = {}
    for kind, svg in panels.items():
        digest = hashlib.sha256(svg.encode()).hexdigest()[:12]
        path = ASSETS / f"{kind}-{digest}.svg"
        path.write_text(svg, encoding="utf-8")
        paths[kind] = path.relative_to(ROOT).as_posix()
    links = config["links"]
    handle = config["profile"]["handle"]
    readme = f'''![{config["profile"]["name"]} — {handle}]({paths["header"]})

<p align="center">
  <a href="{html.escape(links["website"], quote=True)}"><img src="{paths["link-website"]}" alt="Website: {valid_url(links["website"])}" width="49.4%"></a>&nbsp;&nbsp;<a href="{html.escape(links["linkedin"], quote=True)}"><img src="{paths["link-linkedin"]}" alt="LinkedIn: {valid_url(links["linkedin"])}" width="49.4%"></a>
</p>

![Terminal profile with ASCII art and system information]({paths["terminal"]})

![Technology icons grouped by languages, frontend, and backend APIs]({paths["skills"]})

[![Pinned projects, generated from the public GitHub profile]({paths["projects"]})](https://github.com/{handle})
'''
    (ROOT / "README.md").write_text(readme, encoding="utf-8")
    for kind in KINDS:
        for old in ASSETS.glob(f"{kind}-????????????.svg"):
            if old.relative_to(ROOT).as_posix() != paths[kind]:
                old.unlink()


if __name__ == "__main__":
    main()
