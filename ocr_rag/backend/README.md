# 多模态 RAG 工作台 - 后端 API

基于 LangChain 1.0 的智能对话后端服务，支持 DeepSeek 等最新模型。

## 🚀 快速开始

### 1. 安装依赖

```bash
cd backend
pip install -r requirements.txt
```


### 2. 配置 API Key

有两种方式配置 API Key：

#### 方法一：修改 `env_config.py` 文件中的 DeepSeek API Key：

```python
os.environ["OPENAI_API_KEY"] = "your_actual_deepseek_api_key_here"
```

#### 方法二：复制 `.env.example` 文件为 `.env` 并填写 API Key：

```bash
cp .env.example .env
```

然后编辑 `.env` 文件，填写你的 DeepSeek API Key：

```
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### 3. 启动服务

```bash
python start.py
```

服务将在 `http://localhost:8000` 启动

## 📚 API 接口

### 流式聊天接口
- **URL**: `POST /api/chat/stream`
- **Content-Type**: `application/json`
- **Response**: `text/event-stream`

```json
{
  "content": "你好",
  "history": [],
  "model": "deepseek-chat",
  "knowledge_base": "default"
}
```

### 同步聊天接口
- **URL**: `POST /api/chat`
- **Content-Type**: `application/json`

### 健康检查
- **URL**: `GET /`

### 模型列表
- **URL**: `GET /api/models`

### 知识库列表
- **URL**: `GET /api/knowledge-bases`

## 🧪 测试

运行测试客户端：

```bash
python test_client.py
```

## 📖 API 文档

访问 `http://localhost:8000/docs` 查看交互式 API 文档。

## 🔧 配置说明

### 支持的模型
- `deepseek-chat` - DeepSeek通用对话模型
- `deepseek-coder` - DeepSeek代码专用模型

### 环境变量
- `OPENAI_API_KEY` - DeepSeek API 密钥
- `OPENAI_BASE_URL` - API 基础URL (默认为 https://api.deepseek.com/v1)
- `HOST` - 服务器主机
- `PORT` - 服务器端口
- `DEBUG` - 调试模式
- `LOG_LEVEL` - 日志级别

## 🔗 前端对接

前端通过 `src/api/chat.ts` 与后端通信，支持：
- 流式文本响应
- 历史对话管理
- 错误处理
- 模型切换

## 🔧 可用工具（扩展说明）

后端现在集成了若干可供模型调用的工具，模型可以在对话中自动决定是否使用这些工具来增强回答质量（例如获取实时信息或执行检索）。以下是当前已集成的两个主要工具：

- **网络搜索工具（web_search / search_recent_news）**
  - 功能：在互联网上检索实时信息，默认使用 DuckDuckGo（无需 API Key），并可选支持 SerpAPI 或 Tavily 以获得更结构化/更多源的结果。
  - 提供的工具：
    - `web_search(query, max_results)` — 通用网络搜索，返回格式化的文本结果。
    - `search_recent_news(topic, days)` — 用于拉取最近几天的新闻（后端会把当前日期插入查询以提高时效性）。
  - 集成与流程：
    - 模型在对话中识别需要检索信息时发出 `tool_calls`。
    - 后端执行对应搜索工具并通过 SSE 发出 `tool_results`（以及搜索摘要的日志）。
    - 模型基于检索结果生成回答并返回给用户。
  - 前端事件流（SSE）：后端会发送 `tool_calls`、`tool_results`、`content_delta`、`message_complete` 四类事件，前端可据此展示工具调用与搜索过程。
  - 启用说明：
    - 默认 DuckDuckGo 可开箱即用；如需更强检索能力，可配置 SerpAPI 或 Tavily。

  环境配置与 API Key 获取
  - DuckDuckGo（默认）：无需配置，开箱即用。

  - SerpAPI（可选）
    1. 访问 SerpAPI 官网： https://serpapi.com
    2. 注册账号（邮箱或使用 GitHub/Google 登录）并登录。
    3. 在 Dashboard／Account 页面找到你的 API Key。
    4. 在后端的 `.env` 中添加：
       ```
       SERPAPI_API_KEY=your_api_key
       ```
    5. 可选：阅读 SerpAPI 的配额与计费说明，合理规划调用频率（https://serpapi.com/pricing）。

    注意：在代码中该配置对应 `Settings` 的字段名为 `serpapi_api_key`（小写）。如果你在 `.env` 中使用大写 `SERPAPI_API_KEY`，Pydantic 会把它映射到 `serpapi_api_key`，但 `config.py` 需要包含该字段以避免启动时的验证错误。示例 `.env`：

    ```env
    OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
    SERPAPI_API_KEY=your_serpapi_key_here
    ```

  - Tavily（可选）
    1. 访问 Tavily 或你所选的聚合搜索服务的官网并注册账号（若是内部/商业服务，请向供应商索取接入信息）。
    2. 在用户控制台创建或查看 API Key。
    3. 在后端的 `.env` 中添加：
       ```
       TAVILY_API_KEY=your_api_key
       ```
    4. 注意服务的调用限制与计费规则，避免意外费用。

  - 安全性建议
    - 切勿把 API Key 提交到公共仓库；在开发仓库中使用 `.env` 或机密管理服务（如 Vault、AWS Secrets Manager）。
    - 在仓库中提交 `.env.example` 指示所需的环境变量，但不要包含真实密钥。

  测试与扩展
  - 启动并测试：
    ```bash
    cd ocr_rag/backend
    pip install -r requirements.txt
    python start.py
    # 或运行测试脚本
    python test_search_simple.py
    ```
  - 添加新工具：在 `tools/web_search_tool.py` 中定义 `@tool` 并添加到 `WEB_SEARCH_TOOLS` 列表，重启后端即可生效。

  注意事项
  - 网络搜索依赖外部服务，结果质量和速度随搜索引擎与网络状况而异。
  - 搜索调用会增加响应延迟；在高并发场景下考虑限流或缓存策略。

- **时间工具（get_current_time）**
  - 功能：返回当前的日期、时间及星期，供模型正确理解“今天/现在/最近”等时间概念；在执行时事检索时，模型应先调用此工具并把返回的日期包含到搜索查询中以提高时效性。
  - 提供的工具：`get_current_time()` — 返回格式化的时间信息（日期/星期/时间/完整时间字符串）并包含使用提示。
  - 使用场景示例：
    - 用户："今天有什么人工智能的新闻？"
      1. 模型调用 `get_current_time()` → 获得 "2025-11-22"
      2. 模型调用 `search_recent_news("人工智能", days=7)`（后端会将日期附加到内部查询）
      3. 返回带日期的搜索结果，模型基于结果生成回答。
    - 用户："现在几点了？" → 直接调用 `get_current_time()` 并把结果展示给用户。
  - 返回示例：

  ```
  当前时间信息：
  📅 日期: 2025年11月22日
  📆 星期: 星期六
  🕐 时间: 15:53:46
  🌍 完整时间: 2025-11-22 15:53:46

  提示：在搜索时事新闻或最新信息时，请在搜索查询中包含此日期，以获得更准确的结果。
  ```

  配置与调试
  - 默认开箱即用：`get_current_time` 不需要外部 API。
  - 若需在受控环境禁用：在 `main.py` 的入口处将 `enable_tools` 设为 `False`，或将该选项暴露到 `config.py` 中进行集中管理。
  - 调试示例（查看日志）：
    ```bash
    tail -f logs/app.log | grep "工具"
    ```
    你将看到工具调用与时间/搜索相关的日志记录。


## 使用示例

1. 用户问：“今天有什么人工智能的新闻？”
   - 模型调用 `get_current_time()` 获取当前日期
   - 模型调用 `search_recent_news("人工智能", days=7)`（后端自动在查询中加入日期）
   - 后端返回搜索结果，模型基于结果生成最终回答

2. 用户问：“现在几点了？”
   - 模型直接调用 `get_current_time()` 并把返回的时间信息展示给用户

## 调试与扩展

- 查看工具调用日志：检查后端日志可以看到工具调用和搜索行为的详细记录
- 添加工具：在 `tools/web_search_tool.py` 中添加新的 `@tool` 并把工具加入 `WEB_SEARCH_TOOLS` 列表，然后重启后端即可

更多详细说明请参阅仓库下的 `tools/guides/WEB_SEARCH_GUIDE.md` 和 `tools/guides/TIME_TOOL_GUIDE.md`。

## 🛡️ 新增：搜索结果审查工具（automatic review）

后端新增了一个**搜索结果审查工具**，用于在模型调用网络搜索后自动评估返回结果的相关性与时间一致性，避免模型直接把基于关键词但不相关或过时的搜索片段作为最终证据引用。

主要特性：
- 自动触发：当后端执行以 `web_search` / `search_recent_news` 等搜索类工具时，系统会在后台自动调用 `review_search_results` 审查工具并把审查结果作为额外的工具消息返回给模型；前端通过 SSE 会收到对应的 `tool_results`，其中会包含审查结果。
- 输出结构化：`review_search_results` 返回一个 JSON 字符串，包含 `summary`, `recommendations`, `entries` 等字段。每个 `entry` 包含 `index, title, snippet, url, source, relevance_score, recency_score, final_score, reasons`，方便模型或前端做可信度判断与展示。
- 轻量评分策略：基于关键词重合（相关性）与时间一致性（是否含当前日期、是否提及“最近/今天/昨日”等词、年份匹配等）计算最终分数。

工具接口示例：

- 调用参数（自动由后端传入）：
  - `formatted_results`：来自 `web_search` 的格式化文本
  - `user_question`：用户的原始问题文本（后端会从最近的用户消息中提取）
  - `current_date`：当前日期字符串（例如 `2025-11-22`）

- 返回示例（JSON）：
```
{
  "summary": "共解析到 5 条结果，推荐使用 2 条。",
  "recommendations": [1,3],
  "entries": [
    {
      "index": 1,
      "title": "...",
      "snippet": "...",
      "relevance_score": 0.45,
      "recency_score": 0.8,
      "final_score": 0.545,
      "reasons": ["关键词匹配(0.45)", "时间信息与查询高度一致"]
    }
  ]
}
```

如何解读：
- `final_score` 越高表示该条搜索结果越值得被引用（默认阈值 0.4，会作为推荐标准）。
- `recommendations` 列表给出按阈值/排序选择的推荐索引，模型在生成最终答案时应优先使用这些条目并在回答中作出处引用标注。

可配置项（未来可扩展）：
- 将审查阈值、权重（相关性 vs 时间）以及是否自动触发的开关放入配置文件，便于产品化调整。

示例日志：
- 当模型触发搜索时，后端日志会包含搜索摘要（info）与完整搜索结果（debug），随后会记录审查工具的执行与输出摘要，便于离线审计。

如果需要，我可以：
- 将审查结果同时写入独立日志文件 `logs/search_reviews.log`（便于审计）；
- 把审查工具的参数（阈值/权重）提到 `config.py` 进行可配置化。