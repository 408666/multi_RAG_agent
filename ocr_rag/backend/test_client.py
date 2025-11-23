#!/usr/bin/env python3
"""
测试客户端 - 用于测试后端多个接口：
- 健康检查接口 /            (test_health)
- 同步聊天接口 /api/chat      (test_sync_chat)
- 流式聊天接口 /api/chat/stream (test_streaming_chat)
"""

import asyncio
import httpx
import json
from typing import AsyncGenerator


async def test_streaming_chat():
    """测试流式聊天接口 (/api/chat/stream)

    通过 HTTP 流 (Server-Sent Events / text-event-stream) 持续接收模型的回答，
    一边接收一边在终端打印出来。
    """
    print("🧪 测试流式聊天接口...")
    
    # 后端流式接口地址
    url = "http://localhost:8000/api/chat/stream"
    
    # 测试请求数据：发送给大模型的基本参数
    test_data = {
        "content": "你好！请介绍一下你的功能。",  # 本次提问内容
        "history": [],                           # 历史对话，这里为空列表
        "model": "deepseek-chat",              # 使用的模型名称
        "knowledge_base": "default"            # 知识库标识
    }
    
    try:
        # 创建一个异步 HTTP 客户端，设置整体超时时间为 60 秒
        async with httpx.AsyncClient(timeout=60.0) as client:
            # 使用 client.stream 以“流”的方式发起 POST 请求
            # - "POST"：HTTP 方法
            # - url：请求地址
            # - json=test_data：自动将 test_data 序列化为 JSON 放入请求体
            # - headers={"Accept": "text/event-stream"}：告知服务端期望返回 SSE 流
            async with client.stream(
                "POST",
                url,
                json=test_data,
                headers={"Accept": "text/event-stream"}
            ) as response:
                
                # 打印 HTTP 状态码，方便排查接口是否正常
                print(f"状态码: {response.status_code}")
                print("=" * 50)
                print("📨 流式响应:")
                
                # 用于在本地拼接完整的回答内容
                full_content = ""

                # 通过 aiter_lines() 异步逐行读取服务端推送的数据
                # 服务器通常以类似 "data: {json字符串}" 的形式按行推送
                async for line in response.aiter_lines():
                    # 只处理以 "data: " 开头的行，忽略注释行或心跳行
                    if line.startswith("data: "):
                        try:
                            # line 形如："data: {\"type\": ..., ...}"，前 6 个字符是 "data: "
                            # 通过 line[6:] 去掉前缀，得到纯 JSON 字符串
                            # 再用 json.loads 将 JSON 字符串反序列化为 Python 字典对象
                            data = json.loads(line[6:])  # 移除 "data: " 前缀，将 JSON 格式转为 Python 对象

                            # 根据服务端约定的字段 "type" 决定如何处理这条事件
                            if data["type"] == "content_delta":
                                # content_delta 表示“内容增量”，即一小段新的回答文本
                                content = data["content"]
                                # end="" 表示打印后不自动换行；flush=True 让内容立即刷新到终端
                                print(content, end="", flush=True)
                                # 同时累加到 full_content 中，便于需要完整内容时使用
                                full_content += content
                            elif data["type"] == "message_complete":
                                # message_complete 表示本次回答已结束
                                print("\n" + "=" * 50)
                                print(f"✅ 响应完成")
                                # 服务端也会返回完整内容，可以从 data['full_content'] 获取
                                print(f"📄 完整内容长度: {len(data['full_content'])} 字符")
                                break
                            elif data["type"] == "error":
                                # error 类型表示服务端在流中报告了错误
                                print(f"\n❌ 错误: {data['error']}")
                                break
                                
                        except json.JSONDecodeError:
                            # 如果这一行不是合法的 JSON，直接忽略，继续读取下一行
                            continue
                
                print(f"\n✅ 测试完成")
                
    except Exception as e:
        # 捕获网络错误、超时等异常，避免程序直接崩溃
        print(f"❌ 测试失败: {e}")


async def test_sync_chat():
    """测试同步聊天接口 (/api/chat)

    一次性发送问题，等待服务端返回完整回答后再打印出来。
    """
    print("\n🧪 测试同步聊天接口...")
    
    # 同步聊天接口地址
    url = "http://localhost:8000/api/chat"
    
    # 请求参数与流式接口类似，只是这里走的是非流式一次性返回
    test_data = {
        "content": "简单介绍一下LangChain",
        "history": [],
        "model": "deepseek-chat",
        "knowledge_base": "default"
    }
    
    try:
        # 创建异步 HTTP 客户端
        async with httpx.AsyncClient(timeout=60.0) as client:
            # 直接 await client.post(...)，一次性得到完整响应
            response = await client.post(url, json=test_data)
            
            print(f"状态码: {response.status_code}")
            if response.status_code == 200:
                # 服务器返回 JSON，转为字典方便取字段
                result = response.json()
                print("📨 同步响应:")
                print(f"角色: {result['role']}")      # 比如 "assistant"
                print(f"时间: {result['timestamp']}")  # 服务端生成此消息的时间
                print(f"内容: {result['content']}")    # 模型回答内容
                print("✅ 测试完成")
            else:
                # 非 200 视为错误，直接打印服务端返回的文本
                print(f"❌ 响应错误: {response.text}")
                
    except Exception as e:
        print(f"❌ 测试失败: {e}")


async def test_health():
    """测试健康检查接口 (/)

    用于判断后端服务是否正常启动，以及基本状态信息。
    """
    print("🧪 测试健康检查接口...")
    
    try:
        # 不指定超时就使用默认配置，这里仅仅是一个简单 GET
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8000/")
            
            print(f"状态码: {response.status_code}")
            if response.status_code == 200:
                # 将健康检查返回的 JSON 打印出来，每个 key-value 一行
                result = response.json()
                print("📊 服务状态:")
                for key, value in result.items():
                    print(f"  {key}: {value}")
                print("✅ 服务运行正常")
            else:
                print(f"❌ 服务异常: {response.text}")
                
    except Exception as e:
        # 通常这里意味着后端服务没有启动或端口不对
        print(f"❌ 连接失败: {e}")
        print("💡 请确保后端服务正在运行: python start.py")


async def main():
    """主测试函数

    按顺序依次执行：健康检查 -> 同步接口 -> 流式接口。
    可以直观看到整个后端的基本可用情况。
    """
    print("🚀 开始API接口测试")
    print("=" * 60)
    
    # 1. 先测试健康检查，确认服务是否已启动
    await test_health()
    
    # 2. 再测试一次性返回的同步聊天接口
    await test_sync_chat()
    
    # 3. 最后测试流式聊天接口，观察实时输出效果
    await test_streaming_chat()
    
    print("\n🎉 所有测试完成!")


if __name__ == "__main__":
    # 直接运行此脚本时，启动异步事件循环并执行 main()
    asyncio.run(main())
