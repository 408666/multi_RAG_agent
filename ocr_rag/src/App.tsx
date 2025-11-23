import { useState, useEffect, useRef, Component, ErrorInfo, ReactNode } from "react";
import { 导航栏 } from "./components/导航栏";
import { 侧边栏 } from "./components/侧边栏";
import { chatAPI } from "./api/chat";
import { 顶部栏 } from "./components/顶部栏";
import { 消息气泡, Message, Reference } from "./components/消息气泡";
import { 引用抽屉 } from "./components/引用抽屉";
import { 输入栏 } from "./components/输入栏";
import { 顶部进度条 } from "./components/顶部进度条";
import { 迷你波形 } from "./components/迷你波形";
import { 日志抽屉 } from "./components/日志抽屉";
import { 轻提示, ToastMessage } from "./components/轻提示";
import { 粒子背景 } from "./components/粒子背景";

import { Alert, AlertDescription } from "./components/ui/alert";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "./components/ui/dialog";

interface ParseStep {
  key: string;
  label: string;
  completed: boolean;
}

interface LogEntry {
  timestamp: string;
  level: 'info' | 'warning' | 'error' | 'success';
  message: string;
  details?: string;
}

interface ConversationItem {
  id: string;
  title: string;
  timestamp: Date;
  messageCount: number;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error?: Error;
}

class ErrorBoundary extends Component<{children: ReactNode}, ErrorBoundaryState> {
  constructor(props: {children: ReactNode}) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("Error caught by boundary:", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="h-screen flex items-center justify-center bg-red-50">
          <div className="text-center p-8 bg-white rounded-lg shadow-lg max-w-md">
            <h2 className="text-2xl font-bold text-red-600 mb-4">出错了</h2>
            <p className="text-gray-700 mb-4">
              应用遇到了一些问题，请尝试刷新页面。
            </p>
            <button 
              className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
              onClick={() => window.location.reload()}
            >
              刷新页面
            </button>
            {this.state.error && (
              <details className="mt-4 text-left text-sm text-gray-500">
                <summary>错误详情</summary>
                <pre className="mt-2 whitespace-pre-wrap">{this.state.error.message}</pre>
              </details>
            )}
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default function App() {
  // 状态管理
  const [知识库, set知识库] = useState("default");
  const [模型, set模型] = useState("deepseek-chat");
  const [inputValue, setInputValue] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [引用抽屉Open, set引用抽屉Open] = useState(false);
  const [selectedReferences, setSelectedReferences] = useState<Reference[]>([]);
  const [selectedReference, setSelectedReference] = useState<Reference | undefined>();
  const [toast, setToast] = useState<ToastMessage | null>(null);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [helpOpen, setHelpOpen] = useState(false);
  
  // 侧边栏状态
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [conversations, setConversations] = useState<ConversationItem[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<string | undefined>(undefined);
  const [sessionId, setSessionId] = useState<string | undefined>(undefined);

  // 工具调用状态
  const [activeTools, setActiveTools] = useState<Array<{name: string, args: any}>>([]);

  // 加载会话列表
  useEffect(() => {
    loadConversations();
  }, []);

  const loadConversations = async () => {
    try {
      const data = await chatAPI.getConversations();
      const items: ConversationItem[] = data.map((c: any) => ({
        id: c.id,
        title: c.title,
        timestamp: new Date(c.updated_at),
        messageCount: c.message_count || 0
      }));
      setConversations(items);
    } catch (error) {
      console.error('Failed to load conversations:', error);
      showToast({
        id: Date.now().toString(),
        type: 'error',
        title: '加载会话列表失败',
        description: '请稍后重试'
      });
    }
  };

  const handleNewConversation = async () => {
    try {
      const newConv = await chatAPI.createConversation();
      await loadConversations();
      setActiveConversationId(newConv.id);
      setSessionId(newConv.id);
      setMessages([]);
    } catch (error) {
      console.error('Failed to create conversation:', error);
      showToast({
        id: Date.now().toString(),
        type: 'error',
        title: '创建新会话失败',
        description: '请稍后重试'
      });
    }
  };

  const handleConversationSelect = async (id: string) => {
    try {
      setActiveConversationId(id);
      setSessionId(id);
      const conv = await chatAPI.getConversation(id);
      
      // 转换消息格式
      const loadedMessages: Message[] = conv.messages.map((msg: any) => {
        let contentBlocks = [];
        if (msg.content_blocks && msg.content_blocks.length > 0) {
          contentBlocks = msg.content_blocks.map((b: any) => ({
            type: b.type,
            content: b.content,
            thumbnail: b.thumbnail,
            transcription: b.transcription,
            filename: b.filename,
            filesize: b.filesize
          }));
        } else {
          contentBlocks = [{ type: 'text', content: msg.content || '' }];
        }

        return {
          id: Date.now().toString() + Math.random(), // 临时ID
          role: msg.role,
          contentBlocks: contentBlocks,
          timestamp: new Date(msg.timestamp),
          references: msg.references,
          isStreaming: false
        };
      });
      
      setMessages(loadedMessages);
    } catch (error) {
      console.error('Failed to load conversation:', error);
      showToast({
        id: Date.now().toString(),
        type: 'error',
        title: '加载会话详情失败',
        description: '请稍后重试'
      });
    }
  };

  const handleDeleteConversation = async (id: string) => {
    try {
      await chatAPI.deleteConversation(id);
      await loadConversations();
      if (activeConversationId === id) {
        setActiveConversationId(undefined);
        setSessionId(undefined);
        setMessages([]);
      }
      showToast({
        id: Date.now().toString(),
        type: 'success',
        title: '会话已删除',
        description: ''
      });
    } catch (error) {
      console.error('Failed to delete conversation:', error);
      showToast({
        id: Date.now().toString(),
        type: 'error',
        title: '删除会话失败',
        description: '请稍后重试'
      });
    }
  };


  // PDF 解析进度相关
  const [parseProgress, setParseProgress] = useState({
    isVisible: false,
    fileName: "",
    progress: 0,
    currentStep: "upload",
    logs: [] as LogEntry[]
  });
  const [logDrawerOpen, setLogDrawerOpen] = useState(false);

  // 音频处理相关
  const [audioFile, setAudioFile] = useState<{ name: string; duration: number } | null>(null);
  const [transcription, setTranscription] = useState("");
  const [isTranscribing, setIsTranscribing] = useState(false);

  // 图片暂存相关
  const [pendingImages, setPendingImages] = useState<Array<{
    id: string;
    file: File;
    dataUrl: string;
    thumbnail: string;
  }>>([]);

  // PDF暂存相关
  const [pendingPDFs, setPendingPDFs] = useState<Array<{
    id: string;
    file: File;
    filename: string;
    size: number;
    processed?: boolean;
    chunks?: Array<{
      id: string;
      content: string;
      metadata: any;
    }>;
  }>>([]);

  // 音频暂存相关
  const [pendingAudios, setPendingAudios] = useState<Array<{
    id: string;
    file: File;
    filename: string;
    duration: number;
    transcription?: string;
    processed?: boolean;
  }>>([]);

  // PDF处理进度
  const [pdfProcessing, setPdfProcessing] = useState<{
    isProcessing: boolean;
    progress: number;
    step: string;
    message: string;
  }>({
    isProcessing: false,
    progress: 0,
    step: '',
    message: ''
  });

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const scrollAreaRef = useRef<HTMLDivElement>(null);

  // 解析步骤定义
  const parseSteps: ParseStep[] = [
    { key: "upload", label: "上传", completed: false },
    { key: "ocr", label: "OCR", completed: false },
    { key: "segment", label: "切分", completed: false },
    { key: "vectorize", label: "向量化", completed: false },
    { key: "store", label: "入库", completed: false }
  ];

  // 模拟引用数据（更新到新的Reference接口）

    // 自动滚动到底部
  useEffect(() => {
    if (scrollAreaRef.current) {
      // 延迟滚动以确保内容已渲染
      const scrollToBottom = () => {
        if (scrollAreaRef.current) {
          const element = scrollAreaRef.current;
          element.scrollTop = element.scrollHeight - element.clientHeight;
        }
      };
      
      // 立即滚动
      scrollToBottom();
      // 延迟滚动确保内容完全渲染
      setTimeout(scrollToBottom, 100);
    }
  }, [messages]);

  // 流式回复时也要自动滚动
  useEffect(() => {
    if (isStreaming && scrollAreaRef.current) {
      const scrollToBottom = () => {
        if (scrollAreaRef.current) {
          const element = scrollAreaRef.current;
          element.scrollTop = element.scrollHeight - element.clientHeight;
        }
      };
      
      const interval = setInterval(scrollToBottom, 300);
      return () => clearInterval(interval);
    }
  }, [isStreaming]);

  // 键盘快捷键
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        set引用抽屉Open(false);
        setLogDrawerOpen(false);
        setSettingsOpen(false);
        setHelpOpen(false);
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, []);

  // 发送消息
  const handleSend = async () => {
    if ((!inputValue.trim() && pendingImages.length === 0 && pendingAudios.length === 0) || isStreaming) return;

    const currentInput = inputValue;
    
    // 构建用户消息（包含文本、图片和PDF信息）
    const contentBlocks: any[] = [];
    
    // 添加文本内容
    if (currentInput.trim()) {
      contentBlocks.push({ type: 'text', content: currentInput });
    }
    
    // 添加暂存的图片
    if (pendingImages.length > 0) {
      console.log('🖼️ 发送消息时包含图片数量:', pendingImages.length);
      pendingImages.forEach(img => {
        contentBlocks.push({
          type: 'image',
          content: img.dataUrl,
          thumbnail: img.thumbnail
        });
      });
    }

    // 添加暂存的音频
    if (pendingAudios.length > 0) {
      console.log('🎙️ 发送消息时包含音频数量:', pendingAudios.length);
      pendingAudios.forEach((audio, index) => {
        console.log(`🎵 音频 ${index + 1}:`, {
          filename: audio.filename,
          hasTranscription: !!audio.transcription,
          transcriptionPreview: audio.transcription?.substring(0, 100) + '...'
        });
        contentBlocks.push({
          type: 'audio',
          content: '', // 音频文件不直接传输
          transcription: audio.transcription || ''
        });
      });
    }

    // 处理PDF文档（如果有的话）
    let pdfDocuments = null;
    if (pendingPDFs.length > 0) {
      console.log('📄 发送消息时包含PDF数量:', pendingPDFs.length);
      // 为每个PDF文档创建单独的内容块
      pendingPDFs.forEach(pdf => {
        contentBlocks.push({
          type: 'pdf',
          content: pdf.filename,
          filename: pdf.filename,
          filesize: pdf.size
        });
      });
      pdfDocuments = pendingPDFs;
    }

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      contentBlocks: contentBlocks,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputValue("");
    clearPendingImages(); // 清除暂存图片
    clearPendingAudios(); // 清除暂存音频
    setIsStreaming(true);

    // 创建助手消息用于流式更新（在try块外定义，以便在catch和finally中访问）
    const assistantMessageId = (Date.now() + 1).toString();
    
    try {
      // 准备聊天历史（保持多模态结构）
      const history = messages.map(msg => ({
        role: msg.role,
        content: msg.contentBlocks.map(block => block.content).join(''), // 兼容纯文本
        content_blocks: msg.contentBlocks.map(block => ({
          type: block.type,
          content: block.content,
          thumbnail: block.thumbnail,
          transcription: block.transcription // 保持音频转写信息
        }))
      }));

      console.log('📜 传递给API的对话历史:', history.length, '条消息');
      if (history.length > 0) {
        console.log('📝 最近的历史消息预览:', history.slice(-2).map(h => ({
          role: h.role,
          content_blocks_count: h.content_blocks.length,
          has_transcription: h.content_blocks.some(b => b.transcription)
        })));
      }

      const assistantMessage: Message = {
        id: assistantMessageId,
        role: 'assistant',
        contentBlocks: [{ type: 'text', content: '正在思考...' }],
        references: [],
        timestamp: new Date(),
        isStreaming: true
      };

      setMessages(prev => [...prev, assistantMessage]);

      // 如果有PDF，先处理PDF并获取内容
      let pdfContent = '';
      let allProcessedPdfChunks: any[] = []; // 直接收集PDF块，不依赖state
      
      if (pdfDocuments && pdfDocuments.length > 0) {
        console.log('🚀 开始处理PDF文档...');
        
        try {
          // 处理所有PDF文档并收集内容和块
          for (const pdf of pdfDocuments) {
            console.log(`📄 处理PDF: ${pdf.filename}`);
            const chunks = await processPDF(pdf);
            if (chunks && chunks.length > 0) {
              // 将PDF内容添加到用户消息中
              const pdfTexts = chunks.map((chunk: any) => chunk.content).join('\n\n');
              pdfContent += `\n\n=== PDF文档：${pdf.filename} ===\n${pdfTexts}`;
              
              // 直接收集PDF块用于引用
              allProcessedPdfChunks = allProcessedPdfChunks.concat(chunks);
              console.log(`✅ PDF ${pdf.filename} 处理完成，提取文本长度: ${pdfTexts.length}，块数: ${chunks.length}`);
            }
          }
          console.log('✅ 所有PDF处理完成，总内容长度:', pdfContent.length, '，总块数:', allProcessedPdfChunks.length);
        } catch (error) {
          console.error('PDF处理失败，继续进行对话:', error);
        }
        
        // 注意：不在这里清除PDF暂存，因为后续还需要使用PDF块信息
      }
      
      // 调用后端流式API
      // 构建API请求的content_blocks
      const apiContentBlocks: Array<{ 
        type: 'image' | 'audio'; 
        content: string; 
        thumbnail?: string;
        transcription?: string;
      }> = [];
      
      // 添加图片内容块
      if (pendingImages.length > 0) {
        pendingImages.forEach(img => {
          apiContentBlocks.push({
            type: 'image' as const,
            content: img.dataUrl,
            thumbnail: img.thumbnail
          });
        });
      }

      // 添加音频内容块
      if (pendingAudios.length > 0) {
        console.log('🔊 添加音频到API请求，数量:', pendingAudios.length);
        pendingAudios.forEach((audio, index) => {
          console.log(`🎵 添加音频 ${index + 1} 到API:`, {
            filename: audio.filename,
            hasTranscription: !!audio.transcription,
            transcriptionLength: audio.transcription?.length || 0
          });
          apiContentBlocks.push({
            type: 'audio' as const,
            content: '', // 音频文件不直接传输
            transcription: audio.transcription || ''
          });
        });
      }

      console.log('📋 最终apiContentBlocks:', apiContentBlocks.map(b => ({
        type: b.type,
        hasContent: !!b.content,
        hasTranscription: !!b.transcription
      })));

      // 构建完整的用户输入（包含PDF内容）
      const fullUserInput = pdfContent ? `${currentInput}${pdfContent}` : currentInput;
      console.log('📤 发送给GPT的完整内容长度:', fullUserInput.length);
      if (pdfContent) {
        console.log('📄 包含PDF内容，预览:', pdfContent.substring(0, 200) + '...');
      }
      
      // 使用直接收集的PDF块信息（不依赖state）
      console.log('📚 传递PDF块信息，总数:', allProcessedPdfChunks.length);

      let fullContent = '';
      let thoughtProcessContent = '';
      let thoughtProcessCompleted = false;
      let answerStarted = false;

      try {
        for await (const chunk of chatAPI.streamChat({
          content: fullUserInput,
          content_blocks: apiContentBlocks,
          pdf_chunks: allProcessedPdfChunks,
          history: history,
          model: 模型,
          knowledge_base: 知识库,
          session_id: sessionId
        })) {
          // 添加防护性检查
          if (!chunk) continue;

          if (chunk.type === 'session_init' && chunk.session_id) {
            if (!sessionId) {
              setSessionId(chunk.session_id);
              setActiveConversationId(chunk.session_id);
              loadConversations();
            }
            continue;
          }

          if (chunk.type === 'tool_calls' && chunk.tools) {
            console.log('🔧 收到工具调用事件:', chunk.tools);
            setActiveTools(chunk.tools);
            continue;
          }

          if (chunk.type === 'tool_results' && chunk.results) {
            console.log('✅ 收到工具结果事件:', chunk.results);
            setActiveTools([]); // 清除活跃工具
            continue;
          }
          
          if (chunk.type === 'thought_process_start') {
            thoughtProcessContent = '';
          } else if (chunk.type === 'thought_process_content' && chunk.content) {
            thoughtProcessContent += chunk.content;
          } else if (chunk.type === 'thought_process_end') {
            thoughtProcessCompleted = true;
          } else if (chunk.type === 'answer_start') {
            answerStarted = true;
            fullContent = '';
          } else if (chunk.type === 'content_delta' && chunk.content) {
            fullContent += chunk.content;
          } else if (chunk.type === 'message_complete' && ('full_content' in chunk)) {
            fullContent = chunk.full_content || fullContent || '';
            // Final update with references
            setMessages(prev => prev.map(msg => {
              // 添加防护性检查
              if (!msg) return msg;
              
              if (msg.id === assistantMessageId) {
                const contentBlocks = [];
                
                // 只有当思考过程有实际内容时才添加
                if (thoughtProcessContent && thoughtProcessContent.trim() !== '') {
                  contentBlocks.push({ 
                    type: 'text' as const, 
                    content: `思考过程：\n${thoughtProcessContent}` 
                  });
                }
                
                // 添加答案内容，确保即使为空也有显示
                contentBlocks.push({ 
                  type: 'text' as const, 
                  content: fullContent || '无内容' 
                });
                
                return {
                  ...msg,
                  contentBlocks,
                  references: Array.isArray(chunk.references) ? chunk.references : [],
                  isStreaming: false
                };
              }
              return msg;
            }));
            continue; // Skip the generic update below
          }

          // Update UI for streaming content
          setMessages(prev => prev.map(msg => {
            // 添加防护性检查
            if (!msg) return msg;
            
            if (msg.id === assistantMessageId) {
              const newContentBlocks: any[] = [];
              
              // 只有当思考过程有实际内容时才添加
              if (thoughtProcessContent && thoughtProcessContent.trim() !== '') {
                newContentBlocks.push({ type: 'text', content: `思考过程：\n${thoughtProcessContent}` });
              }
              
              // 只有当有内容或仍在接收内容时才添加内容块
              if (answerStarted && (fullContent || !thoughtProcessCompleted)) {
                newContentBlocks.push({ type: 'text', content: fullContent || '正在思考...' });
              } else if (!answerStarted && thoughtProcessCompleted) {
                // 思考过程完成但答案还没开始时显示默认消息
                newContentBlocks.push({ type: 'text', content: '正在生成答案...' });
              } else if (answerStarted && !fullContent) {
                // 答案已经开始但没有内容时显示默认消息
                newContentBlocks.push({ type: 'text', content: '正在生成答案...' });
              }
              
              return { ...msg, contentBlocks: newContentBlocks };
            }
            return msg;
          }));
        }
      } catch (streamError) {
        console.error('流式响应处理错误:', streamError);
        
        // 显示错误提示
        setToast({
          id: Date.now().toString(),
          type: 'error',
          title: '响应处理失败',
          description: '处理响应时发生错误'
        });

        // 更新消息状态为错误
        setMessages(prev => prev.map(msg => {
          if (msg && msg.id === assistantMessageId) {
            return { 
              ...msg, 
              contentBlocks: [{ type: 'text', content: '发生错误，请检查日志' }], 
              isStreaming: false 
            };
          }
          return msg;
        }));
      }
    } catch (error) {
      console.error('API调用失败:', error);

      // 显示错误提示
      setToast({
        id: Date.now().toString(),
        type: 'error',
        title: '连接失败',
        description: '无法连接到后端服务，请检查服务是否正常运行'
      });

      // 更新消息状态为错误
      setMessages(prev => prev.map(msg =>
        msg.id === assistantMessageId
          ? { ...msg, contentBlocks: [{ type: 'text', content: '发生错误，请检查日志' }], isStreaming: false }
          : msg
      ));
    } finally {
      setIsStreaming(false);
      // 确保最后一条消息的isStreaming状态被设置为false
      setMessages(prev => prev.map(msg =>
        msg.id === assistantMessageId ? { ...msg, isStreaming: false } : msg
      ));
      setActiveTools([]); // 清除活跃工具状态
      // 清理暂存的PDF
      if (pendingPDFs.length > 0) {
        clearPendingPDFs();
      }
    }
  };

  // 停止生成
  const handleStop = () => {
    setIsStreaming(false);
    setMessages(prev => prev.map(msg => ({ ...msg, isStreaming: false })));
    setActiveTools([]); // 清除活跃工具状态
  };

  // 引用点击处理
  const handleReferenceClick = (references: Reference[]) => {
    console.log('🔍 点击引用:', references);
    
    if (references.length > 0) {
      const ref = references[0];
      
      // 显示Toast提示
      showToast({
        id: Date.now().toString(),
        type: 'info',
        title: `引用来源：${ref.source_info}`,
        description: ref.text.substring(0, 100) + (ref.text.length > 100 ? '...' : '')
      });
      
      // 保留原有的引用面板功能
      setSelectedReferences(references);
      setSelectedReference(references[0]);
      set引用抽屉Open(true);
    }
  };

  // PDF 上传处理

    // 图片上传处理（暂存，不自动发送）
  const handleUploadImage = async (file: File) => {
    console.log('🖼️ 开始处理图片上传:', file.name, file.size);
    
    if (isStreaming) {
      console.log('❌ 当前正在流式响应中，跳过图片上传');
      return;
    }

    const reader = new FileReader();
    reader.onload = (e) => {
      const imageData = e.target?.result as string;
      console.log('📁 图片读取完成，数据长度:', imageData.length);
      
      // 将图片添加到暂存区
      const pendingImage = {
        id: Date.now().toString(),
        file: file,
        dataUrl: imageData,
        thumbnail: imageData
      };
      
      setPendingImages(prev => [...prev, pendingImage]);
      console.log('📌 图片已暂存，等待用户输入问题');
      
      showToast({
        id: Date.now().toString(),
        type: 'info',
        title: '图片已上传',
        description: '请输入您的问题，然后点击发送'
      });
    };
    
    reader.readAsDataURL(file);
  };

  // 清除暂存图片
  const clearPendingImages = () => {
    setPendingImages([]);
  };

  // 清除暂存PDF
  const clearPendingPDFs = () => {
    setPendingPDFs([]);
  };

  // 清除暂存音频
  const clearPendingAudios = () => {
    setPendingAudios([]);
  };



  // 简化的PDF上传处理（暂存版）
  const handleUploadPDFNew = async (file: File) => {
    if (isStreaming || pdfProcessing.isProcessing) return;

    console.log('📄 PDF上传:', file.name, file.size);

    // 将PDF添加到暂存区
    const pendingPDF = {
      id: Date.now().toString(),
      file: file,
      filename: file.name,
      size: file.size,
      processed: false
    };

    setPendingPDFs(prev => [...prev, pendingPDF]);

    showToast({
      id: Date.now().toString(),
      type: 'info',
      title: 'PDF已上传',
      description: '请输入您的问题，系统将自动处理PDF并回答'
    });
  };

  // PDF处理函数
  const processPDF = async (pdfFile: {id: string, file: File}) => {
    console.log('🚀 开始处理PDF:', pdfFile.file.name);

    setPdfProcessing({
      isProcessing: true,
      progress: 0,
      step: 'preparing',
      message: '准备处理PDF...'
    });

    try {
      // 将PDF转换为base64
      const reader = new FileReader();
      const fileData = await new Promise<string>((resolve, reject) => {
        reader.onload = (e) => resolve(e.target?.result as string);
        reader.onerror = reject;
        reader.readAsDataURL(pdfFile.file);
      });

      console.log('📤 开始调用PDF处理API');

      // 调用PDF处理API
      const response = await fetch('http://localhost:8000/api/pdf/process', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          content: fileData,
          filename: pdfFile.file.name
        })
      });

      if (!response.body) {
        throw new Error('响应体为空');
      }

      const reader2 = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';  // 用于存储不完整的数据

      while (true) {
        const { done, value } = await reader2.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        buffer += chunk;

        // 按行分割处理
        const lines = buffer.split('\n');
        // 保留最后一行（可能不完整）
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6).trim();
            if (data === '[DONE]') continue;
            if (!data) continue;  // 跳过空数据

            try {
              const parsed = JSON.parse(data);
              console.log('📦 PDF处理进度:', parsed);

              if (parsed.type === 'progress') {
                setPdfProcessing({
                  isProcessing: true,
                  progress: parsed.progress || 0,
                  step: parsed.step || '',
                  message: parsed.message || ''
                });
              } else if (parsed.type === 'result') {
                // 处理完成，保存结果到state（用于UI显示）
                setPendingPDFs(prev => prev.map(pdf =>
                  pdf.id === pdfFile.id
                    ? { ...pdf, processed: true, chunks: parsed.chunks }
                    : pdf
                ));
                console.log('✅ PDF处理完成，文档块数量:', parsed.chunks?.length);
                return parsed.chunks; // 返回文档块
              } else if (parsed.type === 'error') {
                throw new Error(parsed.error);
              }
            } catch (e) {
              console.warn('解析PDF处理响应失败:', e, '数据:', data.slice(0, 200));
            }
          }
        }
      }

      // 处理最后的缓冲区数据
      if (buffer.trim() && buffer.startsWith('data: ')) {
        const data = buffer.slice(6).trim();
        if (data !== '[DONE]' && data) {
          try {
            const parsed = JSON.parse(data);
            if (parsed.type === 'result') {
              setPendingPDFs(prev => prev.map(pdf =>
                pdf.id === pdfFile.id
                  ? { ...pdf, processed: true, chunks: parsed.chunks }
                  : pdf
              ));
              console.log('✅ PDF处理完成（缓冲区），文档块数量:', parsed.chunks?.length);
              return parsed.chunks;
            }
          } catch (e) {
            console.warn('解析缓冲区PDF响应失败:', e);
          }
        }
      }

    } catch (error) {
      console.error('PDF处理失败:', error);
      const errorMessage = error instanceof Error ? error.message : '未知错误';
      showToast({
        id: Date.now().toString(),
        type: 'error',
        title: 'PDF处理失败',
        description: `处理 ${pdfFile.file.name} 时出错: ${errorMessage}`
      });
      throw error;
    } finally {
      setPdfProcessing({
        isProcessing: false,
        progress: 0,
        step: '',
        message: ''
      });
    }
  };

  // 音频上传处理  
  const handleUploadAudio = async (file: File) => {
    console.log('🎙️ 音频上传:', file.name, file.size);
    
    try {
      setToast({
        id: Date.now().toString(),
        type: 'info',
        title: '正在处理音频...',
        description: '请稍等，正在进行语音转文字'
      });

      // 调用后端音频处理API
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch('http://localhost:8000/api/audio/process', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || '音频处理失败');
      }

      const result = await response.json();
      console.log('✅ 音频处理成功:', result);

      // 创建待处理音频对象
      const pendingAudio = {
        id: Date.now().toString(),
        file: file,
        filename: result.filename,
        duration: result.duration,
        transcription: result.transcription,
        processed: true
      };

      // 添加到暂存列表
      setPendingAudios(prev => [...prev, pendingAudio]);

      setToast({
        id: Date.now().toString(),
        type: 'success',
        title: '音频处理完成',
        description: `转写内容：${result.transcription.substring(0, 50)}${result.transcription.length > 50 ? '...' : ''}`
      });

    } catch (error) {
      console.error('❌ 音频处理失败:', error);
      setToast({
        id: Date.now().toString(),
        type: 'error',
        title: '音频处理失败',
        description: error instanceof Error ? error.message : '未知错误'
      });
    }
  };

  // 音频转写
  const handleTranscribe = () => {
    setIsTranscribing(true);
    
    setTimeout(() => {
      const mockTranscription = "您好，我想了解关于多模态RAG系统的技术实现细节，特别是在处理图像和文档时的最佳实践。";
      setTranscription(mockTranscription);
      setInputValue(mockTranscription);
      setIsTranscribing(false);
      setAudioFile(null);

      showToast({
        id: Date.now().toString(),
        type: 'success',
        title: '转写完成',
        description: '语音内容已插入到输入框'
      });
    }, 3000);
  };



  // 显示提示
  const showToast = (message: ToastMessage) => {
    setToast(message);
  };

  return (
    <ErrorBoundary>
      <div className="h-screen bg-background flex flex-col relative overflow-hidden">
        {/* 粒子背景 */}
        <粒子背景 />

        {/* 导航栏 */}
        <导航栏 />

        {/* 主内容区域 */}
        <div className="flex-1 flex relative min-h-0">
          {/* 侧边栏 */}
          <侧边栏 
            isCollapsed={sidebarCollapsed}
            onToggle={() => setSidebarCollapsed(!sidebarCollapsed)}
            conversations={conversations}
            activeConversationId={activeConversationId}
            onConversationSelect={handleConversationSelect}
            onNewConversation={handleNewConversation}
            onSettings={() => setSettingsOpen(true)}
            onHelp={() => setHelpOpen(true)}
            onDeleteConversation={handleDeleteConversation}
            知识库={知识库}
            on知识库Change={set知识库}
          />

          {/* 主聊天区域 */}
          <div className="flex-1 flex flex-col relative min-h-0">
            {/* 顶部栏 */}
            <顶部栏
              currentSessionTitle={conversations.find(c => c.id === activeConversationId)?.title}
            />

            {/* 顶部进度条 */}
            <顶部进度条
              isVisible={parseProgress.isVisible}
              fileName={parseProgress.fileName}
              progress={parseProgress.progress}
              currentStep={parseProgress.currentStep}
              steps={parseSteps.map(step => ({
                ...step,
                completed: parseSteps.indexOf(step) < parseSteps.findIndex(s => s.key === parseProgress.currentStep)
              }))}
              onClose={() => setParseProgress(prev => ({ ...prev, isVisible: false }))}
              onViewLog={() => setLogDrawerOpen(true)}
            />

            {/* 消息区域 */}
            <div className={`flex-1 relative ${parseProgress.isVisible ? 'mt-24' : ''}`} style={{ minHeight: 0 }}>
              <div 
                ref={scrollAreaRef} 
                className="absolute inset-0 overflow-y-auto overflow-x-hidden chat-scroll"
              >
                <div className="w-full max-w-[1100px] mx-auto px-6 sm:px-8 lg:px-12 py-10 space-y-6 relative z-10 min-h-full">
                  {messages.length === 0 && (
                    <div className="text-center py-16">
                      <div className="w-20 h-20 bg-gradient-to-br from-gray-800 to-gray-900 dark:from-gray-100 dark:to-gray-200 rounded-2xl mx-auto mb-8 flex items-center justify-center shadow-2xl">
                        <span className="text-white dark:text-black text-2xl font-bold">RAG</span>
                      </div>
                      <h2 className="text-3xl text-foreground mb-4 font-semibold">
                        欢迎使用多模态 RAG 工作台
                      </h2>
                      <p className="text-muted-foreground text-lg mb-10 max-w-2xl mx-auto">
                        基于先进AI技术，提供专业的文档分析、图像理解和音频处理能力
                      </p>
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-6 max-w-4xl mx-auto">
                        <div className="p-6 bg-card backdrop-blur-sm rounded-lg border border-gray-200 dark:border-gray-600 hover:border-blue-300 dark:hover:border-blue-500 hover:shadow-lg transition-all duration-300 group">
                          <div className="w-12 h-12 bg-gradient-to-r from-blue-500 to-blue-600 rounded-lg mx-auto mb-4 flex items-center justify-center shadow-lg group-hover:scale-105 group-hover:shadow-blue-200 transition-all duration-300">
                            <span className="text-white text-lg">📝</span>
                          </div>
                          <p className="text-sm font-medium text-card-foreground group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">智能问答</p>
                        </div>
                        <div className="p-6 bg-card backdrop-blur-sm rounded-lg border border-gray-200 dark:border-gray-600 hover:border-green-300 dark:hover:border-green-500 hover:shadow-lg transition-all duration-300 group">
                          <div className="w-12 h-12 bg-gradient-to-r from-green-500 to-green-600 rounded-lg mx-auto mb-4 flex items-center justify-center shadow-lg group-hover:scale-105 group-hover:shadow-green-200 transition-all duration-300">
                            <span className="text-white text-lg">🖼️</span>
                          </div>
                          <p className="text-sm font-medium text-card-foreground group-hover:text-green-600 dark:group-hover:text-green-400 transition-colors">图片分析</p>
                        </div>
                        <div className="p-6 bg-card backdrop-blur-sm rounded-lg border border-gray-200 dark:border-gray-600 hover:border-purple-300 dark:hover:border-purple-500 hover:shadow-lg transition-all duration-300 group">
                          <div className="w-12 h-12 bg-gradient-to-r from-purple-500 to-purple-600 rounded-lg mx-auto mb-4 flex items-center justify-center shadow-lg group-hover:scale-105 group-hover:shadow-purple-200 transition-all duration-300">
                            <span className="text-white text-lg">🎙️</span>
                          </div>
                          <p className="text-sm font-medium text-card-foreground group-hover:text-purple-600 dark:group-hover:text-purple-400 transition-colors">音频转写</p>
                        </div>
                        <div className="p-6 bg-card backdrop-blur-sm rounded-lg border border-gray-200 dark:border-gray-600 hover:border-orange-300 dark:hover:border-orange-500 hover:shadow-lg transition-all duration-300 group">
                          <div className="w-12 h-12 bg-gradient-to-r from-orange-500 to-orange-600 rounded-lg mx-auto mb-4 flex items-center justify-center shadow-lg group-hover:scale-105 group-hover:shadow-orange-200 transition-all duration-300">
                            <span className="text-white text-lg">📄</span>
                          </div>
                          <p className="text-sm font-medium text-card-foreground group-hover:text-orange-600 dark:group-hover:text-orange-400 transition-colors">PDF 解析</p>
                        </div>
                      </div>
                    </div>
                  )}

                  {messages.map((message) => (
                    <消息气泡
                      key={message.id}
                      message={message}
                      onReferenceClick={handleReferenceClick}
                      activeTools={activeTools}
                    />
                  ))}

                  {/* 音频波形卡片 */}
                  {audioFile && (
                    <div className="max-w-md">
                      <迷你波形
                        fileName={audioFile.name}
                        duration={audioFile.duration}
                        onTranscribe={handleTranscribe}
                        isTranscribing={isTranscribing}
                        transcription={transcription}
                      />
                    </div>
                  )}

                  <div ref={messagesEndRef} />
                </div>
              </div>
            </div>

            {/* 输入栏 */}
            <输入栏
              value={inputValue}
              onChange={setInputValue}
              onSend={handleSend}
              onStop={handleStop}
              onUploadPDF={handleUploadPDFNew}
              onUploadImage={handleUploadImage}
              onUploadAudio={handleUploadAudio}
              isStreaming={isStreaming}
              pendingImages={pendingImages}
              onRemoveImage={(id) => setPendingImages(prev => prev.filter(img => img.id !== id))}
              pendingPDFs={pendingPDFs}
              onRemovePDF={(id) => setPendingPDFs(prev => prev.filter(pdf => pdf.id !== id))}
              pdfProcessing={pdfProcessing}
              pendingAudios={pendingAudios}
              onRemoveAudio={(id) => setPendingAudios(prev => prev.filter(audio => audio.id !== id))}
              模型={模型}
              on模型Change={set模型}
            />
          </div>
        </div>

        {/* 引用抽屉 */}
        <引用抽屉
          isOpen={引用抽屉Open}
          onClose={() => set引用抽屉Open(false)}
          references={selectedReferences}
          selectedReference={selectedReference}
          onReferenceSelect={setSelectedReference}
        />

        {/* 日志抽屉 */}
        <日志抽屉
          isOpen={logDrawerOpen}
          onClose={() => setLogDrawerOpen(false)}
          logs={parseProgress.logs}
          fileName={parseProgress.fileName}
        />

        {/* 轻提示 */}
        <轻提示
          message={toast}
          onClose={() => setToast(null)}
        />

        {/* 设置对话框 */}
        <Dialog open={settingsOpen} onOpenChange={setSettingsOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>系统设置</DialogTitle>
              <DialogDescription>
                配置多模态 RAG 系统的参数和偏好设置
              </DialogDescription>
            </DialogHeader>
            <div className="py-4">
              <Alert>
                <AlertDescription>
                  设置功能正在开发中，敬请期待更多自定义选项。
                </AlertDescription>
              </Alert>
            </div>
          </DialogContent>
        </Dialog>

        {/* 帮助对话框 */}
        <Dialog open={helpOpen} onOpenChange={setHelpOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>使用帮助</DialogTitle>
              <DialogDescription>
                了解如何使用多模态 RAG 工作台的各项功能
              </DialogDescription>
            </DialogHeader>
            <div className="py-4 space-y-4">
              <div>
                <h4 className="font-medium mb-2">键盘快捷键</h4>
                <ul className="text-sm text-muted-foreground space-y-1">
                  <li>• Enter: 发送消息</li>
                  <li>• Shift + Enter: 换行</li>
                  <li>• Ctrl/Cmd + U: 上传 PDF</li>
                  <li>• Ctrl/Cmd + I: 上传图片</li>
                  <li>• Esc: 关闭弹窗</li>
                </ul>
              </div>
              <div>
                <h4 className="font-medium mb-2">支持的文件格式</h4>
                <ul className="text-sm text-muted-foreground space-y-1">
                  <li>• PDF: 支持 OCR 文字识别</li>
                  <li>• 图片: JPG, PNG, WebP 等常见格式</li>
                  <li>• 音频: MP3, WAV, M4A 等格式</li>
                </ul>
              </div>
            </div>
          </DialogContent>
        </Dialog>


      </div>
    </ErrorBoundary>
  );
}