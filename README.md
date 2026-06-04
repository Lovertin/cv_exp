# Computer Vision Experiments Source Code

This repository stores the source code for the computer vision experiments.

## Source Code Policy

Current and future experiment source files should be placed in `src/`.

Generated result images, Word reports, PPT files, original experiment images, compressed datasets, and temporary Office files are ignored by Git and should stay local.

## Current Scripts

- `src/exp1_basic_operations.py`: Experiment 1, basic image operations.
- `src/make_exp1_report_docx.py`: Helper script for generating Experiment 1 report content.
- `src/exp2_image_transform.py`: Experiment 2, image transforms, smoothing, and thresholding.
- `src/make_exp2_report_docx.py`: Helper script for generating Experiment 2 report content.
- `src/exp3_collect_augment.py`: Experiment 3, public hand gesture data collection and augmentation.

## Report Template Scheme

For future reports, use this scheme in the "程序源代码" and "程序说明" sections.

### 四、程序源代码

源码仓库：

```text
https://github.com/Lovertin/cv_exp.git
```

本实验源码文件：

```text
src/expX_xxx.py
```

本地源码路径：

```text
E:\实验报告\实验\src\expX_xxx.py
```

### 五、程序说明

运行环境：

```bash
pip install -r requirements.txt
```

运行命令：

```bash
python E:\实验报告\实验\src\expX_xxx.py
```

程序运行后，结果图像保存到：

```text
E:\实验报告\实验\outputs\expX
```

If OpenCV GUI windows are needed and supported by the local environment, run:

```bash
python E:\实验报告\实验\src\expX_xxx.py --show
```
