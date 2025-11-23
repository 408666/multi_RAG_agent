"""
测试：tools 下的时间工具
"""
import asyncio

from tools.web_search_tool import get_current_time, search_recent_news


async def main():
    result = await get_current_time.ainvoke({})
    print(result)
    news = await search_recent_news.ainvoke({"topic": "人工智能", "days": 3})
    print(news[:500])


if __name__ == '__main__':
    asyncio.run(main())
