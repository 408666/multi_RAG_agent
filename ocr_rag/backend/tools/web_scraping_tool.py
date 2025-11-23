"""
网页抓取工具模块
用于访问特定URL并提取网页内容
"""
import asyncio
import requests
from bs4 import BeautifulSoup
from typing import Optional, Dict, Any
from urllib.parse import urlparse, urljoin
from loguru import logger
from langchain_core.tools import tool


class WebScraper:
    """网页抓取工具类"""

    def __init__(self, timeout: int = 30, max_content_length: int = 50000):
        """
        初始化网页抓取工具

        Args:
            timeout: 请求超时时间（秒）
            max_content_length: 最大内容长度限制
        """
        self.timeout = timeout
        self.max_content_length = max_content_length
        self.session = requests.Session()

        # 设置请求头，模拟浏览器
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })

    def _is_valid_url(self, url: str) -> bool:
        """验证URL是否有效"""
        try:
            parsed = urlparse(url)
            return bool(parsed.scheme and parsed.netloc)
        except Exception:
            return False

    def _extract_main_content(self, soup: BeautifulSoup, url: str) -> str:
        """
        从HTML中提取主要内容

        Args:
            soup: BeautifulSoup对象
            url: 原始URL

        Returns:
            提取的文本内容
        """
        # 移除不需要的元素
        for element in soup.find_all(['script', 'style', 'nav', 'header', 'footer', 'aside', 'advertisement']):
            element.decompose()

        # 尝试多种策略提取主要内容
        content_selectors = [
            'main',
            '[role="main"]',
            '.main-content',
            '.content',
            '.article-content',
            '.post-content',
            '#main',
            '#content',
            '.entry-content'
        ]

        main_content = None
        for selector in content_selectors:
            main_content = soup.select_one(selector)
            if main_content:
                break

        # 如果没找到特定内容区域，使用body
        if not main_content:
            main_content = soup.find('body') or soup

        # 提取文本
        text = main_content.get_text(separator='\n', strip=True)

        # 清理文本
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        cleaned_text = '\n\n'.join(lines)

        return cleaned_text

    def _get_page_info(self, soup: BeautifulSoup, url: str) -> Dict[str, str]:
        """获取页面基本信息"""
        title = soup.find('title')
        title_text = title.get_text().strip() if title else "无标题"

        # 尝试获取描述
        description = ""
        meta_desc = soup.find('meta', attrs={'name': 'description'}) or soup.find('meta', attrs={'property': 'og:description'})
        if meta_desc:
            description = meta_desc.get('content', '').strip()

        return {
            'title': title_text,
            'description': description,
            'url': url
        }

    async def scrape_url(self, url: str) -> Dict[str, Any]:
        """
        抓取指定URL的内容

        Args:
            url: 要抓取的URL

        Returns:
            包含页面信息和内容的字典
        """
        if not self._is_valid_url(url):
            return {
                'error': f'无效的URL: {url}',
                'content': '',
                'title': '',
                'description': '',
                'url': url
            }

        try:
            logger.info(f"🌐 开始抓取网页: {url}")

            # 在线程池中执行同步请求
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.session.get(url, timeout=self.timeout, allow_redirects=True)
            )

            response.raise_for_status()

            # 检查内容类型
            content_type = response.headers.get('content-type', '').lower()
            if 'text/html' not in content_type:
                return {
                    'error': f'不支持的内容类型: {content_type}',
                    'content': '',
                    'title': '',
                    'description': '',
                    'url': url
                }

            # 解析HTML
            soup = BeautifulSoup(response.content, 'lxml')

            # 获取页面信息
            page_info = self._get_page_info(soup, url)

            # 提取主要内容
            content = self._extract_main_content(soup, url)

            # 限制内容长度
            if len(content) > self.max_content_length:
                content = content[:self.max_content_length] + "...\n\n[内容已截断]"

            result = {
                'title': page_info['title'],
                'description': page_info['description'],
                'content': content,
                'url': url,
                'status_code': response.status_code,
                'content_length': len(content)
            }

            logger.info(f"✅ 网页抓取成功: {page_info['title']} ({len(content)} 字符)")
            return result

        except requests.exceptions.RequestException as e:
            error_msg = f"网络请求错误: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return {
                'error': error_msg,
                'content': '',
                'title': '',
                'description': '',
                'url': url
            }
        except Exception as e:
            error_msg = f"网页抓取失败: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return {
                'error': error_msg,
                'content': '',
                'title': '',
                'description': '',
                'url': url
            }


# 创建全局抓取工具实例
_scraper_instance = None


def get_web_scraper() -> WebScraper:
    """获取网页抓取工具实例（单例模式）"""
    global _scraper_instance
    if _scraper_instance is None:
        _scraper_instance = WebScraper()
    return _scraper_instance


@tool
async def fetch_webpage(url: str) -> str:
    """
    访问指定的网页URL并提取其内容

    Args:
        url: 要访问的完整URL，必须包含http://或https://

    Returns:
        格式化的网页内容，包括标题、描述和正文

    Examples:
        - "https://www.example.com/article"
        - "https://news.sina.com.cn/c/2024-01-01/doc-abc123"
    """
    logger.info(f"🔗 访问网页: {url}")

    try:
        scraper = get_web_scraper()
        result = await scraper.scrape_url(url)

        if 'error' in result:
            return f"❌ 访问失败: {result['error']}"

        # 格式化输出
        formatted = f"📄 网页标题: {result['title']}\n"
        if result['description']:
            formatted += f"📝 页面描述: {result['description']}\n"
        formatted += f"🔗 URL: {result['url']}\n"
        formatted += f"📊 内容长度: {result['content_length']} 字符\n\n"
        formatted += f"📖 页面内容:\n{'-'*50}\n{result['content']}"

        return formatted

    except Exception as e:
        error_msg = f"网页抓取工具执行失败: {str(e)}"
        logger.error(f"❌ {error_msg}")
        return error_msg


# 导出工具列表
WEB_SCRAPING_TOOLS = [
    fetch_webpage
]