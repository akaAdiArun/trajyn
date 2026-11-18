import os
import re
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path
from struct import unpack
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
    assert html.count("Experiment 002 ·") == 4
    assert "Ministral, unaided" in html
    assert "Branch-aware transfer had" in html
    assert "The original gate withheld advice in all 24 attempts" in html
    assert '<a href="#experiments">Progress</a>' in html
    assert 'id="experiments-heading">Research Progress</h2>' in html
    assert html.index('id="experiment-003b"') < html.index('id="experiment-002-heading"')
    assert "Waiting did not improve completion over no memory." in html
    assert all(
        f"/docs/{name}" in html
        for name in (
            "EXPERIMENT_003B_RESULTS.md",
            "EXPERIMENT_003B_FROZEN.json",
            "EXPERIMENT_003.md",
        )
    )
    assert "The case stayed open." in html
    assert html.count("Acknowledged delivery and closed the case.") == 2
    assert "SoftwareSourceCode" in html
    assert 'type="module" src="assets/site.js"' in html
    assert 'id="story-progress"' in html and "data-story-track" in html
    assert (tmp_path / "assets/replay-motion.mjs").is_file()
    assert "Tool request" in html and "Guarded procedure" in html
    assert html.count("<h1 ") == 1
    assert 'content="1200"' in html and 'content="630"' in html
    chapter_positions = [
        html.index(f'id="{name}"')
        for name in ("replay", "second-case", "experiments", "architecture", "roadmap")
    ]
    assert chapter_positions == sorted(chapter_positions)
    mark_rows = re.findall(r'<div class="marks" aria-hidden="true">(.+?)</div>', html)
    assert len(mark_rows) == 2
    assert all(row.count("<span") == 10 for row in mark_rows)
    assert [row.count('class="complete"') for row in mark_rows] == [3, 0]
    assert "<strong>3 of 10</strong>" in html and "<strong>0 of 10</strong>" in html
    page = Page()
    page.feed(html)
    assert {f"trace-{index}" for index in range(1, 8)} <= page.ids
    assert {f"#trace-{index}" for index in range(1, 8)} <= set(page.links)
    assert "evidence/source.jsonl" in page.links and "evidence/capsule.json" in page.links
    for link in page.links:
        if link.startswith("#"):
            assert link[1:] in page.ids
        elif not link.startswith("https://"):
            assert (tmp_path / link).exists()
    assert not (tmp_path / "robots.txt").exists()
    sitemap = ElementTree.parse(tmp_path / "sitemap.xml")
    loc = sitemap.find("{*}url/{*}loc")
    assert loc is not None and loc.text == "https://akaadiarun.github.io/trajyn/"
    output_trace = tmp_path / "evidence/source.jsonl"
    source_trace = ROOT / "examples/local-pilot/action-first/source/source-0.jsonl"
    assert output_trace.read_bytes() == source_trace.read_bytes()
    trace = read_trajectory(output_trace)
    capsule = read_capsule(tmp_path / "evidence/capsule.json")
    assert trace.verification.passed
    assert capsule.evidence[0].trajectory_id == trace.trajectory_id
    assert len(trace.steps) == 4
    replacement, closure = trace.steps[2:]
    receipt = replacement.observation.data["receipt_id"]
    assert isinstance(receipt, str) and receipt == closure.action.arguments["receipt_id"]
    assert closure.observation.code == "case_closed"
    assert receipt not in html.split('id="replay"', 1)[0]
    panels = dict(re.findall(r'id="(trace-\d+)" data-evidence>(.*?)</article>', html, re.S))
    assert len(panels) == 7
    for anchor in ("trace-4", "trace-5"):
        assert "<summary>Show recorded data</summary>" in panels[anchor]
        assert f"<mark>{receipt}</mark>" in panels[anchor]
    assert "ship_replacement" in panels["trace-4"] and "close_case" in panels["trace-5"]
    assert (
        panels["trace-4"].index("Environment observation")
        < panels["trace-4"].index("<mark>")
        < panels["trace-4"].index("Tool request")
    )
    assert (
        panels["trace-5"].index("Tool request")
        < panels["trace-5"].index("<mark>")
        < panels["trace-5"].index("Environment observation")
    )
    social_preview = (tmp_path / "assets/social-preview.png").read_bytes()
    assert social_preview.startswith(b"\x89PNG\r\n\x1a\n")
    assert unpack(">II", social_preview[16:24]) == (1200, 630)
