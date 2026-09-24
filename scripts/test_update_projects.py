import xml.etree.ElementTree as ET

from update_projects import render


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


if __name__ == "__main__":
    demo()
