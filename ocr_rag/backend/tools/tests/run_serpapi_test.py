from pathlib import Path
import sys
import asyncio
from dotenv import load_dotenv

# 确保 backend 目录在 sys.path
# 修正路径：从 tests -> tools -> backend
backend_dir = Path(__file__).parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.append(str(backend_dir))

# 加载 .env
load_dotenv(dotenv_path=backend_dir / '.env')

from tools.web_search_tool import get_search_tool


async def run_search():
    tool = get_search_tool(search_engine='serpapi', max_results=3)
    print(f"Using engine: {tool.search_engine}")
    results = await tool.search('Python 异步编程最佳实践', language='zh-CN')
    print('--- Search Results ---')
    for i, r in enumerate(results, 1):
        print(i, r.get('title'))
        print(r.get('snippet'))
        print(r.get('url'))
        print('source:', r.get('source'))
        print()


if __name__ == '__main__':
    asyncio.run(run_search())
