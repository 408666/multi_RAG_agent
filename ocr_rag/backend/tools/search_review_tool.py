"""
搜索结果审查工具
用于判定从网络搜索得到的新闻/结果是否与用户问题相关，解决仅基于关键词的误判以及时间不一致问题。

主要策略（轻量、无需外部依赖）：
- 解析 `web_search` 格式化文本为结构化条目
- 对每条结果计算：关键词重合得分 + 时间一致性得分
- 输出结构化 JSON 字符串，包含每条结果的评分、原因，以及推荐使用的结果索引列表

此工具以 `@tool` 导出，供模型在工具链中调用。
"""
import re
import json
from datetime import datetime
from typing import List, Dict, Any
from loguru import logger
from langchain_core.tools import tool


def _tokenize(text: str) -> List[str]:
    text = text or ""
    # 简单拆分并去掉常见标点
    tokens = re.findall(r"[\w\u4e00-\u9fff]+", text.lower())
    # 去掉非常短的词
    return [t for t in tokens if len(t) > 1]


def _parse_formatted_results(formatted: str) -> List[Dict[str, Any]]:
    """
    解析 `WebSearchTool.format_results` 产出的文本格式为结构化条目。
    支持的字段：index, title, snippet, url, source
    """
    if not formatted:
        return []

    entries = []
    # 每条记录以 "[i] title" 开头，接着有一行以 "📝" 开头的 snippet，可能有 "🔗 url"，最后有 "📍 来源: source"
    pattern = re.compile(
        r"\[(?P<index>\d+)\]\s*(?P<title>.*?)\n📝\s*(?P<snippet>.*?)(?:\n🔗\s*(?P<url>.*?))?\n📍 来源:\s*(?P<source>.*?)\n\n",
        re.S
    )

    for m in pattern.finditer(formatted):
        entries.append({
            "index": int(m.group("index")),
            "title": (m.group("title") or "").strip(),
            "snippet": (m.group("snippet") or "").strip(),
            "url": (m.group("url") or "").strip(),
            "source": (m.group("source") or "").strip(),
        })

    # 如果没有解析到（格式不同），尝试按空行分块解析最小信息
    if not entries:
        blocks = [b.strip() for b in formatted.split('\n\n') if b.strip()]
        for i, b in enumerate(blocks, 1):
            lines = b.split('\n')
            title = lines[0] if lines else f"结果 {i}"
            snippet = ''
            url = ''
            source = ''
            for ln in lines[1:]:
                if ln.startswith('📝'):
                    snippet = ln.replace('📝', '').strip()
                elif ln.startswith('🔗'):
                    url = ln.replace('🔗', '').strip()
                elif '来源' in ln or '来源:' in ln:
                    source = ln.split(':')[-1].strip()

            entries.append({
                'index': i,
                'title': title,
                'snippet': snippet,
                'url': url,
                'source': source,
            })

    return entries


def _date_mentioned(text: str) -> List[str]:
    """在文本中查找可能的日期字符串，返回发现的日期片段"""
    if not text:
        return []
    patterns = [
        r"\d{4}年\d{1,2}月\d{1,2}日",
        r"\d{4}-\d{1,2}-\d{1,2}",
        r"\d{1,2}月\d{1,2}日",
    ]
    found = []
    for p in patterns:
        found += re.findall(p, text)
    return found


def _compute_relevance_score(question: str, title: str, snippet: str) -> float:
    """基于关键词重合计算简单相关性得分（0-1）"""
    q_tokens = set(_tokenize(question))
    doc_tokens = set(_tokenize(title + ' ' + snippet))
    if not q_tokens or not doc_tokens:
        return 0.0
    inter = q_tokens & doc_tokens
    union = q_tokens | doc_tokens
    return len(inter) / len(union)


def _compute_recency_score(current_date: str, title: str, snippet: str) -> float:
    """
    简单时间一致性评分：
    - 如果片段中出现当前日期 -> 1.0
    - 如果出现最近/日前/小时 等提示词 -> 0.8
    - 如果出现年份并且与当前年份相同 -> 0.6
    - 否则 0.3（未知时间）
    """
    now_year = None
    try:
        if current_date:
            # 支持 'YYYY-MM-DD' 或 'YYYY年MM月DD日' 的解析
            if '年' in current_date:
                now_year = int(re.search(r"(\d{4})年", current_date).group(1))
            else:
                now_year = int(current_date.split('-')[0])
    except Exception:
        now_year = None

    text = (title or '') + ' ' + (snippet or '')
    # 直接包含完整当前日期
    if current_date and (current_date in text or current_date.replace('-', '年') in text):
        return 1.0

    # 含有“最近/日前/小时/今天/昨日/昨天/本周/本月”等词
    if re.search(r"最近|日前|小时|今天|昨日|昨天|本周|本月|刚刚", text):
        return 0.8

    # 查找年份
    years = re.findall(r"(\d{4})年", text)
    if years:
        try:
            if now_year and int(years[0]) == now_year:
                return 0.6
            else:
                return 0.2
        except Exception:
            return 0.2

    return 0.3


@tool
async def review_search_results(formatted_results: str, user_question: str, current_date: str = '') -> str:
    """
    审查搜索结果：判断哪些结果与用户问题相关并给出理由。

    Args:
        formatted_results: 来自 `web_search` 的格式化文本（或其他类似文本）
        user_question: 用户原始问题/上下文
        current_date: 可选，传入当前日期字符串（例如 '2025-11-22' 或 '2025年11月22日'），用于时间一致性判断

    Returns:
        JSON 字符串，结构如下：
        {
          "summary": "简短审查结论",
          "recommendations": [1,3],
          "entries": [ {index, title, snippet, url, source, relevance_score, recency_score, final_score, reasons: []}, ... ]
        }
    """
    try:
        entries = _parse_formatted_results(formatted_results)

        results = []
        rec_list = []

        for e in entries:
            title = e.get('title', '')
            snippet = e.get('snippet', '')
            idx = e.get('index')

            rel = _compute_relevance_score(user_question, title, snippet)
            rec = _compute_recency_score(current_date or '', title, snippet)

            # 最终分数：关键词相关性占比 0.7，时间一致性 0.3
            final = rel * 0.7 + rec * 0.3

            reasons = []
            if rel > 0.4:
                reasons.append(f"关键词匹配({rel:.2f})")
            else:
                reasons.append(f"关键词匹配弱({rel:.2f})")

            if rec >= 0.8:
                reasons.append("时间信息与查询高度一致")
            elif rec >= 0.5:
                reasons.append("时间可能相关")
            else:
                reasons.append("时间不明确或较旧")

            results.append({
                'index': idx,
                'title': title,
                'snippet': snippet,
                'url': e.get('url', ''),
                'source': e.get('source', ''),
                'relevance_score': round(rel, 3),
                'recency_score': round(rec, 3),
                'final_score': round(final, 3),
                'reasons': reasons,
            })

        # 推荐：选取 final_score >= threshold 或 top-N
        threshold = 0.4
        recommended = [r['index'] for r in results if r['final_score'] >= threshold]

        # 如果没有任何达到阈值，则取 top2
        if not recommended and results:
            sorted_by_score = sorted(results, key=lambda x: x['final_score'], reverse=True)
            recommended = [sorted_by_score[i]['index'] for i in range(min(2, len(sorted_by_score)))]

        summary = f"共解析到 {len(results)} 条结果，推荐使用 {len(recommended)} 条。"

        output = {
            'summary': summary,
            'recommendations': recommended,
            'entries': results,
            'metadata': {
                'checked_at': datetime.now().isoformat(),
                'question_tokens': len(_tokenize(user_question))
            }
        }

        logger.info(f"🔎 审查完成：{summary}")
        return json.dumps(output, ensure_ascii=False)

    except Exception as e:
        logger.error(f"审查工具执行失败: {e}")
        return json.dumps({'error': str(e)}, ensure_ascii=False)


# 导出工具列表以便被 main.py 导入绑定
REVIEW_TOOLS = [
    review_search_results
]
