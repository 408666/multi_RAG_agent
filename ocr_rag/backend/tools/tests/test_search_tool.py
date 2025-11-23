"""
测试：tools 下的网络搜索工具
"""
import asyncio
from loguru import logger

from tools.web_search_tool import web_search, search_recent_news, get_search_tool


async def test_web_search():
    logger.info("测试 tools.web_search_tool:web_search")
    query = "Python 异步编程教程"
    result = await web_search.ainvoke({"query": query, "max_results": 3})
    print(result[:500] if isinstance(result, str) else str(result))


async def test_recent_news():
    logger.info("测试 tools.web_search_tool:search_recent_news")
    result = await search_recent_news.ainvoke({"topic": "人工智能", "days": 3})
    print(result[:500] if isinstance(result, str) else str(result))


async def test_search_tool_directly():
    logger.info("测试直接使用 get_search_tool")
    search_tool = get_search_tool(max_results=3)
    results = await search_tool.search("FastAPI 教程")
    for i, r in enumerate(results, 1):
        print(i, r.get('title'), r.get('source'))


async def main():
    await test_web_search()
    await asyncio.sleep(0.5)
    await test_recent_news()
    await asyncio.sleep(0.5)
    await test_search_tool_directly()


if __name__ == '__main__':
    asyncio.run(main())
