# 多模态 RAG 工作台 - AI 编程指南

欢迎来到多模态 RAG 工作台项目！本文档旨在帮助 AI 编程代理快速理解项目结构、关键约定和开发工作流程。

## 架构概览

本项目是一个全栈应用，由两部分组成：

1.  **React 前端**: 位于 `ocr_rag/` 目录下，使用 Vite、TypeScript 和 React 构建。它负责用户界面和与后端的交互。
2.  **Python 后端**: 位于 `ocr_rag/backend/` 目录下，使用 FastAPI 和 LangChain 构建。它提供了一个多模态聊天 API，能够处理文本、PDF、图片和音频。

### 数据流

-   用户在 React 前端与应用交互。
-   前端通过调用 `http://localhost:8000` 上的 API 端点与 FastAPI 后端通信。
-   后端处理请求，与 LangChain 集成的大语言模型（如 DeepSeek）进行交互，并流式返回响应。
-   前端接收流式响应并实时更新 UI。

## 关键约定

### 前端 (`ocr_rag/`)

-   **组件命名**: **一个非常重要的约定是，React 组件使用中文命名**。例如：`ocr_rag/src/components/导航栏.tsx` 和 `ocr_rag/src/components/消息气泡.tsx`。在创建或修改组件时，请遵循此约定。
-   **UI 库**: 项目使用 `shadcn/ui` 和 `tailwindcss`。核心 UI 组件位于 `ocr_rag/src/components/ui/`。
-   **状态管理**: 应用状态主要通过 React Hooks (`useState`, `useEffect`) 在 `ocr_rag/src/App.tsx` 中管理。
-   **API 调用**: 与后端的所有 API 通信都封装在 `ocr_rag/src/api/chat.ts` 中。
-   **多模态内容**: 用户消息中的多模态内容（文本、图片、音频）被构造成一个 `contentBlocks` 数组进行处理。

### 后端 (`ocr_rag/backend/`)

-   **核心逻辑**: 主要的应用逻辑位于 `ocr_rag/backend/main.py`，其中定义了 FastAPI 的路由和核心聊天功能。
-   **配置**: 应用配置通过 `ocr_rag/backend/config.py` 和 `ocr_rag/backend/env_config.py` 管理。API 密钥等敏感信息应存储在 `.env` 文件中。
-   **LangChain 集成**: 后端深度集成 LangChain。`get_chat_model` 函数根据请求初始化不同的语言模型。`convert_history_to_messages` 负责将对话历史转换为 LangChain 的消息格式。
-   **模块化处理器**: 针对不同文件类型的处理逻辑是模块化的，例如 `pdf_processor.py` 和 `audio_processor.py`。
-   **引用提取**: `extract_references_from_content` 函数负责从模型的响应中解析出文档引用，这是 RAG 功能的核心部分。

## 开发工作流程

### 后端设置与运行

1.  **安装依赖**:
    ```bash
    cd ocr_rag/backend
    pip install -r requirements.txt
    ```
2.  **配置环境**:
    在 `ocr_rag/backend/` 目录下创建一个 `.env` 文件，并设置 `OPENAI_API_KEY`（用于 DeepSeek）。
    ```
    OPENAI_API_KEY=your_deepseek_api_key
    ```
3.  **启动服务**:
    ```bash
    python ocr_rag/backend/start.py
    ```
    服务将在 `http://localhost:8000` 启动。API 文档可在 `http://localhost:8000/docs` 查看。

### 前端设置与运行

1.  **安装依赖**:
    ```bash
    cd ocr_rag
    npm install
    ```
2.  **启动开发服务器**:
    ```bash
    npm run dev
    ```
    前端应用将在 `http://localhost:5173` （或另一个可用端口）上可用。

## 修改代码时的注意事项

-   **添加新组件**: 如果您在前端添加新组件，请使用中文命名并将其放在 `ocr_rag/src/components/` 目录下。
-   **修改 API**: 如果您修改了后端 API，请确保更新前端的 `ocr_rag/src/api/chat.ts` 文件以匹配新的接口。同时，记得更新 `http://localhost:8000/docs` 上的 OpenAPI 文档。
-   **处理新文件类型**: 如果要支持新的文件类型，您需要在后端创建一个新的处理器（例如 `video_processor.py`），并在 `main.py` 中集成它。同时，前端也需要更新以处理该文件的上传和表示。
