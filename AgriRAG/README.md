# AgriRAG — 农业领域知识问答系统

基于 **RAG（Retrieval-Augmented Generation）** 架构的垂直领域智能问答系统，面向农业知识场景，实现从文档入库、向量检索到大模型生成的完整链路。

## 技术架构

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  知识文档     │────▶│  文本切分     │────▶│  Embedding   │
│  (.txt)      │     │  动态递归     │     │  Qwen3-Emb   │
└──────────────┘     └──────────────┘     └──────┬───────┘
                                                  │
                                                  ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  LLM 生成    │◀────│  Prompt 组装  │◀────│  Milvus      │
│  API/Local   │     │  上下文拼接   │     │  向量检索     │
└──────────────┘     └──────────────┘     └──────────────┘
```

## 核心技术点

- **RAG 检索增强生成**：将外部知识库与大模型结合，解决 LLM 幻觉和知识时效性问题
- **向量数据库 Milvus**：高性能向量存储与 ANN 近似最近邻检索，支持 COSINE 相似度
- **Qwen3 Embedding 模型**：使用 `Qwen3-Embedding-0.6B` 中文语义向量化，1024 维稠密表示
- **动态递归文本切分**：段落→句子→子句边界感知切分，动态调整块大小保持语义完整，带 overlap 上下文重叠
- **内容哈希去重**：基于 MD5 的确定性 ID 生成，支持增量入库不重复
- **相似度阈值过滤**：检索结果低于阈值自动丢弃，减少噪声对生成质量的影响
- **双模式 LLM 推理**：支持本地模型（transformers）和 OpenAI 兼容 API，灵活切换
- **SSE 流式输出**：API 模式支持 Server-Sent Events 流式响应，逐 token 输出
- **批量 Embedding 生成**：分 batch 处理避免 OOM，带实时进度显示

## 项目结构

```
AgriRAG/
├── config.py              # 全局配置（支持环境变量热切换）
├── models.py              # 模型层：Embedding + LLM（API/本地双模式）
├── milvus_client.py       # 数据层：Milvus 向量库 CRUD 封装
├── ingest.py              # 入库管线：文档加载 → 切分 → 向量化 → 存储
├── query.py               # 查询管线：问题 → 检索 → 生成 → 输出
├── requirements.txt       # Python 依赖
├── database_dir/          # 知识库文档目录
│   └── 农业/txt/          # 农业领域知识文本
└── Qwen3-Embedding-0.6B/      # Embedding 模型（本地部署）
```

## 环境要求

- Python 3.8+
- Milvus 2.3+ 向量数据库
- PyTorch / Transformers
- （可选）GPU 用于本地模型推理

## 快速开始

```bash
# 安装依赖
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

## 配置说明

支持通过环境变量或直接编辑 `config.py` 进行配置：

| 配置项 | 环境变量 | 默认值 | 说明 |
|--------|----------|--------|------|
| Milvus 地址 | `MILVUS_HOST` | 127.0.0.1 | 向量数据库地址 |
| Milvus 端口 | `MILVUS_PORT` | 19530 | 向量数据库端口 |
| LLM 模式 | `LLM_MODE` | local | `local` 或 `api` |
| API 地址 | `LLM_API_URL` | localhost:8000 | OpenAI 兼容接口 |
| API Key | `LLM_API_KEY` | - | API 密钥 |
| API 模型 | `LLM_API_MODEL` | qwen | 模型名称 |
| 相似度阈值 | - | 0.5 | 低于此值的检索结果被过滤 |
| 流式输出 | - | True | API 模式逐 token 输出 |

## 设计亮点

1. **模块化分层**：配置层 / 模型层 / 数据层 / 业务层职责清晰，易于扩展
2. **增量入库 + 去重**：生产环境可反复执行入库脚本，不会产生冗余数据
3. **双模式推理**：开发阶段用 API 快速迭代，部署时可切换本地模型降低成本
4. **可观测性**：检索分数可视化 + 耗时统计，便于调优 chunk_size、top_k 等参数
5. **容错处理**：Milvus 连接检测、模型加载校验、API 超时重试，不会因单点故障崩溃
