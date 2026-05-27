# AITools

一个集成多个实用 AI 工具和智能体的项目，覆盖智能财务分析、自然语言转 SQL 查询和社交媒体视频下载功能。

## 📋 目录

- [项目概述](#项目概述)
- [主要功能](#主要功能)
- [项目结构](#项目结构)
- [技术栈](#技术栈)
- [模块详情](#模块详情)
  - [FinGuard Agent — 智能财报审查智能体](#finguard-agent--智能财报审查智能体)
  - [NL2SQL — 自然语言转 SQL](#nl2sql---自然语言转-sql)
  - [SocialVideoDownloader — 社交视频下载器](#socialvideodownloader---社交视频下载器)
- [安装与使用](#安装与使用)
- [常见问题](#常见问题)
- [更新日志](#更新日志)
- [贡献指南](#贡献指南)
- [许可证](#许可证)

## 项目概述

AITools 是一个开源项目，致力于提供实用的人工智能工具集。通过集成 Dify 工作流、大语言模型推理、结构化数据提取等技术，为用户提供 AI 应用覆盖财报审查、数据库查询和媒体下载等场景。

## 主要功能

| 模块 | 功能 | 核心技术 |
|------|------|----------|
| **FinGuard Agent** | 智能财务报告审查 | Dify 工作流 + LLM 财报数据提取 + AI 风控诊断 |
| **NL2SQL** | 自然语言转 SQL 查询 | Ollama LLM + Gradio + MySQL |
| **SocialVideoDownloader** | 社交媒体视频下载 | yt-dlp + Playwright + LLM |

## 项目结构

```
AITools/
├── FinGuard Agent/                 # 智能财报审查智能体
│   └── 公司财报审查.yml               # Dify 工作流配置文件
├── NL2SQL/                         # 自然语言转 SQL 工具
│   ├── gradio_app.py               # Gradio Web 应用主入口
│   ├── sql_test.sql                # 测试数据与表结构
│   └── README.md                   # 模块详细文档
├── SocialVideoDownloader/          # 社交媒体视频下载器
│   ├── douyin_downloader_llm.py    # 抖音下载器
│   ├── xiaohongshu_downloader_llm.py  # 小红书下载器
│   ├── bilibili_downloader_llm.py  # B站下载器
│   └── README.md                   # 模块详细文档
└── README.md                       # 本文件
```

## 技术栈

### 核心技术

| 技术 | 用途 | 版本要求 |
|------|------|---------|
| Python | 主编程语言 | 3.8+ |
| Gradio | Web UI 框架 | 最新 |
| Ollama | 本地 LLM 推理 | 最新 |
| MySQL | 关系型数据库 | 5.7+ |
| yt-dlp / Playwright | 视频下载与浏览器自动化 | 最新 |
| Dify | AI 工作流编排平台 | 0.6+ |

### LLM 集成方式

- **Ollama** — 本地模型推理（NL2SQL 模块）
- **OpenAI 兼容 API** — 远程/本地 API 调用（SocialVideoDownloader）
- **Dify 工作流** — 可视化编排 LLM 调用链（FinGuard Agent）

---

## 模块详情

### FinGuard Agent — 智能财报审查智能体

基于 **Dify 工作流** 的自动化企业财务报表审查系统。上传财报文档即可自动提取关键财务数据，并由 CFO 角色 LLM 进行深度风控诊断。

#### 核心工作流程

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  上传财报     │────▶│  文档提取器    │────▶│  LLM 1       │────▶│  LLM 2       │
│  (PDF/DOCX)  │     │  解析文本      │     │  财务数据     │     │  风控诊断     │
│              │     │              │     │  结构化提取    │     │  生成报告     │
└──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
```

- **LLM 1（数据提取）** — 从财报文本中提取营收、净利润、现金流等核心指标，自动处理单位转换、符号识别、报表口径选择
- **LLM 2（风控诊断）** — 以 CFO 角色分析数据，输出包含成长性、现金流、偿债能力、风险因子的结构化风控报告

#### 技术架构

- **Dify 工作流** — 可视化编排 AI 流程，支持文档上传、多节点 LLM 调用
- **文档提取器** — 自动解析 PDF/DOCX 格式的财报文件

#### 快速使用

1. 将 `FinGuard Agent/公司财报审查.yml` 导入 Dify 平台
2. 配置火山引擎 API Key 和模型端点
3. 发布为 Web 应用后即可使用

---

### NL2SQL — 自然语言转 SQL

将中文自然语言查询转换为 MySQL SELECT 语句的 Web 应用，基于本地 Ollama LLM。

#### 工作流程

```
用户输入（自然语言）
    │
    ▼
数据库架构分析（INFORMATION_SCHEMA）
    │
    ▼
Ollama LLM 推理（qwen3:8b）
    │
    ▼
SQL 验证与安全检查（仅允许 SELECT）
    │
    ▼
执行查询 → 格式化结果展示
```

#### 核心特性

- 中文自然语言理解，智能解析查询意图
- 支持复杂查询（JOIN、GROUP BY、ORDER BY、聚合函数）
- 安全优先 — 仅允许 SELECT，防止 SQL 注入
- 自动获取表结构，格式化结果可视化
- 流式输出 LLM 思考过程

#### 快速使用

```bash
# 安装依赖
pip install gradio requests pymysql dbutils

# 确保 Ollama 已运行
ollama run qwen3:8b

# 启动应用
python NL2SQL/gradio_app.py
```

访问 `http://127.0.0.1:7860` 即可使用。

#### 示例查询

```
输入: "查询所有用户的名字和邮箱"
SQL:  SELECT name, email FROM users;

输入: "统计每个班级的平均分"
SQL:  SELECT class_id, AVG(score) FROM students GROUP BY class_id;

输入: "查询物理成绩最高的5名学生"
SQL:  SELECT * FROM student_scores WHERE subject='物理' ORDER BY score DESC LIMIT 5;
```

---

### SocialVideoDownloader — 社交视频下载器

支持抖音、小红书、哔哩哔哩的 AI 智能视频下载工具。**yt-dlp 优先，失败后 Playwright + LLM 兜底二次提取下载**。

#### 支持平台

| 平台 | 脚本 | 短链支持 | 主下载 | 回退 |
|------|------|----------|--------|------|
| 抖音 | `douyin_downloader_llm.py` | v.douyin.com | yt-dlp | Playwright 拦截 + HTML 解析 + LLM 正则提取 |
| 小红书 | `xiaohongshu_downloader_llm.py` | xhslink.com | yt-dlp | Playwright 获取页面 + LLM 正则提取 |
| 哔哩哔哩 | `bilibili_downloader_llm.py` | b23.tv | yt-dlp | Playwright 获取页面 + LLM 正则提取 |

#### 核心特性

- **yt-dlp 优先** — 三个平台统一先调 yt-dlp，成功即止，Playwright 不加载
- **LLM 二次下载** — yt-dlp 失败后 Playwright 获取页面源码，LLM 返回 URL 提取模式，正则匹配后 `requests` 直链下载
- **JSON 校验自动重试** — LLM 返回的 JSON 格式错误时，将具体错误原因反馈给 LLM 修正，最多重试 3 次
- **短链接自动解析** — 支持分享文本提取、短链跳转
- **可选禁用** — `--no-llm` 关闭 LLM 备用方案

#### 快速使用

```bash
# 安装依赖
pip install yt-dlp playwright requests
playwright install chromium

# 抖音下载
python SocialVideoDownloader/douyin_downloader_llm.py "https://v.douyin.com/Ksb4dKSz9y0/" my_video.mp4

# 小红书下载
python SocialVideoDownloader/xiaohongshu_downloader_llm.py "https://www.xiaohongshu.com/explore/699473ba000000001d02758e"

# B站下载
python SocialVideoDownloader/bilibili_downloader_llm.py "https://b23.tv/FwARg66"

# 禁用 LLM 备用方案
python SocialVideoDownloader/douyin_downloader_llm.py <URL> --no-llm
```

#### LLM 配置

编辑各脚本中的配置部分：

```python
LLM_API_KEY = "your-api-key"
LLM_BASE_URL = "your-api-base-url"
LLM_MODEL = "your-model-name"
```

支持 OpenAI 兼容格式的 API。

---

## 安装与使用

### 环境要求

- Python 3.8+
- pip 包管理器
- MySQL 5.7+（NL2SQL 模块）
- Ollama（NL2SQL 模块）
- Dify 平台（FinGuard Agent 模块）

### 快速开始

```bash
# 克隆仓库
git clone https://github.com/zyzy898/AITools.git
cd AITools

# 按模块安装依赖
pip install gradio requests pymysql dbutils
pip install yt-dlp playwright requests
playwright install chromium
```

各模块独立运行，按需选择即可。

## 常见问题

**Q: NL2SQL 支持哪些数据库？**  
A: 目前支持 MySQL，后续计划扩展 PostgreSQL 等。

**Q: FinGuard Agent 如何使用？**  
A: 将 `FinGuard Agent/公司财报审查.yml` 导入 Dify 平台，配置模型提供商后即可发布使用。

**Q: SocialVideoDownloader 下载失败怎么办？**  
A: 系统会依次尝试 yt-dlp → Playwright 提取 → LLM 智能分析。确保 yt-dlp 和 Playwright 正确安装。若仍失败，配置 LLM API 后 LLM 将自动分析页面并尝试二次提取下载。


## 贡献指南

欢迎贡献！请遵循以下步骤：

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交改动 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 联系方式

- GitHub: [@zyzy898](https://github.com/zyzy898)
- Issues: [提交问题](https://github.com/zyzy898/AITools/issues)

## 许可证

本项目采用开源许可证发布。详见 LICENSE 文件。

---

**最后更新**: 2026-05-27
