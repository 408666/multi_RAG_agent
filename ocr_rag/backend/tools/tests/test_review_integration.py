import asyncio

from main import execute_tool_calls
from langchain_core.messages import HumanMessage


class FakeSearchTool:
    name = 'web_search'

    async def ainvoke(self, args):
        return (
            "[1] 测试标题\n"
            "📝 这是一个关于人工智能的测试摘要，包含最近的事件和数据。\n"
            "🔗 http://example.com/article\n"
            "📍 来源: 测试来源\n\n"
        )


def test_review_merging_behavior():
    tool_call = {'name': 'web_search', 'args': {'query': '人工智能 最新 新闻', 'max_results': 3}, 'id': 'test-1'}
    messages = [HumanMessage(content='请告诉我最近的人工智能新闻')]
    import main
    orig_web_tools = list(getattr(main, 'WEB_SEARCH_TOOLS', []))
    try:
        main.WEB_SEARCH_TOOLS = [FakeSearchTool()]
        tool_messages = asyncio.get_event_loop().run_until_complete(execute_tool_calls([tool_call], messages))
        assert len(tool_messages) >= 1
        combined = '\n'.join([tm.content for tm in tool_messages])
        assert '[REVIEW_RESULTS]' in combined
    finally:
        main.WEB_SEARCH_TOOLS = orig_web_tools
