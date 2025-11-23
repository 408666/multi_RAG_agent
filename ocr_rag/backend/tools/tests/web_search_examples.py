"""
网络搜索工具集成示例和测试

演示如何在对话中自动触发网络搜索
"""

# ============ 示例 1: 搜索实时信息 ============
"""
用户: Python 3.13 有哪些新特性？

后端处理流程：
1. 模型接收问题
2. 识别需要搜索最新信息
3. 自动调用 web_search("Python 3.13 新特性")
4. 获取搜索结果
5. 基于搜索结果生成回答

前端接收事件：
{
  "type": "tool_calls",
  "tools": [{"name": "web_search", "args": {"query": "Python 3.13 新特性"}}]
}
→ {
  "type": "tool_results", 
  "results": [{"tool": "web_search", "content": "搜索结果..."}]
}
→ {
  "type": "content_delta",
  "content": "Python 3.13 的新特性包括..."
}
"""

# ============ 示例 2: 搜索新闻 ============
"""
用户: 最近AI领域有什么新闻？

后端自动调用：
search_recent_news("AI", days=7)

返回最近7天的AI新闻
"""

# ============ 示例 3: 结合 PDF 和搜索 ============
"""
用户上传了一篇2020年的论文，然后问：
"这篇论文的方法现在还有效吗？最新的研究进展如何？"

后端处理：
1. 读取 PDF 内容（RAG）
2. 识别需要最新信息
3. 调用 web_search("论文标题 最新研究进展 2024")
4. 综合 PDF 内容和搜索结果回答

这就是 RAG + 实时搜索的威力！
"""

# ============ 代码集成示例 ============

# main.py 中的关键代码：
"""
# 1. 导入工具
from web_search_tool import WEB_SEARCH_TOOLS

# 2. 创建带工具的模型
model = get_chat_model_with_tools(model_name, enable_tools=True)

# 3. 流式响应中自动处理工具调用
async def generate_streaming_response_with_tools(...):
    while iteration < max_iterations:
        response = await model.ainvoke(messages)
        
        # 检查工具调用
        if response.tool_calls:
            # 执行工具
            tool_messages = await execute_tool_calls(response.tool_calls, messages)
            # 添加工具结果到消息
            messages.extend(tool_messages)
            # 继续下一轮
            continue
        
        # 没有工具调用，输出最终答案
        break
"""

# ============ 测试 API 调用 ============
"""
使用 curl 测试：

curl -X POST http://localhost:8000/api/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "content": "2024年人工智能有哪些突破？",
    "content_blocks": [{
      "type": "text",
      "content": "2024年人工智能有哪些突破？"
    }],
    "model": "deepseek-chat",
    "history": [],
    "pdf_chunks": null,
    "knowledge_base": "default"
  }'

预期响应：
data: {"type":"tool_calls","tools":[{"name":"web_search","args":{"query":"2024年人工智能突破"}}]}

data: {"type":"tool_results","results":[...]}

data: {"type":"content_delta","content":"根据搜索结果..."}
...
"""

# ============ 自定义工具示例 ============
"""
在 web_search_tool.py 中添加新工具：

@tool
async def calculate(expression: str) -> str:
    '''执行数学计算'''
    result = eval(expression)
    return f"计算结果: {result}"

@tool  
async def get_current_time() -> str:
    '''获取当前时间'''
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# 添加到工具列表
WEB_SEARCH_TOOLS = [
    web_search,
    search_recent_news,
    calculate,
    get_current_time
]

然后模型就能使用这些工具了！
"""

# ============ 前端显示工具调用（可选）============
"""
如果想在前端显示工具调用过程，在 chat.ts 中添加处理：

const eventSource = new EventSource(...);

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  if (data.type === 'tool_calls') {
    // 显示 "正在搜索: xxx"
    onToolCall?.(data.tools);
  }
  
  if (data.type === 'tool_results') {
    // 显示 "搜索完成，正在分析..."
    onToolResult?.(data.results);
  }
  
  if (data.type === 'content_delta') {
    // 正常的流式文本
    onChunk?.(data.content);
  }
};
"""

print("✅ 网络搜索工具已成功集成！")
print("📖 详细文档请查看: WEB_SEARCH_GUIDE.md")
print("🚀 启动服务: python start.py")
