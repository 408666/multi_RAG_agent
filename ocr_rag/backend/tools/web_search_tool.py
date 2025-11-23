"""
网络搜索工具模块（迁移到 tools 目录）
支持多种搜索引擎：DuckDuckGo、SerpAPI、Tavily
"""
import os
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
from loguru import logger
from langchain_core.tools import tool


class WebSearchTool:
    """网络搜索工具类"""
    
    def __init__(self, search_engine: str = "duckduckgo", max_results: int = 5):
        self.search_engine = search_engine
        self.max_results = max_results
        self.searcher = None
        self._initialize_searcher()

    def _initialize_searcher(self):
        try:
            if self.search_engine == "duckduckgo":
                from langchain_community.tools import DuckDuckGoSearchRun
                self.searcher = DuckDuckGoSearchRun()
                logger.info("✅ 初始化 DuckDuckGo 搜索引擎")
            elif self.search_engine == "serpapi":
                from langchain_community.utilities import SerpAPIWrapper
                api_key = os.getenv("SERPAPI_API_KEY")
                if not api_key:
                    raise ValueError("未找到 SERPAPI_API_KEY 环境变量")
                self.searcher = SerpAPIWrapper(serpapi_api_key=api_key)
                logger.info("✅ 初始化 SerpAPI 搜索引擎")
            elif self.search_engine == "tavily":
                from langchain_community.tools.tavily_search import TavilySearchResults
                api_key = os.getenv("TAVILY_API_KEY")
                if not api_key:
                    raise ValueError("未找到 TAVILY_API_KEY 环境变量")
                self.searcher = TavilySearchResults(api_key=api_key, max_results=self.max_results)
                logger.info("✅ 初始化 Tavily 搜索引擎")
            else:
                raise ValueError(f"不支持的搜索引擎: {self.search_engine}")
        except Exception as e:
            logger.error(f"❌ 搜索引擎初始化失败: {e}")
            if self.search_engine != "duckduckgo":
                logger.warning("⚠️ 降级使用 DuckDuckGo 搜索引擎")
                self.search_engine = "duckduckgo"
                try:
                    from langchain_community.tools import DuckDuckGoSearchRun
                    self.searcher = DuckDuckGoSearchRun()
                except Exception as fallback_error:
                    logger.error(f"❌ DuckDuckGo 初始化也失败: {fallback_error}")
                    self.searcher = None

    async def search(self, query: str, language: str = "zh-CN") -> List[Dict[str, Any]]:
        if not self.searcher:
            logger.error("❌ 搜索引擎未初始化")
            return [{
                "title": "搜索错误",
                "snippet": "搜索引擎未正确初始化",
                "url": "",
                "source": "error"
            }]
        try:
            logger.info(f"🔍 开始搜索: {query}")
            if self.search_engine == "duckduckgo":
                results = await self._search_duckduckgo(query)
            elif self.search_engine == "serpapi":
                results = await self._search_serpapi(query, language)
            elif self.search_engine == "tavily":
                results = await self._search_tavily(query)
            else:
                results = []
            logger.info(f"✅ 搜索完成，找到 {len(results)} 条结果")
            return results
        except Exception as e:
            logger.error(f"❌ 搜索失败: {e}")
            return [{
                "title": "搜索错误",
                "snippet": f"搜索时发生错误: {str(e)}",
                "url": "",
                "source": "error"
            }]

    async def _search_duckduckgo(self, query: str) -> List[Dict[str, Any]]:
        try:
            loop = asyncio.get_event_loop()
            result_text = await loop.run_in_executor(None, self.searcher.run, query)
            results = []
            snippets = result_text.split('\n\n')
            for i, snippet in enumerate(snippets[:self.max_results], 1):
                if snippet.strip():
                    results.append({
                        "title": f"结果 {i}",
                        "snippet": snippet.strip(),
                        "url": "",
                        "source": "DuckDuckGo"
                    })
            return results
        except Exception as e:
            logger.error(f"❌ DuckDuckGo 搜索失败: {e}")
            raise

    async def _search_serpapi(self, query: str, language: str) -> List[Dict[str, Any]]:
        try:
            loop = asyncio.get_event_loop()
            # 使用 results 方法获取结构化数据，而不是 run 方法（返回字符串）
            raw_results = await loop.run_in_executor(None, self.searcher.results, query)
            results = []
            if isinstance(raw_results, dict):
                organic_results = raw_results.get("organic_results", [])[:self.max_results]
                for item in organic_results:
                    results.append({
                        "title": item.get("title", ""),
                        "snippet": item.get("snippet", ""),
                        "url": item.get("link", ""),
                        "source": "Google (SerpAPI)"
                    })
            return results
        except Exception as e:
            logger.error(f"❌ SerpAPI 搜索失败: {e}")
            raise

    async def _search_tavily(self, query: str) -> List[Dict[str, Any]]:
        try:
            loop = asyncio.get_event_loop()
            raw_results = await loop.run_in_executor(None, self.searcher.run, query)
            results = []
            if isinstance(raw_results, list):
                for item in raw_results[:self.max_results]:
                    results.append({
                        "title": item.get("title", ""),
                        "snippet": item.get("content", ""),
                        "url": item.get("url", ""),
                        "source": "Tavily"
                    })
            return results
        except Exception as e:
            logger.error(f"❌ Tavily 搜索失败: {e}")
            raise

    def format_results(self, results: List[Dict[str, Any]], max_length: int = 500) -> str:
        if not results:
            return "未找到相关搜索结果。"
        formatted = "🔍 网络搜索结果：\n\n"
        for i, result in enumerate(results, 1):
            title = result.get("title", "无标题")
            snippet = result.get("snippet", "无描述")
            url = result.get("url", "")
            source = result.get("source", "未知来源")
            if len(snippet) > max_length:
                snippet = snippet[:max_length] + "..."
            formatted += f"[{i}] {title}\n"
            formatted += f"📝 {snippet}\n"
            if url:
                formatted += f"🔗 {url}\n"
            formatted += f"📍 来源: {source}\n\n"
        return formatted


# 单例实例
_search_tool_instance = None


def get_search_tool(search_engine: str = "serpapi", max_results: int = 5) -> WebSearchTool:
    global _search_tool_instance
    if _search_tool_instance is None:
        _search_tool_instance = WebSearchTool(search_engine, max_results)
    return _search_tool_instance


@tool
async def web_search(query: str, max_results: int = 5) -> str:
    """在互联网上搜索信息并返回格式化结果文本。

    Args:
        query: 搜索查询，应该是清晰、具体的问题或关键词。
        max_results: 返回的最大结果数（默认5条）。

    Returns:
        格式化的搜索结果字符串，包含每条结果的序号、片段和来源信息。
    """
    logger.info(f"🔍 执行网络搜索: {query}")
    try:
        search_tool = get_search_tool(max_results=max_results)
        results = await search_tool.search(query)
        formatted_results = search_tool.format_results(results)
        return formatted_results
    except Exception as e:
        error_msg = f"搜索失败: {str(e)}"
        logger.error(f"❌ {error_msg}")
        return error_msg


@tool
async def search_recent_news(topic: str, days: int = 7) -> str:
    """搜索最近若干天内的新闻，并返回格式化的新闻列表文本。

    Args:
        topic: 新闻主题关键词。
        days: 向前搜索的天数范围（默认7天）。

    Returns:
        格式化的新闻搜索结果字符串。
    """
    logger.info(f"📰 搜索最近新闻: {topic} (最近{days}天)")
    try:
        from datetime import datetime
        current_date = datetime.now().strftime("%Y年%m月%d日")
        query = f"{current_date} {topic} 最近{days}天 新闻"
        search_tool = get_search_tool(max_results=5)
        results = await search_tool.search(query)
        formatted_results = search_tool.format_results(results)
        return formatted_results
    except Exception as e:
        error_msg = f"新闻搜索失败: {str(e)}"
        logger.error(f"❌ {error_msg}")
        return error_msg


@tool
async def get_current_time() -> str:
    """返回当前的日期、时间和星期信息，供模型用于时间敏感查询。

    Returns:
        包含本地日期、星期和时间的多行字符串，示例：
        "当前时间信息：\n📅 日期: 2025年11月22日\n📆 星期: 星期六\n🕐 时间: 15:53:46\n..."
    """
    from datetime import datetime
    now = datetime.now()
    weekday_names = {
        0: "星期一", 1: "星期二", 2: "星期三", 3: "星期四",
        4: "星期五", 5: "星期六", 6: "星期日"
    }
    weekday = weekday_names[now.weekday()]
    time_info = f"""当前时间信息：\n📅 日期: {now.strftime("%Y年%m月%d日")}\n📆 星期: {weekday}\n🕐 时间: {now.strftime("%H:%M:%S")}\n🌍 完整时间: {now.strftime("%Y-%m-%d %H:%M:%S")}\n\n提示：在搜索时事新闻或最新信息时，请在搜索查询中包含此日期，以获得更准确的结果。"""
    logger.info(f"🕐 返回当前时间: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    return time_info


WEB_SEARCH_TOOLS = [
    web_search,
    search_recent_news,
    get_current_time
]
