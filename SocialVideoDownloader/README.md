# SocialVideo Downloader

抖音、小红书、哔哩哔哩视频下载工具。优先使用常规方法提取，失败时自动调用 LLM 分析页面结构并给出提取方案。

## 支持平台

| 平台 | 脚本 | 短链接 | 主下载方式 | LLM 回退 |
|------|------|--------|-----------|---------|
| 抖音 | `douyin_downloader_llm.py` | v.douyin.com | Playwright HTML 解析 | 用 LLM 返回的 URL 模式再次提取 |
| 小红书 | `xiaohongshu_downloader_llm.py` | xhslink.com | yt-dlp | LLM 反爬分析（仅输出建议） |
| 哔哩哔哩 | `bilibili_downloader_llm.py` | b23.tv | yt-dlp | LLM 反爬分析（仅输出建议） |

## 安装

```bash
pip install yt-dlp playwright requests
playwright install chromium
```

各脚本按需导入依赖（如 yt-dlp 和 Playwright 均为延迟导入，未被使用时不会加载）。

## 快速开始

```bash
# 抖音
python douyin_downloader_llm.py https://v.douyin.com/Ksb4dKSz9y0/
python douyin_downloader_llm.py https://www.douyin.com/video/7600716080790165165 my_video.mp4

# 小红书
python xiaohongshu_downloader_llm.py "https://www.xiaohongshu.com/explore/699473ba000000001d02758e"
python xiaohongshu_downloader_llm.py "分享文本 http://xhslink.com/o/2BOIVJaEtms 复制后打开小红书查看"

# 哔哩哔哩
python bilibili_downloader_llm.py "https://www.bilibili.com/video/BV11XwuzRET8"
python bilibili_downloader_llm.py "【标题】 https://b23.tv/FwARg66"
```

> 支持从分享文本自动提取链接。未指定输出文件名时，自动根据视频 ID / 笔记 ID / BV 号生成。

## LLM 配置

LLM 用于常规方法失败时的页面分析。**三个脚本的 LLM 配置各自独立**，需要分别编辑：

```python
# 各文件顶部（约第 35 行）
LLM_API_KEY = "sk-your-key"
LLM_BASE_URL = "https://api.openai.com/v1"
LLM_MODEL = "gpt-4o"
```

支持所有 OpenAI 兼容格式的 API。LLM 分析请求参数：`temperature=0.3`，`max_tokens=2000`，超时 60 秒。

### 禁用 LLM

```bash
python douyin_downloader_llm.py <URL> --no-llm
python xiaohongshu_downloader_llm.py <URL> --no-llm
python bilibili_downloader_llm.py <URL> --no-llm
```

## 工作原理

### 抖音（Playwright 优先 + LLM 回退可下载）

```
URL 解析 → Playwright 启动 → 拦截网络请求（douyinvod.com/aweme/v1/play/）
    ├─ 成功 → requests 直链下载
    └─ 失败 → LLM 分析 HTML → 返回 URL 提取模式 → 正则匹配 → 直链下载
```

- 无 yt-dlp 依赖，全程通过 Playwright 分析页面和 CDN 直链
- 使用异步 Playwright（`async_playwright`）
- LLM 返回的 URL 模式会立即用于二次提取并尝试下载

### 小红书 / 哔哩哔哩（yt-dlp 优先 + LLM 分析）

```
URL 解析 → yt-dlp
    ├─ 成功 → 完成
    └─ 失败 → Playwright 截图 + 页面源码 → LLM 分析 → 输出反爬建议
```

- yt-dlp 优先，成功即止（Playwright 不加载）
- LLM 回退为**信息输出**：展示检测到的反爬技术、绕过建议、提取代码提示
- 使用同步 Playwright（`sync_playwright`），仅在 yt-dlp 失败时懒加载

## LLM 分析结构

LLM 响应为 JSON 格式，包含以下字段：

| 字段 | 说明 |
|------|------|
| `has_video_url` | `true` / `false` |
| `video_url_patterns` | HTML 中可匹配视频地址的 URL 模式列表 |
| `anti_crawl_techniques` | 检测到的反爬手段（如签名校验、动态 token） |
| `bypass_suggestions` | 绕过反爬的操作建议 |
| `extraction_code` | 提取视频地址的 Python 示例代码 |
| `confidence` | 分析置信度（`high` / `medium` / `low`） |

## 高级用法

```bash
# 禁用 LLM，仅用常规方式下载
python douyin_downloader_llm.py "https://v.douyin.com/xxx/" --no-llm

# 指定输出文件名
python bilibili_downloader_llm.py "https://b23.tv/xxx" tutorial.mp4

# 从分享文本直接提取（小红书、哔哩哔哩均支持）
python xiaohongshu_downloader_llm.py "8.79 复制打开抖音，看看【xxx】... https://v.douyin.com/xxx/"
```

## 注意事项

- 下载的视频仅供个人学习使用，请遵守各平台的服务条款
- 输出文件不覆盖同名文件，自动追加数字后缀（`video_1.mp4`、`video_2.mp4`）
