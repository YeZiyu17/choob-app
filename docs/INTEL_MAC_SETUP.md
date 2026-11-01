# Choob Intel Mac 安装、启动与排错

适用范围：Intel `x86_64` Mac、macOS、Python 3.11。该配置只解决 Intel Mac 无法安装 `torch>=2.3` 的兼容问题；其他平台继续使用 `requirements.txt`，Docker 配置未降级。

## 1. 全新安装

在仓库根目录运行：

```bash
uname -m                     # 应显示 x86_64
python3.11 --version         # 应显示 Python 3.11.x
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-intel-mac.txt
python -m pip check
```

`pip check` 应显示 `No broken requirements found.`。兼容文件固定核心 AI 组合：

- `numpy==1.26.4`
- `torch==2.2.2`
- `transformers==4.44.2`
- `sentence-transformers==3.0.1`

Flask、Gunicorn、Pandas、Pillow 和 Requests 保留经过测试的主版本范围。

## 2. 预先缓存模型

演示前连接稳定网络并运行：

```bash
python cache_models.py
```

该命令下载并缓存两套公开预训练权重：

- 图片识别：`openai/clip-vit-base-patch32`（CLIP ViT-B/32）。应用代码加入提示词集合、同义词、文本特征缓存和已记录阈值的范围检查；没有微调权重。
- 文字推荐：`sentence-transformers/all-MiniLM-L6-v2`，修订版由推荐 manifest 固定为 `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`。应用把查询嵌入与已保存向量比较，再按 85% 语义相似度 + 15% 平滑菜品情感排序；没有微调权重。

应用现在先读取本地缓存，缓存缺失时才联网下载，因此缓存完成后课堂断网仍可启动。模型缓存不进入 Git。

## 3. 验证安装、测试和真实推理

安装成功、页面可用和模型推理成功是三件不同的事，应分别检查。

```bash
# A. 包依赖
python -m pip check

# B. 61 个合成/接口回归检查（不是模型准确率）
python -m unittest discover -s tests -v

# C. 真实 MiniLM、CSV/NPY/manifest 对齐与不同查询
python evaluation/run_recommendation_smoke.py

# D. 预热两个模型并启动服务器
python cache_models.py
python app.py
```

另开终端：

```bash
curl http://127.0.0.1:7860/api/status
```

最后必须在浏览器打开 `http://127.0.0.1:7860/`，在 Discover 输入至少两个明显不同的英文偏好，并在 Snap 上传自己的照片。仅看到首页或仅通过 `pip check` 不代表推理成功。

## 4. 启动与停止

开发/课堂演示：

```bash
source .venv/bin/activate
python app.py
```

浏览器打开 `http://127.0.0.1:7860/`。终端保持运行；停止时在该终端按 `Ctrl+C`。

更接近生产方式的本机启动：

```bash
source .venv/bin/activate
gunicorn -w 1 -b 127.0.0.1:7860 --timeout 180 app:app
```

只使用一个 worker，避免每个 worker 各自加载一份大模型。公网部署不是 11 月 2 日演示的前置条件。

## 5. 常见问题

### `No matching distribution found for torch>=2.3`

确认机器是 Intel Mac，并使用 `requirements-intel-mac.txt`，不要修改共享 `requirements.txt`。

### 第一次请求很慢

首次下载、进程内模型加载和首次推理要分开理解。提前运行 `cache_models.py`；启动应用后先各做一次 Discover 和 Snap 作为预热，再开始录屏。

### 断网时仍反复访问 Hugging Face

先确认模型已完整缓存。当前代码会先使用 `local_files_only=True`，只有缓存缺失时才联网。若缓存不完整，重新联网运行 `python cache_models.py`。

### 端口 7860 已占用

先停止旧的 Choob 终端，或临时换端口：

```bash
PORT=7861 python app.py
```

### 返回 503

- Snap 503：检查 CLIP 缓存、内存和 `recognition_config.json`。
- Discover 503：检查 MiniLM 缓存，以及 `data/` 下 CSV、NPY、manifest 是否来自同一次构建且未被改动。
- Results metadata 503：检查 manifest 存在且 JSON 字段完整。

### 图片被拒绝

文件必须是有效 JPG/PNG/WebP、小于 8 MB 且不超过 16 MP。范围检查返回 Unknown 不等于请求失败；按界面填写实际菜名后仍可收藏。

## 6. 2026-11-01 实际验证范围

- 机器：Quad-Core Intel Core i5，`x86_64`，macOS 26.7.1，Python 3.11.9。
- 新建 `/private/tmp` 虚拟环境，从空环境安装 `requirements-intel-mac.txt`，`pip check` 通过。
- 同一干净环境 61/61 回归检查通过，首页和 `/api/status` 均为 HTTP 200。
- 干净环境真实 MiniLM 和 CLIP 推理均成功；模型已缓存，因此没有测量下载时间。
- 干净环境的推荐数据 + 模型加载为约 80.43 秒；首次 MiniLM encode 约 1.43 秒，后续 2 次平均约 0.013 秒。
- 干净环境的 CLIP 模型 + 提示缓存构建约 4.25 秒；首次图片推理约 0.284 秒，后续 5 次平均约 0.203 秒。

完整机器可读结果见 `evaluation/results/person4_clean_intel_benchmark_2026-11-01.json`。这些时间是一次本机测量，不是服务等级保证。
