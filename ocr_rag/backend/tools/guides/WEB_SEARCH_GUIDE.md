# 网络搜索工具使用文档

## 功能说明

已成功集成网络搜索工具到你的多模态 RAG 系统中，模型现在可以自动调用网络搜索来获取实时信息！

## 集成内容

### 1. **网络搜索工具类** (`web_search_tool.py`)

创建了完整的网络搜索工具类，支持：
- **DuckDuckGo 搜索**（默认，无需 API Key）
- **SerpAPI**（需要 API Key）
- **Tavily**（需要 API Key）

### 2. **工具函数**

定义了两个 LangChain 工具：
- `web_search(query, max_results)` - 通用网络搜索
- `search_recent_news(topic, days)` - 搜索最近新闻

### 3. **模型集成**

修改了 `main.py`，添加了：
- `get_chat_model_with_tools()` - 返回绑定工具的模型
- `execute_tool_calls()` - 执行工具调用
- `generate_streaming_response_with_tools()` - 支持工具的流式响应

## 使用方式

### 前端不需要任何改动！

模型会自动判断何时需要搜索：

**示例对话：**

```
用户: 2024年人工智能领域有哪些重大突破？

[模型自动调用] web_search("2024年人工智能重大突破")
[返回搜索结果]
模型: 根据搜索结果，2024年人工智能领域的重大突破包括...
```

```
用户: 今天的天气怎么样？

[模型自动调用] web_search("今天天气")
[返回搜索结果]  
模型: 抱歉，我需要知道您的具体位置才能查询天气...
```

## 工作流程

```
用户提问
   ↓
模型分析是否需要搜索
   ↓
[需要] → 调用 web_search 工具
   ↓
获取搜索结果
   ↓
模型基于搜索结果生成回答
   ↓
流式返回给用户
```

## 前端事件流

后端会发送以下事件类型：

1. **tool_calls** - 工具调用通知
```json
{
  "type": "tool_calls",
  "tools": [
    {
      "name": "web_search",
      "args": {"query": "xxx", "max_results": 5}
    }
  ],
  "timestamp": "..."
}
```

2. **tool_results** - 工具结果
```json
{
  "type": "tool_results",
  "results": [
    {
      "tool": "web_search",
      "content": "搜索结果摘要..."
    }
  ],
  "timestamp": "..."
}
```

3. **content_delta** - 内容增量（正常流式响应）

4. **message_complete** - 消息完成

## 启用/禁用工具

目前只有 `deepseek-chat` 模型支持工具调用。其他模型（reasoner、视觉模型）自动禁用工具。

代码中的控制：
```python
enable_tools = request.model in ["deepseek-chat", None]
```

## 环境配置

### DuckDuckGo（默认）
无需配置，开箱即用！

### SerpAPI（可选）
在 `.env` 文件添加：
```
SERPAPI_API_KEY=your_api_key
```

注意：`SERPAPI_API_KEY` 在代码中的 `pydantic` 配置对应字段为 `serpapi_api_key`（小写）。请确保 `config.py` 中包含 `serpapi_api_key` 字段或将 `Settings.Config.extra` 设置为 `ignore`，否则在读取 `.env` 时会触发验证错误。示例 `.env`：

```env
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
SERPAPI_API_KEY=your_serpapi_key_here
```

### Tavily（可选）
在 `.env` 文件添加：
```
TAVILY_API_KEY=your_api_key
```

### 如何获取 SerpAPI 与 Tavily 的 API Key

以下是获取两个可选搜索提供方 API Key 的快速指南：

- SerpAPI
  1. 访问 SerpAPI 官网： https://serpapi.com
  2. 注册账号（可使用邮箱注册或使用 GitHub/Google 登录）
  3. 登录后进入 Dashboard -> API Key（或 Account）页面
  4. 复制你的 API Key，并将其写入后端的 `.env`：`SERPAPI_API_KEY=你的_key`
  5. （可选）阅读 SerpAPI 的文档，了解配额与付费计划：https://serpapi.com/pricing

- Tavily
  > Tavily 是一个示例的商业搜索/聚合 API（如果你使用的是其它提供者，按类似流程操作）。
  1. 访问 Tavily 服务页面（或你所使用的聚合搜索服务）的注册页面。若无明确网址，请联系你的服务提供方获取注册入口。
  2. 注册并验证邮箱/账号。
  3. 在用户控制台或 API 管理页面创建/查看你的 API Key。
  4. 将 Key 填入后端 `.env`：`TAVILY_API_KEY=你的_key`
  5. 注意阅读服务的调用限制与费用说明，确保在生产中合理使用。

安全性提示：
- 请不要将 API Key 提交到公共仓库。将它们放在服务器的 `.env` 文件或受限的密钥管理服务（如 AWS Secrets Manager、Azure Key Vault）中。
- 若你在团队中共享代码，请用 `.env.example` 提示需要哪些环境变量，而不要包含真实 Key。

## 测试命令

```bash
# 安装依赖
cd ocr_rag/backend
pip install -r requirements.txt

# 启动服务
python start.py

# 测试搜索工具（可选）
python test_search_simple.py
```

## 扩展自定义工具

要添加新工具，只需：

1. 在 `web_search_tool.py` 中定义新的 `@tool` 函数
2. 添加到 `WEB_SEARCH_TOOLS` 列表
3. 重启服务即可！

示例：
```python
@tool
async def get_weather(city: str) -> str:
    """获取城市天气"""
    # 实现天气查询
    return f"{city}的天气信息..."

WEB_SEARCH_TOOLS = [
    web_search,
    search_recent_news,
    get_weather  # 新工具
]
```

## 优势

✅ **无缝集成** - 前端无需改动  
✅ **自动判断** - 模型智能决定何时搜索  
✅ **流式反馈** - 实时显示搜索过程  
✅ **易于扩展** - 添加新工具非常简单  
✅ **无需 API** - 默认使用免费的 DuckDuckGo

## 注意事项

1. 网络搜索需要稳定的网络连接
2. 搜索结果质量依赖于搜索引擎
3. DuckDuckGo 可能有请求频率限制
4. 工具调用会增加响应时间
5. 目前仅 deepseek-chat 支持工具调用

享受增强的 RAG 系统吧！🎉
