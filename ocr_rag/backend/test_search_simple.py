"""
简单测试网络搜索工具
"""
import asyncio
from web_search_tool import web_search


async def main():
    print("测试网络搜索工具...")
    
    try:
        result = await web_search.ainvoke({"query": "Python", "max_results": 2})
        print("\n搜索成功!")
        print("结果预览:")
        print(result[:300])
        print("\n✅ 测试通过!")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
