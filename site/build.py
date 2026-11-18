"""Build the static Pages artifact from replayed TRAJYN results."""

import argparse
import json
import os
import re
from collections import Counter
from dataclasses import dataclass
from html import escape
from pathlib import Path
from shutil import copyfile
from string import Template
from urllib.parse import urlsplit

from trajyn.capability import read_capsules
from trajyn.evaluation import Evaluation
from trajyn.provenance import read_trajectory
from trajyn.recording import encode_json
from trajyn.report import read_evaluation

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
REPO = "https://github.com/akaAdiArun/trajyn"
CANONICAL = "https://akaadiarun.github.io/trajyn/"
PILOT = ROOT / "examples/local-pilot/action-first"
STUDY_001 = ROOT / "examples/experiment-001/run"
STUDY_002 = ROOT / "examples/experiment-002/run"
DESCRIPTION = (
    "TRAJYN is a research project about helping one AI learn from another AI’s work. "
    "Follow a recorded delivery case and see what the experiments found."
)
LABELS = {
    "A": "No memory",
    "B": "Raw trajectory",
    "C": "Procedural summary",
    "D": "Static capsule",
    "E": "Irrelevant memory",
    "F": "Branch-aware capsule",
}


@dataclass(frozen=True)
class Stop:
    tool: str
    code: str
    label: str
    result: str
    consequence: str
    tag: str = ""


STOPS = (
    Stop(
        "read_case",
        "case_read",
        "Read the case",
        "Parcel reported missing",
        "The linked parcel ID let the AI look up the carrier’s record.",
    ),
    Stop(
        "inspect_parcel",
        "parcel_inspected",
        "Check the carrier",
        "Parcel confirmed lost",
        "The carrier confirmed the loss and supplied the product ID for a replacement.",
    ),
    Stop(
        "ship_replacement",
        "remedy_posted",
        "Send a replacement",
        "Replacement accepted. Receipt returned.",
        "The returned receipt gave the AI the value it needed to close this ticket.",
        "Receipt returned",
    ),
    Stop(
        "close_case",
        "case_closed",
        "Close the case",
        "The same receipt is used to close the ticket.",
        "The simulator returned case_closed. The independent verifier passed the run.",
        "Receipt used",
    ),
)


def _block(label: str, data: object, highlight: str | None = None) -> str:
    pretty = escape(json.dumps(json.loads(encode_json(data)), indent=2))
    if highlight is not None:
        value = escape(json.dumps(highlight)[1:-1])
        needle = f"&quot;{value}&quot;"
        pretty = pretty.replace(needle, f"&quot;<mark>{value}</mark>&quot;")
    return f'<p class="record-label">{label}</p><pre tabindex="0"><code>{pretty}</code></pre>'


def _recorded(blocks: str) -> str:
    return f'<details class="recorded"><summary>Show recorded data</summary>{blocks}</details>'


def _panel(anchor: int, label: str, body: str, kicker: str = "") -> str:
    heading = f'<p class="kicker">{kicker}</p>' if kicker else ""
    return (
        f'<article class="evidence" id="trace-{anchor}" data-evidence>'
        f"{heading}<h3>{label}</h3>{body}</article>"
    )


def render_replay(output: Path) -> tuple[str, str, str]:
    path = PILOT / "source/source-0.jsonl"
    trace = read_trajectory(path)
    capsules = read_capsules(PILOT / "capsules.jsonl")
    capsule = next(
        item
        for item in capsules
        if any(evidence.trajectory_id == trace.trajectory_id for evidence in item.evidence)
    )
    if (
        not trace.verification.passed
        or tuple((step.action.tool, step.observation.code) for step in trace.steps)
        != tuple((stop.tool, stop.code) for stop in STOPS)
        or trace.steps[0].observation.data["reported_status"] != "lost"
        or trace.steps[1].observation.data["status"] != "lost"
    ):
        raise ValueError("featured trajectory does not match the verified lost-delivery case")
    receipt = trace.steps[2].observation.data.get("receipt_id")
    if (
        not isinstance(receipt, str)
        or not receipt
        or trace.steps[3].action.arguments.get("receipt_id") != receipt
    ):
        raise ValueError("featured close-case request must use the recorded replacement receipt")

    evidence = output / "evidence"
    evidence.mkdir(exist_ok=True)
    copyfile(path, evidence / "source.jsonl")
    (evidence / "capsule.json").write_text(encode_json(capsule) + "\n", encoding="utf-8")
    slip_rows = []
    links = []
    panels = [
        _panel(
            1,
            "Task input",
            f"<p>{escape(trace.task.goal)}</p><p>Recorded model <code>"
            f"{escape(trace.agent.model)}</code></p>"
            + _recorded(
                _block(
                    "Public task",
                    {
                        "ticket_id": trace.task.ticket_id,
                        "source_model": trace.agent.model,
                        "split": trace.task.split,
                        "seed": trace.task.seed,
                    },
                )
            ),
            "Case 01",
        )
    ]
    for step, stop in zip(trace.steps, STOPS, strict=True):
        number = step.index
        anchor = number + 1  # Keep the public trace-1 through trace-7 destinations.
        tag = f'<span class="receipt-tag">{stop.tag}</span>' if stop.tag else ""
        slip_rows.append(
            f'<li><span class="stop">{number:02}</span><div>'
            f'<strong class="slip-action">{stop.label}</strong>'
            f'<span class="slip-fact">{stop.result}</span></div>{tag}</li>'
        )
        route_tag = f'<span class="route-tag">{stop.tag}</span>' if stop.tag else ""
        links.append(
            f'<li{" data-handoff" if stop.tag else ""}><a href="#trace-{anchor}" '
            f'aria-controls="trace-{anchor}"><span class="stop">{number:02}</span>'
            f'<span class="route-copy"><span class="route-label">{stop.label}</span>'
            f"{route_tag}</span></a></li>"
        )
        request = _block("Tool request", step.action, receipt if number == 4 else None)
        response = _block(
            "Environment observation", step.observation, receipt if number == 3 else None
        )
        records = response + request if number == 3 else request + response
        panels.append(
            _panel(
                anchor,
                stop.label,
                f"<dl><div><dt>System returned</dt><dd>{stop.result}</dd></div>"
                f"<div><dt>What this allowed</dt><dd>{stop.consequence}</dd></div></dl>"
                + _recorded(records),
                f"Stop {number:02}" + (f" / {stop.tag}" if stop.tag else ""),
            )
        )
    panels.extend(
        (
            _panel(
                6,
                "Final verification",
                "<p>The independent verifier checked the resulting state. The case was closed.</p>"
                + _recorded(_block("Verifier outcome", trace.verification)),
                "Case 01",
            ),
            _panel(
                7,
                "Saved procedure",
                "<p>The procedure records where each input comes from and links back to the "
                "verified run. The close-case step uses the receipt returned by the previous "
                "step.</p>"
                + _recorded(
                    _block("Evidence references", capsule.evidence)
                    + _block("Guarded procedure", capsule.steps)
                ),
                "Case 01",
            ),
        )
    )
    return "".join(slip_rows), "".join(links), "".join(panels)


def render_comparison() -> tuple[str, str]:
    directory = STUDY_002 / "grounded/evaluation/trajectories"
    outcomes = []
    expected = (
        ("D", "Fixed advice", False, "Attempted an ineligible replacement. The case stayed open."),
        ("F", "Withheld advice", True, "Acknowledged delivery and closed the case."),
        ("A", "No advice", True, "Acknowledged delivery and closed the case."),
    )
    for arm, label, passed, description in expected:
        trace = read_trajectory(directory / f"530-{arm}.jsonl")
        actions = {(step.action.tool, step.observation.code) for step in trace.steps}
        delivered = any(
            step.action.tool == "query_carrier_backup"
            and step.observation.data.get("status") == "delivered"
            for step in trace.steps
        )
        expected_action = (
            ("acknowledge_delivery", "remedy_posted")
            if passed
            else ("ship_replacement", "remedy_ineligible")
        )
        if (
            trace.task.seed != 530
            or ("inspect_parcel", "carrier_unavailable") not in actions
            or not delivered
            or expected_action not in actions
            or trace.verification.passed != passed
            or (("close_case", "case_closed") in actions) != passed
        ):
            raise ValueError(f"seed 530 arm {arm} no longer supports the published comparison")
        style = ' class="caution"' if not passed else ""
        outcomes.append(f"<li{style}><strong>{label}.</strong> {description}</li>")
    return "Delivered", "".join(outcomes)


def render_experiment(path: Path, evaluation: Evaluation, heading: str, number: str) -> str:
    pilot = json.loads((path / "pilot.json").read_text(encoding="utf-8"))
    results = Counter(row.condition.value for row in evaluation.trials if row.passed)
    totals = Counter(row.condition.value for row in evaluation.trials)
    chart = "".join(
        f'<div class="metric {"capsule" if arm in ("D", "F") else ""}">'
        f'<div class="metric-label">{LABELS[arm]}</div>'
        '<div class="metric-track" aria-hidden="true">'
        '<div class="metric-fill" '
        f'style="--percentage:{100 * results[arm] / totals[arm]:.2f}%"></div>'
        f'</div><div class="metric-value">{results[arm]}/{totals[arm]}</div></div>'
        for arm in sorted(totals)
    )
    details = (
        f"{escape(pilot['source_model']['name'])} verified {pilot['verified_sources']}/"
        f"{pilot['source_count']} source tasks. {pilot['capsule_count']} capsules qualified. "
        f"Target {escape(evaluation.trials[0].agent.model)}. "
        f"{len(evaluation.plan.seeds)} held-out tasks per condition."
    )
    if heading.startswith("Experiment 001"):
        details += (
            " The static capsule arm regressed on three paired tasks and improved on none. "
            "All ten capsules passed interface checks."
        )
    else:
        analysis = json.loads((path / "evaluation/analysis.json").read_text(encoding="utf-8"))
        branch = analysis["branch_transfer"]
        continued = branch["continued_after_divergence"]
        details += (
            f" Branch-aware transfer had {branch['improved']} paired gains "
            f"and {branch['regressed']} paired regressions versus static transfer. "
            f"After divergence, static transfer delivered {continued['D']} capsule prompts "
            f"and branch-aware transfer delivered {continued['F']}."
        )
    raw = path.relative_to(ROOT).as_posix() + "/evaluation/results.json"
    return (
        f'<article class="experiment"><h3>{escape(heading)}</h3><p>{details}</p>'
        f'<div class="chart">{chart}</div><p class="links">'
        f'<a href="{REPO}/blob/main/docs/EXPERIMENT_{number}.md">Protocol ↗</a>'
        f'<a href="{REPO}/blob/main/docs/EXPERIMENT_{number}_RESULTS.md">Full results ↗</a>'
        f'<a href="{REPO}/blob/main/{raw}">Recorded JSON ↗</a></p></article>'
    )


def render_results() -> tuple[str, int, str]:
    first = read_evaluation(STUDY_001 / "evaluation/results.json")
    marks = []
    for arm, label in (("A", "Without advice"), ("D", "With the saved procedure")):
        rows = [row for row in first.trials if row.condition.value == arm]
        count = sum(row.passed for row in rows)
        cells = '<span class="complete"></span>' * count + "<span></span>" * (len(rows) - count)
        marks.append(
            f'<div class="mark-row" data-condition="{arm}"><span>{label}</span>'
            f"<strong>{count} of {len(rows)}</strong>"
            f'<div class="marks" aria-hidden="true">{cells}</div></div>'
        )
    charts = [render_experiment(STUDY_001, first, "Experiment 001 · Static transfer", "001")]
    abstained = 0
    for mode, label in (
        ("grounded", "Granite, public grounding"),
        ("unaided", "Granite, unaided"),
        ("secondary-grounded", "Ministral, public grounding"),
        ("secondary-unaided", "Ministral, unaided"),
    ):
        path = STUDY_002 / mode
        evaluation = read_evaluation(path / "evaluation/results.json")
        analysis = json.loads((path / "evaluation/analysis.json").read_text(encoding="utf-8"))[
            "branch_transfer"
        ]
        baseline = {row.seed: row.passed for row in evaluation.trials if row.condition.value == "A"}
        gated = [row for row in evaluation.trials if row.condition.value == "F"]
        if (
            analysis["abstained"] != len(gated)
            or any(row.memory_delivered for row in gated)
            or {row.seed: row.passed for row in gated} != baseline
        ):
            raise ValueError("Experiment 002 no longer matches the published abstention summary")
        abstained += len(gated)
        charts.append(render_experiment(path, evaluation, f"Experiment 002 · {label}", "002"))
    return "".join(marks), abstained, "".join(charts)


def render_metadata(url: str, verification: str) -> str:
    summary = escape(DESCRIPTION)
    image = url + "assets/social-preview.png"
    data = {
        "@context": "https://schema.org",
        "@type": "SoftwareSourceCode",
        "name": "TRAJYN",
        "description": DESCRIPTION,
        "url": url,
        "codeRepository": REPO,
        "programmingLanguage": "Python",
        "license": "https://www.apache.org/licenses/LICENSE-2.0",
    }
    metadata = [
        f'<meta name="description" content="{summary}">',
        f'<link rel="canonical" href="{url}">',
        '<meta property="og:type" content="website">',
        '<meta property="og:site_name" content="TRAJYN">',
        '<meta property="og:title" content="TRAJYN · Follow the receipt">',
        f'<meta property="og:description" content="{summary}">',
        f'<meta property="og:url" content="{url}">',
        f'<meta property="og:image" content="{image}">',
        '<meta property="og:image:width" content="1200">',
        '<meta property="og:image:height" content="630">',
        '<meta property="og:image:alt" content="Four recorded delivery steps with a bracket '
        'connecting the receipt returned at stop 03 to the receipt used at stop 04.">',
        '<meta name="twitter:card" content="summary_large_image">',
        f'<script type="application/ld+json">{json.dumps(data)}</script>',
    ]
    if verification:
        if re.fullmatch(r"[A-Za-z0-9_-]{10,128}", verification) is None:
            raise ValueError("supply only the content value from the Google verification tag")
        metadata.append(f'<meta name="google-site-verification" content="{verification}">')
    return "\n  ".join(metadata)


def build(output: Path, base_url: str = CANONICAL, verification: str = "") -> None:
    url = base_url.rstrip("/") + "/"
    parsed = urlsplit(url)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.query
        or parsed.fragment
        or parsed.username is not None
        or re.fullmatch(r"https://[a-zA-Z0-9./-]+", url) is None
    ):
        raise ValueError("the canonical URL must be an HTTPS public URL")
    output.mkdir(parents=True, exist_ok=True)
    assets = output / "assets"
    assets.mkdir(exist_ok=True)
    for name in ("social-preview.png", "site.css", "site.js"):
        copyfile(SITE / "assets" / name, assets / name)
    slip, links, panels = render_replay(output)
    backup_status, backup_outcomes = render_comparison()
    completion_marks, abstained, experiments = render_results()
    template = Template((SITE / "index.html").read_text(encoding="utf-8"))
    (output / "index.html").write_text(
        template.substitute(
            metadata=render_metadata(url, verification),
            slip_rows=slip,
            replay_links=links,
            replay_steps=panels,
            backup_status=backup_status,
            backup_outcomes=backup_outcomes,
            completion_marks=completion_marks,
            abstained=abstained,
            experiments=experiments,
        ),
        encoding="utf-8",
        newline="\n",
    )
    (output / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        f"<url><loc>{url}</loc></url></urlset>\n",
        encoding="utf-8",
        newline="\n",
    )
    (output / ".nojekyll").touch()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "dist/site")
    parser.add_argument("--url", default=CANONICAL)
    args = parser.parse_args()
    build(args.output, args.url, os.environ.get("GOOGLE_SITE_VERIFICATION", ""))
