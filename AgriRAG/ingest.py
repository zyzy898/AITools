import os
import re
import argparse
import config
import models
import milvus_client


def chunk_text(text, chunk_size=300, overlap=50):
    """滑动窗口切分文本，保证 overlap 生效"""
    text = re.sub(r'\n+', '\n', text).strip()
    if not text:
        return []
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start = end - overlap

    return chunks


def load_knowledge_files():
    documents = []
    knowledge_dir = config.KNOWLEDGE_DIR

    if not os.path.exists(knowledge_dir):
        print(f"知识目录不存在: {knowledge_dir}")
        return documents

    for filename in os.listdir(knowledge_dir):
        if filename.endswith(".txt"):
            filepath = os.path.join(knowledge_dir, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                text = f.read()
            chunks = chunk_text(text)
            for chunk in chunks:
                documents.append({
                    "text": chunk,
                    "source": filename
                })
            print(f"已加载 {filename}: {len(chunks)} 个文本块")

    return documents


def ingest(reset=False):
    print("正在加载知识文档...")
    documents = load_knowledge_files()
    if not documents:
        print("没有找到知识文档")
        return

    print(f"共 {len(documents)} 个文档块，正在生成 Embedding...")

    texts = [doc["text"] for doc in documents]
    embeddings = models.encode_texts(texts)

    docs_with_embeddings = []
    for i, doc in enumerate(documents):
        doc["embedding"] = embeddings[i].tolist()
        docs_with_embeddings.append(doc)

    print("正在存储到 Milvus...")
    if reset:
        milvus_client.reset_collection()
    else:
        milvus_client.create_collection()

    count = milvus_client.insert_documents(docs_with_embeddings)
    print(f"入库完成，新增 {count} 个文档块")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="知识入库工具")
    parser.add_argument("--reset", action="store_true", help="清空旧数据后重新入库")
    args = parser.parse_args()
    ingest(reset=args.reset)
