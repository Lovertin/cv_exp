from __future__ import annotations

import argparse
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageOps


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "outputs" / "exp1"

EXPERIMENT_IMAGE_ROOT = next(PROJECT_ROOT.glob("实验图像"))
EXP1_IMAGE_DIR = next(EXPERIMENT_IMAGE_ROOT.glob("测试图像*实验一*"))
READ_DISPLAY_DIR = next(EXP1_IMAGE_DIR.glob("*读取*写入*显示*"))
ADD_DIR = next(EXP1_IMAGE_DIR.glob("*加法*"))

READ_DISPLAY_IMAGE = READ_DISPLAY_DIR / "Fig0651(a)(flower_no_compression).tif"
ADD_IMAGE_A = ADD_DIR / "Fig1016(a)(building_original).tif"
ADD_IMAGE_B = READ_DISPLAY_DIR / "Fig0637(a)(caster_stand_original).tif"


def imread_unicode(path: Path, flags: int = cv2.IMREAD_UNCHANGED) -> np.ndarray:
    with Image.open(path) as pil_image:
        pil_image = ImageOps.exif_transpose(pil_image)
        if flags == cv2.IMREAD_GRAYSCALE:
            return np.array(pil_image.convert("L"))
        if pil_image.mode == "L":
            return np.array(pil_image)
        if pil_image.mode == "RGBA":
            rgba = np.array(pil_image)
            return cv2.cvtColor(rgba, cv2.COLOR_RGBA2BGRA)
        rgb = np.array(pil_image.convert("RGB"))
        return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)


def imwrite_unicode(path: Path, image: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ext = path.suffix or ".png"
    ok, encoded = cv2.imencode(ext, image)
    if not ok:
        raise OSError(f"Cannot encode image: {path}")
    encoded.tofile(str(path))


def to_bgr(image: np.ndarray) -> np.ndarray:
    if image.ndim == 2:
        return cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    if image.ndim == 3 and image.shape[2] == 4:
        return cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)
    return image


def image_info(image: np.ndarray) -> str:
    if image.ndim == 2:
        h, w = image.shape
        channels = 1
    else:
        h, w, channels = image.shape
    return f"width={w}, height={h}, channels={channels}, dtype={image.dtype}"


def add_label(image: np.ndarray, label: str) -> np.ndarray:
    canvas = image.copy()
    h, w = canvas.shape[:2]
    scale = max(0.55, min(w, h) / 520)
    thickness = max(1, int(round(scale * 2)))
    margin = int(12 * scale)
    (text_w, text_h), baseline = cv2.getTextSize(
        label, cv2.FONT_HERSHEY_SIMPLEX, scale, thickness
    )
    cv2.rectangle(
        canvas,
        (0, 0),
        (min(w, text_w + margin * 2), text_h + baseline + margin * 2),
        (255, 255, 255),
        -1,
    )
    cv2.putText(
        canvas,
        label,
        (margin, margin + text_h),
        cv2.FONT_HERSHEY_SIMPLEX,
        scale,
        (0, 0, 0),
        thickness,
        cv2.LINE_AA,
    )
    return canvas


def make_grid(images: list[tuple[str, np.ndarray]], cell_size: tuple[int, int]) -> np.ndarray:
    cell_w, cell_h = cell_size
    cells: list[np.ndarray] = []
    for label, image in images:
        bgr = to_bgr(image)
        h, w = bgr.shape[:2]
        ratio = min(cell_w / w, cell_h / h)
        resized = cv2.resize(
            bgr,
            (max(1, int(w * ratio)), max(1, int(h * ratio))),
            interpolation=cv2.INTER_AREA,
        )
        cell = np.full((cell_h, cell_w, 3), 245, dtype=np.uint8)
        y = (cell_h - resized.shape[0]) // 2
        x = (cell_w - resized.shape[1]) // 2
        cell[y : y + resized.shape[0], x : x + resized.shape[1]] = resized
        cell = add_label(cell, label)
        cells.append(cell)
    return np.hstack(cells)


def maybe_show(title: str, image: np.ndarray, enabled: bool) -> None:
    if not enabled:
        return
    try:
        cv2.imshow(title, image)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    except cv2.error as exc:
        print(f"OpenCV GUI display is unavailable in this environment: {exc}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Experiment 1: basic image operations.")
    parser.add_argument(
        "--show",
        action="store_true",
        help="Show images with cv2.imshow if the local OpenCV build supports GUI windows.",
    )
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    original = imread_unicode(READ_DISPLAY_IMAGE, cv2.IMREAD_UNCHANGED)
    original_bgr = to_bgr(original)
    half_size = (original_bgr.shape[1] // 2, original_bgr.shape[0] // 2)
    half = cv2.resize(original_bgr, half_size, interpolation=cv2.INTER_AREA)
    black = np.zeros((50, 50, 3), dtype=np.uint8)

    imwrite_unicode(OUTPUT_DIR / "01_original_flower.png", original_bgr)
    imwrite_unicode(OUTPUT_DIR / "02_flower_half_size.png", half)
    imwrite_unicode(OUTPUT_DIR / "03_black_50x50.png", black)

    read_write_summary = make_grid(
        [
            ("Original image", original_bgr),
            ("Resized to 1/2", half),
            ("50x50 black image", black),
        ],
        (420, 330),
    )
    imwrite_unicode(OUTPUT_DIR / "04_read_write_display_summary.png", read_write_summary)
    maybe_show("Experiment 1 - read/write/display", read_write_summary, args.show)

    add_a = to_bgr(imread_unicode(ADD_IMAGE_A, cv2.IMREAD_UNCHANGED))
    add_b = to_bgr(imread_unicode(ADD_IMAGE_B, cv2.IMREAD_UNCHANGED))
    add_size = (512, 512)
    add_a = cv2.resize(add_a, add_size, interpolation=cv2.INTER_AREA)
    add_b = cv2.resize(add_b, add_size, interpolation=cv2.INTER_AREA)

    numpy_plus = add_a + add_b
    cv2_added = cv2.add(add_a, add_b)
    diff = cv2.absdiff(numpy_plus, cv2_added)

    imwrite_unicode(OUTPUT_DIR / "05_add_input_building.png", add_a)
    imwrite_unicode(OUTPUT_DIR / "06_add_input_caster_stand.png", add_b)
    imwrite_unicode(OUTPUT_DIR / "07_numpy_plus_result.png", numpy_plus)
    imwrite_unicode(OUTPUT_DIR / "08_cv2_add_result.png", cv2_added)
    imwrite_unicode(OUTPUT_DIR / "09_addition_difference.png", diff)

    addition_summary = make_grid(
        [
            ("Input A: building", add_a),
            ("Input B: caster stand", add_b),
            ("NumPy + result", numpy_plus),
            ("cv2.add result", cv2_added),
            ("Absolute difference", diff),
        ],
        (300, 300),
    )
    imwrite_unicode(OUTPUT_DIR / "10_addition_summary.png", addition_summary)
    maybe_show("Experiment 1 - addition", addition_summary, args.show)

    summary_lines = [
        "Experiment 1: Basic Image Operations",
        "",
        f"Read/display source: {READ_DISPLAY_IMAGE}",
        f"Original image: {image_info(original_bgr)}",
        f"Half-size image: {image_info(half)}",
        f"Black square: {image_info(black)}",
        "",
        f"Addition image A: {ADD_IMAGE_A}",
        f"Addition image B: {ADD_IMAGE_B}",
        f"Addition input A after resize: {image_info(add_a)}",
        f"Addition input B after resize: {image_info(add_b)}",
        f"NumPy + result: {image_info(numpy_plus)}",
        f"cv2.add result: {image_info(cv2_added)}",
        f"Mean absolute difference between addition results: {diff.mean():.2f}",
        "",
        "Generated files:",
    ]
    for path in sorted(OUTPUT_DIR.glob("*.png")):
        summary_lines.append(f"- {path.name}")

    (OUTPUT_DIR / "exp1_result_summary.txt").write_text(
        "\n".join(summary_lines), encoding="utf-8"
    )
    print("\n".join(summary_lines))


if __name__ == "__main__":
    main()
