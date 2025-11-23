# multi_RAG_agent

多模态 RAG 工作台（Multi RAG Agent） — 一个集成前端（React + Vite）与后端（FastAPI + LangChain）的多模态检索增强生成（RAG）工作台样例项目。

本仓库包含：

- `ocr_rag/`：前端与后端主代码目录。
  - `ocr_rag/src/`：React + TypeScript 前端应用（Vite）。
  - `ocr_rag/backend/`：FastAPI 后端服务，集成 LangChain、工具（web search、time tool 等）。

## 主要特性

- 多模态输入：文本、图片、音频、PDF。
- RAG（检索增强生成）架构，支持知识库引用与来源回溯。
- 流式聊天（SSE）与同步聊天 API。
- 后端工具集成：网络检索、时间工具、搜索结果审查等。
- 简洁的前端 UI，支持对话历史、知识库管理与模型切换。

## 快速开始

以下步骤在 Windows / PowerShell 下演示。请根据实际环境调整。

### 后端

1. 进入后端目录并安装依赖：

```powershell
cd ocr_rag/backend
pip install -r requirements.txt
```

2. 配置环境变量（推荐使用 `.env`）：

- 复制示例并编辑：

```powershell
copy .env.example .env
# 然后用编辑器打开 .env 并填写 OPENAI_API_KEY 等
```

- 或在 `env_config.py` 中直接设置（开发用）：

```python
os.environ["OPENAI_API_KEY"] = "your_actual_deepseek_api_key_here"
```

3. 启动服务：

```powershell
# 在 backend 目录
python start.py
```

服务将默认在 `http://localhost:8000` 启动，API 文档在 `http://localhost:8000/docs`。

### 前端

1. 进入前端目录并安装依赖：

```powershell
cd ocr_rag
npm install
```

2. 启动开发服务器：

```powershell
npm run dev
```

前端通常在 `http://localhost:5173`（或 Vite 指定的端口）可访问。

## 项目结构（简要）

- `ocr_rag/src/`：前端源码
  - `components/`：React 组件（组件以中文命名是项目约定）
  - `api/`：前端 API 封装，例如 `chat.ts`
  - `assets/`：图标与图片
- `ocr_rag/backend/`：后端源码
  - `main.py`：FastAPI 应用入口
  - `start.py`：启动脚本
  - `tools/`：后端工具（web search、time tool 等）
  - `data/`：运行时数据（对话存储等）
  - `logs/`：日志输出目录

## API 概览

- `GET /` — 健康检查
- `GET /api/models` — 获取支持的模型列表
- `GET /api/knowledge-bases` — 列出知识库
- `POST /api/chat` — 同步聊天接口
- `POST /api/chat/stream` — 流式聊天（SSE）接口
- `GET /api/conversations/{conversation_id}` — 获取会话详情

后端 `README.md`（`ocr_rag/backend/README.md`）有更详尽的接口与工具说明。

## 开发提示

- 请确保不要将敏感信息（API Key）提交到公共仓库，使用 `.env` 或秘钥管理服务。
- 前端依赖较多（node_modules），建议将 `node_modules/` 添加到 `.gitignore`（通常已配置）。
- 若在将代码推送到 GitHub 时遇到网络问题（例如 `Recv failure: Connection reset`），请检查网络/代理/VPN 设置或改用 SSH 推送。

## 常见运维命令

- 后端查看日志（Linux / WSL）：

```bash
tail -f ocr_rag/backend/logs/app.log
```

- 前端构建生产包：

```powershell
cd ocr_rag
npm run build
```

- 将本地仓库推送到 GitHub（示例）：

```powershell
git remote add origin https://github.com/<你的用户名>/multi_RAG_agent.git
git branch -M main
git push -u origin main
```

## 贡献

欢迎提交 Issue 与 Pull Request。请遵循良好的提交信息与代码风格，前端遵循 TypeScript + React 约定，后端遵循 PEP8 与项目既有风格。

## 许可证

请在此处添加许可证说明（例如 MIT）。

---

如需我把这个 `README.md` 自动提交到本地 Git 并尝试推送到你的 GitHub（需要网络连通与认证），我可以继续执行。