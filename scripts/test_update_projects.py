import xml.etree.ElementTree as ET
from unittest.mock import patch

from update_projects import render
from render_profile import build, read_config


def demo():
    repo = {
        "name": "repo",
        "nameWithOwner": "Dexaroz/repo",
        "description": "Data <science> & AI",
        "stargazerCount": 3,
        "pushedAt": "2026-09-24T12:00:00Z",
        "primaryLanguage": {"name": "Python"},
        "repositoryTopics": {"nodes": [{"topic": {"name": "machine-learning"}}]},
    }
    svg = render([repo])
    ET.fromstring(svg)
    assert "Data &lt;science&gt; &amp; AI" in svg
    assert "★ 3" in svg and "1 pinned" in svg

    config, avatar = read_config()
    config["profile"]["name"] = "Another Person"
    config["profile"]["role"] = "Engineer & Researcher"
    config["links"]["website"] = "https://example.com/new"
    config["technologies"]["languages"][0]["name"] = "Kotlin"
    with patch.dict("os.environ", {"GITHUB_TOKEN": "test"}), patch("render_profile.fetch", return_value=[repo]):
        panels = build(config, avatar)
    assert "Another Person" in panels["header"] and "Engineer &amp; Researcher" in panels["header"]
    assert "example.com/new" in panels["link-website"]
    assert "Kotlin" in panels["terminal"] and "Another Person" in panels["terminal"]
    assert "Dexaroz pinned projects" in panels["projects"]
    for panel in panels.values():
        ET.fromstring(panel)


if __name__ == "__main__":
    demo()
