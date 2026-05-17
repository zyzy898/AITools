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
    query_embedding = models.encode_texts([question])
    results = milvus_client.search_vectors(query_embedding[0].tolist(), top_k)

    # 过滤低于阈值的结果
    filtered = [r for r in results if r.get("score", 0) >= config.SIMILARITY_THRESHOLD]

    if not filtered and results:
        print(f"  (所有结果相似度低于阈值 {config.SIMILARITY_THRESHOLD}，已过滤)")

    context_parts = []
    for i, result in enumerate(filtered):
        text = result.get("text", "")
        source = result.get("source", "")
        score = result.get("score", 0.0)
        if text:
            header = f"[{i+1}] [{source}]"
            if show_score:
                header += f" (相似度: {score:.4f})"
            context_parts.append(f"{header}\n{text}")

    return "\n\n".join(context_parts) if context_parts else "未找到相关知识"


def answer_question(question):
    # 检索阶段计时
    t0 = time.time()
    print("检索相关知识...")
    context = retrieve_context(question)
    t_retrieve = time.time() - t0

    # 生成阶段计时
    t1 = time.time()
    print("生成答案...")
    prompt = config.PROMPT_TEMPLATE.format(context=context, question=question)

    # 流式模式下答案会直接打印，非流式则返回文本
    is_stream = config.LLM_MODE == "api" and config.LLM_API_STREAM
    if is_stream:
        print()  # 空行分隔

    answer = models.generate_answer(prompt)
    t_generate = time.time() - t1

    # 耗时统计
    print(f"\n⏱ 检索: {t_retrieve:.2f}s | 生成: {t_generate:.2f}s | 总计: {t_retrieve + t_generate:.2f}s")

    return answer


def main():
    print("=" * 50)
    print("农业知识问答系统 (RAG)")
    print(f"LLM 模式: {config.LLM_MODE}", end="")
    if config.LLM_MODE == "api":
        stream_status = "流式" if config.LLM_API_STREAM else "非流式"
        print(f" ({stream_status})", end="")
    print(f" | 相似度阈值: {config.SIMILARITY_THRESHOLD}")
    print("输入 'quit' 或 'exit' 退出")
    print("=" * 50)

    # 支持命令行直接传入问题
    if len(sys.argv) > 1:
        question = " ".join(sys.argv[1:])
        answer = answer_question(question)
        # 非流式模式才需要额外打印答案
        if not (config.LLM_MODE == "api" and config.LLM_API_STREAM):
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
            if not (config.LLM_MODE == "api" and config.LLM_API_STREAM):
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
