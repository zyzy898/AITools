import sys
import os
import time
import config
import models
import milvus_client

if sys.platform == "win32":
    os.system("chcp 65001 > nul")  # 设置终端为 UTF-8 编码
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def retrieve_context(question, top_k=None, show_score=True):
    """两阶段检索：Milvus 初检 → Cross-Encoder 重排序 → 按文件分组组装上下文"""
    query_embedding = models.encode_texts([question])

    retrieval_k = config.RERANK_RETRIEVAL_K if config.RERANK_ENABLED else (top_k or config.TOP_K)
    results = milvus_client.search_vectors(query_embedding[0].tolist(), retrieval_k)

    # 过滤低于阈值的结果
    filtered = [r for r in results if r.get("score", 0) >= config.SIMILARITY_THRESHOLD]

    if not filtered and results:
        print(f"  (所有结果相似度低于阈值 {config.SIMILARITY_THRESHOLD}，已过滤)")

    # Reranker 重排序
    if config.RERANK_ENABLED and filtered:
        try:
            filtered = models.rerank(question, filtered, top_k or config.TOP_K)
        except Exception as e:
            print(f"  (Reranker 不可用，使用初检结果: {e})")

    # 按文件分组：摘要块放前面，原文块放后面（每个文件原文最多3块，防止单一主题占满）
    file_groups = {}
    file_order = []
    MAX_DETAIL_PER_FILE = 8
    for result in filtered:
        source = result.get("source", "")
        text = result.get("text", "")
        score = result.get("score", 0.0)
        if not text:
            continue
        is_summary = source.endswith("#摘要")
        base_name = source[:-3] if is_summary else source
        if base_name not in file_groups:
            file_groups[base_name] = {"summary": [], "detail": [], "detail_count": 0}
            file_order.append(base_name)
        if is_summary:
            file_groups[base_name]["summary"].append((text, score))
        else:
            if file_groups[base_name]["detail_count"] < MAX_DETAIL_PER_FILE:
                file_groups[base_name]["detail"].append((text, score))
                file_groups[base_name]["detail_count"] += 1

    # 组装上下文：每个文件先摘要后细节
    context_parts = []
    for base_name in file_order:
        group = file_groups[base_name]
        parts = []

        # 摘要块
        for text, score in group["summary"]:
            header = f"[摘要] {base_name}"
            if show_score:
                header += f" (相似度: {score:.4f})"
            parts.append(f"{header}\n{text}")

        # 原文块
        for text, score in group["detail"]:
            header = f"[原文] {base_name}"
            if show_score:
                header += f" (相似度: {score:.4f})"
            parts.append(f"{header}\n{text}")

        if parts:
            context_parts.append("\n\n".join(parts))

    return "\n\n---\n\n".join(context_parts) if context_parts else "未找到相关知识"


def answer_question(question):
    # 检索阶段计时
    t0 = time.time()
    print("检索相关知识...")
    context = retrieve_context(question)
    t_retrieve = time.time() - t0

    # 生成阶段计时
    t1 = time.time()
    print("生成答案...")
    prompt = config.USER_TEMPLATE.format(context=context, question=question)

    # 流式模式下答案会直接打印，非流式则返回文本
    if config.LLM_API_STREAM:
        print()  # 空行分隔

    answer = models.generate_answer(prompt)
    t_generate = time.time() - t1

    # 耗时统计
    print(f"\n⏱ 检索: {t_retrieve:.2f}s | 生成: {t_generate:.2f}s | 总计: {t_retrieve + t_generate:.2f}s")

    return answer


def main():
    print("=" * 50)
    print("农业知识问答系统 (RAG)")
    print(f"LLM 模式: API ({'流式' if config.LLM_API_STREAM else '非流式'}) | 相似度阈值: {config.SIMILARITY_THRESHOLD}")
    if config.RERANK_ENABLED:
        print(f"Reranker: {config.RERANK_MODEL_NAME} (初检{config.RERANK_RETRIEVAL_K}→重排→TOP{config.TOP_K})")
    print("输入 'quit' 或 'exit' 退出")
    print("=" * 50)

    # 支持命令行直接传入问题
    if len(sys.argv) > 1:
        question = " ".join(sys.argv[1:])
        answer = answer_question(question)
        # 非流式模式才需要额外打印答案
        if not config.LLM_API_STREAM:
            print(f"\n答案:\n{answer}")
        return

    while True:
        try:
            question = input("\n请输入问题: ").strip()
            if question.lower() in ["quit", "exit", "q"]:
                print("再见!")
                break
            if not question:
                continue

            print()
            answer = answer_question(question)
            # 非流式模式打印答案
            if not config.LLM_API_STREAM:
                print(f"\n答案:\n{'-' * 50}")
                print(answer)
                print("-" * 50)

        except KeyboardInterrupt:
            print("\n\n再见!")
            break
        except Exception as e:
            print(f"\n错误: {e}")


if __name__ == "__main__":
    main()
