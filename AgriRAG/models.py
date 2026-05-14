import sys
import json
import numpy as np
import torch
from transformers import AutoTokenizer, AutoModel, AutoModelForCausalLM
import config

embedding_model = None
embedding_tokenizer = None
llm_model = None
llm_tokenizer = None


def load_embedding_model():
    global embedding_model, embedding_tokenizer
    if embedding_model is None:
        model_path = config.EMBEDDING_MODEL_PATH
        try:
            embedding_tokenizer = AutoTokenizer.from_pretrained(
                model_path, trust_remote_code=True
            )
            embedding_model = AutoModel.from_pretrained(
                model_path, trust_remote_code=True
            )
            embedding_model.eval()
        except OSError as e:
            print(f"\n[错误] Embedding 模型加载失败")
            print(f"  路径: {model_path}")
            print(f"  原因: {e}")
            print(f"  请检查模型文件是否完整，或路径是否正确")
            raise SystemExit(1)
        except Exception as e:
            print(f"\n[错误] Embedding 模型加载异常: {e}")
            raise SystemExit(1)
    return embedding_model, embedding_tokenizer


def encode_texts(texts, batch_size=32):
    """分批编码文本，带进度提示，避免大量文本时 OOM"""
    model, tokenizer = load_embedding_model()
    all_embeddings = []
    total_batches = (len(texts) + batch_size - 1) // batch_size

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        batch_idx = i // batch_size + 1

        if total_batches > 1:
            progress = f"[{batch_idx}/{total_batches}] Embedding 生成中... ({min(i + batch_size, len(texts))}/{len(texts)})"
            print(f"\r{progress}", end="", flush=True)

        with torch.no_grad():
            inputs = tokenizer(batch, padding=True, truncation=True, max_length=512, return_tensors="pt")
            outputs = model(**inputs)
            embeddings = outputs.last_hidden_state[:, 0]
            embeddings = torch.nn.functional.normalize(embeddings, p=2, dim=1)
            all_embeddings.append(embeddings.cpu().numpy())

    if total_batches > 1:
        print()  # 换行

    return np.concatenate(all_embeddings, axis=0)


def load_llm_model():
    global llm_model, llm_tokenizer
    if llm_model is None:
        model_path = config.LLM_MODEL_PATH
        try:
            llm_tokenizer = AutoTokenizer.from_pretrained(
                model_path, trust_remote_code=True
            )
            llm_model = AutoModelForCausalLM.from_pretrained(
                model_path,
                torch_dtype=torch.float16,
                device_map="auto",
                trust_remote_code=True
            )
            llm_model.eval()
        except OSError as e:
            print(f"\n[错误] LLM 模型加载失败")
            print(f"  路径: {model_path}")
            print(f"  原因: {e}")
            print(f"  请检查模型文件是否完整，或路径是否正确")
            raise SystemExit(1)
        except Exception as e:
            print(f"\n[错误] LLM 模型加载异常: {e}")
            raise SystemExit(1)
    return llm_model, llm_tokenizer


def generate_answer_local(prompt):
    """使用本地模型生成答案"""
    model, tokenizer = load_llm_model()
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
    with torch.no_grad():
        outputs = model.generate(
            inputs.input_ids,
            max_new_tokens=config.LLM_MAX_LENGTH,
            top_p=config.LLM_TOP_P,
            top_k=config.LLM_TOP_K,
            temperature=config.LLM_TEMPERATURE,
            do_sample=True,
            pad_token_id=tokenizer.pad_token_id or tokenizer.eos_token_id
        )
    response = tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True)
    return response


def generate_answer_api(prompt):
    """使用 OpenAI 兼容 API 生成答案，支持流式输出"""
    import requests

    headers = {"Content-Type": "application/json"}
    if config.LLM_API_KEY:
        headers["Authorization"] = f"Bearer {config.LLM_API_KEY}"

    stream = config.LLM_API_STREAM

    payload = {
        "model": config.LLM_API_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": config.LLM_TEMPERATURE,
        "top_p": config.LLM_TOP_P,
        "max_tokens": config.LLM_MAX_LENGTH,
        "stream": stream,
    }

    try:
        resp = requests.post(config.LLM_API_URL, json=payload, headers=headers, timeout=60, stream=stream)
        resp.raise_for_status()

        if stream:
            return _handle_stream_response(resp)
        else:
            data = resp.json()
            return data["choices"][0]["message"]["content"].strip()

    except requests.exceptions.ConnectionError:
        return "[错误] 无法连接到 LLM API，请检查 LLM_API_URL 配置"
    except requests.exceptions.Timeout:
        return "[错误] LLM API 请求超时"
    except Exception as e:
        return f"[错误] API 调用失败: {e}"


def _handle_stream_response(resp):
    """处理 SSE 流式响应，逐字打印并返回完整文本"""
    full_content = ""
    for line in resp.iter_lines(decode_unicode=True):
        if not line:
            continue
        if line.startswith("data: "):
            data_str = line[6:]
            if data_str.strip() == "[DONE]":
                break
            try:
                data = json.loads(data_str)
                delta = data.get("choices", [{}])[0].get("delta", {})
                content = delta.get("content", "")
                if content:
                    sys.stdout.write(content)
                    sys.stdout.flush()
                    full_content += content
            except json.JSONDecodeError:
                continue
    print()  # 流式结束后换行
    return full_content


def generate_answer(prompt):
    """根据配置选择本地模型或 API 生成答案"""
    if config.LLM_MODE == "api":
        return generate_answer_api(prompt)
    else:
        return generate_answer_local(prompt)
