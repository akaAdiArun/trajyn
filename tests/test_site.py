import os
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path
from xml.etree import ElementTree

from trajyn.capability import read_capsule
from trajyn.provenance import read_trajectory

ROOT = Path(__file__).resolve().parents[1]


class Page(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: set[str] = set()
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if identifier := values.get("id"):
            assert identifier not in self.ids
            self.ids.add(identifier)
        self.links.extend(value for key, value in attrs if value and key in {"src", "href"})


def test_site_build_is_crawlable_and_replayable(tmp_path: Path) -> None:
    verification = "example-verification-token"
    result = subprocess.run(
        [sys.executable, str(ROOT / "site/build.py"), "--output", str(tmp_path)],
        env={**os.environ, "GOOGLE_SITE_VERIFICATION": verification},
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    html = (tmp_path / "index.html").read_text(encoding="utf-8")
    assert '<meta name="google-site-verification" content="example-verification-token">' in html
    assert '<link rel="canonical" href="https://akaadiarun.github.io/trajyn/">' in html
    assert "noindex" not in html
    assert "Experiment 001" in html
    assert "verified 8/8 source tasks" in html
    assert "SoftwareSourceCode" in html
    assert "Tool arguments" in html and "Guarded procedure" in html
    assert html.count("<h1 ") == 1
    page = Page()
    page.feed(html)
    for link in page.links:
        if link.startswith("#"):
            assert link[1:] in page.ids
        elif not link.startswith("https://"):
            assert (tmp_path / link).exists()
    assert not (tmp_path / "robots.txt").exists()
    sitemap = ElementTree.parse(tmp_path / "sitemap.xml")
    loc = sitemap.find("{*}url/{*}loc")
    assert loc is not None and loc.text == "https://akaadiarun.github.io/trajyn/"
    trace = read_trajectory(tmp_path / "evidence/source.jsonl")
    capsule = read_capsule(tmp_path / "evidence/capsule.json")
    assert trace.verification.passed
    assert capsule.evidence[0].trajectory_id == trace.trajectory_id
