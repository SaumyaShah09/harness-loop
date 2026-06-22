"""
Generate production-quality HarnessLoop README demo GIF.

Renders a pixel-accurate Playground UI mockup in headless Chromium,
captures smooth animation frames, and exports an optimized GIF.

Requirements: pip install pillow playwright && playwright install chromium

Run: python scripts/generate_demo_gif.py
"""

from __future__ import annotations

import math
import subprocess
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
HTML = Path(__file__).resolve().parent / "demo_capture.html"
OUTPUT = ROOT / "assets" / "harnessloop-demo.gif"

WIDTH, HEIGHT = 1280, 720
FPS = 15
DURATION_MS = int(1000 / FPS)
TOTAL_FRAMES = 72  # 4.8 seconds
SUPERSAMPLE = 1  # HTML already at target resolution


def ensure_playwright():
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
        return
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "playwright", "-q"])
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
    except ImportError as exc:
        raise SystemExit("Failed to install playwright") from exc

    subprocess.check_call([sys.executable, "-m", "playwright", "install", "chromium"])


def ease_in_out(t: float) -> float:
    return t * t * (3 - 2 * t)


def capture_frames() -> list[Image.Image]:
    from playwright.sync_api import sync_playwright

    frames: list[Image.Image] = []
    html_uri = HTML.as_uri()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": WIDTH, "height": HEIGHT})
        page.goto(html_uri, wait_until="networkidle")
        page.wait_for_timeout(200)

        for i in range(TOTAL_FRAMES):
            raw_t = i / (TOTAL_FRAMES - 1)
            progress = ease_in_out(raw_t)
            page.evaluate(f"window.setProgress({progress:.4f})")
            page.wait_for_timeout(30)

            png_bytes = page.screenshot(type="png")
            frame = Image.open(__import__("io").BytesIO(png_bytes)).convert("RGB")
            if SUPERSAMPLE != 1:
                frame = frame.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)
            frames.append(frame)

        browser.close()

    return frames


def optimize_palette(frames: list[Image.Image]) -> list[Image.Image]:
    """Convert to adaptive palette for smaller file size without banding."""
    quantized = []
    for frame in frames:
        q = frame.quantize(colors=128, method=Image.Quantize.MEDIANCUT)
        quantized.append(q.convert("P", palette=Image.Palette.ADAPTIVE, colors=128))
    return quantized


def save_gif(frames: list[Image.Image]) -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    # Hold last frame for readability
    frames = frames + [frames[-1].copy()] * 15

    # Resize for README display (sharp at 800px embed, smaller file)
    resized = [
        f.resize((960, 540), Image.Resampling.LANCZOS) for f in frames
    ]

    resized[0].save(
        OUTPUT,
        save_all=True,
        append_images=resized[1:],
        duration=DURATION_MS,
        loop=0,
        optimize=True,
        disposal=2,
    )


def main():
    if not HTML.exists():
        raise SystemExit(f"Missing {HTML}")

    print("Installing browser if needed…")
    ensure_playwright()

    print(f"Capturing {TOTAL_FRAMES} frames at {WIDTH}x{HEIGHT}…")
    frames = capture_frames()

    print("Encoding GIF…")
    save_gif(frames)

    size_kb = OUTPUT.stat().st_size / 1024
    print(f"Done -> {OUTPUT} ({size_kb:.0f} KB, {len(frames)} frames @ {FPS} fps)")


if __name__ == "__main__":
    main()
