import os
import sys
import re
import numpy as np
import tiktoken
from nltk.tokenize import sent_tokenize
from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from models import encode_texts


def tiktoken_len(text):
    tokenizer = tiktoken.get_encoding("cl100k_base")
    return len(tokenizer.encode(text))


def production_dynamic_splitter(markdown_text):
    # 1. 结构解析：按Markdown标题分割
    headers_to_split_on = [("#", "Header 1"), ("##", "Header 2"), ("###", "Header 3")]
    markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on, strip_headers=False)
    initial_chunks = markdown_splitter.split_text(markdown_text)
    
    final_chunks = []
    
    for chunk in initial_chunks:
        content = chunk.page_content
        metadata = chunk.metadata
        
        # 2. 内容类型识别
        if re.search(r"```[\s\S]*?```", content):
            content_type = "code"
            base_size = 300
            base_overlap = 50
        elif re.search(r"\|.*\|.*\|", content):
            content_type = "table"
            base_size = 800
            base_overlap = 100
        elif re.search(r"^(\d+\.|-|\*)\s", content, re.MULTILINE):
            content_type = "list"
            base_size = 400
            base_overlap = 80
        else:
            content_type = "text"
            base_size = 512
            base_overlap = 100
        
        # 3. 重要性评分
        key_patterns = [r"(定义|概念|结论|步骤|公式)[:：]"]
        is_important = any(re.search(pattern, content) for pattern in key_patterns)
        if is_important:
            base_size = int(base_size * 0.8)  # 重要内容切得更小
            base_overlap = int(base_overlap * 1.2)  # 重要内容重叠更大
        
        # 4. 语义密度计算
        sentences = sent_tokenize(content)
        if len(sentences) >= 3:
            sentence_embeddings = encode_texts(sentences[:5])
            avg_density = np.mean([np.var(emb) for emb in sentence_embeddings])
            density_factor = 1.0 / (avg_density * 1000) if avg_density > 0 else 1.0
            adjusted_size = int(base_size * density_factor)
            adjusted_size = max(100, min(1024, adjusted_size))
        else:
            adjusted_size = base_size
        
        # 5. 智能切割
        if tiktoken_len(content) > adjusted_size:
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=adjusted_size,
                chunk_overlap=base_overlap,
                length_function=tiktoken_len,
                separators=["\n\n", "\n", ". ", " ", ""]
            )
            sub_chunks = text_splitter.split_documents([chunk])
            for sub_chunk in sub_chunks:
                sub_chunk.metadata.update({
                    "content_type": content_type,
                    "is_important": is_important,
                    "adjusted_size": adjusted_size
                })
            final_chunks.extend(sub_chunks)
        else:
            chunk.metadata.update({
                "content_type": content_type,
                "is_important": is_important,
                "adjusted_size": adjusted_size
            })
            final_chunks.append(chunk)
    
    return final_chunks

if __name__ == "__main__":
    sample_markdown = """
水稻种植技术

育苗
水稻育苗是关键步骤。首先需要选择优质种子。
步骤一：浸种催芽，将种子浸泡在温水中24小时。
步骤二：播种育苗，保持苗床湿润。

田间管理
田间管理包括以下方面：
1. 水分管理：保持适宜水层
2. 施肥管理：根据生长阶段施肥
3. 病虫害防治：定期检查

施肥要点
概念：合理施肥是水稻高产的重要保证。
公式：氮肥用量 = 目标产量 × 需氮量 - 土壤供氮量

```python
def calc_fertilizer(yield_target, soil_n):
    return yield_target * 0.02 - soil_n
```

收获
收获时间一般在稻谷含水量20-25%时进行。
"""
    chunks = production_dynamic_splitter(sample_markdown)
    for i, c in enumerate(chunks):
        print(f"\n===== Chunk {i+1} =====")
        print(f"Metadata: {c.metadata}")
        print(f"Content ({tiktoken_len(c.page_content)} tokens):")
        print(c.page_content[:200])