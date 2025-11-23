// 聊天API适配器
export interface ChatMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp?: string;
  references?: Array<{
    id: string;
    title: string;
    content: string;
    source: string;
  }>;
}

export interface StreamingResponse {
  type: 'content_delta' | 'message_complete' | 'error' | 'thought_process_start' | 'thought_process_content' | 'thought_process_end' | 'answer_start' | 'session_init' | 'tool_calls' | 'tool_results';
  content?: string;
  full_content?: string;
  error?: string;
  timestamp: string;
  references?: Array<any>;
  session_id?: string;
  tools?: Array<{
    name: string;
    args: any;
  }>;
  results?: Array<{
    tool: string;
    content: string;
  }>;
}

// 内容块接口（支持多模态）
export interface ContentBlock {
  type: 'text' | 'image' | 'audio' | 'pdf';
  content: string;
  thumbnail?: string;
  transcription?: string; // 音频转写文本
  filename?: string; // PDF文件名
  filesize?: number; // PDF文件大小
}

export interface ChatRequest {
  content: string;
  content_blocks?: ContentBlock[];
  pdf_chunks?: any[];  // PDF文档块信息，用于引用溯源
  history: Array<{
    role: string;
    content: string;
    content_blocks?: ContentBlock[];
  }>;
  model?: string;
  knowledge_base?: string;
  session_id?: string;
}

export interface Conversation {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  messages: any[];
}

const API_BASE_URL = 'http://localhost:8000';

export class ChatAPI {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  /**
   * 获取所有会话
   */
  async getConversations(): Promise<Conversation[]> {
    const response = await fetch(`${this.baseUrl}/api/conversations`);
    if (!response.ok) {
      throw new Error('Failed to fetch conversations');
    }
    return response.json();
  }

  /**
   * 获取单个会话详情
   */
  async getConversation(id: string): Promise<Conversation> {
    const response = await fetch(`${this.baseUrl}/api/conversations/${id}`);
    if (!response.ok) {
      throw new Error('Failed to fetch conversation');
    }
    return response.json();
  }

  /**
   * 创建新会话
   */
  async createConversation(title?: string): Promise<Conversation> {
    const response = await fetch(`${this.baseUrl}/api/conversations`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ title }),
    });
    if (!response.ok) {
      throw new Error('Failed to create conversation');
    }
    return response.json();
  }

  /**
   * 删除会话
   */
  async deleteConversation(id: string): Promise<void> {
    const response = await fetch(`${this.baseUrl}/api/conversations/${id}`, {
      method: 'DELETE',
    });
    if (!response.ok) {
      throw new Error('Failed to delete conversation');
    }
  }

  /**
   * 流式聊天接口
   */
  async *streamChat(request: ChatRequest): AsyncGenerator<StreamingResponse, void, unknown> {
    try {
      console.log('🌐 发起API请求到:', `${this.baseUrl}/api/chat/stream`);
      console.log('📤 请求数据:', {
        content: request.content,
        content_blocks_count: request.content_blocks?.length || 0,
        audio_blocks: request.content_blocks?.filter(b => b.type === 'audio').length || 0,
        has_transcription: request.content_blocks?.some(b => b.type === 'audio' && b.transcription) || false,
        pdf_chunks_count: request.pdf_chunks?.length || 0,
        history_count: request.history?.length || 0,
        model: request.model,
        session_id: request.session_id
      });
      
      // 调试PDF chunks
      if (request.pdf_chunks && request.pdf_chunks.length > 0) {
        console.log('📚 前端发送PDF chunks数量:', request.pdf_chunks.length);
        console.log('📚 前端PDF chunks预览:', request.pdf_chunks.slice(0, 2));
      } else {
        console.log('📚 前端没有PDF chunks数据');
      }

      // 详细显示content_blocks
      if (request.content_blocks && request.content_blocks.length > 0) {
        console.log('📋 详细content_blocks:', request.content_blocks.map(b => ({
          type: b.type,
          hasContent: !!b.content,
          hasTranscription: !!b.transcription,
          transcriptionPreview: b.transcription ? b.transcription.substring(0, 50) + '...' : 'N/A'
        })));
      }
      
      const response = await fetch(`${this.baseUrl}/api/chat/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'text/event-stream',
        },
        body: JSON.stringify({
          content: request.content || '',
          content_blocks: request.content_blocks || [],
          pdf_chunks: request.pdf_chunks || [],
          history: request.history || [],
          model: request.model || 'deepseek-chat',
          session_id: request.session_id,
          knowledge_base: request.knowledge_base || 'default'
        }),
      });

      console.log('📡 收到响应，状态码:', response.status);
      
      if (!response.ok) {
        const errorText = await response.text();
        console.error('❌ HTTP错误:', response.status, errorText);
        yield {
          type: 'error',
          error: `HTTP error! status: ${response.status}, body: ${errorText}`,
          timestamp: new Date().toISOString()
        };
        return;
      }

      const reader = response.body?.getReader();
      if (!reader) {
        console.error('❌ 无法获取响应流读取器');
        yield {
          type: 'error',
          error: '无法读取响应流',
          timestamp: new Date().toISOString()
        };
        return;
      }
      
      console.log('📖 开始读取流式响应...');

      const decoder = new TextDecoder();
      let buffer = '';

      try {
        while (true) {
          const { done, value } = await reader.read();
          
          if (done) {
            console.log('✅ 流式响应读取完成');
            // 确保在流结束时发送一个完成消息
            yield {
              type: 'message_complete',
              full_content: '',
              timestamp: new Date().toISOString()
            };
            break;
          }

          buffer += decoder.decode(value, { stream: true });
          console.log('📋 收到数据块，缓冲区长度:', buffer.length);
          
          // 处理 Server-Sent Events 格式
          const lines = buffer.split('\n');
          buffer = lines.pop() || ''; // 保留最后一行（可能不完整）

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6));
                console.log('✨ 解析SSE数据:', data.type, data.content?.substring(0, 30));
                
                // 添加防护性检查
                if (!data || !data.type) {
                  console.warn('⚠️ 收到无效数据:', data);
                  continue;
                }
                
                yield data as StreamingResponse;
                
                // 如果收到完成或错误信号，停止解析
                if (data.type === 'message_complete' || data.type === 'error') {
                  console.log('🏁 收到完成或错误信号，结束流');
                  return;
                }
              } catch (e) {
                console.warn('⚠️ 解析SSE数据失败:', e, '原始行:', line);
              }
            }
          }
        }
      } finally {
        // 确保读取器被释放
        reader.releaseLock();
      }
    } catch (error) {
      console.error('流式聊天请求失败:', error);
      yield {
        type: 'error',
        error: error instanceof Error ? error.message : '未知错误',
        timestamp: new Date().toISOString()
      };
    }
  }

  /**
   * 同步聊天接口
   */
  async chat(request: ChatRequest): Promise<ChatMessage> {
    try {
      const response = await fetch(`${this.baseUrl}/api/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          content: request.content,
          content_blocks: request.content_blocks || [],
          pdf_chunks: request.pdf_chunks || [],
          history: request.history,
          model: request.model || 'deepseek-chat',
          knowledge_base: request.knowledge_base || 'default'
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();
      return {
        role: result.role,
        content: result.content,
        timestamp: result.timestamp,
        references: result.references
      };
    } catch (error) {
      console.error('同步聊天请求失败:', error);
      throw error;
    }
  }

  /**
   * 获取可用模型列表
   */
  async getModels(): Promise<Array<{id: string, name: string, description: string}>> {
    try {
      const response = await fetch(`${this.baseUrl}/api/models`);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();
      return result.models;
    } catch (error) {
      console.error('获取模型列表失败:', error);
      throw error;
    }
  }

  /**
   * 获取知识库列表
   */
  async getKnowledgeBases(): Promise<Array<{id: string, name: string, description: string}>> {
    try {
      const response = await fetch(`${this.baseUrl}/api/knowledge-bases`);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();
      return result.knowledge_bases;
    } catch (error) {
      console.error('获取知识库列表失败:', error);
      throw error;
    }
  }

  /**
   * 健康检查
   */
  async health(): Promise<{status: string, version: string}> {
    try {
      const response = await fetch(`${this.baseUrl}/`);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('健康检查失败:', error);
      throw error;
    }
  }
}

// 创建默认实例
export const chatAPI = new ChatAPI(); 