import json
import uuid
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

DATA_DIR = Path(__file__).parent / "data" / "conversations"
DATA_DIR.mkdir(parents=True, exist_ok=True)


def _now_iso():
    return datetime.now().isoformat()


def _conversation_path(session_id: str) -> Path:
    return DATA_DIR / f"{session_id}.json"


def list_conversations() -> List[Dict[str, Any]]:
    items = []
    for p in DATA_DIR.glob("*.json"):
        try:
            with p.open("r", encoding="utf-8") as f:
                obj = json.load(f)
                items.append({
                    "id": obj.get("id"),
                    "title": obj.get("title"),
                    "created_at": obj.get("created_at"),
                    "updated_at": obj.get("updated_at"),
                    "message_count": len(obj.get("messages", []))
                })
        except Exception:
            continue
    # 按更新时间倒序
    items.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
    return items


def create_conversation(title: str = "未命名会话", metadata: Dict[str, Any] = None) -> Dict[str, Any]:
    session_id = str(uuid.uuid4())
    obj = {
        "id": session_id,
        "title": title,
        "metadata": metadata or {},
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
        "messages": []
    }
    with _conversation_path(session_id).open("w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    return obj


def get_conversation(session_id: str) -> Optional[Dict[str, Any]]:
    p = _conversation_path(session_id)
    if not p.exists():
        return None
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)


def append_message(session_id: str, message: Dict[str, Any]) -> bool:
    p = _conversation_path(session_id)
    if not p.exists():
        return False
    try:
        with p.open("r", encoding="utf-8") as f:
            obj = json.load(f)
        
        obj.setdefault("messages", []).append(message)
        obj["updated_at"] = _now_iso()
        
        # 智能生成会话标题：在第一轮对话完成后（有1个用户消息和1个助手消息时）
        messages = obj.get("messages", [])
        current_title = obj.get("title", "")
        # 支持"新会话"和"未命名会话"两种默认标题
        if current_title in ["未命名会话", "新会话", ""] and len(messages) == 2:
            # 确保是一问一答的格式
            if messages[0].get("role") == "user" and messages[1].get("role") == "assistant":
                user_content = messages[0].get("content", "")
                assistant_content = messages[1].get("content", "")
                
                print(f"🎯 检测到第一轮对话完成，准备生成标题 (session_id: {session_id})")
                
                # 异步生成标题（不阻塞当前保存操作）
                import threading
                def async_generate_title():
                    try:
                        print(f"🚀 开始异步生成标题...")
                        result = generate_conversation_title(session_id, user_content, assistant_content)
                        if result:
                            print(f"✅ 标题生成成功: {result}")
                        else:
                            print(f"⚠️ 标题生成返回None")
                    except Exception as e:
                        print(f"❌ 异步生成标题失败: {e}")
                        import traceback
                        traceback.print_exc()
                
                thread = threading.Thread(target=async_generate_title)
                thread.daemon = True
                thread.start()
                
        with p.open("w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


def delete_conversation(session_id: str) -> bool:
    p = _conversation_path(session_id)
    if not p.exists():
        return False
    p.unlink()
    return True


def generate_conversation_title(session_id: str, user_content: str, assistant_content: str) -> Optional[str]:
    """使用大模型生成会话标题（5-15字）"""
    try:
        print(f"📝 开始生成会话标题 (session_id: {session_id})")
        print(f"📝 用户内容: {user_content[:100]}...")
        print(f"📝 助手内容: {assistant_content[:100]}...")
        
        from langchain_deepseek import ChatDeepSeek
        import os
        
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("❌ OPENAI_API_KEY 未设置")
            return None
        
        # 初始化模型
        print(f"🔧 初始化DeepSeek模型...")
        model = ChatDeepSeek(
            model="deepseek-chat",
            api_key=api_key,
            base_url=os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com"),
            temperature=0.3,
            max_tokens=50
        )
        
        # 构建提示词
        prompt = f"""请根据以下对话内容，生成一个简短精准的会话标题（5-15字）。只返回标题文本，不要任何解释或标点。

用户问题：{user_content[:200]}
助手回答：{assistant_content[:200]}

会话标题："""
        
        print(f"🤖 调用大模型生成标题...")
        # 调用模型生成标题
        response = model.invoke(prompt)
        title = response.content.strip()
        print(f"📤 模型返回原始标题: {title}")
        
        # 清理标题（去除引号、冒号等）
        title = title.strip('"\':：。！？')
        
        # 限制长度
        if len(title) > 15:
            title = title[:15]
        elif len(title) < 5:
            # 如果生成的标题太短，使用默认方式
            print(f"⚠️ 生成标题太短，使用默认方式")
            title = (user_content[:15] + "...") if len(user_content) > 15 else user_content
        
        print(f"✨ 最终标题: {title}")
        
        # 更新会话标题
        p = _conversation_path(session_id)
        if p.exists():
            print(f"💾 更新会话文件...")
            with p.open("r", encoding="utf-8") as f:
                obj = json.load(f)
            obj["title"] = title
            obj["updated_at"] = _now_iso()
            with p.open("w", encoding="utf-8") as f:
                json.dump(obj, f, ensure_ascii=False, indent=2)
            print(f"✅ 会话标题已更新: {title}")
        else:
            print(f"❌ 会话文件不存在: {p}")
        
        return title
    except Exception as e:
        print(f"❌ 生成标题失败: {e}")
        import traceback
        traceback.print_exc()
        return None
