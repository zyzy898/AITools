import sys
import os
import time
import config
import models
import milvus_client

if sys.platform == "win32":
    os.system("chcp 65001 > nul")
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def retrieve_context(question, top_k=None, show_score=True):
    """检索：Milvus 初检 → Cross-Encoder 重排序 → 组装上下文"""
    query_embedding = models.encode_texts([question])

    retrieval_k = config.RERANK_RETRIEVAL_K if config.RERANK_ENABLED else (top_k or config.TOP_K)
    results = milvus_client.search_vectors(query_embedding[0].tolist(), retrieval_k)

    # 过滤低于阈值的结果
    filtered = [r for r in results if r.get("score", 0) >= config.SIMILARITY_THRESHOLD]

    if not filtered and results:
        print(f"  (所有结果相似度低于阈值 {config.SIMILARITY_THRESHOLD}，已过滤)")

    # Reranker 重排序（基于 text1 短摘要或 text2 长内容）
    if config.RERANK_ENABLED and filtered:
        try:
            # 用 text2（长内容）做重排序，更准确
            rerank_texts = [r.get("text2", r.get("text", "")) for r in filtered]
            filtered_for_rerank = [{"text": t, "source": r.get("source", ""), "score": r.get("score", 0)} for r, t in zip(filtered, rerank_texts)]
            filtered = models.rerank(question, filtered_for_rerank, top_k or config.TOP_K)
        except Exception as e:
            print(f"  (Reranker 不可用，使用初检结果: {e})")

    # 组装上下文：直接拼接 text2（长内容），带来源标注
    context_parts = []
    for i, result in enumerate(filtered):
        text = result.get("text2", "") or result.get("text", "")
        source = result.get("source", "")
        score = result.get("score", 0.0)
        if not text:
            continue
        header = f"[{i+1}] {source}"
        if show_score:
            header += f" (相似度: {score:.4f})"
        context_parts.append(f"{header}\n{text}")

    return "\n\n---\n\n".join(context_parts) if context_parts else "未找到相关知识"


def answer_question(question):
    t0 = time.time()
    print("检索相关知识...")
    context = retrieve_context(question)
    t_retrieve = time.time() - t0

    t1 = time.time()
    print("生成答案...")
    prompt = config.USER_TEMPLATE.format(context=context, question=question)

    if config.LLM_API_STREAM:
        print()

    answer = models.generate_answer(prompt)
    t_generate = time.time() - t1

    print(f"\n检索: {t_retrieve:.2f}s | 生成: {t_generate:.2f}s | 总计: {t_retrieve + t_generate:.2f}s")

    return answer


def main():
    print("=" * 50)
    print("农业知识问答系统 (RAG)")
    print(f"LLM: API ({'流式' if config.LLM_API_STREAM else '非流式'}) | 阈值: {config.SIMILARITY_THRESHOLD}")
    if config.RERANK_ENABLED:
        print(f"Reranker: {config.RERANK_MODEL_NAME} (初检{config.RERANK_RETRIEVAL_K}→TOP{config.TOP_K})")
    print("输入 'quit' 或 'exit' 退出")
    print("=" * 50)

    if len(sys.argv) > 1:
        question = " ".join(sys.argv[1:])
        answer = answer_question(question)
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
