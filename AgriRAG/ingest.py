import os
import re
import argparse
import config
import models
import milvus_client


def chunk_text(text, chunk_size=512, overlap=64):
    """动态切割：递归按段落→句子→子句边界切分，避免截断语义"""
    text = re.sub(r'\n{3,}', '\n\n', text).strip()
    if not text:
        return []
    if len(text) <= chunk_size:
        return [text]

    separators = ["\n\n", "\n", "。", "！", "？", "；", "：", "，", "、", " ", ""]
    splits = _recursive_split(text, separators, chunk_size)
    return _merge_with_overlap(splits, chunk_size, overlap)


def _recursive_split(text, separators, chunk_size):
    """递归切分：尝试用当前分隔符切分，超长部分递归用下一级分隔符"""
    if not separators:
        return [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]

    sep = separators[0]
    if sep and sep not in text:
        return _recursive_split(text, separators[1:], chunk_size)

    if not sep:
        return [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]

    parts = text.split(sep)
    result = []
    current = ""

    for part in parts:
        if not part:
            continue
        candidate = (current + sep + part) if current else part
        if len(candidate) <= chunk_size:
            current = candidate
        else:
            if current:
                result.append(current)
            if len(part) <= chunk_size:
                current = part
            else:
                result.extend(_recursive_split(part, separators[1:], chunk_size))
                current = ""

    if current:
        result.append(current)

    return result


def _merge_with_overlap(splits, chunk_size, overlap):
    """合并过短的相邻片段，并在相邻块之间添加重叠"""
    if not splits:
        return []

    merged = []
    current = splits[0]
    for i in range(1, len(splits)):
        nxt = splits[i]
        if len(current) + len(nxt) + 1 <= chunk_size:
            current += "\n" + nxt
        else:
            merged.append(current)
            current = nxt
    merged.append(current)

    if overlap <= 0 or len(merged) <= 1:
        return merged

    overlapped = [merged[0]]
    for i in range(1, len(merged)):
        prev = merged[i - 1]
        prefix = prev[-overlap:] if len(prev) > overlap else prev
        overlapped.append(prefix + "\n" + merged[i])

    return overlapped


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
