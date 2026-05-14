# AITools

一个集成多个实用 AI 工具的 Python 项目，包括农业领域 RAG 知识问答、自然语言转 SQL 查询和社交媒体视频下载功能。

## 📋 目录

- [项目概述](#项目概述)
- [主要功能](#主要功能)
- [项目结构](#项目结构)
- [技术栈](#技术栈)
- [模块详情](#模块详情)
  - [AgriRAG - 农业知识问答系统](#agrirag---农业知识问答系统)
  - [NL2SQL - 自然语言转 SQL](#nl2sql---自然语言转-sql)
  - [SocialVideoDownloader - 社交视频下载器](#socialvideodownloader---社交视频下载器)
- [安装与使用](#安装与使用)
- [常见问题](#常见问题)
- [更新日志](#更新日志)
- [贡献指南](#贡献指南)
- [许可证](#许可证)

## 项目概述

AITools 是一个开源项目，致力于提供实用的人工智能工具集。通过集成 RAG 检索增强生成、大语言模型推理、向量数据库检索等技术，为用户提供便捷的 AI 应用，覆盖知识问答、数据库查询和媒体下载等场景。

## 主要功能

| 模块 | 功能 | 核心技术 |
|------|------|----------|
| **AgriRAG** | 农业领域知识问答 | RAG + Milvus + BGE Embedding |
| **NL2SQL** | 自然语言转 SQL 查询 | Ollama LLM + Gradio |
| **SocialVideoDownloader** | 社交媒体视频下载 | yt-dlp + Playwright + LLM |

## 项目结构

```
AITools/
├── AgriRAG/                       # 农业领域 RAG 知识问答系统
│   ├── config.py                  # 全局配置（支持环境变量）
│   ├── models.py                  # 模型层：Embedding + LLM
│   ├── milvus_client.py           # 数据层：Milvus 向量库封装
│   ├── ingest.py                  # 入库管线：文档 → 切分 → 向量化 → 存储
│   ├── query.py                   # 查询管线：问题 → 检索 → 生成
│   ├── requirements.txt           # 依赖清单
│   ├── database_dir/农业/txt/     # 知识库文档
│   ├── bge-base-zh-v1.5/          # Embedding 模型（本地）
│   └── README.md                  # 模块详细文档
├── NL2SQL/                        # 自然语言转 SQL 工具
│   ├── gradio_app.py              # Gradio Web 应用主入口
│   ├── sql_test.sql               # 测试数据与表结构
│   └── README.md                  # 模块详细文档
├── SocialVideoDownloader/         # 社交媒体视频下载器
│   ├── douyin_downloader_llm.py   # 抖音下载器
│   ├── xiaohongshu_downloader_llm.py  # 小红书下载器
│   ├── bilibili_downloader_llm.py # B站下载器
│   └── README.md                  # 模块详细文档
└── README.md                      # 本文件
```

## 技术栈

### 核心技术

| 技术 | 用途 | 版本要求 |
|------|------|---------|
| Python | 主编程语言 | 3.8+ |
| PyTorch / Transformers | 模型推理 | 最新 |
| Milvus | 向量数据库 | 2.3+ |
| Gradio | Web UI 框架 | 最新 |
| Ollama | 本地 LLM 推理 | 最新 |
| MySQL | 关系型数据库 | 5.7+ |
| yt-dlp / Playwright | 视频下载与浏览器自动化 | 最新 |

### LLM 集成方式

- **Ollama** — 本地模型推理（NL2SQL 模块）
- **OpenAI 兼容 API** — 远程/本地 API 调用（AgriRAG、SocialVideoDownloader）
- **Transformers 本地加载** — 直接加载 HuggingFace 模型（AgriRAG 备选）

---

## 模块详情

### AgriRAG — 农业知识问答系统

基于 **RAG（Retrieval-Augmented Generation）** 架构的垂直领域智能问答系统，面向农业知识场景。

#### 技术架构

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  知识文档     │────▶│  文本切分     │────▶│  Embedding   │
│  (.txt)      │     │  滑动窗口     │     │  BGE-zh      │
└──────────────┘     └──────────────┘     └──────┬───────┘
                                                  │
                                                  ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  LLM 生成    │◀────│  Prompt 组装  │◀────│  Milvus      │
│  API/Local   │     │  上下文拼接   │     │  向量检索     │
└──────────────┘     └──────────────┘     └──────────────┘
```

#### 核心特性

- **RAG 检索增强生成** — 外部知识库与大模型结合，解决幻觉和知识时效性问题
- **Milvus 向量检索** — 高性能 ANN 近似最近邻检索，COSINE 相似度
- **BGE-base-zh-v1.5** — 中文语义向量化，768 维稠密表示
- **滑动窗口切分** — 带 overlap 的分块策略，保证语义连贯性
- **内容哈希去重** — MD5 确定性 ID，支持增量入库不重复
- **相似度阈值过滤** — 低于阈值的检索结果自动丢弃
- **双模式 LLM 推理** — 本地模型 / OpenAI 兼容 API 灵活切换
- **SSE 流式输出** — API 模式逐 token 输出

#### 快速使用

```bash
cd AgriRAG
pip install -r requirements.txt

# 知识入库（增量）
python ingest.py

# 清空重建
python ingest.py --reset

# 交互式问答
python query.py

# 单次提问
python query.py 樱桃根系有什么特征？
```

#### 配置说明

| 配置项 | 环境变量 | 默认值 | 说明 |
|--------|----------|--------|------|
| Milvus 地址 | `MILVUS_HOST` | 10.253.205.160 | 向量数据库地址 |
| Milvus 端口 | `MILVUS_PORT` | 19530 | 向量数据库端口 |
| LLM 模式 | `LLM_MODE` | api | `api` 或 `local` |
| API 地址 | `LLM_API_URL` | localhost:8000 | OpenAI 兼容接口 |
| API Key | `LLM_API_KEY` | — | API 密钥 |
| API 模型 | `LLM_API_MODEL` | qwen | 模型名称 |

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

- 🎯 中文自然语言理解，智能解析查询意图
- ⚙️ 支持复杂查询（JOIN、GROUP BY、ORDER BY、聚合函数）
- 🛡️ 安全优先 — 仅允许 SELECT，防止 SQL 注入
- 📊 自动获取表结构，格式化结果可视化
- 🔄 流式输出 LLM 思考过程

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

支持抖音、小红书、哔哩哔哩的 AI 智能视频下载工具。常规方法失败时自动调用 LLM 分析页面结构。

#### 支持平台

| 平台 | 脚本 | 短链支持 |
|------|------|----------|
| 🎵 抖音 | `douyin_downloader_llm.py` | v.douyin.com |
| 🌟 小红书 | `xiaohongshu_downloader_llm.py` | xhslink.com |
| 🎬 哔哩哔哩 | `bilibili_downloader_llm.py` | b23.tv |

#### 核心特性

- 支持短链接解析与分享文本自动提取
- 主流方式：yt-dlp / Playwright 下载
- 备用方案：LLM 分析页面 HTML 结构，提取视频 URL
- 提供反爬绕过建议
- 可通过 `--no-llm` 禁用 LLM 备用方案

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
- Milvus 2.3+（AgriRAG 模块）
- Ollama（NL2SQL 模块）
- GPU（可选，用于本地模型推理加速）

### 快速开始

```bash
# 克隆仓库
git clone https://github.com/zyzy898/AITools.git
cd AITools

# 按模块安装依赖
pip install -r AgriRAG/requirements.txt
pip install gradio requests pymysql dbutils
pip install yt-dlp playwright requests
playwright install chromium
```

各模块独立运行，按需选择即可。

## 常见问题

**Q: 可以离线使用吗？**  
A: 可以。AgriRAG 支持本地 Embedding + 本地 LLM 模式；NL2SQL 使用 Ollama 本地模型；SocialVideoDownloader 下载过程不依赖云服务（LLM 备用方案需要 API）。

**Q: NL2SQL 支持哪些数据库？**  
A: 目前支持 MySQL，后续计划扩展 PostgreSQL 等。

**Q: AgriRAG 如何添加自己的知识库？**  
A: 将 `.txt` 格式的知识文档放入 `AgriRAG/database_dir/农业/txt/` 目录，然后运行 `python ingest.py` 即可增量入库。

**Q: 如何切换 AgriRAG 的 LLM 模式？**  
A: 设置环境变量 `LLM_MODE=local` 使用本地模型，或 `LLM_MODE=api`（默认）使用 OpenAI 兼容 API。

**Q: SocialVideoDownloader 下载失败怎么办？**  
A: 确保 yt-dlp 和 Playwright 已正确安装。如果仍然失败，配置 LLM API 后系统会自动分析页面结构并给出建议。

## 更新日志

### v0.2.0 (2026-05-14)
- ✨ 新增 AgriRAG 模块（RAG + Milvus + BGE Embedding）
- 📚 完善项目文档，补充模块详情

### v0.1.0 (2026-05-11)
- 🎉 项目初始化
- ✨ 添加 NL2SQL 模块（Ollama + Gradio + MySQL）
- ✨ 添加 SocialVideoDownloader 模块（支持抖音、小红书、B站）

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

**最后更新**: 2026-05-14
