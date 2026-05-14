# AITools

一个集成多个实用 AI 工具的 Python 项目，包括自然语言转 SQL 查询和社交媒体视频下载功能。

## 📋 目录

- [项目概述](#项目概述)
- [主要功能](#主要功能)
- [项目结构](#项目结构)
- [技术栈](#技术栈)
- [安装要求](#安装要求)
- [使用方法](#使用方法)
- [功能介绍](#功能介绍)
- [贡献指南](#贡献指南)
- [许可证](#许可证)

## 项目概述

AITools 是一个开源项目，致力于提供实用的人工智能工具集。通过集成先进的 AI 技术，为用户提供便捷的功能，包括自然语言处理和媒体下载等服务。

## 主要功能

✨ **多功能集成** - 集合了多个实用工具  
🔧 **易于使用** - 简洁的接口设计  
⚙️ **可扩展性** - 模块化架构，便于扩展  
🐍 **Python 开发** - 100% Python 实现  

## 项目结构

```
AITools/
├── NL2SQL/                    # 自然语言转 SQL 工具
│   ├── gradio_app.py          # Gradio Web 应用主入口
│   ├── sql_test.sql           # 测试数据与表结构
│   └── README.md              # NL2SQL 详细文档
├── SocialVideoDownloader/     # 社交媒体视频下载器
│   ├── douyin_downloader_llm.py       # 抖音下载器
│   ├── xiaohongshu_downloader_llm.py  # 小红书下载器
│   ├── bilibili_downloader_llm.py     # B站下载器
│   └── README.md                      # 下载器详细文档
└── README.md                  # 本文件
```

## 技术栈

### 核心技术

| 技术 | 用途 | 版本要求 |
|------|------|---------|
| **Python** | 主编程语言 | 3.8+ |
| **Gradio** | Web UI 框架 | 最新 |
| **Ollama** | 本地 LLM 推理 | 最新 |
| **MySQL** | 数据库系统 | 5.7+ |

### 依赖库

**NL2SQL 模块：**
- `gradio` - 快速构建 Web 应用
- `requests` - HTTP 请求库
- `pymysql` - MySQL 数据库连接
- `dbutils` - 数据库连接池管理

**SocialVideoDownloader 模块：**
- `yt-dlp` - 多平台视频下载
- `playwright` - 浏览器自动化
- `requests` - HTTP 请求

**LLM 集成：**
- `Ollama` (本地模型)
- `OpenAI` 兼容 API (备选方案)

### NL2SQL

#### 功能概述
将自然语言查询转换为 SQL 语句的工具。基于本地 Ollama LLM，使用 Gradio 提供 Web 用户界面。

#### 主要特性：

🎯 **自然语言理解**
- 支持中文查询输入
- 智能解析用户意图
- 上下文感知的查询转换

⚙️ **SQL 生成**
- 自动生成 MySQL SELECT 查询语句
- 支持复杂查询（JOIN、GROUP BY、ORDER BY 等）
- 流式输出 LLM 思考过程

🛡️ **安全优先**
- 仅允许 SELECT 查询
- 防止 SQL 注入攻击
- 保护数据库免受破坏性操作

📊 **数据库集成**
- 自动获取数据库表结构
- 支持多表联合查询
- 格式化的查询结果可视化展示

#### 技术实现

```python
# 系统架构组件
├── LLM 推理引擎 (Ollama - qwen3:8b)
├── 数据库连接池 (dbutils)
├── SQL 验证器 (正则表达式)
├── Web UI (Gradio)
└── 结果格式化器
```

#### 支持的数据库操作

- ✅ SELECT 基础查询
- ✅ WHERE 条件过滤
- ✅ JOIN 多表关联
- ✅ GROUP BY 分组统计
- ✅ ORDER BY 排序
- ✅ LIMIT 限制结果数
- ✅ 聚合函数 (COUNT, SUM, AVG, MAX, MIN)

### SocialVideoDownloader

从社交媒体平台下载视频的工具。

**支持平台：**
- 🎵 抖音 (Douyin)
- 🌟 小红书 (Xiaohongshu)
- 🎬 哔哩哔哩 (Bilibili)

**主要特性：**
- 支持短链接解析（v.douyin.com、xhslink.com、b23.tv）
- 支持从分享文本自动提取链接
- 主流方式使用 yt-dlp/Playwright 下载
- 备用方案：LLM 分析页面结构
- 提供反爬绕过建议
- 高效的下载管理
- 灵活的视频格式选择

## 安装要求

- Python 3.8 或更高版本
- pip 包管理器
- MySQL 5.7+ (用于 NL2SQL)
- Ollama (用于本地 LLM 推理)

## 使用方法

### 基本安装

```bash
# 克隆仓库
git clone https://github.com/zyzy898/AITools.git
cd AITools

# 安装依赖
pip install -r requirements.txt

# 对于 Playwright
playwright install chromium
```

### NL2SQL 使用示例

```bash
# 启动 Web 应用
python NL2SQL/gradio_app.py
```

然后访问 `http://127.0.0.1:7860` 即可使用。

**示例查询：**
```
用户输入: "查询所有用户的名字和邮箱"
生成 SQL: SELECT name, email FROM users;

用户输入: "查询成绩大于80分的学生"
生成 SQL: SELECT * FROM students WHERE score > 80;

用户输入: "统计每个班级的平均分"
生成 SQL: SELECT class_id, AVG(score) FROM students GROUP BY class_id;
```

### SocialVideoDownloader 使用示例

```python
# 抖音下载
python SocialVideoDownloader/douyin_downloader_llm.py "https://v.douyin.com/Ksb4dKSz9y0/" my_video.mp4

# 小红书下载
python SocialVideoDownloader/xiaohongshu_downloader_llm.py "https://www.xiaohongshu.com/explore/699473ba000000001d02758e"

# B 站下载
python SocialVideoDownloader/bilibili_downloader_llm.py "https://b23.tv/FwARg66"

# 禁用 LLM 备用方案
python SocialVideoDownloader/douyin_downloader_llm.py <URL> --no-llm
```

## 功能介绍

### NL2SQL 工具工作流程

```
┌─────────────────┐
│  用户输入       │ "查询所有活跃用户"
│  (自然语言)     │
└────────┬────────┘
         │
         ▼
┌─────────────────────┐
│  数据库架构分析      │ 获取表结构、字段类型
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  Ollama LLM 推理     │ 理解查询意图
└────────┬────────────┘ 生成 SQL 语句
         │
         ▼
┌─────────────────────┐
│  SQL 验证与安全检查  │ 仅允许 SELECT
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  执行数据库查询      │ MySQL 查询执行
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  结果格式化显示      │ 表格化展示结果
└─────────────────────┘
```

### SocialVideoDownloader 工具工作流程

```
┌────────────────────┐
│  输入视频链接       │
└────────┬───────────┘
         │
         ▼
┌────────────────────────┐
│  链接格式识别          │ 检测短链/长链
└────────┬───────────────┘
         │
         ▼
┌────────────────────────────┐
│  方案1: yt-dlp/Playwright  │ 主流下载方式
└────────┬────────────────────┘
         │
    成功├─────► 下载完成
         │
    失败│
         ▼
┌────────────────────────────┐
│  方案2: LLM 页面分析       │ 备用方案
│  - 分析HTML结构           │
│  - 提取视频URL模式        │
│  - 反爬绕过建议           │
└────────┬────────────────────┘
         │
         ▼
┌────────────────────┐
│  下载完成          │
└────────────────────┘
```

## 贡献指南

欢迎贡献！请遵循以下步骤：

1. Fork 本仓库
2. 创建你的特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交你的改动 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启一个 Pull Request

## 常见问题

**Q: 如何报告 bug？**  
A: 请在 Issues 中创建新的 issue，详细描述问题和复现步骤。

**Q: 我可以在生产环境中使用这个项目吗？**  
A: 可以，但请根据你的具体需求进行测试和调整。

**Q: NL2SQL 支持哪些数据库？**  
A: 目前主要支持 MySQL，后续会扩展 PostgreSQL 等数据库支持。

**Q: 可以离线使用吗？**  
A: 可以。NL2SQL 使用 Ollama 本地模型，SocialVideoDownloader 依赖不需要云服务。

## 更新日志

### v0.1.0 (2026-05-11)
- 🎉 项目初始化
- ✨ 添加 NL2SQL 模块（Ollama + Gradio + MySQL）
- ✨ 添加 SocialVideoDownloader 模块（支持抖音、小红书、B站）
- 📚 完善项目文档

## 联系方式

- GitHub: [@zyzy898](https://github.com/zyzy898)
- Issues: [提交问题](https://github.com/zyzy898/AITools/issues)

## 许可证

本项目采用开源许可证发布。详见 LICENSE 文件。

---

**最后更新**: 2026-05-11

如有任何问题或建议，欢迎提交 Issue 或 Pull Request！
