import os
import re
import argparse
import config
import models
import milvus_client
from langchain_text_splitters import RecursiveCharacterTextSplitter

SUMMARY_BATCH_SIZE = 10000    # 每批输入字符数
SUMMARY_BATCH_OVERLAP = 300   # 相邻批次重叠字符数（防止断句丢失上下文）
SKIP_SHORT_THRESHOLD = 3000   # 短于此字符数的文档跳过摘要生成


def call_summary_llm(system_prompt, user_prompt, max_tokens=1024):
    """调用 LLM 生成摘要，失败时返回空字符串"""
    try:
        return models.call_llm_api(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.3,
            max_tokens=max_tokens,
            stream=False
        )
    except Exception as e:
        print(f"      [警告] API 调用失败: {e}")
        return ""


def split_text_batches(text, batch_size, overlap):
    """将文本按固定大小分批次，相邻批次有 overlap 字符重叠"""
    batches = []
    start = 0
    while start < len(text):
        end = min(start + batch_size, len(text))
        batches.append(text[start:end])
        if end >= len(text):
            break
        start = end - overlap
    return batches


def summarize_batch(text_batch, source_name, batch_idx, total_batches):
    """为单个文本批次生成短摘要和长摘要，返回合并后的摘要文本"""
    batch_label = f"第{batch_idx}/{total_batches}部分" if total_batches > 1 else ""

    system_short = "你是一个农业知识摘要引擎。只输出摘要文本本身，禁止任何前缀、后缀、解释或客套话。"
    user_short = (
        f"将以下文档{batch_label}总结为一句话（约20字），直接输出结果，不要任何额外文字：\n\n"
        f"{text_batch}"
    )
    short = call_summary_llm(system_short, user_short, max_tokens=128)

    system_long = (
        "你是一个农业知识结构化引擎。只输出markdown摘要内容本身。"
        "禁止输出任何开场白、过渡句、结语或解释，如'好的'、'本部分文档'、'以下是摘要'等。"
        "直接从正文标题开始输出。"
    )
    user_long = (
        f"将以下文档{batch_label}整理为markdown摘要，包含知识要点、分类和关键数据。"
        f"直接从内容开始，不要写任何介绍性或总结性文字：\n\n"
        f"{text_batch}"
    )
    long = call_summary_llm(system_long, user_long, max_tokens=1536)

    if short and long:
        return f"{short}\n\n{long}"
    return short or long or ""


def split_by_sections(text):
    """按章节标题（如 1.1 根系特征、4.1.1 叶斑病）分段，保持每个知识点完整"""
    pattern = r'^\d+\.\d+(?:\.\d+)*\s*\S'
    matches = list(re.finditer(pattern, text, flags=re.MULTILINE))
    if not matches:
        return [text.strip()] if text.strip() else []

    sections = []
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        section = text[start:end].strip()
        if section:
            sections.append(section)

    if matches and matches[0].start() > 0:
        prefix = text[:matches[0].start()].strip()
        if prefix:
            sections.insert(0, prefix)

    return sections


def chunk_with_langchain(text):
    """
    先按章节标题分段，自动追踪层级关系，为子章节补充父章节名称，
    再用 LangChain 切割过长段落。保证每个块都带有完整的上下文标识。
    """
    sections = split_by_sections(text)
    if not sections:
        return []

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=config.CHUNK_SIZE,
        chunk_overlap=config.CHUNK_OVERLAP,
        separators=["\n\n", "\n", "。", "！", "？", "；", "：", "，", " ", ""],
        length_function=len,
    )

    chunks = []
    context_stack = []  # [(level, title, top_level_num), ...]
    HEADER_RE = re.compile(r'^(\d+(?:\.\d+)*)\s*(\S.*)')

    for section in sections:
        first_line = section.split('\n')[0].strip()
        m = HEADER_RE.match(first_line)
        if m:
            number = m.group(1)
            level = number.count('.') + 1
            title = m.group(2) if m.group(2) else first_line
            top_num = number.split('.')[0]

            if context_stack and context_stack[0][2] != top_num:
                context_stack.clear()

            while context_stack and context_stack[-1][0] >= level:
                context_stack.pop()
            context_stack.append((level, title, top_num))

        if context_stack:
            prefix = " > ".join(t for _, t, _ in context_stack)
        else:
            prefix = ""

        content = section if not prefix else f"【{prefix}】\n{section}"

        if len(content) <= config.CHUNK_SIZE:
            chunks.append(content)
        else:
            sub_chunks = splitter.split_text(content)
            for sub in sub_chunks:
                if prefix and not sub.strip().startswith("【"):
                    chunks.append(f"【{prefix}】\n{sub}")
                else:
                    chunks.append(sub)

    return chunks


def load_and_process_knowledge_files():
    """
    加载知识文件，对每个文件：
    - 短文档（<3000字）：跳过摘要，直接切割入库
    - 长文档：分批生成短+长摘要 → 嵌入相似度去重 → 短摘要用于检索嵌入，长摘要用于展示
    - 原文 LangChain 切割入库，确保精确检索
    """
    documents = []
    knowledge_dir = config.KNOWLEDGE_DIR
    summary_dir = os.path.join(os.path.dirname(knowledge_dir), "summary")
    os.makedirs(summary_dir, exist_ok=True)

    if not os.path.exists(knowledge_dir):
        print(f"知识目录不存在: {knowledge_dir}")
        return documents

    for filename in sorted(os.listdir(knowledge_dir)):
        if not filename.endswith(".txt"):
            continue

        filepath = os.path.join(knowledge_dir, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            original_text = f.read().strip()

        if not original_text:
            print(f"跳过空文件: {filename}")
            continue

        print(f"\n{'=' * 50}")
        print(f"处理: {filename} ({len(original_text)} 字符)")

        # 短文档：跳过 LLM 摘要生成，原文直接作为摘要内容
        if len(original_text) < SKIP_SHORT_THRESHOLD:
            print(f"  短文档（<{SKIP_SHORT_THRESHOLD}字），跳过LLM摘要，原文直接写入summary")
            merged_summary = f"## {filename}\n\n{original_text}"
        else:
            # 长文档：分批生成摘要
            batches = split_text_batches(original_text, SUMMARY_BATCH_SIZE, SUMMARY_BATCH_OVERLAP)
            print(f"  文本分割为 {len(batches)} 批 "
                  f"(每批≤{SUMMARY_BATCH_SIZE}字，重叠{SUMMARY_BATCH_OVERLAP}字)")

            batch_summaries = []
            for i, batch_text in enumerate(batches):
                print(f"    处理第 {i+1}/{len(batches)} 批 ({len(batch_text)} 字符)...")
                merged = summarize_batch(batch_text, filename, i + 1, len(batches))
                if merged:
                    batch_summaries.append(merged)

            # 直接拼接所有批次摘要（不做去重避免误杀）
            if len(batch_summaries) == 1:
                merged_summary = batch_summaries[0]
            else:
                parts = [f"## {filename}"]
                for i, s in enumerate(batch_summaries):
                    parts.append(f"\n### 第{i + 1}部分\n{s}")
                merged_summary = "\n\n".join(parts)
            print(f"  最终摘要: {len(merged_summary)} 字符")

        # 保存摘要
        if merged_summary:
            summary_path = os.path.join(summary_dir, filename.replace(".txt", "_summary.md"))
            with open(summary_path, "w", encoding="utf-8") as f:
                f.write(merged_summary)
            print(f"  摘要已保存: {summary_path}")

        # 原文块：LangChain 切割，用原文做嵌入（精确检索）
        original_chunks = chunk_with_langchain(original_text)
        print(f"  原文切割为 {len(original_chunks)} 个文本块")

        for chunk in original_chunks:
            documents.append({"text": chunk, "source": filename})

        # LLM摘要：短摘要直接入库，长摘要用 RecursiveCharacterTextSplitter 简单切割
        if merged_summary:
            if len(merged_summary) <= config.CHUNK_SIZE:
                summary_chunks = [merged_summary]
            else:
                simple_splitter = RecursiveCharacterTextSplitter(
                    chunk_size=config.CHUNK_SIZE,
                    chunk_overlap=config.CHUNK_OVERLAP,
                    separators=["\n\n", "\n", "。", "！", "？", "；", "，", " ", ""],
                    length_function=len,
                )
                summary_chunks = simple_splitter.split_text(merged_summary)
            if summary_chunks:
                print(f"  摘要切割为 {len(summary_chunks)} 个文本块")
                for chunk in summary_chunks:
                    documents.append({
                        "text": chunk,
                        "source": f"{filename}#摘要",
                    })

    return documents


def ingest(reset=False):
    print("正在加载并处理知识文档...")
    documents = load_and_process_knowledge_files()

    if not documents:
        print("没有可入库的文档块")
        return

    print(f"\n共 {len(documents)} 个文档块，正在生成 Embedding...")

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
    parser = argparse.ArgumentParser(description="知识入库工具 — 分批摘要 +  LangChain 切割")
    parser.add_argument("--reset", action="store_true", help="清空旧数据后重新入库")
    args = parser.parse_args()
    ingest(reset=args.reset)
