"""Render the TRAJYN social-preview card. Requires Pillow."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

WIDTH, HEIGHT, SCALE = 1280, 640, 2
CYAN = "#60e7ec"
VIOLET = "#a594ff"
WHITE = "#f2f5ff"
MUTED = "#aeb8d2"


def font(
    size: int, *, bold: bool = False, mono: bool = False
) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    if mono:
        windows, portable = "consola.ttf", "DejaVuSansMono.ttf"
    elif bold:
        windows, portable = "segoeuib.ttf", "DejaVuSans-Bold.ttf"
    else:
        windows, portable = "segoeui.ttf", "DejaVuSans.ttf"
    for candidate in (str(Path("C:/Windows/Fonts") / windows), portable):
        try:
            return ImageFont.truetype(candidate, size * SCALE)
        except OSError:
            continue
    return ImageFont.load_default(size * SCALE)


def coordinates(*values: int) -> tuple[int, ...]:
    return tuple(value * SCALE for value in values)


def point_list(points: list[tuple[int, int]]) -> list[tuple[int, int]]:
    return [(x * SCALE, y * SCALE) for x, y in points]


def halo(image: Image.Image, bounds: tuple[int, int, int, int], color: str) -> None:
    tint = Image.new("RGB", image.size, color)
    mask = Image.new("L", image.size)
    ImageDraw.Draw(mask).ellipse(coordinates(*bounds), fill=67)
    image.paste(tint, mask=mask.filter(ImageFilter.GaussianBlur(103 * SCALE)))


def make_social_preview(path: Path) -> None:
    image = Image.new("RGB", (WIDTH * SCALE, HEIGHT * SCALE), "#090d17")
    halo(image, (698, 28, 1201, 590), "#413790")
    halo(image, (712, 245, 1006, 457), "#175b6a")
    draw = ImageDraw.Draw(image)
    for y in range(52, 613, 24):
        for x in range(52, 1250, 24):
            draw.ellipse(coordinates(x, y, x + 1, y + 1), fill="#253047")
    draw.rounded_rectangle(
        coordinates(30, 30, 1250, 610), radius=24 * SCALE, outline="#2b3650", width=SCALE
    )

    draw.rounded_rectangle(
        coordinates(87, 88, 174, 175),
        radius=21 * SCALE,
        fill="#131c30",
        outline="#566b9f",
        width=SCALE,
    )
    draw.line(point_list([(107, 116), (153, 116), (130, 139), (130, 154)]), CYAN, 5 * SCALE)
    draw.line(point_list([(113, 141), (131, 123), (146, 123)]), VIOLET, 3 * SCALE)
    for x, y in ((107, 116), (153, 116), (130, 154)):
        draw.ellipse(coordinates(x - 3, y - 3, x + 3, y + 3), WHITE)
    draw.text((79 * SCALE, 198 * SCALE), "TRAJYN", WHITE, font(121, bold=True), anchor="lt")
    for y, line in ((349, "The Experience Layer"), (405, "for AI Agents")):
        draw.text((87 * SCALE, y * SCALE), line, MUTED, font(47), anchor="lt")
    draw.text(
        (87 * SCALE, 550 * SCALE),
        "EXPERIMENTAL  /  OPEN SOURCE",
        CYAN,
        font(17, mono=True),
        anchor="lt",
    )

    for offset, color in ((-18, "#28616f"), (0, "#4896a5"), (18, "#334f7c")):
        incoming = [
            (655, 320 + offset),
            (701, 320 + offset),
            (748, 273 + offset),
            (805, 273 + offset),
        ]
        draw.line(point_list(incoming), color, 2 * SCALE, joint="curve")
    for offset, color in ((-16, "#4b4779"), (0, "#8a77d0"), (16, "#514782")):
        outgoing = [
            (1084, 315 + offset),
            (1110, 315 + offset),
            (1146, 279 + offset),
            (1192, 279 + offset),
        ]
        draw.line(point_list(outgoing), color, 2 * SCALE, joint="curve")

    faces = [
        ([(802, 235), (943, 314), (943, 458), (802, 377)], "#162d42", "#60e7ec"),
        ([(943, 314), (1085, 235), (1085, 377), (943, 458)], "#242345", "#a594ff"),
        ([(802, 235), (943, 155), (1085, 235), (943, 314)], "#222641", "#acaff7"),
    ]
    for points, base, edge in faces:
        draw.polygon(point_list(points), fill=base)
        draw.line(point_list([*points, points[0]]), edge, 2 * SCALE, joint="curve")
    for points, color in (
        ([(832, 235), (943, 172), (1055, 235), (943, 299), (832, 235)], "#53628f"),
        ([(852, 235), (943, 184), (1035, 235), (943, 287), (852, 235)], "#46577f"),
        ([(866, 239), (944, 194), (1020, 237)], CYAN),
        ([(942, 278), (944, 243), (986, 219)], VIOLET),
        ([(1020, 237), (968, 268), (966, 280)], CYAN),
        ([(828, 290), (915, 340)], "#4b95ae"),
        ([(828, 307), (899, 348)], "#4b95ae"),
        ([(828, 324), (883, 356)], "#4b95ae"),
        ([(971, 340), (1059, 290)], "#8076bb"),
        ([(971, 357), (1059, 307)], "#8076bb"),
        ([(971, 374), (1059, 324)], "#8076bb"),
    ):
        draw.line(point_list(points), color, 2 * SCALE, joint="curve")
    for x, y, color in (
        (655, 320, CYAN),
        (802, 273, CYAN),
        (1085, 315, VIOLET),
        (1192, 279, VIOLET),
    ):
        draw.ellipse(coordinates(x - 4, y - 4, x + 4, y + 4), color)

    image.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS).save(path, optimize=True)


if __name__ == "__main__":
    make_social_preview(Path(__file__).with_name("assets") / "social-preview.png")
