# 自然语言转 SQL 查询系统

[![Python 版本](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/)
[![许可证](https://img.shields.io/badge/license-MIT-green)](LICENSE)

> 基于 Gradio 的 Web 应用，使用本地 Ollama LLM 将中文自然语言转换为 MySQL SELECT 查询语句。

## 目录

- [功能特点](#功能特点)
- [环境要求](#环境要求)
- [安装](#安装)
- [配置](#配置)
  - [数据库配置](#数据库配置)
  - [Ollama 配置](#ollama-配置)
- [项目结构](#项目结构)
- [使用](#使用)
- [测试数据](#测试数据)
- [示例查询](#示例查询)
- [常见问题](#常见问题)

## 功能特点

- 将中文自然语言转换为 SQL SELECT 查询语句
- 流式输出 LLM 思考过程
- **安全优先设计**：仅允许 SELECT 查询，保护数据库免受破坏性操作
- 自动获取数据库表结构
- 格式化的查询结果可视化展示

## 环境要求

| 组件 | 版本 | 说明 |
|------|------|------|
| Python | 3.8+ | 运行环境 |
| MySQL | 5.7+ | 目标数据库 |
| Ollama | 最新版 | 本地 LLM 运行时 |

## 安装

```bash
pip install gradio requests pymysql dbutils
```

## 配置

### 数据库配置

在 `gradio_app.py` 中修改数据库连接设置：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| host | string | （空） | 数据库主机 |
| user | string | （空） | 数据库用户名 |
| password | string | （空） | 数据库密码 |
| database | string | （空） | 数据库名称 |
| port | int | 3306 | 连接端口 |
| charset | string | utf8mb4 | 字符编码 |

```python
DB_CONFIG = {
    "host": "localhost",
    "user": "your_user",
    "password": "your_password",
    "database": "your_database",
    "port": 3306,
    "charset": "utf8mb4",
}
```

### Ollama 配置

确保本地运行 Ollama 并加载模型：

```bash
ollama run qwen3:8b
```

或在 `gradio_app.py` 中修改模型配置：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| OLLAMA_MODEL | qwen3:8b | LLM 模型名称 |
| OLLAMA_URL | http://localhost:11434/api/generate | API 端点 |

## 项目结构

```
NL2SQL/
├── gradio_app.py      # 主应用入口
├── sql_test.sql       # 测试数据与表结构
└── README.md          # 本文件
```

## 使用

```bash
python gradio_app.py
```

访问 `http://127.0.0.1:7860` 即可使用。

## 测试数据

`sql_test.sql` 包含以下测试表：

| 表名 | 说明 |
|------|------|
| users | 用户信息表 |
| student_scores | 学生成绩表 |
| family_contact | 家庭联系方式表 |
| physical_condition | 身体状况表 |

## 示例查询

- 查询语文成绩大于 80 分的学生姓名和总分
- 查询物理成绩最高的 5 名学生
- 查找体脂率大于 20% 的男生
- 统计每个学科的平均分
- 查询王强家的联系电话

## 常见问题

**问：为什么只允许 SELECT 查询？**

答：安全是首要考量。由于系统处理自然语言输入，存在注入风险。限制为 SELECT-only 查询确保用户只能查询数据，无法修改或删除任何内容。

**问：可以使用其他 LLM 模型吗？**

答：可以，只需确保你的 Ollama 实例已下载该模型且 API 端点兼容。

**问：系统如何获取表结构？**

答：系统自动查询 `INFORMATION_SCHEMA` 获取表和列的元数据，使 LLM 能基于实际数据库结构生成准确的查询语句。