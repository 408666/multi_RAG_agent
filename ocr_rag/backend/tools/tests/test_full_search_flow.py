import asyncio
import json
import sys
from pathlib import Path
from dotenv import load_dotenv

# Setup path
backend_dir = Path(__file__).parent
sys.path.append(str(backend_dir))

# Load env
load_dotenv(backend_dir / '.env')

from tools.web_search_tool import web_search
from tools.search_review_tool import review_search_results

async def test_flow():
    query = "2025年11月22日 Gemini 3.0 发布 最近30天 新闻"
    print(f"1. Executing search for: {query} (max_results=20)")
    
    try:
        # Invoke web_search tool
        # Note: The tool expects 'query' and 'max_results'
        search_result_text = await web_search.ainvoke({"query": query, "max_results": 20})
    except Exception as e:
        print(f"Search failed: {e}")
        return

    print(f"Search returned text length: {len(search_result_text)}")
    # Count items roughly
    count = search_result_text.count("📍 来源:")
    print(f"Raw result count: {count}")
    
    if count == 0:
        print("No results found. Check API key or network.")
        print("Raw output:", search_result_text[:500])
        return

    # 2. Review
    print("\n2. Executing review...")
    try:
        review_json_str = await review_search_results.ainvoke({
            "formatted_results": search_result_text,
            "user_question": query,
            "current_date": "2025-11-22"
        })
    except Exception as e:
        print(f"Review failed: {e}")
        return
    
    # 3. Filter (Logic from main.py)
    print("\n3. Applying filtering logic...")
    try:
        review_json = json.loads(review_json_str)
        recommendations = review_json.get('recommendations', [])
        entries = review_json.get('entries', [])
        
        print(f"Review summary: {review_json.get('summary')}")
        print(f"Recommendations indices: {recommendations}")
        
        # Logic from main.py
        if recommendations and entries:
            entry_map = {e['index']: e for e in entries}
            final_entries = []
            for idx in recommendations[:10]:
                if idx in entry_map:
                    final_entries.append(entry_map[idx])
            
            # Fill up to 10 if needed
            if len(final_entries) < 10:
                existing_indices = set(e['index'] for e in final_entries)
                sorted_entries = sorted(entries, key=lambda x: x.get('final_score', 0), reverse=True)
                for e in sorted_entries:
                    if len(final_entries) >= 10:
                        break
                    if e['index'] not in existing_indices:
                        final_entries.append(e)
                        existing_indices.add(e['index'])
            
            print(f"\nFinal filtered count: {len(final_entries)}")
            print("-" * 50)
            for i, entry in enumerate(final_entries, 1):
                print(f"[{i}] {entry.get('title')}")
                print(f"    Score: {entry.get('final_score')} | Reasons: {entry.get('reasons')}")
                print(f"    Source: {entry.get('source')}")
                print("-" * 50)
        else:
            print("No recommendations or entries found in review output.")
            
    except Exception as e:
        print(f"Filtering failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_flow())
