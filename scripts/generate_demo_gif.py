"""
Generate HarnessLoop README demo GIF.
Shows the self-evolving prompt loop with live score progression.
Run: python scripts/generate_demo_gif.py
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

WIDTH, HEIGHT = 800, 450
FPS = 12
DURATION_MS = int(1000 / FPS)

# HarnessLoop dark theme palette
BG = (9, 9, 11)
CARD = (17, 17, 19)
BORDER = (39, 39, 42)
TEXT = (250, 250, 250)
MUTED = (161, 161, 170)
ACCENT = (99, 102, 241)
SUCCESS = (16, 185, 129)
WARNING = (245, 158, 11)
DANGER = (239, 68, 68)

SCORES = [0, 62, 68, 73, 79, 84, 87]
ITERATIONS = [0, 1, 1, 2, 3, 4, 5]
STATUSES = [
    "Ready",
    "Evaluating 20 cases...",
    "Analyzing failures...",
    "Rewriting prompt...",
    "Evaluating 20 cases...",
    "Analyzing failures...",
    "Target reached!",
]

LOOP_NODES = ["Goal", "Harness", "Loop", "Evolve"]
OUTPUT = Path(__file__).resolve().parent.parent / "assets" / "harnessloop-demo.gif"


def get_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def score_color(score: float) -> tuple[int, int, int]:
    if score >= 75:
        return SUCCESS
    if score >= 50:
        return WARNING
    return DANGER


def draw_rounded_rect(draw: ImageDraw.ImageDraw, xy, radius: int, fill, outline=None):
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline)


def draw_loop_diagram(draw: ImageDraw.ImageDraw, active_idx: int):
    cx, cy = 400, 118
    radius = 72
    import math

    for i, label in enumerate(LOOP_NODES):
        angle = -math.pi / 2 + (2 * math.pi * i / len(LOOP_NODES))
        x = cx + radius * math.cos(angle)
        y = cy + radius * math.sin(angle)
        is_active = i == active_idx % len(LOOP_NODES)
        node_fill = ACCENT if is_active else CARD
        text_fill = TEXT if is_active else MUTED
        r = 34
        draw.ellipse((x - r, y - r, x + r, y + r), fill=node_fill, outline=BORDER, width=2)
        font = get_font(13, bold=is_active)
        bbox = draw.textbbox((0, 0), label, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text((x - tw / 2, y - th / 2 - 1), label, fill=text_fill, font=font)

    for i in range(len(LOOP_NODES)):
        a1 = -math.pi / 2 + (2 * math.pi * i / len(LOOP_NODES))
        a2 = -math.pi / 2 + (2 * math.pi * ((i + 1) % len(LOOP_NODES)) / len(LOOP_NODES))
        x1 = cx + (radius - 8) * math.cos(a1)
        y1 = cy + (radius - 8) * math.sin(a1)
        x2 = cx + (radius - 8) * math.cos(a2)
        y2 = cy + (radius - 8) * math.sin(a2)
        draw.line((x1, y1, x2, y2), fill=BORDER, width=2)

    title_font = get_font(11)
    draw.text((cx - 52, cy - 8), "FEEDBACK LOOP", fill=MUTED, font=title_font)


def draw_chart(draw: ImageDraw.ImageDraw, frame_idx: int):
    chart_box = (48, 210, 752, 390)
    draw_rounded_rect(draw, chart_box, 12, CARD, outline=BORDER)

    title_font = get_font(14, bold=True)
    draw.text((64, 224), "Score Progression", fill=TEXT, font=title_font)

    chart_left, chart_right = 90, 720
    chart_top, chart_bottom = 260, 360
    target_y = chart_bottom - (85 / 100) * (chart_bottom - chart_top)

    draw.line((chart_left, target_y, chart_right, target_y), fill=MUTED, width=1)
    target_font = get_font(10)
    draw.text((chart_right - 72, target_y - 16), "Target 85%", fill=MUTED, font=target_font)

    visible_points = min(frame_idx + 1, len(SCORES))
    if visible_points <= 1:
        hint_font = get_font(12)
        draw.text((chart_left + 180, chart_top + 42), "Starting evolution...", fill=MUTED, font=hint_font)
        return

    points = []
    for i in range(visible_points):
        if SCORES[i] == 0:
            continue
        x = chart_left + (i / (len(SCORES) - 1)) * (chart_right - chart_left)
        y = chart_bottom - (SCORES[i] / 100) * (chart_bottom - chart_top)
        points.append((x, y))

    if len(points) >= 2:
        draw.line(points, fill=ACCENT, width=3)

    for x, y in points:
        color = score_color(SCORES[points.index((x, y)) + (1 if SCORES[0] == 0 else 0)])
        draw.ellipse((x - 6, y - 6, x + 6, y + 6), fill=color, outline=TEXT, width=2)

    label_font = get_font(10)
    draw.text((chart_left - 8, chart_bottom + 6), "Iter", fill=MUTED, font=label_font)
    draw.text((chart_left - 22, chart_top - 4), "Score", fill=MUTED, font=label_font)


def draw_metrics(draw: ImageDraw.ImageDraw, frame_idx: int):
    idx = min(frame_idx, len(SCORES) - 1)
    score = SCORES[idx]
    iteration = ITERATIONS[idx]
    status = STATUSES[idx]

    metrics = [
        ("Current", f"{score}%" if score else "—", score_color(score) if score else MUTED),
        ("Iteration", str(iteration), ACCENT),
        ("Best", f"{max(SCORES[: idx + 1])}%" if score else "—", SUCCESS if score >= 75 else WARNING if score >= 50 else MUTED),
        ("Status", status[:18] + ("…" if len(status) > 18 else ""), SUCCESS if "reached" in status else ACCENT),
    ]

    x = 48
    for label, value, color in metrics:
        box = (x, 400, x + 168, 438)
        draw_rounded_rect(draw, box, 8, BG, outline=BORDER)
        label_font = get_font(9)
        value_font = get_font(13, bold=True)
        draw.text((x + 10, 406), label.upper(), fill=MUTED, font=label_font)
        draw.text((x + 10, 418), value, fill=color, font=value_font)
        x += 176


def render_frame(frame_idx: int) -> Image.Image:
    img = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(img)

    title_font = get_font(26, bold=True)
    subtitle_font = get_font(13)
    draw.text((48, 28), "HarnessLoop", fill=TEXT, font=title_font)
    draw.text((48, 62), "Self-evolving prompt optimization", fill=MUTED, font=subtitle_font)

    badge_font = get_font(10, bold=True)
    draw_rounded_rect(draw, (620, 34, 752, 58), 6, (24, 24, 27), outline=ACCENT)
    draw.text((636, 40), "Harness → Loop → Evolve", fill=ACCENT, font=badge_font)

    active_loop = frame_idx % len(LOOP_NODES)
    draw_loop_diagram(draw, active_loop)
    draw_chart(draw, frame_idx)
    draw_metrics(draw, frame_idx)

    if frame_idx == len(SCORES) - 1:
        pulse = 8 + (frame_idx % 3) * 2
        draw_rounded_rect(draw, (280, 168, 520, 198), 10, (16, 185, 129, 30))
        done_font = get_font(12, bold=True)
        draw.text((300, 176), "Target achieved — prompt discovered", fill=SUCCESS, font=done_font)

    return img


def main():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    hold_frames = 8
    frames: list[Image.Image] = []

    for i in range(len(SCORES)):
        frame = render_frame(i)
        repeat = hold_frames if i in (0, len(SCORES) - 1) else 5
        frames.extend([frame.copy() for _ in range(repeat)])

    frames[0].save(
        OUTPUT,
        save_all=True,
        append_images=frames[1:],
        duration=DURATION_MS,
        loop=0,
        optimize=True,
    )

    size_kb = OUTPUT.stat().st_size / 1024
    print(f"Generated {OUTPUT} ({size_kb:.1f} KB, {len(frames)} frames @ {FPS} fps)")


if __name__ == "__main__":
    main()
