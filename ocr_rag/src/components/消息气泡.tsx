import { cn } from "./ui/utils";
import { Avatar, AvatarFallback } from "./ui/avatar";
import { Badge } from "./ui/badge";
import { Bot, User, Wrench, FileText } from "lucide-react";
import { 引用上标 } from "./引用上标";
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useState } from "react";

export interface ContentBlock {
  type: 'text' | 'image' | 'audio' | 'pdf';
  content: string;
  thumbnail?: string;
  transcription?: string;
  filename?: string;
  filesize?: number;
}

export interface Reference {
  id: number;
  text: string;
  source: string;
  page: number;
  chunk_id: number;
  source_info: string;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'tool';
  contentBlocks: ContentBlock[];
  references?: Reference[];
  timestamp: Date;
  isStreaming?: boolean;
}

interface 消息气泡Props {
  message: Message;
  onReferenceClick: (references: Reference[]) => void;
  activeTools?: Array<{name: string, args: any}>;
}

export function 消息气泡({ message, onReferenceClick, activeTools }: 消息气泡Props) {
  // 添加防护性检查
  if (!message) {
    return <div className="flex gap-3 mb-4">消息加载中...</div>;
  }

  const isUser = message.role === 'user';
  const isAssistant = message.role === 'assistant';
  const isTool = message.role === 'tool';
  const [isThoughtProcessCollapsed, setIsThoughtProcessCollapsed] = useState(false);

  const renderAvatar = () => {
    if (isUser) {
      return (
        <Avatar className="w-10 h-10 shadow-[0_10px_25px_rgba(15,23,42,0.08)] border border-white/60 bg-white">
          <AvatarFallback className="bg-slate-100 text-slate-600">
            <User className="w-4 h-4" />
          </AvatarFallback>
        </Avatar>
      );
    } else if (isAssistant) {
      return (
        <Avatar className="w-10 h-10 shadow-[0_10px_25px_rgba(15,23,42,0.08)] border border-white/60 bg-white">
          <AvatarFallback className="bg-sky-100 text-sky-600">
            <Bot className="w-4 h-4" />
          </AvatarFallback>
        </Avatar>
      );
    } else {
      return (
        <Avatar className="w-10 h-10 shadow-[0_10px_25px_rgba(15,23,42,0.08)] border border-white/60 bg-white">
          <AvatarFallback className="bg-indigo-100 text-indigo-600">
            <Wrench className="w-4 h-4" />
          </AvatarFallback>
        </Avatar>
      );
    }
  };

  const renderContent = (block: ContentBlock, index: number) => {
    // 添加防护性检查
    if (!block) {
      return <div key={index}>内容加载中...</div>;
    }

    switch (block.type) {
      case 'text':
        // 添加防护性检查
        if (typeof block.content !== 'string') {
          return <div key={index}>内容格式错误</div>;
        }

        const isThoughtProcess = block.content.startsWith('思考过程：');

        if (isThoughtProcess) {
          const thoughtProcess = block.content.substring('思考过程：'.length).trim();
          // 如果思考过程为空，不渲染任何内容
          if (!thoughtProcess) {
            return null;
          }
          
          // 确保只有一个思考过程组件
          return (
            <div key={index} className="bg-blue-50/50 border border-blue-100 rounded-2xl overflow-hidden mb-4">
              <div
                className="font-medium text-blue-700 p-3 px-4 flex items-center justify-between cursor-pointer hover:bg-blue-50 transition-colors"
                onClick={() => setIsThoughtProcessCollapsed(!isThoughtProcessCollapsed)}
              >
                <div className="flex items-center text-sm">
                  <span className="mr-2">🧠</span>
                  思考过程
                </div>
                <span className="text-xs opacity-60">{isThoughtProcessCollapsed ? '展开' : '收起'}</span>
              </div>
              {!isThoughtProcessCollapsed && (
                <div className="text-slate-600 px-4 pb-4 pt-1 prose prose-sm max-w-none break-words leading-relaxed bg-blue-50/30">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {thoughtProcess || '无思考过程内容'}
                  </ReactMarkdown>
                </div>
              )}
            </div>
          );
        }

        // 默认渲染最终答案
        const processAnswerContent = (content: string) => {
          // 如果内容为空，显示默认文本
          if (content === undefined || content === null) {
            return <span className="text-gray-500 italic">正在生成内容...</span>;
          }
          
          if (content === '') {
            return <span className="text-gray-500 italic">无内容</span>;
          }
          
          const parts = content.split(/(\[\d+\])/g);
          
          return parts.map((part, i) => {
            const match = part.match(/\[(\d+)\]/);
            if (match) {
              if (message.references && message.references.length > 0) {
                const refId = parseInt(match[1], 10);
                const reference = message.references.find(ref => ref && ref.id === refId);
                if (reference) {
                  return (
                    <引用上标
                      key={i}
                      number={refId.toString()}
                      onClick={() => onReferenceClick([reference])}
                    />
                  );
                }
              }
            }
            
            // 修复：移除 ReactMarkdown 组件的 className 属性
            return (
              <span key={i} className="inline">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{part || ''}</ReactMarkdown>
              </span>
            );
          });
        };

        return (
          <div key={index} className={cn(
            "prose prose-slate dark:prose-invert max-w-none break-words leading-relaxed text-[15px]",
            isAssistant && "px-1"
          )}>
            {processAnswerContent(block.content)}
          </div>
        );

      case 'image':
        // 添加防护性检查
        if (!block.content && !block.thumbnail) {
          return <div key={index}>图片加载失败</div>;
        }
        
        return (
          <div key={index} className="mt-2">
            <img
              src={block.thumbnail || block.content}
              alt="用户上传的图片"
              className="max-w-xs rounded-2xl shadow-[0_12px_30px_rgba(15,23,42,0.08)]"
              onError={(e) => {
                e.currentTarget.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjZGRkIi8+PHRleHQgeD0iNTAlIiB5PSI1MCUiIGZvbnQtZmFtaWx5PSJhcmlhbCIgZm9udC1zaXplPSIxNCIgZmlsbD0iIzk5OSIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZHk9Ii4zZW0iPuWbvueJh+WKoTwvdGV4dD48L3N2Zz4=';
              }}
            />
          </div>
        );
        
      case 'pdf':
        return (
          <div key={index} className="flex items-center gap-2 p-3 bg-slate-50 dark:bg-gray-800 rounded-2xl text-sm text-slate-700">
            <FileText className="w-4 h-4" />
            <span>{block.filename || 'PDF文档'}</span>
          </div>
        );

      default:
        return <div key={index}>{block.content || '无内容'}</div>;
    }
  };

  // 如果没有任何内容块，显示一个默认消息
  const hasContent = message.contentBlocks && Array.isArray(message.contentBlocks) && message.contentBlocks.length > 0;
  
  return (
    <div className={cn(
      "flex w-full gap-4 mb-6",
      isUser ? "justify-end" : "justify-start"
    )}>
      <div className={cn("flex items-start gap-4", isUser && "flex-row-reverse")}
      >
        {renderAvatar()}

        <div 
          className={cn(
            "flex flex-col",
            isUser ? "max-w-[85%] sm:max-w-[75%]" : "w-full max-w-[800px]"
          )}
        >
        {/* 角色标识 */}
        {!isUser && (
          <div className="flex items-center gap-2 mb-2 ml-1 text-xs uppercase tracking-wide text-slate-400">
            <Badge
              variant="secondary"
              className="bg-transparent border-transparent px-0 font-semibold text-[10px] text-slate-500"
            >
              {isAssistant ? "助手" : "工具"}
            </Badge>
            <span>
              {message.timestamp ? message.timestamp.toLocaleTimeString() : '未知时间'}
            </span>
            {/* 工具调用状态 */}
            {isAssistant && activeTools && activeTools.length > 0 && (
              <div className="flex items-center gap-1 ml-2">
                <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse"></div>
                <span className="text-blue-600 font-medium">
                  正在调用: {activeTools.map(tool => tool.name).join(', ')}
                </span>
              </div>
            )}
          </div>
        )}

        {/* User Message Wrapper */}
        {isUser && (
           <div className="bg-[#f5f7fb] text-slate-900 rounded-[24px] rounded-tr-sm px-6 py-4 shadow-sm text-[15px] leading-relaxed border border-transparent">
              <div className="space-y-3">
                {hasContent ? (
                  message.contentBlocks.map((block, index) => {
                    if (!block) return <div key={index}>内容加载中...</div>;
                    return renderContent(block, index);
                  })
                ) : (
                  <div className="text-gray-500 italic">
                    {message.isStreaming ? '正在生成内容...' : '无内容'}
                  </div>
                )}
              </div>
           </div>
        )}

        {/* Assistant Message Wrapper (Transparent) */}
        {!isUser && (
           <div className="space-y-3">
              {hasContent ? (
                message.contentBlocks.map((block, index) => {
                  if (!block) return <div key={index}>内容加载中...</div>;
                  return renderContent(block, index);
                })
              ) : (
                <div className="text-gray-500 italic px-1">
                  {message.isStreaming ? '正在生成内容...' : '无内容'}
                </div>
              )}
           </div>
        )}

        {/* 流式输出骨架屏 */}
        {message.isStreaming && (
          <div className="flex items-center gap-1 mt-3 px-1">
            <div className="w-2 h-2 bg-sky-400 rounded-full animate-pulse"></div>
            <div className="w-2 h-2 bg-sky-400 rounded-full animate-pulse" style={{ animationDelay: '0.2s' }}></div>
            <div className="w-2 h-2 bg-sky-400 rounded-full animate-pulse" style={{ animationDelay: '0.4s' }}></div>
          </div>
        )}
        </div>
      </div>
    </div>
  );
}