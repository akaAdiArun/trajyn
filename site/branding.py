"""Render the website and GitHub TRAJYN receipt previews. Requires Pillow."""

import argparse
from pathlib import Path

from build import STOPS
from PIL import Image, ImageDraw, ImageFont

WIDTH, HEIGHT, SCALE = 1200, 630, 2
PAPER = "#F6F2E7"
INSET = "#FFFCF4"
INK = "#1D2520"
MUTED = "#535D53"
RULE = "#CBC5B7"
FOREST = "#194638"


def font(size: int, face: str) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    windows, portable = {
        "display": ("georgia.ttf", "DejaVuSerif.ttf"),
        "body": ("segoeui.ttf", "DejaVuSans.ttf"),
        "strong": ("segoeuib.ttf", "DejaVuSans-Bold.ttf"),
        "mono": ("consola.ttf", "DejaVuSansMono.ttf"),
    }[face]
    for candidate in (str(Path("C:/Windows/Fonts") / windows), portable):
        try:
            return ImageFont.truetype(candidate, size * SCALE)
        except OSError:
            continue
    return ImageFont.load_default(size * SCALE)


def scaled(*values: int) -> tuple[int, ...]:
    return tuple(value * SCALE for value in values)


def make_social_preview(path: Path) -> None:
    image = Image.new("RGB", (WIDTH * SCALE, HEIGHT * SCALE), PAPER)
    draw = ImageDraw.Draw(image)

    def text(x: int, y: int, label: str, size: int, face: str, fill: str = INK) -> None:
        draw.text(scaled(x, y), label, fill, font(size, face), anchor="lt")

    def rule(*points: int, fill: str = RULE, width: int = 1) -> None:
        draw.line(scaled(*points), fill=fill, width=width * SCALE)

    text(63, 86, "TRAJYN", 29, "strong")
    rule(64, 135, 532, 135)
    for y, line in zip(
        (168, 244, 320), ("One AI fixed it.", "What can the", "next one reuse?"), strict=True
    ):
        text(62, y, line, 65, "display")
    text(65, 444, "Follow the receipt →", 27, "strong", FOREST)

    draw.rectangle(scaled(632, 67, 1143, 572), fill="#EAE4D6")
    draw.rectangle(scaled(624, 58, 1135, 563), fill=INSET, outline=RULE, width=SCALE)
    rule(624, 59, 1135, 59, fill=FOREST, width=4)
    text(651, 87, "RECORDED RUN · SIMULATED DELIVERY SYSTEM", 16, "mono", FOREST)
    text(650, 120, "Case 01 / Lost delivery", 38, "display")
    rule(651, 173, 1106, 173)
    centers = (214, 295, 376, 457)
    rule(653, centers[0], 653, centers[-1], fill=FOREST, width=2)
    for index, (stop, center) in enumerate(zip(STOPS, centers, strict=True), 1):
        rule(653, center, 665, center, fill=FOREST, width=2)
        text(673, center - 13, f"{index:02}", 30, "mono", FOREST)
        text(726, center - 18, stop.label, 22, "strong")
        fact = stop.result
        if stop.tag == "Receipt returned":
            fact = "Replacement accepted"
        elif stop.tag == "Receipt used":
            fact = "Same receipt closes the ticket"
        text(726, center + 10, fact, 15, "body", MUTED)
        if stop.tag:
            draw.rectangle(scaled(956, center - 13, 1098, center + 13), fill=FOREST)
            draw.text(scaled(1027, center), stop.tag, INSET, font(14, "mono"), anchor="mm")
        rule(673, center + 39, 1106, center + 39)
    rule(1098, 376, 1110, 376, 1110, 457, 1098, 457, fill=FOREST, width=3)
    text(653, 521, "Verified outcome · Case closed", 20, "strong", FOREST)
    image.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS).save(path, optimize=True)


def make_github_preview(path: Path) -> None:
    width, height = 1280, 640
    image = Image.new("RGB", scaled(width, height), PAPER)
    draw = ImageDraw.Draw(image)

    def text(x: int, y: int, label: str, size: int, face: str, fill: str = INK) -> None:
        draw.text(scaled(x, y), label, fill, font(size, face), anchor="lt")

    draw.line(scaled(64, 90, 1216, 90), FOREST, width=4 * SCALE)
    text(62, 190, "TRAJYN", 110, "strong", FOREST)
    text(65, 321, "Follow the receipt", 54, "display")

    draw.rectangle(scaled(631, 139, 1224, 557), fill="#EAE4D6")
    draw.rectangle(scaled(622, 130, 1215, 548), fill=INSET, outline=RULE, width=SCALE)
    draw.line(scaled(622, 132, 1215, 132), FOREST, width=5 * SCALE)
    text(650, 159, "RECORDED RUN · LOST DELIVERY", 22, "mono", FOREST)
    for step, y, label, tag in (
        (3, 219, "Send a replacement", "Receipt returned"),
        (4, 374, "Close the case", "Receipt used"),
    ):
        draw.line(scaled(651, y, 1184, y), RULE, width=SCALE)
        text(651, y + 23, f"{step:02}", 32, "mono", FOREST)
        text(721, y + 20, label, 37, "display")
        draw.rectangle(scaled(721, y + 74, 1076, y + 122), fill=FOREST)
        text(740, y + 84, tag, 26, "strong", INSET)
    draw.line(scaled(1076, 316, 1147, 316, 1147, 471, 1076, 471), FOREST, width=5 * SCALE)
    draw.polygon([scaled(1076, 471), scaled(1094, 459), scaled(1094, 483)], fill=FOREST)
    image.resize((width, height), Image.Resampling.LANCZOS).save(path, optimize=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--github", action="store_true", help="render the repository share image")
    if parser.parse_args().github:
        make_github_preview(
            Path(__file__).resolve().parents[1] / "docs/assets/github-social-preview.png"
        )
    else:
        make_social_preview(Path(__file__).with_name("assets") / "social-preview.png")
