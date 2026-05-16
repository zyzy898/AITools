import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Milvus 配置（支持环境变量覆盖）
MILVUS_HOST = os.environ.get("MILVUS_HOST", "127.0.0.1")
MILVUS_PORT = int(os.environ.get("MILVUS_PORT", 19530))
MILVUS_URI = f"http://{MILVUS_HOST}:{MILVUS_PORT}"

COLLECTION_NAME = "agriculture_knowledge"

# Embedding 模型
EMBEDDING_MODEL_PATH = os.path.join(BASE_DIR, "Qwen3-Embedding-0.6B")
EMBEDDING_DIM = 768

# LLM 配置
LLM_MODE = os.environ.get("LLM_MODE", "api")  # "local" 或 "api"

# 本地模型配置
LLM_MODEL_PATH = os.path.join(BASE_DIR, "llama-model")
LLM_MAX_LENGTH = 512
LLM_TOP_P = 0.9
LLM_TOP_K = 40
LLM_TEMPERATURE = 0.7

# API 模式配置（兼容 OpenAI 接口格式）
LLM_API_URL = os.environ.get("LLM_API_URL", "http://localhost:8000/v1/chat/completions")
LLM_API_KEY = os.environ.get("LLM_API_KEY", "")
LLM_API_MODEL = os.environ.get("LLM_API_MODEL", "qwen")
LLM_API_STREAM = True  # API 模式是否启用流式输出

# 知识库
KNOWLEDGE_DIR = os.path.join(BASE_DIR, "database_dir", "农业", "txt")

# 检索参数
TOP_K = 5
SIMILARITY_THRESHOLD = 0.5  # 低于此分数的检索结果不纳入上下文

PROMPT_TEMPLATE = """请根据以下知识回答用户问题。如果知识不足以回答，可以说明不知道。

知识：
{context}

用户问题：{question}

答案："""
