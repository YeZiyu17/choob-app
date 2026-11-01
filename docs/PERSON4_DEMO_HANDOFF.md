# Person 4 — 11 月 2 日 Intermediate Demo 交接

## 当前结论

当前路线是可重复安装、稳定运行的本地 Flask 应用。没有为演示引入账号、数据库、社区后端、框架迁移或付费部署。代码保留 Person 1 的单页 UI，并直接使用 Person 3 的 CLIP 识别、MiniLM 推荐、CSV/NPY/manifest 和既有评估记录。

Project Forward Guidelines 和老师最新邮件的原始附件/正文不在仓库中；本文件按团队提供的摘要执行。正式提交仍以 Brightspace 原文为准。

## 架构与数据流

```text
index.html (Person 1 UI)
  ├─ Snap 上传 ──> Flask /api/recognize ──> CLIP ViT-B/32
  │                                      └─ 提示词集 + 已记录阈值范围检查
  ├─ Discover 文本 ─> Flask /api/recommend ─> all-MiniLM-L6-v2
  │                                         ├─ data CSV + 5,993×384 NPY
  │                                         ├─ manifest 哈希/版本校验
  │                                         └─ 85% 相似度 + 15% 菜品情感
  ├─ Results ─────> /api/recommendation-summary ─> 当前 manifest 构建信息
  └─ Collect ─────> 浏览器 localStorage ─> 刷新保留、同菜名+餐厅去重
```

图片区分：CLIP 只在九个支持菜品家族间排序，并通过范围检查决定是否 Unknown。文字推荐区分：MiniLM 将偏好编码后与 Yelp 派生菜品描述向量比较。两者不是同一个模型。

项目使用的 Yelp 派生数据为历史样本：3,526 条评论、123 家费城餐厅、8,667 个有证据的评论–菜品提及、5,993 个餐厅–菜品对。团队实现了数据验证/manifest、范围检查、排名公式、Flask API、UI 流程和测试；没有微调 CLIP 或 MiniLM，也没有集成 notebook 中的 Qwen2.5-VL-3B。

## 2026-11-01 实际验证

### 自动化/模拟测试

- 现有 Intel 环境：61/61 通过。
- 独立新建 Intel 环境：61/61 通过。
- 这些检查使用合成 fixture 和 mock 验证接口、错误处理、排序计算、数据一致性和缓存刷新，不是模型准确率。
- 新增覆盖：Flask 提供原 UI/状态、空/损坏/大于 8 MB 图片、有效图片进入识别器、模型失败返回 503。

### 真实模型调用

- MiniLM：真实加载 manifest 固定修订版；CSV/NPY 为 5,993 行 × 384 维且哈希一致。三个偏好分别以 Sushi、Tiramisu Dessert、Spicy Fish 为最高语义匹配，证明输入变化会改变结果。
- CLIP：两张本次验证新选的外部照片，各连续运行 3 次。
  - [Pizza.jpeg](https://commons.wikimedia.org/wiki/File:Pizza.jpeg)，SHA-256 `a5c3fe114e310199c76b59336b451de2a9ba6f8c23d37744cbde0c357cda9819`：返回 Pizza，accepted=true。
  - [Sushi!.jpg](https://commons.wikimedia.org/wiki/File:Sushi!.jpg)，SHA-256 `1c83bce3be348d73d9e6bf6687fbbc197087c5fd4de9b3493deeb992fd3f93aa`：返回 Unknown，建议候选 Sushi，accepted=false；人工输入流程正常。
- 两张照片此前不在仓库评估文件中，是本次 Person 4 验证新选样本。两次结果不能当作准确率。

### 实际 HTTP

- 首页、`/api/status`、`/api/recommendation-summary`：200。
- 3 个不同偏好：3 组不同 Top-5，全部 200。
- 两张图片真实推理：全部 200。
- 空偏好 400；未验证的 gluten-free 请求 422；缺图 400；损坏图片 400；超过 8 MB 为 413。
- 冷 HTTP（含加载 + 推理 + Flask + 回环网络）：MiniLM 约 8.57 秒；CLIP 约 20.63 秒。
- 缓存后 HTTP：MiniLM 两次约 0.033/0.024 秒；第二张 CLIP 图片约 0.690 秒。

### 浏览器

Snap 确认/修改、Discover 两种偏好、两条收藏来源、刷新持久化、重复去重、连续请求最新结果获胜和 Results 当前构建信息均已实际观察通过。详情见 `evaluation/results/person4_browser_verification_2026-11-01.md`。

### 干净 Intel 环境

- `x86_64`、macOS 26.7.1、Python 3.11.9。
- 从空 venv 安装 `requirements-intel-mac.txt`；`pip check` 通过。
- 首页和状态接口 200；61/61 测试通过；CLIP 与 MiniLM 均真实推理成功。
- 模型已缓存，下载耗时未测。干净环境第一次进程内推荐数据 + 模型加载约 80.43 秒；MiniLM 首次 encode 约 1.43 秒，后续 n=2 平均约 0.013 秒。CLIP 模型 + 提示缓存约 4.25 秒；首次推理约 0.284 秒，后续 n=5 平均约 0.203 秒。
- 这是单次本机测量；不要泛化为所有 Intel Mac 的性能。

机器可读证据：

- `evaluation/results/person4_clean_intel_benchmark_2026-11-01.json`
- `evaluation/results/person4_intel_benchmark_2026-11-01.json`
- `evaluation/results/person4_http_verification_2026-11-01.json`

## 演示前 10 分钟

1. 接电并关闭占用内存的软件。
2. `source .venv/bin/activate`。
3. `python -m pip check`。
4. `python cache_models.py`（仍有网络时确认缓存）。
5. `python app.py`。
6. 浏览器打开 `http://127.0.0.1:7860/`。
7. 先私下运行一次 Discover 和一次 Snap，完成进程内预热。
8. 保留两张照片本地副本；关闭无关标签页和通知。

## 不超过 5 分钟的录屏流程

目标总长约 4:40。

1. **0:00–0:25，范围和变化**：说明这是项目自有 UI、数据和模型的本地端到端应用；公网部署不是本次硬要求。
2. **0:25–1:15，Snap 正常结果**：上传 Pizza 照片，点击圆形按钮；指出是实时 CLIP、相对分数不是概率；确认 Pizza 并收藏。
3. **1:15–2:00，Snap 安全回退**：上传 Sushi 照片；展示 Unknown + Sushi 建议候选；手动输入 `Sushi` 后收藏，说明不会为不确定结果编造 cuisine/category。
4. **2:00–2:25，Collect**：显示 Pizza 来源为 `Live Snap inference`、手动 Sushi 为 `Snap · manual dish name`；刷新页面确认仍在；重复收藏时显示 Already、数量不增加。
5. **2:25–3:35，Discover**：输入 `I want sushi with fresh fish.`，收藏第一项；再输入 `I want a sweet dessert, such as tiramisu or cheesecake.`，展示 Top-5 变化。强调历史 Yelp 样本不能验证菜单、过敏或饮食要求。
6. **3:35–4:20，Results**：展示当前构建 3,526 / 8,667 / 5,993；明确上方识别指标和推荐示例是已记录结果，不是刚才两张照片；人工推荐相关性仍待 Person 5。
7. **4:20–4:40，技术挑战与结尾**：一句话说明 Intel `torch>=2.3` 安装失败，采用独立 `torch 2.2.2` 配置并在新环境完成真实双模型验证；提醒课堂 AI Trust Lab 选项待 Brightspace 原文。

不要在录屏中等待冷加载；预热后再录。若要展示冷启动数字，直接打开本文件或 Results 说明，不现场重启。

## 备用方案

- **模型已缓存但断网**：当前加载器先读取本地缓存；重启 Flask 后继续演示。不要清理 `~/.cache/huggingface`。
- **模型冷加载慢**：保持服务器进程运行并提前预热；录屏前不要重启。
- **现场网络/模型失败**：展示明确错误提示和 Results 的 `RECORDED` 证据，同时播放预先完成的短备份录屏。不要把记录输出说成现场推理。
- **一张照片返回 Unknown**：这是预期安全行为；展示人工确认/修改流程。Pizza 是已验证的 accepted 演示照片。
- **端口冲突**：停止旧进程，或用 `PORT=7861 python app.py` 并打开对应地址。
- **完全无法启动**：保留 Git 提交、JSON 测试证据和备份视频；不要临时迁移框架或购买部署资源。

## 自 Showcase 以来的变化

仓库没有提供明确标注的 Showcase 提交或 Showcase 材料，因此不能把任意 commit 硬当成正式基线。下列变化有 Git 历史证据，但“是否均发生在 Showcase 之后”需要团队确认。候选 UI 基线为 2026-10-19 的 `7762fc2`，不是已确认的 Showcase tag。

- 2026-10-23：CLIP 提示词集合、缓存文本特征、背景类别竞争和冻结阈值范围检查；新增 Food-101 calibration/holdout 记录和 API 检查（`d83cc89` 至 `5b05de1`）。
- 2026-10-23：真实 Yelp 派生推荐数据、MiniLM 推理、Flask 推荐 API 和团队运行说明（`45d89b9` 至 `38cb3ca`）。
- 2026-10-29：推荐数据扩大到 123 家餐厅、3,526 条评论、5,993 对；加入 manifest、baseline 对比、Person 5 计划和 Results 当前构建信息（`bf6d133` 至 `b075696`）。
- 当前 Person 4 分支：Intel Mac 独立依赖、缓存优先离线启动、Snap/Discover 超时与连续请求保护、收藏来源/去重、额外 Flask 测试、HTTP/浏览器/干净环境证据和演示文档。

团队应在提交前提供 Showcase 幻灯片/视频日期或 commit/tag，以确认基线并删掉“待确认”。

## Person 4 贡献说明（可直接使用）

“Person 4 完成了 Choob 的 Flask/UI 端到端整合与运行支持：保留原 UI 和 Person 3 模型/数据，补齐 Snap、Discover、Collect、Results 的错误处理、连续请求保护和来源标识；解决 Intel Mac Python 3.11 的 PyTorch 安装兼容与缓存后离线启动；在独立新环境、真实 HTTP 和浏览器中验证两个 AI 功能，并整理演示、排错和可复用测试证据。”

## 仍需其他成员提供

- **Person 3**：确认本分支仍对应其最终模型/数据版本；确认识别阈值和模型说明没有后续替代；如有新的模型评估，只提供可追溯结果。
- **Person 5**：完成 `recommendation_human_review.csv` 的人工相关性评价和报告；不要把当前 61 个接口测试写成推荐准确率。
- **团队**：提供 Showcase 基线材料；提供 Brightspace 的两个 AI Trust Lab 选项原文；课堂发生后再记录选择、结果和反思。

## 建议提交清单

- 独立分支代码与 reviewed PR，不直接合并 main。
- `requirements-intel-mac.txt` 与 `docs/INTEL_MAC_SETUP.md`。
- 本交接文档和三份 Person 4 JSON + 浏览器记录。
- 不超过 5 分钟的录屏链接和必要的备份视频。
- Person 3 模型/数据版本说明，Person 5 的真实人工评估（完成后）。
- AI Trust Lab 测试选项、实际执行结果和团队反思（课堂后）。
- 不提交 `.venv`、模型缓存、临时测试图片、私有原始数据或密钥。

最终提交内容、截止时间和格式以 Brightspace 正式要求及老师最新邮件为准。
