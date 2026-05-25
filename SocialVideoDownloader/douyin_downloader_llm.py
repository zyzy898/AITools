#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抖音视频下载器 - 带LLM智能分析版
支持从抖音视频页面自动提取并下载视频，当常规方法失败时自动调用LLM分析页面结构

使用方法:
    python douyin_downloader_llm.py <抖音视频URL> [输出文件名]
    
示例:
    python douyin_downloader_llm.py https://www.douyin.com/video/7600716080790165155
    python douyin_downloader_llm.py https://v.douyin.com/Ksb4dKSz9y0/ my_video.mp4

LLM配置:
    在代码中设置以下变量：
    - LLM_API_KEY: 你的API密钥
    - LLM_BASE_URL: API基础URL
    - LLM_MODEL: 模型名称
"""

import asyncio
import re
import os
import sys
import json
import argparse
from urllib.parse import unquote, urlparse
from playwright.async_api import async_playwright
import requests
from typing import Optional, Dict, Any, List


# ==================== LLM 配置 ====================
# 请在这里填写你的LLM API配置
LLM_API_KEY = ""  # 替换为你的API密钥
LLM_BASE_URL = ""  # 替换为你的API基础URL
LLM_MODEL = ""  # 替换为你的模型名称
# ==================================================

REQUIRED_FIELDS = frozenset({
    "has_video_url", "video_url_patterns", "anti_crawl_techniques",
    "bypass_suggestions", "extraction_code", "confidence"
})
VALID_CONFIDENCE = frozenset({"high", "medium", "low"})
MAX_JSON_RETRIES = 3

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


def _get_json_error_reason(content: str) -> str:
    """获取JSON提取失败的具体原因，用于反馈给LLM修正。"""
    start = content.find("{")
    if start == -1:
        return "响应中未找到JSON对象（缺少左花括号 {）。"
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
    json_str = content[start:end]
    try:
        data = json.loads(json_str)
        missing = REQUIRED_FIELDS - set(data.keys())
        if missing:
            return f"JSON缺少以下必填字段: {', '.join(sorted(missing))}。"
        if data.get("confidence") not in VALID_CONFIDENCE:
            return f"confidence字段的值'{data.get('confidence')}'无效，必须是high、medium或low之一。"
        return "JSON结构无法解析，请检查花括号是否配对、字符串是否正确转义。"
    except json.JSONDecodeError as e:
        return f"JSON解析错误: {e}。请检查字符串中的引号、换行符是否正确转义，确保输出是合法JSON。"


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
    
    def _call_llm(self, messages):
        """单次LLM API调用，返回响应文本，失败返回None。"""
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": 0.3,
                    "max_tokens": 2000
                },
                timeout=60
            )
            if response.status_code == 200:
                result = response.json()
                return result['choices'][0]['message']['content']
            else:
                print(f"[LLM] API请求失败: {response.status_code}: {response.text[:200]}")
                return None
        except requests.exceptions.Timeout:
            print("[LLM] 请求超时")
            return None
        except requests.exceptions.RequestException as e:
            print(f"[LLM] 网络请求失败: {e}")
            return None

    def analyze_page_structure(self, html_content, page_url, previous_attempts=None):
        """
        分析页面结构，找出视频下载链接和反爬对策
        当LLM返回的JSON格式不正确时，自动将错误反馈给LLM并重试最多MAX_JSON_RETRIES次。
        
        Args:
            html_content: 页面HTML内容
            page_url: 页面URL
            previous_attempts: 之前尝试过的方法（避免重复）
        
        Returns:
            dict: 包含分析结果和建议的字典
        """
        if not self.is_configured():
            print("[LLM] LLM未配置，跳过智能分析")
            return None
        
        print("[LLM] 正在调用LLM分析页面结构...")
        
        html_sample = html_content[:8000] if len(html_content) > 8000 else html_content
        
        previous_info = ""
        if previous_attempts:
            previous_info = f"\n之前尝试过的方法（都失败了）：\n{json.dumps(previous_attempts, ensure_ascii=False, indent=2)}"
        
        system_prompt = "你是一个专业的网页数据提取和反爬绕过专家。请提供详细、实用的技术分析。"
        user_prompt = f"""你是一个网页数据提取专家。我需要从抖音视频页面提取视频下载链接。

页面URL: {page_url}

页面HTML片段（前8000字符）：
```html
{html_sample}
```
{previous_info}

请分析：
1. 页面中是否包含视频下载链接？在哪里？
2. 视频URL通常有哪些特征？（如包含 douyinvod.com、/aweme/v1/play/ 等）
3. 页面使用了什么反爬技术？（如动态加载、加密、验证等）
4. 如何绕过这些反爬措施？
5. 提供具体的Python代码建议来提取视频URL

请以JSON格式返回，只返回JSON对象，不包含任何其他文字：
{{
    "has_video_url": true/false,
    "video_url_patterns": ["可能的URL模式1", "模式2"],
    "anti_crawl_techniques": ["反爬技术1", "反爬技术2"],
    "bypass_suggestions": ["绕过建议1", "绕过建议2"],
    "extraction_code": "具体的Python代码建议",
    "confidence": "high/medium/low"
}}"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        for attempt in range(MAX_JSON_RETRIES + 1):
            content = self._call_llm(messages)
            if content is None:
                return None

            analysis = extract_json_block(content)
            if analysis:
                print(f"[LLM] 分析完成，置信度: {analysis.get('confidence', 'unknown')}")
                return analysis

            if attempt < MAX_JSON_RETRIES:
                error_reason = _get_json_error_reason(content)
                print(f"[LLM] JSON校验失败({error_reason})，正在重试 ({attempt + 1}/{MAX_JSON_RETRIES})...")
                messages.append({"role": "assistant", "content": content})
                messages.append({
                    "role": "user",
                    "content": f"你的上一次回复JSON格式不正确。{error_reason}\n请只返回一个合法的JSON对象，确保包含所有必填字段，不要有任何额外文字。"
                })
            else:
                print(f"[LLM] 达到最大重试次数({MAX_JSON_RETRIES})，JSON校验仍然失败")
                print(f"[LLM] 原始响应: {content[:500]}...")
                return {"raw_response": content}

        return None
    
    def get_extraction_strategy(self, html_content, page_url):
        """
        获取视频提取策略
        
        Returns:
            list: 提取策略列表，按优先级排序
        """
        analysis = self.analyze_page_structure(html_content, page_url)
        
        if not analysis:
            return None
        
        strategies = []
        
        # 根据分析结果构建策略
        if analysis.get('has_video_url'):
            patterns = analysis.get('video_url_patterns', [])
            for pattern in patterns:
                strategies.append({
                    'type': 'regex',
                    'pattern': pattern,
                    'priority': 1
                })
        
        # 添加绕过建议作为策略
        bypass_suggestions = analysis.get('bypass_suggestions', [])
        for suggestion in bypass_suggestions:
            strategies.append({
                'type': 'bypass',
                'suggestion': suggestion,
                'priority': 2
            })
        
        return strategies


def extract_url_from_text(text):
    """从分享文本中提取抖音链接"""
    # 匹配 v.douyin.com 短链接
    match = re.search(r'https?://v\.douyin\.com/[a-zA-Z0-9]+/?', text)
    if match:
        return match.group(0)
    # 匹配 www.douyin.com 链接
    match = re.search(r'https?://www\.douyin\.com/[^\s]+', text)
    if match:
        return match.group(0)
    return None


class DouyinDownloader:
    def __init__(self, use_llm=True):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://www.douyin.com/',
            'Accept': '*/*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
        }
        self.use_llm = use_llm
        self.llm = LLMAnalyzer() if use_llm else None
        self.attempts_history = []
    
    def download_with_ytdlp(self, video_url, output_path):
        """使用 yt-dlp 下载视频"""
        try:
            import yt_dlp
        except ImportError:
            print("yt-dlp 未安装，跳过")
            return False
        
        try:
            ydl_opts = {
                'outtmpl': output_path,
                'quiet': False,
                'no_warnings': False,
                'headers': {
                    'Referer': 'https://www.douyin.com/',
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
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
    
    def resolve_short_url(self, short_url):
        """解析短链接获取真实URL"""
        try:
            response = requests.head(short_url, headers=self.headers, allow_redirects=True, timeout=10)
            return response.url
        except Exception as e:
            print(f"解析短链接失败: {e}")
            return short_url
    
    async def extract_video_urls_with_llm(self, video_url, html_content):
        """使用LLM分析提取视频URL"""
        if not self.llm or not self.llm.is_configured():
            return []
        
        print("\n[LLM] 常规方法失败，启动LLM智能分析...")
        
        analysis = self.llm.analyze_page_structure(
            html_content, 
            video_url, 
            self.attempts_history
        )
        
        if not analysis:
            return []
        
        video_urls = []
        
        # 根据LLM建议尝试提取
        if analysis.get('has_video_url'):
            patterns = analysis.get('video_url_patterns', [])
            for pattern in patterns:
                try:
                    matches = re.findall(pattern, html_content)
                    for match in matches:
                        if isinstance(match, tuple):
                            match = match[0]
                        if match and match not in video_urls:
                            video_urls.append(match)
                            print(f"[LLM] 找到视频URL: {match[:80]}...")
                except Exception as e:
                    print(f"[LLM] 模式匹配失败: {e}")
        
        # 显示建议
        bypass_suggestions = analysis.get('bypass_suggestions', [])
        if bypass_suggestions:
            print("\n[LLM] 反爬绕过建议:")
            for i, suggestion in enumerate(bypass_suggestions, 1):
                print(f"  {i}. {suggestion}")
        
        return video_urls
    
    # 从页面HTML中提取视频URL的多种方法
    def extract_from_html(self, html_content):
        """从HTML内容中提取视频URL"""
        results = []

        # 方法1: 从video标签提取
        pattern = r'<source[^>]+src="([^"]+)"'
        matches = re.findall(pattern, html_content)
        results.extend([(m, 'source_tag') for m in matches if 'douyinvod.com' in m or '/aweme/v1/play/' in m])

        # 方法2: 从window.__INITIAL_STATE__提取
        init_state_pattern = r'window\.__INITIAL_STATE__\s*=\s*({.*?});?\s*</script>'
        matches = re.findall(init_state_pattern, html_content, re.DOTALL)
        for match in matches:
            try:
                data = json.loads(match)
                video_url = self._search_video_url_in_json(data)
                if video_url:
                    results.append((video_url, 'initial_state'))
            except:
                pass

        # 方法3: 从RENDER_DATA提取（抖音使用的另一个变量）
        render_data_pattern = r'window\.__RENDER_DATA__\s*=\s*({.*?});?\s*</script>'
        matches = re.findall(render_data_pattern, html_content, re.DOTALL)
        for match in matches:
            try:
                data = json.loads(unquote(match))
                video_url = self._search_video_url_in_json(data)
                if video_url:
                    results.append((video_url, 'render_data'))
            except:
                pass

        # 方法4: 从script标签中的JSON提取
        script_pattern = r'<script[^>]*>\s*({.*?})\s*</script>'
        matches = re.findall(script_pattern, html_content, re.DOTALL)
        for match in matches:
            if 'video' in match.lower() and ('douyinvod' in match or 'aweme' in match):
                try:
                    video_urls = re.findall(r'https?://[^\s"\']+(?:douyinvod\.com|aweme)[^\s"\']*', match)
                    for url in video_urls:
                        results.append((url, 'script_json'))
                except:
                    pass

        return results

    def _search_video_url_in_json(self, obj, depth=0):
        """递归搜索JSON对象中的视频URL"""
        if depth > 10:
            return None

        if isinstance(obj, str):
            if 'douyinvod.com' in obj or ('/aweme/v1/play/' in obj and 'videos' in obj.lower()):
                return obj
            return None

        if isinstance(obj, dict):
            for key, value in obj.items():
                if key in ('playAddr', 'url', 'video_url', 'download_addr'):
                    if isinstance(value, str) and ('douyinvod' in value or '/aweme/v1/play/' in value):
                        return value
                result = self._search_video_url_in_json(value, depth + 1)
                if result:
                    return result

        if isinstance(obj, list):
            for item in obj:
                result = self._search_video_url_in_json(item, depth + 1)
                if result:
                    return result

        return None

    async def extract_video_urls(self, video_url):
        """
        使用 Playwright 访问抖音页面并提取视频真实地址
        如果常规方法失败，调用LLM分析
        """
        print(f"正在访问页面: {video_url}")

        video_urls = []
        html_content = ""

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-web-security',
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                ]
            )

            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                locale='zh-CN',
                timezone_id='Asia/Shanghai',
            )

            # 添加反检测脚本
            await context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
                window.chrome = { runtime: {} };
            """)

            page = await context.new_page()

            # 拦截视频请求
            async def handle_route(route, request):
                url = request.url
                if 'douyinvod.com' in url or '/aweme/v1/play/' in url:
                    if url not in video_urls:
                        video_urls.append(url)
                        print(f"捕获到视频URL: {url[:80]}...")
                await route.continue_()

            await page.route("**/*", handle_route)

            try:
                # 访问页面，等待DOM加载完成
                await page.goto(video_url, wait_until='domcontentloaded', timeout=30000)

                # 等待视频元素
                try:
                    await page.wait_for_selector('video', timeout=15000)
                except:
                    print("等待视频元素超时，尝试从HTML中提取...")

                # 获取页面HTML
                html_content = await page.content()

                # 使用增强的HTML提取方法
                extracted = self.extract_from_html(html_content)
                for url, source in extracted:
                    if url and url not in video_urls:
                        video_urls.append(url)
                        print(f"从{source}找到视频URL: {url[:80]}...")

                self.attempts_history.append({
                    'method': 'html_extraction',
                    'found': len(extracted) > 0,
                    'count': len(extracted)
                })

                # 方法: 从JavaScript执行获取
                try:
                    sources = await page.evaluate("""
                        () => {
                            const video = document.querySelector('video');
                            if (video) {
                                const sources = video.querySelectorAll('source');
                                return Array.from(sources).map(s => s.src).filter(s => s);
                            }
                            return [];
                        }
                    """)
                    for src in sources:
                        if src and src not in video_urls:
                            video_urls.append(src)

                    self.attempts_history.append({
                        'method': 'javascript_evaluation',
                        'found': len(sources) > 0,
                        'count': len(sources)
                    })
                except Exception as e:
                    self.attempts_history.append({
                        'method': 'javascript_evaluation',
                        'error': str(e)
                    })

                await browser.close()

            except Exception as e:
                print(f"提取视频URL时出错: {e}")
                await browser.close()

        # 如果常规方法没找到视频，调用LLM分析
        if not video_urls and self.use_llm and html_content:
            llm_urls = await self.extract_video_urls_with_llm(video_url, html_content)
            video_urls.extend(llm_urls)
        
        # 去重并排序（优先CDN链接）
        unique_urls = []
        for url in video_urls:
            if url and url not in unique_urls:
                unique_urls.append(url)
        
        # 排序：CDN链接优先
        cdn_urls = [u for u in unique_urls if 'douyinvod.com' in u]
        api_urls = [u for u in unique_urls if '/aweme/v1/play/' in u]
        
        return cdn_urls + api_urls
    
    def download_video(self, video_url, output_path):
        """下载视频到本地"""
        print(f"\n开始下载视频...")
        print(f"视频URL: {video_url[:100]}...")
        print(f"保存路径: {output_path}")
        
        try:
            response = requests.get(video_url, headers=self.headers, stream=True, timeout=120)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            if total_size > 0:
                print(f"文件大小: {total_size / 1024 / 1024:.2f} MB")
            
            downloaded = 0
            chunk_size = 8192
            
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            percent = (downloaded / total_size) * 100
                            bar = '=' * int(percent / 2) + '>' + ' ' * (50 - int(percent / 2))
                            print(f"\r[{bar}] {percent:.1f}%", end='', flush=True)
            
            print(f"\n\n[OK] 视频下载成功: {output_path}")
            return True
            
        except Exception as e:
            print(f"\n[ERROR] 下载失败: {e}")
            return False
    
    async def download(self, video_url, output_path=None):
        """主下载流程：yt-dlp优先，失败后Playwright+LLM兜底"""
        # 从输入文本中提取URL
        extracted_url = extract_url_from_text(video_url)
        if extracted_url:
            video_url = extracted_url
            print(f"提取到链接: {video_url}")
        
        # 处理短链接
        if 'v.douyin.com' in video_url:
            print("检测到短链接，正在解析...")
            video_url = self.resolve_short_url(video_url)
            print(f"真实URL: {video_url}")
        
        # 提取视频ID
        video_id_match = re.search(r'video/(\d+)', video_url)
        video_id = video_id_match.group(1) if video_id_match else "unknown"
        
        # 设置默认输出文件名
        if output_path is None:
            output_path = f"douyin_{video_id}.mp4"
        
        # 确保输出路径有.mp4后缀
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
        
        # [1/2] 尝试使用 yt-dlp 下载
        print("[1/2] 尝试使用 yt-dlp 下载...")
        success = self.download_with_ytdlp(video_url, output_path)
        if success:
            return True
        
        # [2/2] yt-dlp 失败，使用 Playwright + LLM 提取视频URL
        print("\n[2/2] yt-dlp 下载失败，启动 Playwright 提取...")
        video_urls = await self.extract_video_urls(video_url)
        
        if not video_urls:
            print("[ERROR] 未能找到视频下载链接")
            if self.llm and not self.llm.is_configured():
                print("\n提示: 配置LLM API可以获得智能分析功能")
                print("请编辑代码中的 LLM_API_KEY, LLM_BASE_URL, LLM_MODEL 变量")
            return False
        
        print(f"\n共找到 {len(video_urls)} 个视频源")
        
        # 尝试下载
        for i, url in enumerate(video_urls):
            print(f"\n尝试第 {i+1}/{len(video_urls)} 个视频源...")
            if self.download_video(url, output_path):
                return True
        
        return False


def main():
    parser = argparse.ArgumentParser(description='抖音视频下载器 - LLM智能分析版')
    parser.add_argument('url', help='抖音视频URL（支持长链接和短链接）')
    parser.add_argument('output', nargs='?', help='输出文件名（可选）')
    parser.add_argument('--no-llm', action='store_true', help='禁用LLM智能分析')
    
    args = parser.parse_args()

    print("=" * 60)
    print("抖音视频下载器")
    print("=" * 60)
    print(f"输入: {args.url}")
    
    # 检查LLM配置
    llm = LLMAnalyzer()
    if llm.is_configured():
        print("[INFO] LLM智能分析已启用")
        print(f"[INFO] 使用模型: {llm.model}")
    else:
        print("[INFO] LLM未配置，智能分析功能不可用")
        print("[INFO] 如需启用，请编辑代码中的LLM配置部分")
    
    downloader = DouyinDownloader(use_llm=not args.no_llm)
    success = asyncio.run(downloader.download(args.url, args.output))
    
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
