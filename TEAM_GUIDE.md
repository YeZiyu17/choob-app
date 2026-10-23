# Choob 五人协作与本地运行

大家使用同一个 [GitHub 仓库](https://github.com/YeZiyu17/choob-app)保存和修改代码。目前采用 **GitHub 协作＋各自电脑运行**，无需注册托管账号。

## 先把 App 跑起来

1. 安装 **Python 3.11**。Windows 安装时勾选“Add Python to PATH”。
2. 打开仓库，确认分支是 `main`，点绿色 **Code → Download ZIP**，解压到自己的文件夹。
3. 在解压后的 `choob-app-main` 文件夹打开终端；确认能看到 `app.py` 和 `requirements.txt`。
4. 按自己的系统运行下面的命令。

macOS：

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python app.py
```

Windows（命令提示符 CMD）：

```bat
py -3.11 -m venv .venv
.venv\Scripts\activate.bat
python -m pip install -r requirements.txt
python app.py
```

在浏览器打开 **http://localhost:7860/**，保留终端窗口；停止服务时在终端按 `Ctrl+C`。下次运行只需进入同一文件夹、激活 `.venv`，再运行 `python app.py`。

首次使用图片识别和文字推荐时，会从网上下载公开模型；请保持联网，并预留数 GB 的磁盘空间和可用内存。下载与首次加载可能较慢，建议关闭占内存较多的程序。后续会复用本机模型缓存。

先在 **Discover** 输入英文口味，例如 `cheesecake or tiramisu`；再用 **Snap** 上传食物照片。推荐基于 50 家餐厅的抽样评论，不代表完整或最新菜单，也不能验证饮食禁忌与过敏要求。

## 一起改代码

下载 ZIP 适合先运行；持续开发建议安装 **GitHub Desktop**，登录自己的 GitHub 账号后，用 **File → Clone repository → URL** 克隆本仓库。大家已有 collaborator 权限，不需要各自复制一个新仓库。

每次修改按这个顺序：

1. 切到 `main`，点 **Fetch origin / Pull origin**，获取团队最新代码。
2. 从 `main` 创建自己的分支，例如 `person1-ui`、`person2-data` 或 `person3-ai`。
3. 修改文件，在自己的电脑运行和检查，再 **Commit → Publish branch / Push origin**。
4. 点 **Create Pull Request**，目标选择 `main`，说明改了什么、如何检查。
5. 请另一位组员检查后合并；其他人再更新自己的 `main`。

不要把 `.venv`、模型缓存、账号密码或未经确认的原始评论文件上传到 GitHub。修改推荐导出时，CSV、NPY 和 manifest 三个文件要保持同一版本。

## 我们的分工

| 成员 | 负责内容 | 主要交接 |
|---|---|---|
| Person 1 | UI Design + User Flow | `index.html`，与 Person 4 对齐接口 |
| Person 2 | Data Processing | 按 `data/README.md` 提供清洗后的评论与餐厅数据 |
| Person 3（你） | AI Model + Recommendation | 识别、推荐、数据导出及模型局限 |
| Person 4 | App Integration + Deployment | Flask 与界面连接、本地运行支持；需要时再安排云端部署 |
| Person 5 | Evaluation + Testing | 新图片测试、人工评价推荐、完整操作流程检查 |

## 哪些东西是共享的？

- **GitHub 共享代码与版本。** 组员提交并合并后，其他人更新代码才能看到变化。
- **App 各自在自己的电脑运行。** `localhost` 指打开页面的这台电脑；把这个地址发给别人不会打开你的 App。
- **Collect 收藏只存在当前浏览器。** 换电脑或换浏览器不会自动同步，目前没有团队共享账号或数据库。
- 若以后希望所有人点击同一个网址就能直接使用完整 AI App，再安排托管部署。GitHub 的代码页面可以直接查看代码；GitHub Pages 不能运行本项目的 Flask 和 Python 模型。
