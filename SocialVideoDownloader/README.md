# SocialVideo Downloader

支持抖音、小红书、哔哩哔哩的AI智能视频下载工具。当常规下载方法失败时，自动调用LLM分析页面结构并提供解决方案。

## 支持平台

- **抖音** (`douyin_downloader_llm.py`)
- **小红书** (`xiaohongshu_downloader_llm.py`)
- **哔哩哔哩** (`bilibili_downloader_llm.py`)

## 功能特点

- 支持短链接解析（v.douyin.com、xhslink.com、b23.tv）
- 支持从分享文本自动提取链接
- 主流方式使用 yt-dlp/Playwright 下载
- 备用方式：当常规方法失败时，调用LLM分析页面结构
- 提供反爬绕过建议

## 依赖安装

```bash
pip install yt-dlp playwright requests
playwright install chromium
```

## 使用方法

### 抖音

```bash
python douyin_downloader_llm.py <视频URL> [输出文件名]
python douyin_downloader_llm.py https://www.douyin.com/video/7600716080790165155
python douyin_downloader_llm.py https://v.douyin.com/Ksb4dKSz9y0/ my_video.mp4
```

### 小红书

```bash
python xiaohongshu_downloader_llm.py <笔记URL或分享文本> [输出文件名]
python xiaohongshu_downloader_llm.py "https://www.xiaohongshu.com/explore/699473ba000000001d02758e"
python xiaohongshu_downloader_llm.py "分享文本 http://xhslink.com/o/2BOIVJaEtms 复制后打开小红书查看"
```

### 哔哩哔哩

```bash
python bilibili_downloader_llm.py <视频URL或分享文本> [输出文件名]
python bilibili_downloader_llm.py "https://www.bilibili.com/video/BV11XwuzRET8"
python bilibili_downloader_llm.py "【视频标题】 https://b23.tv/FwARg66"
```

## LLM配置

编辑各文件中的配置部分，填入你的API信息：

```python
LLM_API_KEY = "your-api-key"
LLM_BASE_URL = "your-api-base-url"
LLM_MODEL = "your-model-name"
```

支持 OpenAI 兼容格式的API。

## 禁用LLM

```bash
python <脚本名> <URL> --no-llm
```

## 工作原理

1. 优先使用 yt-dlp/Playwright 提取视频
2. 若失败，调用LLM分析HTML结构
3. LLM返回视频URL模式和反爬建议
4. 根据建议尝试提取视频
