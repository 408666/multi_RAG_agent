import os
import sys
from pathlib import Path

# 添加 backend 目录到 sys.path
backend_dir = Path(__file__).parent
sys.path.append(str(backend_dir))

from dotenv import load_dotenv
load_dotenv()

from tools.web_search_tool import get_search_tool

def test_default_engine():
    print("Testing default search engine...")
    try:
        tool = get_search_tool()
        print(f"Default search engine: {tool.search_engine}")
        
        if tool.search_engine == "serpapi":
            print("✅ Default engine is SerpAPI")
        else:
            print(f"❌ Default engine is {tool.search_engine}, expected serpapi")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_default_engine()
