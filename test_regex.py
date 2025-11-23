import re

def test_reference_extraction():
    # 测试内容
    test_content = '''这是测试内容[1]，还有这个引用[2]。
    但是2023年不应该被匹配，价格100元也不应该匹配。
    这是一个真正的引用标记[3]，还有这个(见[4])。
    引用在句子末尾[5]。'''

    # 使用优化后的正则表达式
    reference_pattern = r'(?:^|[\s\[\](){}.,;:!?<>"\'`~#$%^&*+=|\\/-])\[(\d+)\](?:$|[\s\[\](){}.,;:!?<>"\'`~#$%^&*+=|\\/-])'
    matches = re.findall(reference_pattern, test_content)
    
    print("测试内容:")
    print(test_content)
    print("\n匹配到的引用:")
    print(matches)

if __name__ == "__main__":
    test_reference_extraction()