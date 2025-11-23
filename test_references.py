import re

def extract_references_from_content(content: str, pdf_chunks: list = None) -> list:
    """
    从AI回答内容中提取引用信息
    """
    references = []
    
    # 查找所有的引用标记 [1], [2], etc.
    # 使用更简单的正则表达式，避免匹配到普通文本中的数字
    # 只匹配被空白字符或标点符号包围的引用标记
    reference_pattern = r'[\s\[\](){}.,;:!?<>""''`~#$%^&*+=|\\/-]*\[(\d+)\][\s\[\](){}.,;:!?<>""''`~#$%^&*+=|\\/-]*'
    matches = re.findall(reference_pattern, content)
    
    # 去重并保持顺序
    unique_matches = []
    for match in matches:
        if match not in unique_matches:
            unique_matches.append(match)
    
    if unique_matches and pdf_chunks:
        for match in unique_matches:
            ref_num = int(match)
            if 1 <= ref_num <= len(pdf_chunks):
                chunk = pdf_chunks[ref_num - 1]  # 索引从0开始
                # 增加引用文本的长度到300字符，提供更完整的信息
                reference = {
                    "id": ref_num,
                    "text": chunk.get("content", "")[:300] + "..." if len(chunk.get("content", "")) > 300 else chunk.get("content", ""),
                    "source": chunk.get("metadata", {}).get("source", "未知来源"),
                    "page": chunk.get("metadata", {}).get("page_number", 1),
                    "chunk_id": chunk.get("metadata", {}).get("chunk_id", 0),
                    "source_info": chunk.get("metadata", {}).get("source_info", "未知来源")
                }
                references.append(reference)
    
    return references

# 测试内容
test_content = '''这是测试内容[1]，还有这个引用[2]。
但是2023年不应该被匹配，价格100元也不应该匹配。
这是一个真正的引用标记[3]，还有这个(见[4])。
引用在句子末尾[5]。价格是100美元。'''

pdf_chunks_test = [
    {"content": "这是第一个参考文档的内容", "metadata": {"source": "doc1.pdf", "page_number": 1}},
    {"content": "这是第二个参考文档的内容", "metadata": {"source": "doc1.pdf", "page_number": 2}},
    {"content": "这是第三个参考文档的内容", "metadata": {"source": "doc2.pdf", "page_number": 1}},
    {"content": "这是第四个参考文档的内容", "metadata": {"source": "doc2.pdf", "page_number": 2}},
    {"content": "这是第五个参考文档的内容", "metadata": {"source": "doc3.pdf", "page_number": 1}}
]

print("测试内容:")
print(test_content)
print("\n提取到的引用:")
references = extract_references_from_content(test_content, pdf_chunks_test)
for ref in references:
    print(f"[{ref['id']}] {ref['text']} (来源: {ref['source']}, 第{ref['page']}页)")