import os
import json
import asyncio
import tempfile
import re
from typing import List, Dict, Any, AsyncGenerator, Optional
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from loguru import logger

# LangChain imports (使用最新版本的标准方式)
from langchain_openai import ChatOpenAI
from langchain_deepseek import ChatDeepSeek
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage, ToolMessage
from langchain_core.callbacks import AsyncCallbackHandler

# Conversation store (lightweight file storage)
from conversation_store import (
    list_conversations,
    create_conversation,
    get_conversation,
    append_message,
    delete_conversation,
    generate_conversation_title,
)

# 本地配置
from config import settings
from pdf_processor import PDFProcessor
from tools.web_search_tool import WEB_SEARCH_TOOLS, get_search_tool
from tools.search_review_tool import REVIEW_TOOLS
import re

# 加载环境变量
load_dotenv(override=True)

# 配置日志
logger.add(settings.log_file, rotation="500 MB", level=settings.log_level)

app = FastAPI(
    title="多模态 RAG 工作台 API",
    description="基于 LangChain 1.0 的智能对话 API",
    version="1.0.0"
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 内容块模型（支持多模态）
class ContentBlock(BaseModel):
    type: str = Field(..., description="内容类型: text, image, audio")
    content: str = Field(..., description="内容数据")
    thumbnail: str = Field(default="", description="缩略图（可选）")
    transcription: str = Field(default="", description="音频转写文本（音频类型专用）")

# 请求模型（支持多模态）
class MessageRequest(BaseModel):
    content: str = Field(default="", description="纯文本内容（兼容旧版）")
    content_blocks: List[ContentBlock] = Field(default=[], description="多模态内容块")
    pdf_chunks: List[Dict[str, Any]] = Field(default=[], description="PDF文档块信息，用于引用溯源")
    history: List[Dict[str, Any]] = Field(default=[], description="对话历史")
    model: str = Field(default="deepseek-chat", description="使用的模型")
    knowledge_base: str = Field(default="default", description="知识库名称")
    session_id: Optional[str] = Field(default=None, description="可选：会话 ID，用于会话持久化")

class MessageResponse(BaseModel):
    content: str
    role: str
    timestamp: str
    references: List[Dict[str, Any]] = Field(default=[])
    session_id: Optional[str] = Field(default=None)

# 流式回调处理器
class StreamingCallbackHandler(AsyncCallbackHandler):
    def __init__(self):
        self.tokens = []
        self.current_chunk = ""
        
    async def on_llm_new_token(self, token: str, **kwargs: Any) -> None:
        """处理新的 token"""
        self.tokens.append(token)
        self.current_chunk += token

# 初始化处理器
pdf_processor = PDFProcessor()

# 导入音频处理器
try:
    from audio_processor import AudioProcessor
    audio_processor = AudioProcessor()
    logger.info("✅ 音频处理器初始化成功")
except ImportError as e:
    logger.warning(f"⚠️ 音频处理器导入失败: {e}")
    audio_processor = None

# 引用提取函数
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

# 初始化聊天模型
def get_chat_model(model_name: str = None):
    """初始化聊天模型"""
    if model_name is None:
        model_name = settings.default_model# 如果模型名字是空就默认为"deepseek-chat"

    try:
        # 根据模型名称选择不同的API配置
        if model_name == "qwen3-vl-8b-instruct":
            # 使用ModelScope的通义千问3 VL模型
            model = ChatOpenAI(
                model="Qwen/Qwen3-VL-8B-Instruct",
                api_key=settings.modelscope_api_key or "ms-d7f0d9fc-a7b9-4e8f-b0cb-47720b2464f0",
                base_url=settings.modelscope_base_url,
                temperature=settings.temperature,
                max_tokens=settings.max_tokens,
                streaming=True
            )
        else:
            # 使用原有的DeepSeek配置
            model = ChatDeepSeek(
                model=model_name,
                api_key=settings.openai_api_key,
                base_url=settings.openai_base_url,
                temperature=settings.temperature,
                max_tokens=settings.max_tokens,
                streaming=True
            )
        return model
    except Exception as e:
        logger.error(f"初始化模型失败: {e}")
        raise HTTPException(status_code=500, detail=f"模型初始化失败: {str(e)}")

def get_chat_model_with_tools(model_name: str = None, enable_tools: bool = True):
    """初始化带工具的聊天模型"""
    model = get_chat_model(model_name)
    
    # 只有 deepseek-chat 支持工具调用，reasoner 和视觉模型不支持
    if enable_tools and model_name in ["deepseek-chat", None]:
        try:
            # 合并所有工具（搜索工具 + 审查工具）
            all_tools = list(WEB_SEARCH_TOOLS) + list(REVIEW_TOOLS)
            model_with_tools = model.bind_tools(all_tools)
            logger.info(f"✅ 已为模型 {model_name} 绑定 {len(all_tools)} 个工具")
            return model_with_tools
        except Exception as e:
            logger.warning(f"⚠️ 工具绑定失败: {e}，返回原始模型")
            return model
    
    logger.info(f"ℹ️ 模型 {model_name} 不支持工具调用或工具已禁用")
    return model

async def execute_tool_calls(tool_calls: List[Dict], messages: List[BaseMessage]) -> List[BaseMessage]:
    """执行工具调用并返回结果。 

    说明：在搜索类工具执行后，自动调用 `review_search_results` 审查工具，
    并将审查结果作为额外的 ToolMessage 一并返回。
    """
    tool_messages = []

    # 合并所有工具，包含搜索工具与审查工具
    all_tools = list(WEB_SEARCH_TOOLS) + (list(REVIEW_TOOLS) if 'REVIEW_TOOLS' in globals() else [])

    for tool_call in tool_calls:
        tool_name = tool_call.get("name")
        tool_args = tool_call.get("args", {})
        tool_id = tool_call.get("id")

        logger.info(f"🔧 执行工具: {tool_name}, 参数: {tool_args}")

        # 在所有工具中查找
        tool_func = None
        for tool in all_tools:
            if getattr(tool, 'name', None) == tool_name:
                tool_func = tool
                break

        if not tool_func:
            logger.warning(f"⚠️ 未找到工具: {tool_name}")
            continue

        try:
            # 执行工具
            result = await tool_func.ainvoke(tool_args)
            logger.info(f"✅ 工具执行成功: {tool_name}")

            # 如果是搜索类工具，记录搜索引擎和搜索摘要到日志，完整结果作为 debug
            try:
                lower_name = (tool_name or "").lower()
                if "search" in lower_name or "web" in lower_name or "news" in lower_name:
                    # 尝试记录当前使用的搜索引擎
                    try:
                        current_engine = get_search_tool().search_engine
                        logger.info(f"🔎 工具[{tool_name}] 使用搜索引擎: {current_engine}")
                    except Exception:
                        logger.debug(f"无法确定工具[{tool_name}] 使用的搜索引擎")
                    result_text = result if isinstance(result, str) else json.dumps(result, ensure_ascii=False)
                    summary = result_text[:400] + ("..." if len(result_text) > 400 else "")
                    logger.info(f"🔎 工具[{tool_name}] 返回（摘要）: {summary}")
                    logger.debug(f"🔎 工具[{tool_name}] 返回（完整）: {result_text}")
            except Exception:
                logger.debug(f"🔎 无法为工具[{tool_name}] 生成搜索摘要")

            # 如果这是搜索类工具，尝试自动调用审查工具并将审查结果合并到工具消息中
            review_text = None
            try:
                lower_name = (tool_name or "").lower()
                if any(k in lower_name for k in ["search", "web", "news"]):
                    # 从历史消息中找到最近的用户问题
                    user_question = ""
                    for m in reversed(messages):
                        if isinstance(m, HumanMessage):
                            c = m.content
                            if isinstance(c, list):
                                parts = []
                                for item in c:
                                    if isinstance(item, dict) and item.get('type') == 'text':
                                        parts.append(item.get('text', ''))
                                    elif isinstance(item, str):
                                        parts.append(item)
                                user_question = ' '.join(parts).strip()
                            elif isinstance(c, str):
                                user_question = c
                            break

                    # 查找审查工具
                    review_tool = None
                    for t in all_tools:
                        if getattr(t, 'name', '') == 'review_search_results':
                            review_tool = t
                            break

                    if review_tool:
                        review_args = {
                            'formatted_results': str(result),
                            'user_question': user_question or '',
                            'current_date': datetime.now().strftime('%Y-%m-%d')
                        }
                        logger.info(f"🔍 自动调用审查工具: review_search_results")
                        review_result = await review_tool.ainvoke(review_args)
                        logger.info(f"✅ 审查工具执行完成")
                        review_text = str(review_result)

                        # 尝试解析审查结果并筛选原始结果
                        try:
                            review_json = json.loads(review_result)
                            recommendations = review_json.get('recommendations', [])
                            entries = review_json.get('entries', [])
                            
                            # 如果有推荐列表，筛选出推荐的条目
                            if recommendations and entries:
                                # 构建索引映射
                                entry_map = {e['index']: e for e in entries}
                                
                                # 获取推荐的条目，最多取前10个
                                final_entries = []
                                for idx in recommendations[:10]:
                                    if idx in entry_map:
                                        final_entries.append(entry_map[idx])
                                
                                # 如果推荐不足，补充高分结果直到10条
                                if len(final_entries) < 10:
                                    existing_indices = set(e['index'] for e in final_entries)
                                    # 按分数排序
                                    sorted_entries = sorted(entries, key=lambda x: x.get('final_score', 0), reverse=True)
                                    for e in sorted_entries:
                                        if len(final_entries) >= 10:
                                            break
                                        if e['index'] not in existing_indices:
                                            final_entries.append(e)
                                            existing_indices.add(e['index'])
                                
                                # 重新格式化为文本
                                if final_entries:
                                    new_result_text = "🔍 经审查筛选后的搜索结果：\n\n"
                                    for i, entry in enumerate(final_entries, 1):
                                        title = entry.get('title', '无标题')
                                        snippet = entry.get('snippet', '无描述')
                                        url = entry.get('url', '')
                                        source = entry.get('source', '未知来源')
                                        reasons = entry.get('reasons', [])
                                        
                                        new_result_text += f"[{i}] {title}\n"
                                        new_result_text += f"📝 {snippet}\n"
                                        if url:
                                            new_result_text += f"🔗 {url}\n"
                                        new_result_text += f"📍 来源: {source}\n"
                                        if reasons:
                                            new_result_text += f"💡 推荐理由: {', '.join(reasons)}\n"
                                        new_result_text += "\n"
                                    
                                    # 更新 result 为筛选后的文本
                                    result = new_result_text
                                    logger.info(f"✅ 已根据审查结果筛选出 {len(final_entries)} 条高相关结果")
                        except Exception as parse_err:
                            logger.warning(f"⚠️ 解析审查结果失败，保留原始结果: {parse_err}")

            except Exception as e:
                logger.error(f"审查工具调用失败: {e}")

            # 创建工具消息：如果有审查结果，将其合并到搜索结果内容中
            # 注意：如果上面已经更新了 result 为筛选后的文本，这里直接使用即可
            # 审查详情（review_text）可以选择是否附加，为了保持简洁，如果筛选成功，可以只返回筛选后的结果
            # 或者将审查元数据作为补充信息
            
            combined_content = str(result)
            # 如果需要调试审查过程，可以取消下面注释
            # if review_text:
            #     combined_content = combined_content + "\n\n[REVIEW_DEBUG]\n" + review_text

            tool_message = ToolMessage(
                content=combined_content,
                tool_call_id=tool_id,
                name=tool_name
            )
            tool_messages.append(tool_message)
        except Exception as e:
            logger.error(f"❌ 工具执行失败: {tool_name}, 错误: {e}")
            tool_message = ToolMessage(
                content=f"工具执行失败: {str(e)}",
                tool_call_id=tool_id,
                name=tool_name
            )
            tool_messages.append(tool_message)

    return tool_messages

def convert_history_to_messages(history: List[Dict[str, Any]], model_name: str = None) -> List[BaseMessage]:
    """将历史记录转换为 LangChain 消息格式，支持多模态内容"""
    messages = []
    
    # 添加系统消息
    if model_name == "deepseek-reasoner":
        system_prompt = """你是一个专业、严谨的多模态 RAG 助手（可按需展示推理过程）。请严格遵守下列规范以保证回答的专业性：

一、职责与能力
- 熟练进行文档理解、图像与音频分析、知识检索与逻辑推理；
- 在需要时，可以展示分步推理，但最终交付应为经过提炼的结论。

二、表达与风格
- 使用正式、清晰、结构化的书面语言；避免口语化与绝对化表述；
- 回答要点先行（简洁摘要 1-2 行），随后给出支撑要点与必要细节；
- **请直接回答问题，不要在文本中使用 [1]、[2] 等引用标记。**

三、工具与检索规则
- 当问题涉及“今天/现在/最近/当前”等时间概念，**必须先调用 `get_current_time` 工具**以获得精确日期/时间；在随后的任何网络检索查询中，应将该日期包含为查询关键字以提高时效性；
- 需要检索或核实事实时，优先使用 `web_search` 或 `search_recent_news`；
- 当结合用户上传文档（如 PDF）回答时，优先使用文档内容。

四、推理与输出格式（reasoner 模式）
- 可在中间阶段展示“思维链”以便可审计，但最终输出必须：
  1) 要点摘要（结论）；
  2) 支撑要点；
  3) 建议或后续步骤（如需）；
- 如果内部信息不足或检索冲突，应明确说明并建议进一步验证的方法。

五、不确定性处理
- 对无法确认或存在争议的信息，标注不确定性并避免断言性结论。

六、交互和澄清
- 若用户问题含糊或缺重要上下文，先礼貌提问以澄清（列出需要补充的信息）；

始终以专业、可审计、可复现的方式生成回答。"""
    else:
        system_prompt = """你是一个专业、严谨的多模态 RAG 助手（常规模式，不展示内部思维链）。请严格遵守以下规范以确保回答专业：

一、职责与能力
- 熟练进行文档解读、图像 OCR 与分析、音频转写理解与知识检索；

二、表达与风格
- 使用正式、简洁、结构化的书面表达；首段给出要点摘要（1-2 行），随后提供简洁证据与说明；
- **请直接回答问题，不要在文本中使用 [1]、[2] 等引用标记。**

三、工具与检索规则
- 若问题包含时间词（如“今天/现在/最近”）或涉及最新进展，优先调用 `get_current_time` 获取精确日期，并在后续网络搜索查询中包含该日期；
- 在需要时调用 `web_search` 或 `search_recent_news` 获取最新信息，使用检索结果支持结论；

四、回答结构（优先）：
1) 要点总结；
2) 支撑要点；
3) 建议或后续操作（如适用）。

五、澄清请求
- 若问题不够明确或缺关键信息，先提出 1-2 个简短澄清问题再继续处理。

始终保持专业、客观，并确保回答中有明确的不确定性说明。"""
    
    messages.append(SystemMessage(content=system_prompt))
    
    # 转换历史消息
    logger.info(f"处理历史消息: {len(history)} 条")
    for i, msg in enumerate(history):
        content = msg.get("content", "")
        content_blocks = msg.get("content_blocks", [])
        logger.info(f"历史消息 {i+1}: {msg['role']}, 内容块数: {len(content_blocks)}, 音频转写: {any(b.get('transcription') for b in content_blocks)}")
        
        if msg["role"] == "user":
            # 如果有多模态内容块，构建复合消息
            if content_blocks:
                message_content = []
                
                # 添加文本内容（如果有）
                if content.strip():
                    message_content.append({
                        "type": "text",
                        "text": content
                    })
                
                # 处理内容块
                for block in content_blocks:
                    if block.get("type") == "text":
                        message_content.append({
                            "type": "text", 
                            "text": block.get("content", "")
                        })
                    elif block.get("type") == "image":
                        # 图片内容块
                        image_data = block.get("content", "")
                        if image_data.startswith("data:image"):
                            message_content.append({
                                "type": "image_url",
                                "image_url": {
                                    "url": image_data
                                }
                            })
                    elif block.get("type") == "audio":
                        # 音频内容块 - 使用转写文本
                        if block.get("transcription"):
                            message_content.append({
                                "type": "text",
                                "text": f"[音频转写] {block.get('transcription')}"
                            })
                
                messages.append(HumanMessage(content=message_content))
            else:
                # 纯文本消息
                messages.append(HumanMessage(content=content))
                
        elif msg["role"] == "assistant":
            messages.append(AIMessage(content=content))
    
    return messages

def create_multimodal_message(request: MessageRequest) -> HumanMessage:
    """创建多模态消息"""
    logger.info(f"开始构建多模态消息...")
    logger.info(f"文本内容: {request.content[:100]}..." if request.content else "📝 无文本内容")
    logger.info(f"内容块数量: {len(request.content_blocks)}")
    
    message_content = []
    
    # 添加文本内容（如果有）
    if request.content.strip():
        logger.info(f"添加文本内容")
        message_content.append({
            "type": "text",
            "text": request.content
        })
    
    # 处理内容块
    for i, block in enumerate(request.content_blocks):
        logger.info(f"处理内容块 {i+1}/{len(request.content_blocks)}: {block.type}")
        
        if block.type == "text":
            logger.info(f"添加文本块: {block.content[:50]}...")
            message_content.append({
                "type": "text",
                "text": block.content
            })
        elif block.type == "image":
            # 图片内容块
            if block.content.startswith("data:image"):
                logger.info(f"添加图片块，数据长度: {len(block.content)}")
                message_content.append({
                    "type": "image_url", 
                    "image_url": {
                        "url": block.content
                    }
                })
            else:
                logger.warning(f"图片数据格式不正确: {block.content[:50]}...")
        elif block.type == "audio":
            # 音频内容块 - 直接使用转写文本
            if block.transcription:
                logger.info(f"添加音频转写文本: {block.transcription[:50]}...")
                message_content.append({
                    "type": "text",
                    "text": f"[音频转写] {block.transcription}"
                })
            else:
                logger.warning(f"音频块缺少转写文本")
        elif block.type == "pdf":
            # PDF内容块 - 使用文件名作为标识
            logger.info(f"添加PDF块: {block.filename}")
            message_content.append({
                "type": "text", 
                "text": f"[PDF文档] {block.filename} ({(block.filesize or 0) / 1024:.1f} KB)"
            })
        else:
            logger.warning(f"未知内容块类型: {block.type}")
    
    logger.info(f"消息构建完成，内容块数量: {len(message_content)}")
    
    # 如果只有纯文本，直接返回字符串
    if len(message_content) == 1 and message_content[0]["type"] == "text":
        logger.info(f"返回纯文本消息")
        return HumanMessage(content=message_content[0]["text"])
    
    # 多模态消息
    logger.info(f"返回多模态消息")
    return HumanMessage(content=message_content)

async def generate_streaming_response_with_tools(
    messages: List[BaseMessage], 
    model_name: str,
    pdf_chunks: List[Dict[str, Any]] = None,
    enable_tools: bool = True,
    max_iterations: int = 5,
    session_id: Optional[str] = None
) -> AsyncGenerator[str, None]:
    """生成支持工具调用的流式响应"""
    try:
        logger.info(f"🚀 开始生成流式响应（支持工具），模型: {model_name}")
        logger.info(f"📊 消息数量: {len(messages)}, 工具启用: {enable_tools}")
        
        # 如果有PDF内容，将其添加到系统消息中
        if pdf_chunks and len(pdf_chunks) > 0:
            logger.info(f"📚 检测到 {len(pdf_chunks)} 个PDF块，添加到上下文中")
            pdf_content = "\n\n=== 参考文档内容 ===\n"
            for i, chunk in enumerate(pdf_chunks, 1):
                content = chunk.get("content", "")[:500]
                source_info = chunk.get("metadata", {}).get("source_info", f"文档块 {i}")
                pdf_content += f"\n[{i}] {content}\n来源: {source_info}\n"
            
            if messages and isinstance(messages[0], SystemMessage):
                messages[0].content += pdf_content
                logger.info(f"✅ 已将PDF内容添加到系统提示词中")
        
        # 获取带工具的模型
        model = get_chat_model_with_tools(model_name, enable_tools)
        logger.info(f"✅ 模型初始化完成")
        # 如果提供了 session_id，先通知前端该会话ID（用于前端持久化）
        if session_id:
            session_init = {"type": "session_init", "session_id": session_id}
            yield f"data: {json.dumps(session_init, ensure_ascii=False)}\n\n"
        
        # 工具调用循环
        iteration = 0
        while iteration < max_iterations:
            iteration += 1
            logger.info(f"🔄 第 {iteration} 轮调用")
            
            # 先调用一次获取响应
            response = await model.ainvoke(messages)
            
            # 检查是否有工具调用
            if hasattr(response, 'tool_calls') and response.tool_calls:
                logger.info(f"🔧 检测到 {len(response.tool_calls)} 个工具调用")
                
                # 发送工具调用通知
                tool_call_data = {
                    "type": "tool_calls",
                    "tools": [
                        {
                            "name": tc.get("name"),
                            "args": tc.get("args")
                        } for tc in response.tool_calls
                    ],
                    "timestamp": datetime.now().isoformat()
                }
                yield f"data: {json.dumps(tool_call_data, ensure_ascii=False)}\n\n"
                
                # 添加助手消息
                messages.append(response)
                
                # 执行工具调用
                tool_messages = await execute_tool_calls(response.tool_calls, messages)
                
                # 添加工具消息
                messages.extend(tool_messages)
                
                # 发送工具结果
                tool_result_data = {
                    "type": "tool_results",
                    "results": [
                        {
                            "tool": tm.name,
                            "content": tm.content[:200] + "..." if len(tm.content) > 200 else tm.content
                        } for tm in tool_messages
                    ],
                    "timestamp": datetime.now().isoformat()
                }
                yield f"data: {json.dumps(tool_result_data, ensure_ascii=False)}\n\n"
                
                # 继续下一轮
                continue
            
            # 没有工具调用，生成最终流式响应
            logger.info(f"📝 开始流式输出最终响应")
            break
        
        if iteration >= max_iterations:
            logger.warning(f"⚠️ 达到最大迭代次数 {max_iterations}")
        
        # 流式输出最终响应（重新调用以获取流式输出）
        full_response = ""
        is_reasoner_model = model_name == "deepseek-reasoner"
        thought_process_started = False
        thought_process_ended = False
        answer_started = False
        
        chunk_count = 0
        async for chunk in model.astream(messages):
            chunk_count += 1
            logger.debug(f"收到第 {chunk_count} 个chunk")

            # 对于reasoner模型，特殊处理思维链
            if is_reasoner_model and hasattr(chunk, 'additional_kwargs') and chunk.additional_kwargs:
                reasoning_content = chunk.additional_kwargs.get("reasoning_content")
                if reasoning_content:
                    if not thought_process_started:
                        thought_process_started = True
                        thought_data = {
                            "type": "thought_process_start",
                            "timestamp": datetime.now().isoformat()
                        }
                        yield f"data: {json.dumps(thought_data, ensure_ascii=False)}\n\n"
                    
                    thought_data = {
                        "type": "thought_process_content",
                        "content": reasoning_content,
                        "timestamp": datetime.now().isoformat()
                    }
                    yield f"data: {json.dumps(thought_data, ensure_ascii=False)}\n\n"
                    continue

            # 处理普通内容块
            if hasattr(chunk, 'content') and chunk.content:
                content = chunk.content

                # 如果是reasoner模型且已经开始思维过程但还没结束，则发送思维过程结束信号
                if is_reasoner_model and thought_process_started and not thought_process_ended:
                    thought_process_ended = True
                    thought_end_data = {
                        "type": "thought_process_end",
                        "timestamp": datetime.now().isoformat()
                    }
                    yield f"data: {json.dumps(thought_end_data, ensure_ascii=False)}\n\n"

                # 如果还没开始发送答案，则发送答案开始信号
                if not answer_started:
                    answer_started = True
                    answer_start_data = {
                        "type": "answer_start",
                        "timestamp": datetime.now().isoformat()
                    }
                    yield f"data: {json.dumps(answer_start_data, ensure_ascii=False)}\n\n"

                full_response += content
                data = {
                    "type": "content_delta",
                    "content": content,
                    "timestamp": datetime.now().isoformat()
                }
                yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

        # 确保在流结束时发送思维过程结束信号
        if is_reasoner_model and thought_process_started and not thought_process_ended:
            thought_process_ended = True
            thought_end_data = {
                "type": "thought_process_end",
                "timestamp": datetime.now().isoformat()
            }
            yield f"data: {json.dumps(thought_end_data, ensure_ascii=False)}\n\n"

        # 提取引用信息
        references = extract_references_from_content(full_response, pdf_chunks) if pdf_chunks else []
        logger.info(f"📚 提取到 {len(references)} 个引用")
        
        # 发送完成信号
        final_data = {
            "type": "message_complete",
            "full_content": full_response,
            "timestamp": datetime.now().isoformat(),
            "references": references
        }
        # 将 assistant 消息保存到会话存储（如果提供了 session_id）
        if session_id:
            try:
                assistant_msg = {
                    "role": "assistant",
                    "content": full_response,
                    "references": references,
                    "timestamp": datetime.now().isoformat()
                }
                append_message(session_id, assistant_msg)
            except Exception:
                logger.warning("会话写入失败: 无法保存 assistant 消息")

        yield f"data: {json.dumps(final_data, ensure_ascii=False)}\n\n"
        
    except Exception as e:
        logger.error(f"❌ 流式响应生成失败: {e}")
        error_data = {
            "type": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
        yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"

async def generate_streaming_response(
    messages: List[BaseMessage], 
    model_name: str,
    pdf_chunks: List[Dict[str, Any]] = None
) -> AsyncGenerator[str, None]:
    """生成流式响应（兼容旧版本，不支持工具）"""
    try:
        logger.info(f"开始生成流式响应，模型: {model_name}")
        logger.info(f"消息数量: {len(messages)}")
        
        # 如果有PDF内容，将其添加到系统消息中
        if pdf_chunks and len(pdf_chunks) > 0:
            logger.info(f"检测到 {len(pdf_chunks)} 个PDF块，添加到上下文中")
            pdf_content = "\n\n=== 参考文档内容 ===\n"
            for i, chunk in enumerate(pdf_chunks, 1):
                content = chunk.get("content", "")[:500]  # 限制长度
                source_info = chunk.get("metadata", {}).get("source_info", f"文档块 {i}")
                pdf_content += f"\n[{i}] {content}\n来源: {source_info}\n"
            
            # 在第一条消息前添加PDF内容
            if messages and isinstance(messages[0], SystemMessage):
                messages[0].content += pdf_content
                logger.info(f"已将PDF内容添加到系统提示词中")
        
        model = get_chat_model(model_name)
        logger.info(f"模型初始化完成")
        
        # 创建流式响应
        full_response = ""
        logger.info(f"开始流式生成...")
        
        is_reasoner_model = model_name == "deepseek-reasoner"
        thought_process_started = False
        thought_process_ended = False
        answer_started = False
        
        chunk_count = 0
        async for chunk in model.astream(messages):
            chunk_count += 1
            logger.debug(f"收到第 {chunk_count} 个chunk: {chunk}")

            # 对于reasoner模型，特殊处理思维链和答案的流式输出
            if is_reasoner_model and hasattr(chunk, 'additional_kwargs') and chunk.additional_kwargs:
                reasoning_content = chunk.additional_kwargs.get("reasoning_content")
                if reasoning_content:
                    if not thought_process_started:
                        thought_process_started = True
                        thought_data = {
                            "type": "thought_process_start",
                            "timestamp": datetime.now().isoformat()
                        }
                        yield f"data: {json.dumps(thought_data, ensure_ascii=False)}\n\n"
                    
                    thought_data = {
                        "type": "thought_process_content",
                        "content": reasoning_content,
                        "timestamp": datetime.now().isoformat()
                    }
                    yield f"data: {json.dumps(thought_data, ensure_ascii=False)}\n\n"

                    # 不再检查chunk.content，直接continue处理下一个chunk
                    continue

            # 处理普通内容块
            if hasattr(chunk, 'content') and chunk.content:
                content = chunk.content

                # 如果是reasoner模型且已经开始思维过程但还没结束，则发送思维过程结束信号
                if is_reasoner_model and thought_process_started and not thought_process_ended:
                    thought_process_ended = True
                    thought_end_data = {
                        "type": "thought_process_end",
                        "timestamp": datetime.now().isoformat()
                    }
                    yield f"data: {json.dumps(thought_end_data, ensure_ascii=False)}\n\n"

                # 如果还没开始发送答案，则发送答案开始信号
                if not answer_started:
                    answer_started = True
                    answer_start_data = {
                        "type": "answer_start",
                        "timestamp": datetime.now().isoformat()
                    }
                    yield f"data: {json.dumps(answer_start_data, ensure_ascii=False)}\n\n"

                full_response += content
                data = {
                    "type": "content_delta",
                    "content": content,
                    "timestamp": datetime.now().isoformat()
                }
                yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

        # 确保在流结束时发送思维过程结束信号（如果没有发送过）
        if is_reasoner_model and thought_process_started and not thought_process_ended:
            thought_process_ended = True
            thought_end_data = {
                "type": "thought_process_end",
                "timestamp": datetime.now().isoformat()
            }
            yield f"data: {json.dumps(thought_end_data, ensure_ascii=False)}\n\n"


        # 提取引用信息
        references = extract_references_from_content(full_response, pdf_chunks) if pdf_chunks else []
        logger.info(f"提取到 {len(references)} 个引用")
        
        # 发送完成信号
        final_data = {
            "type": "message_complete",
            "full_content": full_response,
            "timestamp": datetime.now().isoformat(),
            "references": references
        }
        yield f"data: {json.dumps(final_data, ensure_ascii=False)}\n\n"
        
    except Exception as e:
        logger.error(f"流式响应生成失败: {e}")
        error_data = {
            "type": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
        yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"

@app.get("/")
async def root():
    """健康检查接口"""
    return {
        "message": "多模态 RAG 工作台 API",
        "version": "1.0.0",
        "status": "running",
        "langchain_version": "1.0.0"
    }

@app.post("/api/chat/stream")
async def chat_stream(request: MessageRequest):
    """流式聊天接口（支持多模态和工具调用）"""
    try:
        # 记录请求信息
        has_images = any(block.type == "image" for block in request.content_blocks)
        content_preview = request.content[:100] if request.content else "多模态消息"
        logger.info(f"📨 收到聊天请求: {content_preview}... (包含图片: {has_images})")
        
        # PDF chunks接收情况
        logger.info(f"📚 接收到的PDF chunks数量: {len(request.pdf_chunks) if request.pdf_chunks else 0}")
        if request.pdf_chunks:
            logger.info(f"📄 PDF chunks预览: {str(request.pdf_chunks[:2])[:200]}...")
        else:
            logger.info(f"📭 PDF chunks为空或None: {request.pdf_chunks}")
        
        # 处理会话ID：若未提供则创建新会话
        session_id = request.session_id
        if not session_id:
            conv = create_conversation(title="新会话", metadata={"knowledge_base": request.knowledge_base})
            session_id = conv["id"]
            logger.info(f"自动创建会话: {session_id}")

        # 转换消息历史
        messages = convert_history_to_messages(request.history, request.model)

        # 添加当前用户消息（支持多模态）并持久化到会话
        current_message = create_multimodal_message(request)
        messages.append(current_message)

        try:
            user_msg = {
                "role": "user",
                "content": request.content or "",
                "content_blocks": [b.dict() for b in request.content_blocks] if request.content_blocks else [],
                "timestamp": datetime.now().isoformat()
            }
            append_message(session_id, user_msg)
        except Exception:
            logger.warning("会话写入失败: 无法保存用户消息")

        # 返回流式响应（支持工具调用）
        enable_tools = request.model in ["deepseek-chat", None]

        return StreamingResponse(
            generate_streaming_response_with_tools(
                messages, 
                request.model, 
                request.pdf_chunks,
                enable_tools=enable_tools,
                session_id=session_id
            ),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream",
            }
        )
        
    except Exception as e:
        logger.error(f"聊天请求处理失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat")
async def chat_sync(request: MessageRequest):
    """同步聊天接口（支持多模态）"""
    try:
        # 记录请求信息
        has_images = any(block.type == "image" for block in request.content_blocks)
        content_preview = request.content[:100] if request.content else "多模态消息"
        logger.info(f"收到同步聊天请求: {content_preview}... (包含图片: {has_images})")
        
        # 处理会话ID：若未提供则创建新会话
        session_id = request.session_id
        if not session_id:
            conv = create_conversation(title="新会话", metadata={"knowledge_base": request.knowledge_base})
            session_id = conv["id"]
            logger.info(f"自动创建会话: {session_id}")

        # 转换消息历史
        messages = convert_history_to_messages(request.history, request.model)

        # 添加当前用户消息（支持多模态）并持久化
        current_message = create_multimodal_message(request)
        messages.append(current_message)
        try:
            user_msg = {
                "role": "user",
                "content": request.content or "",
                "content_blocks": [b.dict() for b in request.content_blocks] if request.content_blocks else [],
                "timestamp": datetime.now().isoformat()
            }
            append_message(session_id, user_msg)
        except Exception:
            logger.warning("会话写入失败: 无法保存用户消息")

        # 获取模型响应
        model = get_chat_model(request.model)
        response = await model.ainvoke(messages)

        # 持久化 assistant 消息
        try:
            assistant_msg = {
                "role": "assistant",
                "content": response.content,
                "references": [],
                "timestamp": datetime.now().isoformat()
            }
            append_message(session_id, assistant_msg)
        except Exception:
            logger.warning("会话写入失败: 无法保存 assistant 消息")

        return MessageResponse(
            content=response.content,
            role="assistant",
            timestamp=datetime.now().isoformat(),
            references=[],
            session_id=session_id
        )
        
    except Exception as e:
        logger.error(f"同步聊天请求处理失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/models")
async def get_models():
    """获取可用模型列表"""
    return {
        "models": [
            {
                "id": "deepseek-chat",
                "name": "DeepSeek Chat",
                "description": "DeepSeek通用对话模型"
            },
            {
                "id": "deepseek-reasoner",
                "name": "DeepSeek Reasoner",
                "description": "DeepSeek推理模型，支持显示推理过程"
            },
            {
                "id": "qwen3-vl-8b-instruct",
                "name": "Qwen3 VL 8B Instruct",
                "description": "通义千问3视觉语言模型，支持图像理解"
            }
        ]
    }

@app.get("/api/knowledge-bases")
async def get_knowledge_bases():
    """获取知识库列表"""
    return {
        "knowledge_bases": [
            {
                "id": "default",
                "name": "默认知识库",
                "description": "通用知识库"
            },
            {
                "id": "technical",
                "name": "技术文档",
                "description": "技术相关文档库"
            }
        ]
    }


@app.get("/api/conversations")
async def api_list_conversations():
    """列出所有会话（元数据）"""
    return list_conversations()


@app.post("/api/conversations")
async def api_create_conversation(payload: Dict[str, Any]):
    """创建新会话（可选 title）"""
    title = payload.get("title", "未命名会话")
    metadata = payload.get("metadata", {})
    conv = create_conversation(title=title, metadata=metadata)
    return conv


@app.get("/api/conversations/{session_id}")
async def api_get_conversation(session_id: str):
    conv = get_conversation(session_id)
    if not conv:
        raise HTTPException(status_code=404, detail="会话不存在")
    return conv


@app.delete("/api/conversations/{session_id}")
async def api_delete_conversation(session_id: str):
    ok = delete_conversation(session_id)
    if not ok:
        raise HTTPException(status_code=404, detail="会话不存在")
    return {"success": True}

@app.post("/api/pdf/process")
async def process_pdf_stream(file_data: Dict[str, Any]):
    """
    流式处理PDF文档
    """
    try:
        # 提取请求数据
        content = file_data.get("content", "")  # base64编码的PDF内容
        filename = file_data.get("filename", "document.pdf")
        
        if not content:
            raise HTTPException(status_code=400, detail="缺少PDF内容")
        
        # 解码base64数据
        import base64
        try:
            pdf_bytes = base64.b64decode(content.split(',')[-1])  # 去除data:application/pdf;base64,前缀
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"PDF数据解码失败: {str(e)}")
        
        logger.info(f"开始处理PDF: {filename}, 大小: {len(pdf_bytes)} bytes")
        
        # 定义流式响应生成器
        async def generate_pdf_stream():
            try:
                async for chunk in pdf_processor.process_pdf_stream(pdf_bytes, filename):
                    chunk_data = json.dumps(chunk, ensure_ascii=False)
                    yield f"data: {chunk_data}\n\n"
                    
                    # 如果是错误，立即结束
                    if chunk.get("type") == "error":
                        break
                        
            except Exception as e:
                logger.error(f"PDF流式处理失败: {str(e)}")
                error_chunk = json.dumps({
                    "type": "error",
                    "error": f"处理过程中出错: {str(e)}"
                }, ensure_ascii=False)
                yield f"data: {error_chunk}\n\n"
            
            yield "data: [DONE]\n\n"
        
        return StreamingResponse(
            generate_pdf_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"PDF处理端点出错: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/pdf/pages")
async def extract_pdf_pages(file_data: Dict[str, Any]):
    """
    提取PDF页面为图像（用于多模态处理）
    """
    try:
        content = file_data.get("content", "")
        max_pages = file_data.get("max_pages", 3)
        
        if not content:
            raise HTTPException(status_code=400, detail="缺少PDF内容")
        
        # 解码PDF数据
        import base64
        try:
            pdf_bytes = base64.b64decode(content.split(',')[-1])
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"PDF数据解码失败: {str(e)}")
        
        logger.info(f"提取PDF页面图像，最多 {max_pages} 页")
        
        # 提取页面图像
        page_images = await pdf_processor.extract_pdf_pages_as_images(pdf_bytes, max_pages)
        
        return {
            "success": True,
            "total_pages": len(page_images),
            "images": page_images
        }
        
    except Exception as e:
        logger.error(f"PDF页面提取失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ================================
# 音频处理端点
# ================================

@app.post("/api/audio/process")
async def process_audio(file: UploadFile = File(...)):
    """处理音频文件，进行语音转文字"""
    
    if not audio_processor:
        raise HTTPException(status_code=500, detail="音频处理器未初始化，请检查依赖")
    
    try:
        logger.info(f"🎙️ 开始处理音频: {file.filename}")
        
        # 检查文件类型
        allowed_types = {
            'audio/mpeg', 'audio/mp3', 'audio/wav', 'audio/flac', 'audio/m4a', 'audio/ogg',
            'video/mp4', 'video/avi', 'video/mov', 'video/mkv', 'video/webm'
        }
        
        if file.content_type not in allowed_types:
            raise HTTPException(status_code=400, detail=f"不支持的文件类型: {file.content_type}")
        
        # 创建临时文件
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        try:
            # 处理音频
            result = audio_processor.process_audio_file(temp_file_path, file.filename)
            
            logger.info(f"音频处理成功: {file.filename}")
            return {
                "success": True,
                "filename": result["filename"],
                "transcription": result["transcription"],
                "duration": result["duration"],
                "format": result["format"]
            }
        
        finally:
            # 清理临时文件
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
        
    except Exception as e:
        logger.error(f"音频处理失败: {e}")
        raise HTTPException(status_code=500, detail=f"音频处理失败: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app, 
        host=settings.host, 
        port=settings.port,
        log_level=settings.log_level.lower()
    ) 