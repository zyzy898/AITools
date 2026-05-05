#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
XiaoHongShu Video Downloader - 小红书视频下载器 (带LLM智能分析版)
支持从小红书笔记页面自动提取并下载视频，当常规方法失败时自动调用LLM分析页面结构

依赖安装:
    pip install yt-dlp playwright requests
    playwright install chromium

使用方法:
    python xiaohongshu_downloader_llm.py <笔记链接或分享文本> [输出文件名]
    
示例:
    python xiaohongshu_downloader_llm.py "https://www.xiaohongshu.com/explore/699473ba000000001d02758e"
    python xiaohongshu_downloader_llm.py "这种轻轻咬着嘬是啥意思？ http://xhslink.com/o/2BOIVJaEtms 复制后打开【小红书】查看笔记！"

LLM配置:
    在代码中设置以下变量：
    - LLM_API_KEY: 你的API密钥
    - LLM_BASE_URL: API基础URL
    - LLM_MODEL: 模型名称
"""

import sys
import os
import re
import json
import argparse
import requests
from urllib.parse import unquote
from typing import Optional, Dict, Any, List


# ==================== LLM 配置 ====================
# 请在这里填写你的LLM API配置
LLM_API_KEY = "ark-bbde0748-5235-4b09-88a7-00b599d73c34-74f2d"  # 替换为你的API密钥
LLM_BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"  # 替换为你的API基础URL
LLM_MODEL = "doubao-seed-2-0-lite-260215" # 替换为你的模型名称
# ==================================================

REQUIRED_FIELDS = frozenset({
    "has_video_url", "video_url_patterns", "anti_crawl_techniques",
    "bypass_suggestions", "extraction_code", "confidence"
})
VALID_CONFIDENCE = frozenset({"high", "medium", "low"})

def extract_json_block(content: str) -> Optional[Dict[str, Any]]:
    """Extract and validate the outermost JSON object from LLM response."""
    start = content.find("{")
    if start == -1:
        return None
    depth = 0
    end = start
    for i, ch in enumerate(content[start:], start):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    try:
        data = json.loads(content[start:end])
        missing = REQUIRED_FIELDS - set(data.keys())
        if missing:
            print(f"[LLM] 响应缺少字段: {missing}")
            return None
        if data.get("confidence") not in VALID_CONFIDENCE:
            print(f"[LLM] 无效的confidence值: {data.get('confidence')}")
            return None
        return data
    except json.JSONDecodeError as e:
        print(f"[LLM] JSON解析失败: {e}")
        return None


def extract_url_from_text(text):
    """从分享文本中提取小红书链接"""
    # 匹配 xhslink.com 短链接
    match = re.search(r'https?://xhslink\.com/[a-zA-Z0-9/]+', text)
    if match:
        return match.group(0)
    # 匹配 www.xiaohongshu.com 链接
    match = re.search(r'https?://www\.xiaohongshu\.com/(explore|discovery/item)/[^\s]+', text)
    if match:
        return match.group(0)
    # 匹配笔记ID直接构建链接
    match = re.search(r'(explore|discovery/item)/([a-f0-9]+)', text)
    if match:
        return f"https://www.xiaohongshu.com/explore/{match.group(2)}"
    return None


class LLMAnalyzer:
    """LLM分析器 - 用于分析页面结构并提供反爬解决方案"""
    
    def __init__(self, api_key=None, base_url=None, model=None):
        self.api_key = api_key or LLM_API_KEY
        self.base_url = base_url or LLM_BASE_URL
        self.model = model or LLM_MODEL
        self.headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key}'
        }
    
    def is_configured(self):
        """检查LLM是否已配置"""
        return (self.api_key and self.api_key != "your-api-key-here" and 
                self.base_url and self.model)
    
    def analyze_page_structure(self, html_content, page_url, previous_attempts=None):
        """
        分析页面结构，找出视频下载链接和反爬对策
        """
        if not self.is_configured():
            print("[LLM] LLM未配置，跳过智能分析")
            return None
        
        print("[LLM] 正在调用LLM分析页面结构...")
        
        html_sample = html_content[:8000] if len(html_content) > 8000 else html_content
        
        previous_info = ""
        if previous_attempts:
            previous_info = f"\n之前尝试过的方法（都失败了）：\n{json.dumps(previous_attempts, ensure_ascii=False, indent=2)}"
        
        prompt = f"""你是一个网页数据提取专家。我需要从小红书(XiaoHongShu)笔记页面提取视频下载链接。

页面URL: {page_url}

页面HTML片段（前8000字符）：
```html
{html_sample}
```
{previous_info}

请分析：
1. 页面中是否包含视频下载链接？在哪里？
2. 视频URL通常有哪些特征？（如包含 xiaohongshu.com、video、mp4 等）
3. 页面使用了什么反爬技术？（如动态加载、加密、验证等）
4. 如何绕过这些反爬措施？
5. 提供具体的Python代码建议来提取视频URL

小红书视频链接常见位置：
- 在 script 标签中的 window.__INITIAL_STATE__
- 在 script 标签中的 SSR 数据
- 在 video 标签的 src 属性
- 在 meta 标签的 content 属性

请以JSON格式返回：
{{
    "has_video_url": true/false,
    "video_url_patterns": ["可能的URL模式1", "模式2"],
    "anti_crawl_techniques": ["反爬技术1", "反爬技术2"],
    "bypass_suggestions": ["绕过建议1", "绕过建议2"],
    "extraction_code": "具体的Python代码建议",
    "confidence": "high/medium/low"
}}"""

        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": "你是一个专业的网页数据提取和反爬绕过专家。请提供详细、实用的技术分析。"},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.3,
                    "max_tokens": 2000
                },
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']

                analysis = extract_json_block(content)
                if analysis:
                    print(f"[LLM] 分析完成，置信度: {analysis.get('confidence', 'unknown')}")
                    return analysis
                print(f"[LLM] 原始响应: {content[:500]}...")
                return {"raw_response": content}
            else:
                print(f"[LLM] API请求失败: {response.status_code}: {response.text[:200]}")
                return None

        except requests.exceptions.Timeout:
            print("[LLM] 请求超时")
            return None
        except requests.exceptions.RequestException as e:
            print(f"[LLM] 网络请求失败: {e}")
            return None


class XiaoHongShuDownloader:
    def __init__(self, use_llm=True):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://www.xiaohongshu.com/',
            'Accept': '*/*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        }
        self.use_llm = use_llm
        self.llm = LLMAnalyzer() if use_llm else None
        self.attempts_history = []
    
    def resolve_short_url(self, short_url):
        """解析短链接获取真实URL"""
        try:
            response = requests.head(short_url, headers=self.headers, allow_redirects=True, timeout=10)
            return response.url
        except Exception as e:
            print(f"解析短链接失败: {e}")
            return short_url
    
    def extract_note_id(self, url):
        """从 URL 中提取笔记 ID"""
        match = re.search(r'/explore/([a-f0-9]+)', url)
        if match:
            return match.group(1)
        return None
    
    def download_with_ytdlp(self, video_url, output_path):
        """使用 yt-dlp 下载视频"""
        try:
            import yt_dlp
        except ImportError:
            print("错误: 未安装 yt-dlp")
            return False
        
        try:
            ydl_opts = {
                'outtmpl': output_path,
                'quiet': False,
                'no_warnings': False,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_url, download=False)
                if info:
                    print(f"标题: {info.get('title', 'Unknown')}")
                    print(f"作者: {info.get('uploader', 'Unknown')}")
                    print(f"时长: {info.get('duration', 0)} 秒")
                
                ydl.download([video_url])
            
            return True
            
        except Exception as e:
            print(f"yt-dlp 下载失败: {e}")
            return False
    
    def analyze_with_llm_after_failure(self, video_url):
        """当 yt-dlp 失败后，使用 LLM 分析页面"""
        if not self.llm or not self.llm.is_configured():
            return None
        
        print("\n[LLM] yt-dlp 失败，启动页面分析...")
        
        try:
            from playwright.sync_api import sync_playwright
            
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                )
                
                page = context.new_page()
                
                print(f"[LLM] 访问页面: {video_url}")
                page.goto(video_url, wait_until='domcontentloaded', timeout=30000)
                
                import time
                time.sleep(3)
                
                html_content = page.content()
                browser.close()
                
                # 调用 LLM 分析
                analysis = self.llm.analyze_page_structure(html_content, video_url, self.attempts_history)
                
                if analysis:
                    print("\n[LLM] 分析结果:")
                    print(f"  找到视频URL: {analysis.get('has_video_url', False)}")
                    
                    anti_crawl = analysis.get('anti_crawl_techniques', [])
                    if anti_crawl:
                        print(f"  检测到的反爬技术: {', '.join(anti_crawl)}")
                    
                    bypass = analysis.get('bypass_suggestions', [])
                    if bypass:
                        print(f"  绕过建议:")
                        for i, suggestion in enumerate(bypass[:3], 1):
                            print(f"    {i}. {suggestion}")
                
                return analysis
                
        except Exception as e:
            print(f"[LLM] 页面分析失败: {e}")
            return None
    
    def download(self, video_url, output_path=None):
        """主下载流程"""
        # 从输入文本中提取URL
        extracted_url = extract_url_from_text(video_url)
        if extracted_url:
            video_url = extracted_url
            print(f"提取到链接: {video_url}")
        
        # 处理短链接
        if 'xhslink.com' in video_url:
            print("检测到短链接，正在解析...")
            video_url = self.resolve_short_url(video_url)
            print(f"真实URL: {video_url}")
        
        # 提取笔记ID
        note_id = self.extract_note_id(video_url)
        if note_id:
            print(f"笔记 ID: {note_id}")
        
        # 设置输出文件名
        if output_path is None:
            output_path = f"xiaohongshu_{note_id or 'video'}.mp4"
        
        if not output_path.endswith('.mp4'):
            output_path += '.mp4'
        
        # 确保文件名唯一
        counter = 1
        original_path = output_path
        while os.path.exists(output_path):
            name, ext = os.path.splitext(original_path)
            output_path = f"{name}_{counter}{ext}"
            counter += 1
        
        print(f"\n输出文件: {output_path}")
        print("-" * 60)
        
        # 尝试使用 yt-dlp 下载
        print("[1/2] 尝试使用 yt-dlp 下载...")
        success = self.download_with_ytdlp(video_url, output_path)
        
        # 如果 yt-dlp 失败且启用了LLM，进行分析
        if not success and self.use_llm:
            print("\n[2/2] yt-dlp 下载失败，尝试LLM分析...")
            analysis = self.analyze_with_llm_after_failure(video_url)
            
            if analysis:
                print("\n[提示] 根据LLM分析，您可以尝试:")
                bypass_suggestions = analysis.get('bypass_suggestions', [])
                for suggestion in bypass_suggestions:
                    print(f"  - {suggestion}")
        
        return success


def main():
    parser = argparse.ArgumentParser(description='小红书视频下载器 - LLM智能分析版')
    parser.add_argument('url', help='小红书笔记URL或分享文本')
    parser.add_argument('output', nargs='?', help='输出文件名（可选）')
    parser.add_argument('--no-llm', action='store_true', help='禁用LLM智能分析')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("小红书视频下载器")
    print("=" * 60)
    print(f"输入: {args.url}")
    
    # 检查LLM配置
    llm = LLMAnalyzer()
    if llm.is_configured():
        print("[INFO] LLM智能分析已启用")
        print(f"[INFO] 使用模型: {llm.model}")
    else:
        print("[INFO] LLM未配置，智能分析功能不可用")
    
    downloader = XiaoHongShuDownloader(use_llm=not args.no_llm)
    success = downloader.download(args.url, args.output)
    
    if success:
        print("-" * 60)
        print(f"[OK] 下载完成!")
        sys.exit(0)
    else:
        print("-" * 60)
        print("[FAIL] 下载失败")
        sys.exit(1)


if __name__ == "__main__":
    main()
