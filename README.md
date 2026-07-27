# Zihao 工作台

每日任务管理 + 表达练习 + 今日复盘 + 灵感来源，四合一工作台。

## 部署到 GitHub Pages（手机电脑都能访问）

### 1. 创建 GitHub 仓库

到 [github.com/new](https://github.com/new) 创建一个新仓库，名字随意（比如 `zihao-workbench`），选 **Public**。

### 2. 推送代码

在本项目目录下执行：

```bash
git init
git add .
git commit -m "init: zihao workbench"
git branch -M main
git remote add origin https://github.com/你的用户名/zihao-workbench.git
git push -u origin main
```

> 如果用 HTTPS 推送需要输入 GitHub 用户名和 Token（不是密码）。
> Token 在 [github.com/settings/tokens](https://github.com/settings/tokens) 生成，勾选 `repo` 权限。

### 3. 开启 GitHub Pages

进入仓库 → **Settings** → **Pages** → **Source** 选 `Deploy from a branch` → 分支选 `main`、文件夹选 `/ (root)` → **Save**。

等待 1-2 分钟，访问地址：`https://你的用户名.github.io/zihao-workbench/`

### 4. 配置仓库地址

打开 `index.html`，找到这一行，填入你的仓库地址：

```js
const GITHUB_REPO = "你的用户名/zihao-workbench";
```

改完 commit push 一次。

### 5. 生成初始热榜数据

进入仓库 → **Actions** → 左侧选 `Update Hot Topics` → 右侧 `Run workflow` → 点绿色按钮运行。

运行完成后会自动 commit 新的 `data/hot_videos.json`，刷新页面即可看到数据。

以后热榜数据每天北京时间 8:00 自动更新，也可以随时手动 Run workflow。

## 功能模块

| 模块 | 说明 |
|------|------|
| 每日任务 | 必做5+选做5，可增删，勾选存浏览器 |
| 表达练习 | 7个主题每天轮换，3个抖音热点素材 |
| 今日复盘 | 做了什么/优化什么/下次怎么做 |
| 灵感来源 | 每日创意灵感卡片 |

## 本地运行（可选）

如果想在本地运行（带实时爬虫）：

```bash
python start.py
```

浏览器打开 `http://127.0.0.1:8766`，手机同 WiFi 访问 `http://你的局域网IP:8766`。

## 说明

- 任务勾选和复盘内容存在浏览器 localStorage，手机和电脑各自独立
- 热榜数据通过 GitHub Actions 更新，存在仓库里，所有设备共享
- 抖音热榜 API 可能偶尔不稳定，数据会保留上次成功的结果
