# SocialVideo Downloader

抖音、小红书、哔哩哔哩视频下载工具。优先使用常规方法提取，失败时自动调用 LLM 分析页面结构并给出提取方案。

## 支持平台

| 平台 | 脚本 | 短链接 | 主下载方式 | 回退 |
|------|------|--------|-----------|------|
| 抖音 | `douyin_downloader_llm.py` | v.douyin.com | yt-dlp | Playwright 拦截 + HTML 解析 + LLM 正则提取 → 直链下载 |
| 小红书 | `xiaohongshu_downloader_llm.py` | xhslink.com | yt-dlp | Playwright 获取页面 → LLM 分析 → 正则提取 URL → 直链下载 |
| 哔哩哔哩 | `bilibili_downloader_llm.py` | b23.tv | yt-dlp | Playwright 获取页面 → LLM 分析 → 正则提取 URL → 直链下载 |

## 安装

```bash
pip install yt-dlp playwright requests
playwright install chromium
```

各脚本按需导入依赖（如 yt-dlp 和 Playwright 均为延迟导入，未被使用时不会加载）。


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

### 抖音（yt-dlp 优先 + Playwright/LLM 兜底）

```
URL 解析 → yt-dlp
    ├─ 成功 → 完成
    └─ 失败 → Playwright 启动 → 拦截网络请求 + HTML 解析 + JS 执行
        ├─ 找到URL → requests 直链下载
        └─ 未找到 → LLM 分析 → 正则提取 → 直链下载
```

- yt-dlp 优先，成功即止（Playwright 不加载）
- 回退时使用异步 Playwright（`async_playwright`），多维度提取：网络拦截、HTML 解析、JS 执行
- LLM 返回的 URL 模式进一步做正则匹配，确保不遗漏

### 小红书 / 哔哩哔哩（yt-dlp 优先 + LLM 二次提取下载）

```
URL 解析 → yt-dlp
    ├─ 成功 → 完成
    └─ 失败 → Playwright 获取页面源码 → LLM 分析 → 正则提取视频URL
        ├─ 找到URL → requests 直链下载
        └─ 未找到 → 输出反爬建议
```

- yt-dlp 优先，成功即止（Playwright 不加载）
- LLM 回退不再是纯信息输出：将 LLM 返回的 `video_url_patterns` 用于正则匹配 HTML，找到视频直链后立即尝试下载
- 仅在 URL 提取也失败时，才降级输出反爬建议

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

### JSON 校验与自动重试

所有三个脚本均内置 JSON 输出校验和自动重试机制：

1. **边界匹配** — 通过括号深度计数精确定位 LLM 响应中最外层的 JSON 对象，而非粗暴正则。
2. **字段校验** — 解析后检查 6 个必填字段是否完整，以及 `confidence` 值是否合法。
3. **错误反馈重试** — 校验失败时，将**具体错误原因**（如缺少字段、JSON 语法错误）以多轮对话方式反馈给 LLM，要求其修正后重新输出。

```
首次调用 → extract_json_block 校验
    ├─ 通过 → 返回结构化分析结果
    └─ 失败 → _get_json_error_reason() 诊断错误
              → 将错误追加入 messages 历史
              → 再次调用 LLM（最多重试 3 次）
              ├─ 第 N 次通过 → 返回
              └─ 全部失败 → 降级返回 {"raw_response": "..."}
```

> 网络超时/API 状态码错误**不触发重试**，直接返回 `None`。

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
