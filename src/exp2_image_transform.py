from __future__ import annotations

import argparse
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageOps


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "outputs" / "exp2"

EXPERIMENT_IMAGE_ROOT = next(PROJECT_ROOT.glob("实验图像"))
EXP2_IMAGE_DIR = next(EXPERIMENT_IMAGE_ROOT.glob("测试图像*实验二*"))
GEOMETRY_IMAGE = EXP2_IMAGE_DIR / "Fig1034(a)(marion_airport).tif"
SMOOTH_IMAGE = EXP2_IMAGE_DIR / "Fig0335(a)(ckt_board_saltpep_prob_pt05).tif"
THRESHOLD_IMAGE = EXP2_IMAGE_DIR / "Fig0343(a)(skeleton_orig).tif"


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


def to_gray(image: np.ndarray) -> np.ndarray:
    if image.ndim == 2:
        return image
    if image.ndim == 3 and image.shape[2] == 4:
        image = cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)


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
    base_scale = max(0.5, min(w, h) / 560)
    margin = max(6, int(12 * base_scale))
    available_width = max(40, w - margin * 2)
    scale = base_scale
    thickness = max(1, int(round(scale * 2)))
    (text_w, text_h), baseline = cv2.getTextSize(
        label, cv2.FONT_HERSHEY_SIMPLEX, scale, thickness
    )
    if text_w > available_width:
        scale *= available_width / text_w
        scale = max(0.32, scale)
        thickness = max(1, int(round(scale * 2)))
        (text_w, text_h), baseline = cv2.getTextSize(
            label, cv2.FONT_HERSHEY_SIMPLEX, scale, thickness
        )
    label_h = text_h + baseline + margin * 2
    label_w = min(w, text_w + margin * 2)
    cv2.rectangle(canvas, (0, 0), (label_w, label_h), (255, 255, 255), -1)
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


def make_grid(
    images: list[tuple[str, np.ndarray]],
    cell_size: tuple[int, int],
    columns: int,
) -> np.ndarray:
    cell_w, cell_h = cell_size
    blank = np.full((cell_h, cell_w, 3), 245, dtype=np.uint8)
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
        cell = blank.copy()
        y = (cell_h - resized.shape[0]) // 2
        x = (cell_w - resized.shape[1]) // 2
        cell[y : y + resized.shape[0], x : x + resized.shape[1]] = resized
        cells.append(add_label(cell, label))

    while len(cells) % columns != 0:
        cells.append(blank.copy())

    rows = []
    for start in range(0, len(cells), columns):
        rows.append(np.hstack(cells[start : start + columns]))
    return np.vstack(rows)


def draw_points(image: np.ndarray, points: np.ndarray, prefix: str) -> np.ndarray:
    canvas = to_bgr(image).copy()
    for idx, (x, y) in enumerate(points.astype(int), start=1):
        cv2.circle(canvas, (x, y), 7, (0, 0, 255), -1)
        cv2.putText(
            canvas,
            f"{prefix}{idx}",
            (x + 8, y - 8),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (0, 0, 255),
            2,
            cv2.LINE_AA,
        )
    return canvas


def maybe_show(title: str, image: np.ndarray, enabled: bool) -> None:
    if not enabled:
        return
    try:
        cv2.imshow(title, image)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    except cv2.error as exc:
        print(f"OpenCV GUI display is unavailable in this environment: {exc}")


def run_geometry(show: bool) -> list[str]:
    lines: list[str] = []
    image = to_bgr(imread_unicode(GEOMETRY_IMAGE, cv2.IMREAD_UNCHANGED))
    h, w = image.shape[:2]
    dsize = (w, h)

    scaled = cv2.resize(
        image,
        None,
        fx=0.1,
        fy=0.1,
        interpolation=cv2.INTER_AREA,
    )

    center = (w / 2, h / 2)
    rotation_matrix = cv2.getRotationMatrix2D(center, 45, 1.0)
    rotated = cv2.warpAffine(
        image,
        rotation_matrix,
        dsize,
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(0, 0, 0),
    )

    translation_matrix = np.float32([[1, 0, 10], [0, 1, 5]])
    translated = cv2.warpAffine(
        image,
        translation_matrix,
        dsize,
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(0, 0, 0),
    )

    src_points = np.float32(
        [
            [0.22 * w, 0.20 * h],
            [0.80 * w, 0.18 * h],
            [0.88 * w, 0.82 * h],
            [0.16 * w, 0.78 * h],
        ]
    )
    dst_points = np.float32(
        [
            [0.10 * w, 0.10 * h],
            [0.90 * w, 0.08 * h],
            [0.82 * w, 0.92 * h],
            [0.18 * w, 0.88 * h],
        ]
    )
    perspective_matrix = cv2.getPerspectiveTransform(src_points, dst_points)
    perspective = cv2.warpPerspective(
        image,
        perspective_matrix,
        dsize,
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(0, 0, 0),
    )

    source_points_view = draw_points(image, src_points, "S")
    perspective_points_view = draw_points(perspective, dst_points, "D")

    outputs = {
        "01_geometry_original.png": image,
        "02_geometry_scale_10_percent_inter_area.png": scaled,
        "03_geometry_rotate_left_45_keep_size.png": rotated,
        "04_geometry_translate_x10_y5.png": translated,
        "05_geometry_perspective_source_points.png": source_points_view,
        "06_geometry_perspective_result.png": perspective,
        "07_geometry_perspective_result_points.png": perspective_points_view,
    }
    for name, out_image in outputs.items():
        imwrite_unicode(OUTPUT_DIR / name, out_image)

    geometry_summary = make_grid(
        [
            ("Original", image),
            ("Scale 10%, INTER_AREA", scaled),
            ("Rotate left 45 deg", rotated),
            ("Translate x=10, y=5", translated),
            ("Perspective source points", source_points_view),
            ("Perspective result", perspective_points_view),
        ],
        (360, 320),
        columns=3,
    )
    imwrite_unicode(OUTPUT_DIR / "08_geometry_summary.png", geometry_summary)
    maybe_show("Experiment 2 - geometry", geometry_summary, show)

    lines.extend(
        [
            "Geometry transform",
            f"- Source image: {GEOMETRY_IMAGE}",
            f"- Original: {image_info(image)}",
            f"- Scale: fx=0.1, fy=0.1, interpolation=cv2.INTER_AREA; result {image_info(scaled)}",
            "- Rotation: center=(width/2, height/2), angle=45 degrees, scale=1.0, output size unchanged",
            "- Translation: x=10 pixels, y=5 pixels",
            "- Perspective source points: "
            + ", ".join([f"({x:.1f}, {y:.1f})" for x, y in src_points]),
            "- Perspective destination points: "
            + ", ".join([f"({x:.1f}, {y:.1f})" for x, y in dst_points]),
            "",
        ]
    )
    return lines


def run_smoothing(show: bool) -> list[str]:
    lines: list[str] = []
    gray = to_gray(imread_unicode(SMOOTH_IMAGE, cv2.IMREAD_UNCHANGED))
    kernels = [3, 5, 9]

    results: list[tuple[str, np.ndarray]] = [("Original noise image", gray)]
    for k in kernels:
        result = cv2.blur(gray, (k, k))
        imwrite_unicode(OUTPUT_DIR / f"09_smooth_mean_{k}x{k}.png", result)
        results.append((f"Mean {k}x{k}", result))

    for k in kernels:
        result = cv2.GaussianBlur(gray, (k, k), sigmaX=0)
        imwrite_unicode(OUTPUT_DIR / f"10_smooth_gaussian_{k}x{k}.png", result)
        results.append((f"Gaussian {k}x{k}", result))

    for k in kernels:
        result = cv2.medianBlur(gray, k)
        imwrite_unicode(OUTPUT_DIR / f"11_smooth_median_{k}.png", result)
        results.append((f"Median {k}", result))

    imwrite_unicode(OUTPUT_DIR / "09_smooth_original_noise.png", gray)
    smoothing_summary = make_grid(results, (290, 250), columns=5)
    imwrite_unicode(OUTPUT_DIR / "12_smoothing_summary.png", smoothing_summary)
    maybe_show("Experiment 2 - smoothing", smoothing_summary, show)

    lines.extend(
        [
            "Image smoothing",
            f"- Source image: {SMOOTH_IMAGE}",
            f"- Original: {image_info(gray)}",
            "- Mean filters: 3x3, 5x5, 9x9",
            "- Gaussian filters: 3x3, 5x5, 9x9, sigmaX=0",
            "- Median filters: 3, 5, 9",
            "- Observation focus: compare noise removal and edge/detail retention as kernel size increases",
            "",
        ]
    )
    return lines


def run_threshold(show: bool) -> list[str]:
    lines: list[str] = []
    gray = to_gray(imread_unicode(THRESHOLD_IMAGE, cv2.IMREAD_UNCHANGED))

    fixed_threshold_value = 127
    fixed_ret, fixed_binary = cv2.threshold(
        gray, fixed_threshold_value, 255, cv2.THRESH_BINARY
    )
    otsu_ret, otsu_binary = cv2.threshold(gray, 0, 255, cv2.THRESH_OTSU)
    combined_ret, combined_binary = cv2.threshold(
        gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )
    adaptive_mean = cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_MEAN_C,
        cv2.THRESH_BINARY,
        31,
        5,
    )
    adaptive_gaussian = cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        5,
    )

    outputs = {
        "13_threshold_original_gray.png": gray,
        "14_threshold_fixed_binary_127.png": fixed_binary,
        "15_threshold_otsu_only.png": otsu_binary,
        "16_threshold_binary_plus_otsu.png": combined_binary,
        "17_threshold_adaptive_mean_binary.png": adaptive_mean,
        "18_threshold_adaptive_gaussian_binary.png": adaptive_gaussian,
    }
    for name, out_image in outputs.items():
        imwrite_unicode(OUTPUT_DIR / name, out_image)

    threshold_summary = make_grid(
        [
            ("Original gray", gray),
            (f"Binary thresh={fixed_ret:.0f}", fixed_binary),
            (f"Otsu ret={otsu_ret:.0f}", otsu_binary),
            (f"Binary+Otsu ret={combined_ret:.0f}", combined_binary),
            ("Adaptive MEAN, block=31, C=5", adaptive_mean),
            ("Adaptive GAUSSIAN, block=31, C=5", adaptive_gaussian),
        ],
        (330, 360),
        columns=3,
    )
    imwrite_unicode(OUTPUT_DIR / "19_threshold_summary.png", threshold_summary)
    maybe_show("Experiment 2 - threshold", threshold_summary, show)

    lines.extend(
        [
            "Threshold processing",
            f"- Source image: {THRESHOLD_IMAGE}",
            f"- Original: {image_info(gray)}",
            f"- Fixed binary threshold: threshold={fixed_threshold_value}, returned={fixed_ret:.1f}",
            f"- Otsu threshold returned={otsu_ret:.1f}",
            f"- Binary + Otsu threshold returned={combined_ret:.1f}",
            "- Adaptive threshold 1: cv2.ADAPTIVE_THRESH_MEAN_C + cv2.THRESH_BINARY, blockSize=31, C=5",
            "- Adaptive threshold 2: cv2.ADAPTIVE_THRESH_GAUSSIAN_C + cv2.THRESH_BINARY, blockSize=31, C=5",
            "",
        ]
    )
    return lines


def write_report_content(summary_lines: list[str]) -> None:
    report = """# 实验二 图像变换

## 一、实验目的

1. 掌握图像几何变换的基本方法。
2. 掌握图像平滑的基本方法。
3. 掌握图像阈值处理的基本方法。

## 二、实验原理

图像几何变换通过坐标映射改变像素在图像中的空间位置。缩放使用插值方法计算新图像像素值，旋转和平移可由仿射变换矩阵实现，透视变换使用 3x3 变换矩阵将原图四点映射到目标图四点。

图像平滑通过邻域运算降低图像噪声。均值滤波用邻域像素平均值替代中心像素；高斯滤波根据距离中心点的远近赋予不同权重；中值滤波用邻域像素的中位数替代中心像素，通常对椒盐噪声效果较好。

阈值处理将灰度图像按灰度值分为不同区域。固定阈值需要人工给定阈值，Otsu 算法可根据类间方差自动选取阈值，自适应阈值则根据局部邻域计算阈值，适合处理光照不均匀的图像。

## 三、实验结果分析

几何变换中，缩放 10% 后图像尺寸明显变小，采用 `cv2.INTER_AREA` 插值可以较好地保留缩小后的整体结构。以图像中心左旋 45 度并保持原尺寸时，部分图像内容会落到边界外，边界处出现黑色填充。平移操作使图像整体向右 10 像素、向下 5 像素移动，移出区域被黑色背景填充。透视变换通过四点对应关系改变图像视角，直线结构仍保持为直线。

平滑处理中，随着卷积核由 3x3 增大到 9x9，均值滤波和高斯滤波的去噪能力增强，但图像细节和边缘也更模糊。中值滤波对椒盐噪声的抑制更明显，在去除孤立黑白噪点的同时能较好保留边缘轮廓。

阈值处理中，固定阈值 127 的二值化结果依赖人工阈值选取；Otsu 算法自动计算阈值，能根据图像灰度分布获得更客观的分割结果；自适应阈值根据局部区域计算阈值，对灰度变化不均匀的图像有更好的局部分割效果。

## 四、程序源代码

源代码文件：

`E:\\实验报告\\实验\\src\\exp2_image_transform.py`

## 五、程序说明

运行环境建议：

```bash
pip install opencv-python numpy
```

运行命令：

```bash
python E:\\实验报告\\实验\\src\\exp2_image_transform.py
```

若本机 OpenCV 支持 GUI 窗口显示，可使用：

```bash
python E:\\实验报告\\实验\\src\\exp2_image_transform.py --show
```

程序运行后，结果图像将保存到：

`E:\\实验报告\\实验\\outputs\\exp2`

## 六、结果文件说明

- `08_geometry_summary.png`：几何变换对比图。
- `12_smoothing_summary.png`：均值滤波、高斯滤波、中值滤波对比图。
- `19_threshold_summary.png`：固定阈值、Otsu、自适应阈值处理对比图。
- `exp2_result_summary.txt`：实验参数和输出文件摘要。

"""
    (OUTPUT_DIR / "实验二报告内容.md").write_text(report, encoding="utf-8")
    (OUTPUT_DIR / "exp2_result_summary.txt").write_text(
        "\n".join(summary_lines), encoding="utf-8"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Experiment 2: image transform.")
    parser.add_argument(
        "--show",
        action="store_true",
        help="Show images with cv2.imshow if the local OpenCV build supports GUI windows.",
    )
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    summary_lines = ["Experiment 2: Image Transform", ""]
    summary_lines.extend(run_geometry(args.show))
    summary_lines.extend(run_smoothing(args.show))
    summary_lines.extend(run_threshold(args.show))

    summary_lines.append("Generated files:")
    for path in sorted(OUTPUT_DIR.glob("*.png")):
        summary_lines.append(f"- {path.name}")

    write_report_content(summary_lines)
    print("\n".join(summary_lines))


if __name__ == "__main__":
    main()
