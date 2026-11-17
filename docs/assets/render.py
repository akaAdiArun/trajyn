"""Render the repository graphics from code and the published experiment artifacts."""

import argparse
import json
from collections import Counter
from functools import cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs/assets"
PILOT = ROOT / "examples/local-pilot/action-first"
INK = "#070c1b"
PANEL = "#111d36"
RULE = "#293b61"
WHITE = "#f2f6ff"
MUTED = "#afc1e5"
CYAN = "#57eaff"
BLUE = "#83aaff"
VIOLET = "#c5a1ff"


@cache
def font(size: int, style: str = "regular") -> ImageFont.FreeTypeFont:
    candidates = {
        "regular": ("segoeui.ttf", "DejaVuSans.ttf"),
        "bold": ("segoeuib.ttf", "DejaVuSans-Bold.ttf"),
        "mono": ("consola.ttf", "DejaVuSansMono.ttf"),
    }
    for name in candidates[style]:
        for candidate in (str(Path("C:/Windows/Fonts") / name), name):
            try:
                return ImageFont.truetype(candidate, size)
            except OSError:
                continue
    raise OSError("Install Segoe UI or DejaVu Sans and Mono")


def canvas(width: int, height: int) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    image = Image.new("RGB", (width, height), INK)
    draw = ImageDraw.Draw(image)
    for y in range(24, height - 16, 24):
        for x in range(24, width - 16, 24):
            draw.point((x, y), fill="#263450")
    draw.rounded_rectangle((2, 2, width - 3, height - 3), 21, outline=RULE, width=2)
    return image, draw


def text(draw, x, y, label, size, color=WHITE, style="regular", anchor="lt"):
    draw.text((x, y), label, fill=color, font=font(size, style), anchor=anchor)


def title(draw, heading, subheading):
    text(draw, 32, 28, heading, 42, style="bold")
    text(draw, 34, 90, subheading, 22, MUTED)


def box(draw, bounds, label, detail, accent=CYAN):
    x, y, right, _ = bounds
    draw.rounded_rectangle(bounds, 12, fill=PANEL, outline=RULE, width=2)
    draw.line((x + 15, y + 1, right - 15, y + 1), accent, width=2)
    text(draw, x + 15, y + 16, label, 23, style="bold")
    text(draw, x + 15, y + 52, detail, 19, MUTED)


def arrow(draw, start, finish, color=BLUE):
    x, y = finish
    draw.line([start, finish], color, width=3)
    if start[0] == x:
        direction = 1 if y > start[1] else -1
        head = [(x, y), (x - 6, y - direction * 8), (x + 6, y - direction * 8)]
    else:
        direction = 1 if x > start[0] else -1
        head = [(x, y), (x - direction * 8, y - 6), (x - direction * 8, y + 6)]
    draw.polygon(head, color)


def hero():
    image, draw = canvas(960, 324)
    for index, color in enumerate(("#1d3272", "#314a9e", "#526dca", "#826bc5", VIOLET)):
        offset = index * 15
        route = [
            (561, 244 + offset),
            (612, 244 + offset),
            (748, 108 + offset),
            (846, 108 + offset),
            (904, 50 + offset),
        ]
        draw.line(route, color, width=2)
        for x, y in route[1:-1]:
            draw.ellipse((x - 3, y - 3, x + 3, y + 3), fill=color)
    draw.rounded_rectangle((46, 56, 134, 144), 22, fill=PANEL, outline=BLUE, width=2)
    draw.line([(65, 85), (114, 85), (91, 108), (91, 126)], CYAN, width=6)
    draw.line([(72, 111), (91, 92), (107, 92)], VIOLET, width=3)
    for x, y in ((65, 85), (114, 85), (91, 126)):
        draw.ellipse((x - 4, y - 4, x + 4, y + 4), fill=WHITE)
    text(draw, 43, 162, "TRAJYN", 103, style="bold")
    text(draw, 48, 272, "VERIFIED EXPERIENCE  /  PORTABLE PROCEDURES", 20, CYAN, "mono")
    image.save(OUT / "wordmark.png", optimize=True)


STAGES = [
    ("Agent A", "Receives a task", CYAN),
    ("Execution", "Calls tools and observes", CYAN),
    ("Trajectory", "Records each tool result", BLUE),
    ("Verification", "Checks resulting state", BLUE),
    ("Induction", "Extracts guarded steps", VIOLET),
    ("Capsule", "Packs steps and evidence", VIOLET),
    ("Compatibility", "Checks target interfaces", VIOLET),
    ("Agent B", "Uses compatible memory", CYAN),
    ("Evaluation", "Compares outcomes", CYAN),
]


def pipeline_frame(stage=-1, pulse=0):
    image, draw = canvas(800, 574)
    title(draw, "From one agent to another", "The experience-transfer pipeline")
    for index, (label, detail, accent) in enumerate(STAGES):
        row, col = divmod(index, 3)
        if row == 1:
            col = 2 - col
        x, y = 28 + 252 * col, 145 + 128 * row
        if index != 8:
            if index % 3 == 2:
                arrow(draw, (x + 118, y + 91), (x + 118, y + 127))
            elif row == 1:
                arrow(draw, (x, y + 45), (x - 18, y + 45))
            else:
                arrow(draw, (x + 234, y + 45), (x + 251, y + 45))
        box(draw, (x, y, x + 234, y + 90), label, detail, accent)
        if stage == index:
            draw.rounded_rectangle((x, y, x + 234, y + 90), 12, outline=accent, width=3)
            for dot in range(3):
                pos = x + 19 + int(190 * ((pulse + dot * 0.064) % 1))
                draw.ellipse((pos, y + 76, pos + 6, y + 82), accent)
    text(draw, 32, 534, "Architecture illustration  /  Results require paired execution", 21, MUTED)
    return image


def pipeline():
    pipeline_frame().save(OUT / "pipeline.png", optimize=True)
    frames = [
        pipeline_frame(stage, pulse / 4).quantize(96)
        for stage in range(len(STAGES))
        for pulse in range(4)
    ]
    frames[0].save(
        OUT / "pipeline.gif",
        save_all=True,
        append_images=frames[1:],
        duration=[150, 150, 150, 420] * len(STAGES),
        loop=0,
        optimize=True,
    )


def architecture():
    image, draw = canvas(800, 866)
    title(draw, "Inside the runtime", "Implemented data flow and planned storage")
    rows = [
        (
            "SOURCE EXECUTION",
            "Agent adapters",
            "Agent protocol / Ollama",
            "Execution environment",
            "Tools + private task state",
            CYAN,
        ),
        (
            "VERIFY & INDUCE",
            "Trajectory recorder",
            "Observable action / result pairs",
            "Independent verifier",
            "Final task-state outcome",
            BLUE,
        ),
        (
            "VERIFIED EXPERIENCE",
            "Induction engine",
            "Replay + observation guards",
            "Capability capsule",
            "Bindings, tools, evidence",
            VIOLET,
        ),
        (
            "TARGET EXECUTION",
            "Experience retrieval",
            "Public task and interfaces",
            "Compatibility checks",
            "Applicability + tool contract",
            VIOLET,
        ),
        (
            "PAIRED MEASUREMENT",
            "Target agent + tools",
            "Fresh environment per trial",
            "Comparative evaluation",
            "State success + failures",
            CYAN,
        ),
    ]
    for i, (group, left, ld, right, rd, accent) in enumerate(rows):
        y = 127 + 130 * i
        text(draw, 400, y, group, 18, accent, "mono", "mt")
        forward = i % 2 == 0
        if not forward:
            left, ld, right, rd = right, rd, left, ld
        box(draw, (32, y + 27, 358, y + 111), left, ld, accent)
        box(draw, (440, y + 27, 768, y + 111), right, rd, accent)
        start, end = (361, 437) if forward else (437, 361)
        arrow(draw, (start, y + 68), (end, y + 68), accent)
        if i < 4:
            edge = 605 if forward else 195
            arrow(draw, (edge, y + 113), (edge, y + 155), MUTED)
    draw.rounded_rectangle((32, 796, 768, 838), 10, outline=VIOLET, width=2)
    text(
        draw,
        51,
        817,
        "PLANNED  /  Versioned capability registry and lineage",
        22,
        VIOLET,
        "mono",
        "lm",
    )
    image.save(OUT / "architecture.png", optimize=True)


def trajectory():
    records = [
        json.loads(line) for line in (PILOT / "source/source-0.jsonl").read_text().splitlines()
    ]
    capsules = [json.loads(line) for line in (PILOT / "capsules.jsonl").read_text().splitlines()]
    capsule = next(
        item
        for item in capsules
        if item["evidence"][0]["trajectory_id"] == records[0]["trajectory_id"]
    )
    image, draw = canvas(800, 739)
    model = records[0]["agent"]["model"]
    seed = records[0]["task"]["seed"]
    title(draw, "A verified execution", f"{model}  /  training seed {seed}  /  published trace")
    for row, record in enumerate(entry for entry in records if entry["event"] == "step"):
        step = record["step"]
        y = 143 + 83 * row
        draw.rounded_rectangle((32, y, 768, y + 69), 12, fill=PANEL, outline=RULE)
        text(draw, 51, y + 21, f"{step['index']:02}", 21, CYAN, "mono")
        text(draw, 108, y + 19, step["action"]["tool"], 25, style="mono")
        text(draw, 744, y + 22, step["observation"]["code"], 20, MUTED, "mono", "rt")
    verification = records[-1]["verification"]
    text(
        draw,
        37,
        482,
        "STATE VERIFIED" if verification["passed"] else "VERIFICATION FAILED",
        22,
        CYAN,
        "mono",
    )
    draw.rounded_rectangle((32, 524, 768, 705), 13, fill=PANEL, outline=VIOLET, width=2)
    text(draw, 50, 543, "Capsule bindings", 28, style="bold")
    procedure = next(step for step in capsule["steps"] if step["tool"] == "ship_replacement")
    origins = {item["parameter"]: item["source_step"] for item in procedure["bindings"]}
    text(draw, 50, 590, f"parcel_id   ←  observation {origins['parcel_id']}", 24, VIOLET, "mono")
    text(draw, 50, 630, f"product_id  ←  observation {origins['product_id']}", 24, VIOLET, "mono")
    evidence = capsule["evidence"][0]
    text(
        draw,
        50,
        673,
        f"Evidence  {evidence['trajectory_id'][:19]}…  •  "
        f"steps {', '.join(map(str, evidence['step_indices']))}",
        19,
        MUTED,
        "mono",
    )
    image.save(OUT / "verified-execution.png", optimize=True)


def results(path: Path):
    records = json.loads(path.read_text(encoding="utf-8"))["evaluation"]["trials"]
    totals = Counter(row["condition"] for row in records)
    passed = Counter(row["condition"] for row in records if row["passed"])
    failures = Counter()
    for row in records:
        failures[row["condition"]] += row["invalid_calls"]
    image, draw = canvas(800, 587)
    title(draw, "Held-out outcomes", f"Recorded model trials  /  {records[0]['agent']['model']}")
    text(draw, 486, 144, "VERIFIED", 18, CYAN, "mono")
    text(draw, 609, 144, "INVALID CALLS", 18, VIOLET, "mono")
    for idx, label in enumerate(
        ("No memory", "Raw trajectory", "Procedural summary", "Capsule", "Irrelevant memory")
    ):
        letter = chr(65 + idx)
        y = 182 + 69 * idx
        draw.rounded_rectangle((32, y, 768, y + 59), 11, fill=PANEL)
        text(draw, 52, y + 17, letter, 23, CYAN, "mono")
        text(draw, 100, y + 16, label, 25, style="bold")
        text(draw, 528, y + 16, f"{passed[letter]}/{totals[letter]}", 26, WHITE, "mono", "mt")
        text(draw, 685, y + 16, str(failures[letter]), 26, VIOLET, "mono", "mt")
    text(draw, 35, 542, "Verified completion is measured from environment state.", 22, MUTED)
    image.save(OUT / "outcomes.png", optimize=True)


def badges():
    for name, label, value, color in (
        ("python", "Python", "3.12+", "#263e74"),
        ("license", "License", "Apache-2.0", "#382d69"),
        ("status", "Status", "Experimental", "#184e62"),
    ):
        width = 72 + 7 * len(value)
        (OUT / f"badge-{name}.svg").write_text(
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="24" '
            f'viewBox="0 0 {width} 24" role="img" aria-label="{label}: {value}">'
            f'<rect width="{width}" height="24" rx="5" fill="#111d36"/>'
            f'<rect x="61" width="{width - 61}" height="24" rx="5" fill="{color}"/>'
            '<g fill="#f2f6ff" font-family="Verdana,sans-serif" '
            'font-size="11" text-anchor="middle">'
            f'<text x="31" y="16">{label}</text>'
            f'<text x="{(width + 61) / 2:g}" y="16">{value}</text></g></svg>\n',
            encoding="utf-8",
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, default=PILOT / "evaluation/results.json")
    args = parser.parse_args()
    OUT.mkdir(exist_ok=True)
    hero()
    pipeline()
    architecture()
    trajectory()
    results(args.results)
    badges()
