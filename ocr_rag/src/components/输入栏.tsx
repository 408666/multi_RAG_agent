import { useState, useRef, KeyboardEvent } from "react";
import { Button } from "./ui/button";
import { Textarea } from "./ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "./ui/select";
import { Paperclip, Image, Mic, Send, Square, X, FileText, Clock, CheckCircle } from "lucide-react";

interface PendingImage {
  id: string;
  file: File;
  dataUrl: string;
  thumbnail: string;
}

interface PendingPDF {
  id: string;
  file: File;
  filename: string;
  size: number;
  processed?: boolean;
}

interface PDFProcessing {
  isProcessing: boolean;
  progress: number;
  step: string;
  message: string;
}

interface PendingAudio {
  id: string;
  file: File;
  filename: string;
  duration: number;
  transcription?: string;
  processed?: boolean;
}

interface 输入栏Props {
  value: string;
  onChange: (value: string) => void;
  onSend: () => void;
  onStop: () => void;
  onUploadPDF: (file: File) => void;
  onUploadImage: (file: File) => void;
  onUploadAudio: (file: File) => void;
  isStreaming: boolean;
  disabled?: boolean;
  pendingImages?: PendingImage[];
  onRemoveImage?: (id: string) => void;
  pendingPDFs?: PendingPDF[];
  onRemovePDF?: (id: string) => void;
  pdfProcessing?: PDFProcessing;
  pendingAudios?: PendingAudio[];
  onRemoveAudio?: (id: string) => void;
  模型: string;
  on模型Change: (value: string) => void;
}

export function 输入栏({
  value,
  onChange,
  onSend,
  onStop,
  onUploadPDF,
  onUploadImage,
  onUploadAudio,
  isStreaming,
  disabled = false,
  pendingImages = [],
  onRemoveImage,
  pendingPDFs = [],
  onRemovePDF,
  pdfProcessing,
  pendingAudios = [],
  onRemoveAudio,
  模型,
  on模型Change
}: 输入栏Props) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const pdfInputRef = useRef<HTMLInputElement>(null);
  const imageInputRef = useRef<HTMLInputElement>(null);  
  const audioInputRef = useRef<HTMLInputElement>(null);
  const toolInputRef = useRef<HTMLInputElement>(null);

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if ((value.trim() || pendingImages.length > 0 || pendingPDFs.length > 0 || pendingAudios.length > 0) && !isStreaming) {
        onSend();
      }
    }
    
    // 键盘快捷键
    if (e.ctrlKey || e.metaKey) {
      switch (e.key) {
        case 'u':
        case 'U':
          e.preventDefault();
          pdfInputRef.current?.click();
          break;
        case 'i':
        case 'I':
          e.preventDefault();
          imageInputRef.current?.click();
          break;
        case 'm':
        case 'M':
          e.preventDefault();
          audioInputRef.current?.click();
          break;
      }
    }
  };

  const handleFileUpload = (
    inputRef: React.RefObject<HTMLInputElement>,
    acceptTypes: string,
    onUpload: (file: File) => void
  ) => {
    if (inputRef.current) {
      inputRef.current.accept = acceptTypes;
      inputRef.current.onchange = (e) => {
        const file = (e.target as HTMLInputElement).files?.[0];
        if (file) {
          onUpload(file);
        }
      };
      inputRef.current.click();
    }
  };

  const handleAddToolClick = () => {
    if (toolInputRef.current) {
      toolInputRef.current.accept = '.pdf,image/*,audio/*,video/mp4,video/avi,video/mov,video/mkv,video/webm';
      toolInputRef.current.onchange = (e) => {
        const file = (e.target as HTMLInputElement).files?.[0];
        if (!file) return;

        if (file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf')) {
          onUploadPDF(file);
        } else if (file.type.startsWith('image/')) {
          onUploadImage(file);
        } else if (file.type.startsWith('audio/') || file.type.startsWith('video/')) {
          onUploadAudio(file);
        } else {
          onUploadPDF(file);
        }
      };
      toolInputRef.current.click();
    }
  };

  return (
    <div className="bg-transparent w-full px-4 sm:px-8 lg:px-12 pb-8 pt-6">
      <div className="w-full max-w-[1100px] mx-auto space-y-4">
        {/* PDF处理进度 */}
      {pdfProcessing?.isProcessing && (
        <div className="p-4 sm:p-5 bg-white/90 rounded-[28px] shadow-[0_18px_40px_rgba(15,23,42,0.08)] border border-white/80">
          <div className="flex items-center gap-2 mb-2">
            <Clock className="w-4 h-4 text-slate-500 animate-spin" />
            <span className="text-sm font-medium text-slate-600">正在处理PDF文档...</span>
          </div>
          <div className="w-full bg-slate-100 rounded-full h-2 mb-2">
            <div
              className="bg-slate-900 h-2 rounded-full transition-all duration-300"
              style={{ width: `${pdfProcessing.progress}%` }}
            />
          </div>
          <p className="text-xs text-slate-500">{pdfProcessing.message}</p>
        </div>
      )}
      
      {/* 暂存PDF预览区 */}
      {pendingPDFs.length > 0 && (
        <div className="space-y-2">
          <div className="text-sm text-slate-500">等待发送的文档</div>
          <div className="flex gap-3 flex-wrap">
            {pendingPDFs.map((pdf) => (
              <div key={pdf.id} className="relative group bg-white rounded-2xl px-4 py-3 shadow-[0_14px_35px_rgba(15,23,42,0.08)] border border-white/80 min-w-[160px]">
                <div className="flex items-center gap-2 mb-2 text-slate-600">
                  <div className="flex items-center justify-center w-9 h-9 rounded-2xl bg-slate-900 text-white text-sm font-medium">
                    <FileText className="w-4 h-4" />
                  </div>
                  {pdf.processed && <CheckCircle className="w-4 h-4 text-emerald-500" />}
                </div>
                <button
                  onClick={() => onRemovePDF?.(pdf.id)}
                  className="absolute -top-2 -right-2 w-6 h-6 bg-black/70 text-white rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
                >
                  <X className="w-3 h-3" />
                </button>
                <div className="text-xs font-medium text-slate-700 truncate mb-1" title={pdf.filename}>
                  {pdf.filename}
                </div>
                <div className="text-xs text-slate-500">
                  {(pdf.size / 1024).toFixed(1)} KB
                </div>
                {pdf.processed && (
                  <div className="text-xs text-emerald-600 mt-1">已处理</div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
      
      {/* 暂存图片预览区 */}
      {pendingImages.length > 0 && (
        <div className="space-y-2">
          <div className="text-sm text-slate-500">等待发送的图片</div>
          <div className="flex gap-3 flex-wrap">
            {pendingImages.map((img) => (
              <div key={img.id} className="relative group shadow-[0_14px_35px_rgba(15,23,42,0.08)] rounded-3xl overflow-hidden">
                <img
                  src={img.thumbnail}
                  alt={img.file.name}
                  className="w-20 h-20 object-cover"
                />
                <button
                  onClick={() => onRemoveImage?.(img.id)}
                  className="absolute -top-2 -right-2 w-6 h-6 bg-black/70 text-white rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
                >
                  <X className="w-3 h-3" />
                </button>
                <div className="absolute bottom-0 left-0 right-0 bg-black/50 text-white text-[11px] px-2 py-1 truncate">
                  {img.file.name}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
      
      {/* 暂存音频预览区 */}
      {pendingAudios.length > 0 && (
        <div className="space-y-2">
          <div className="text-sm text-slate-500">等待发送的音频</div>
          <div className="flex gap-3 flex-wrap">
            {pendingAudios.map((audio) => (
              <div key={audio.id} className="relative group bg-white rounded-2xl px-4 py-3 shadow-[0_14px_35px_rgba(15,23,42,0.08)] border border-white/80 min-w-[180px]">
                <div className="flex items-center gap-2">
                  <Mic className="w-4 h-4 text-slate-500" />
                  <div className="text-xs text-slate-500">
                    <div className="font-medium text-slate-700">{audio.filename}</div>
                    <div>{Math.round(audio.duration)}s</div>
                  </div>
                </div>
                <button
                  onClick={() => onRemoveAudio?.(audio.id)}
                  className="absolute -top-2 -right-2 w-6 h-6 bg-black/70 text-white rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
                >
                  <X className="w-3 h-3" />
                </button>
                {audio.transcription && (
                  <div className="mt-2 text-[11px] text-slate-500 line-clamp-2">
                    {audio.transcription}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="bg-white/95 dark:bg-[#1E1F20] rounded-[32px] shadow-[0_28px_75px_rgba(15,23,42,0.08)] border border-white/80 dark:border-[#444746] p-4 sm:p-6 transition-colors duration-200">
        <div className="flex flex-col gap-4">
          <div className="flex items-center gap-3">
            <Select value={模型} onValueChange={on模型Change}>
              <SelectTrigger className="w-[180px] rounded-2xl bg-slate-100 dark:bg-[#2D2E30] border-0 focus:ring-0 dark:text-gray-200">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="dark:bg-[#1E1F20] dark:border-[#444746]">
                <SelectItem value="deepseek-chat" className="dark:text-gray-200 dark:focus:bg-[#2D2E30]">DeepSeek Chat</SelectItem>
                <SelectItem value="deepseek-reasoner" className="dark:text-gray-200 dark:focus:bg-[#2D2E30]">DeepSeek Reasoner</SelectItem>
                <SelectItem value="qwen3-vl-8b-instruct" className="dark:text-gray-200 dark:focus:bg-[#2D2E30]">Qwen3 VL 8B Instruct</SelectItem>
              </SelectContent>
            </Select>
            <div className="flex-1 relative">
              <Textarea
                ref={textareaRef}
                value={value}
                onChange={(e) => onChange(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={
                  [pendingImages.length > 0 && "图片", pendingPDFs.length > 0 && "文档", pendingAudios.length > 0 && "音频"]
                    .filter(Boolean).length > 0
                    ? `输入关于${[pendingImages.length > 0 && "图片", pendingPDFs.length > 0 && "文档", pendingAudios.length > 0 && "音频"]
                        .filter(Boolean).join("、")}的问题...`
                    : "在这里输入您的问题，Enter 发送"
                }
                className="min-h-[56px] max-h-40 resize-none bg-transparent border-0 focus-visible:ring-0 focus-visible:ring-offset-0 pr-28 text-base leading-relaxed placeholder:text-slate-400 dark:placeholder:text-gray-500 dark:text-gray-100"
                disabled={disabled}
              />
              <div className="absolute right-0 bottom-1 flex items-center gap-1">
                <Button
                  variant="ghost"
                  size="icon"
                  className="w-10 h-10 rounded-full text-slate-500 hover:bg-slate-100 dark:text-gray-400 dark:hover:bg-[#2D2E30] dark:hover:text-gray-200"
                  onClick={() => handleFileUpload(imageInputRef, 'image/*', onUploadImage)}
                  disabled={disabled}
                  title="上传图片 (Ctrl/Cmd+I)"
                >
                  <Image className="w-4 h-4" />
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  className="w-10 h-10 rounded-full text-slate-500 hover:bg-slate-100 dark:text-gray-400 dark:hover:bg-[#2D2E30] dark:hover:text-gray-200"
                  onClick={() => handleFileUpload(audioInputRef, 'audio/*,video/mp4,video/avi,video/mov,video/mkv,video/webm', onUploadAudio)}
                  disabled={disabled}
                  title="上传音频/视频 (Ctrl/Cmd+M)"
                >
                  <Mic className="w-4 h-4" />
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  className="w-10 h-10 rounded-full text-slate-500 hover:bg-slate-100 dark:text-gray-400 dark:hover:bg-[#2D2E30] dark:hover:text-gray-200"
                  onClick={() => handleFileUpload(pdfInputRef, '.pdf', onUploadPDF)}
                  disabled={disabled}
                  title="上传 PDF (Ctrl/Cmd+U)"
                >
                  <Paperclip className="w-4 h-4" />
                </Button>
              </div>
            </div>
            <div className="flex items-center">
              {isStreaming ? (
                <Button
                  onClick={onStop}
                  variant="ghost"
                  size="icon"
                  className="w-12 h-12 rounded-full bg-slate-900 text-white hover:bg-slate-800 dark:bg-white dark:text-black dark:hover:bg-gray-200"
                >
                  <Square className="w-4 h-4" />
                </Button>
              ) : (
                <Button
                  onClick={onSend}
                  disabled={(!value.trim() && pendingImages.length === 0 && pendingPDFs.length === 0 && pendingAudios.length === 0) || disabled}
                  size="icon"
                  className="w-12 h-12 rounded-full bg-slate-900 text-white hover:bg-slate-800 dark:bg-white dark:text-black dark:hover:bg-gray-200"
                >
                  <Send className="w-4 h-4" />
                </Button>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* 隐藏的文件输入 */}
      <input ref={pdfInputRef} type="file" className="hidden" />
      <input ref={imageInputRef} type="file" className="hidden" />
      <input ref={audioInputRef} type="file" className="hidden" />
      <input ref={toolInputRef} type="file" className="hidden" />
      </div>
    </div>
  );
}