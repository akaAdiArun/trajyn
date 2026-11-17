"""Build the static Pages artifact from replayed TRAJYN results."""

import argparse
import json
import os
import re
from collections import Counter
from html import escape
from pathlib import Path
from shutil import copyfile
from string import Template
from urllib.parse import urlsplit

from trajyn.capability import read_capsules
from trajyn.provenance import read_trajectory
from trajyn.recording import encode_json
from trajyn.report import read_evaluation

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
REPO = "https://github.com/akaAdiArun/trajyn"
CANONICAL = "https://akaadiarun.github.io/trajyn/"
PILOT = ROOT / "examples/local-pilot/action-first"
STAGES = (
    ("Agent A", "Receives a public task, an action budget, and the available tool contracts."),
    ("Tool execution", "The environment validates each action and returns an observable result."),
    ("Trajectory recorder", "The recorder stores public actions, observations, and provenance."),
    ("Independent verifier", "The verifier checks the resulting environment state for completion."),
    (
        "Capability induction",
        "Replay verifies the evidence. The inducer binds steps to task fields and "
        "earlier observations.",
    ),
    (
        "Portable capsule",
        "The capsule carries tool requirements, argument origins, observation guards, "
        "and evidence references.",
    ),
    (
        "Retrieval and applicability",
        "Candidates are ranked using public task and tool information. Compatibility "
        "determines whether guidance is admissible.",
    ),
    (
        "Agent B",
        "A separate target model executes the held-out task with the assigned memory condition.",
    ),
    (
        "Comparative evaluation",
        "Every condition is evaluated against the same held-out tasks. State verification "
        "scores each attempt.",
    ),
)
LABELS = {
    "A": "No memory",
    "B": "Raw trajectory",
    "C": "Procedural summary",
    "D": "Static capsule",
    "E": "Irrelevant memory",
    "F": "Branch-aware capsule",
}


def _pretty(data: object) -> str:
    return escape(json.dumps(json.loads(encode_json(data)), indent=2))


def _block(label: str, data: object) -> str:
    return f'<p class="block-label">{label}</p><pre tabindex="0"><code>{_pretty(data)}</code></pre>'


def render_replay(output: Path) -> tuple[str, str]:
    path = PILOT / "source/source-0.jsonl"
    trace = read_trajectory(path)
    capsules = read_capsules(PILOT / "capsules.jsonl")
    capsule = next(
        item
        for item in capsules
        if any(evidence.trajectory_id == trace.trajectory_id for evidence in item.evidence)
    )
    if not trace.verification.passed:
        raise ValueError("featured trajectory must pass state verification")
    evidence = output / "evidence"
    evidence.mkdir(exist_ok=True)
    copyfile(path, evidence / "source.jsonl")
    (evidence / "capsule.json").write_text(encode_json(capsule) + "\n", encoding="utf-8")
    parts = [
        (
            "Task input",
            f"<p>{escape(trace.task.goal)}</p>"
            + _block(
                "Public task",
                {
                    "ticket_id": trace.task.ticket_id,
                    "source_model": trace.agent.model,
                    "split": trace.task.split,
                    "seed": trace.task.seed,
                },
            ),
        )
    ]
    parts.extend(
        (
            step.action.tool,
            _block("Tool arguments", step.action.arguments)
            + _block("Environment observation", step.observation),
        )
        for step in trace.steps
    )
    parts.append(("State verification", _block("Verifier outcome", trace.verification)))
    parts.append(
        (
            "Induced capsule",
            "<p>Induction replaced run-specific identifiers with bindings to the task "
            "or an earlier "
            "observation. The evidence references the verified source trajectory.</p>"
            + _block("Evidence references", capsule.evidence)
            + _block("Guarded procedure", capsule.steps),
        )
    )
    links = "".join(
        f'<a href="#trace-{index}">{index:02} · {escape(title)}</a>'
        for index, (title, _) in enumerate(parts, 1)
    )
    panels = "".join(
        f'<article id="trace-{index}" data-step><h3>{escape(title)}</h3>{body}</article>'
        for index, (title, body) in enumerate(parts, 1)
    )
    return links, panels


def render_experiment(path: Path, heading: str, doc: str, protocol: str) -> str:
    evaluation = read_evaluation(path / "evaluation/results.json")
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
        f'<a href="{REPO}/blob/main/docs/{protocol}">Protocol ↗</a>'
        f'<a href="{REPO}/blob/main/docs/{doc}">Full results ↗</a>'
        f'<a href="{REPO}/blob/main/{raw}">Recorded JSON ↗</a></p></article>'
    )


def render_metadata(url: str, verification: str) -> str:
    summary = (
        "Open-source infrastructure for verified execution traces and portable agent capabilities."
    )
    image = url + "assets/social-preview.png"
    data = {
        "@context": "https://schema.org",
        "@type": "SoftwareSourceCode",
        "name": "TRAJYN",
        "description": summary,
        "url": url,
        "codeRepository": REPO,
        "programmingLanguage": "Python",
        "license": "https://www.apache.org/licenses/LICENSE-2.0",
    }
    metadata = [
        f'<link rel="canonical" href="{url}">',
        '<meta property="og:type" content="website">',
        '<meta property="og:site_name" content="TRAJYN">',
        '<meta property="og:title" content="TRAJYN — The Experience Layer for AI Agents">',
        f'<meta property="og:description" content="{summary}">',
        f'<meta property="og:url" content="{url}">',
        f'<meta property="og:image" content="{image}">',
        '<meta property="og:image:width" content="1280">',
        '<meta property="og:image:height" content="640">',
        '<meta property="og:image:alt" content="TRAJYN — The Experience Layer for AI Agents">',
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
    for name in ("hero.svg", "mark.svg", "social-preview.png", "site.css", "site.js"):
        copyfile(SITE / "assets" / name, assets / name)
    copyfile(ROOT / "docs/assets/architecture.png", assets / "architecture.png")
    links, panels = render_replay(output)
    stages = "".join(
        f'<li><details name="pipeline"{" open" if index == 0 else ""}>'
        f"<summary>{escape(label)}</summary><p>{escape(body)}</p></details></li>"
        for index, (label, body) in enumerate(STAGES)
    )
    experiments = render_experiment(
        ROOT / "examples/experiment-001/run",
        "Experiment 001 · Static transfer",
        "EXPERIMENT_001_RESULTS.md",
        "EXPERIMENT_001.md",
    )
    trial_archive = ROOT / "examples/experiment-002/run"
    for mode, heading in (
        ("grounded", "Granite, public grounding"),
        ("unaided", "Granite, unaided"),
        ("secondary-grounded", "Ministral, public grounding"),
        ("secondary-unaided", "Ministral, unaided"),
    ):
        run = trial_archive / mode
        if (run / "evaluation/results.json").is_file():
            experiments += render_experiment(
                run,
                f"Experiment 002 · {heading}",
                "EXPERIMENT_002_RESULTS.md",
                "EXPERIMENT_002.md",
            )
    template = Template((SITE / "index.html").read_text(encoding="utf-8"))
    (output / "index.html").write_text(
        template.substitute(
            metadata=render_metadata(url, verification),
            stages=stages,
            replay_links=links,
            replay_steps=panels,
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
