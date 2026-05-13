# Implementation Plan: Agent + RAG 个人知识库助手

## Metadata
- Plan ID: plan-agent-rag-20260513
- Source Spec: `.omc/specs/deep-interview-agent-rag-tool-calling.md`
- Consensus Rounds: 0
- Status: DRAFT (pending Architect + Critic review)
- Type: greenfield

---

## RALPLAN-DR Summary

### Principles (3-5)
1. **学习优先 (Learn First)**: 代码结构清晰、关键路径有注释，宁可多写几行也不要过度抽象
2. **最小可行 Agent (Minimal Viable Agent)**: 单工具 Agent 已足够演示工具调用+决策逻辑，不加多余工具
3. **关注点分离 (Separation of Concerns)**: Agent 逻辑 / RAG 管道 / API 路由 / 前端组件各自在独立文件中
4. **模型不可知 (Model Agnostic)**: 通过配置切换 LLM，不硬编码任何提供商
5. **渐进式可扩展 (Progressive Extensibility)**: 后续加工具/换向量库/换模型只需改配置，不需重构

### Decision Drivers (Top 3)
1. **可学习性**: 代码必须能让人看懂 Agent 决策流程、RAG 检索流程
2. **功能完整性**: 上传→索引→Agent决策→检索→生成的完整链路必须跑通
3. **开发速度**: 学习项目不需要过度工程化，尽快跑通全链路

### Viable Options

#### Option A: LangChain create_tool_calling_agent + Chroma（推荐）
**Approach:** 使用 LangChain 内置的 `create_tool_calling_agent` + `AgentExecutor`，Chroma 本地向量库
**Pros:**
- LangChain 原生支持，文档最全
- `create_tool_calling_agent` 自动处理工具调用JSON格式
- Chroma 零配置本地运行，pip install 即可
- 社区最活跃，遇到问题容易搜
**Cons:**
- LangChain 封装层多，抽象泄漏时调试困难
- AgentExecutor 的默认行为有时需要微调
**Verdict:** 最佳学习路径，封装度恰好够用

#### Option B: 手写 Agent 决策循环 + FAISS
**Approach:** 不依赖 LangChain Agent 框架，自己写 while loop + tool dispatch
**Pros:**
- 完全控制，每个决策步骤都透明
- FAISS 性能优于 Chroma（大规模场景）
**Cons:**
- 失去了学习 LangChain Agent 框架的机会（用户核心目标之一）
- 需要处理 OpenAI/Anthropic 不同的 tool calling 格式
- FAISS 安装有时有平台兼容问题
**Why rejected:** 用户想学 LangChain Agent，自己造轮子违背学习目标。FAISS 对这个小项目过度。

#### Option C: LangGraph Agent + Pinecone（云向量库）
**Approach:** 使用 LangGraph 构建有状态 Agent，Pinecone 托管向量库
**Pros:**
- LangGraph 是 LangChain 新方向，有状态 Agent 更灵活
- Pinecone 免运维
**Cons:**
- LangGraph 学习曲线陡，对新手不友好
- Pinecone 需要注册账号+网络，增加学习环境依赖
- 对单工具 Agent 完全过度设计
**Why rejected:** 不必要的复杂度。单工具 Agent 用 LangGraph 是杀鸡用牛刀。

---

## Requirements Summary
构建个人知识库助手：用户通过 React Web UI 上传 PDF/TXT 文档 → FastAPI 后端处理并索引到 Chroma 向量库 → 用户提问时，LangChain Agent 自主判断是否需要用 RAG 检索文档 → 支持 OpenAI/Anthropic/Ollama 三套 LLM 通过配置切换。

## Acceptance Criteria
- [ ] AC1: 用户可通过 Web UI 上传 PDF/TXT 文档
- [ ] AC2: Agent 正确区分"需要检索文档"和"直接回答"的问题（工具决策正确性）
- [ ] AC3: 文档相关问题检索后回答准确、有来源引用
- [ ] AC4: 通用知识问题不触发检索，直接回答
- [ ] AC5: React 前端完成文件上传、消息发送、对话历史展示
- [ ] AC6: FastAPI `/upload` 和 `/chat` API 完整可用
- [ ] AC7: 通过 `.env` 或配置文件切换 LLM 提供商
- [ ] AC8: 代码模块化：`agent.py` / `rag.py` / `main.py` / `config.py` 各自独立
- [ ] AC9: 关键路径有学习性注释

## Implementation Steps

### Step 1: 项目骨架搭建
**Files:** `backend/requirements.txt`, `frontend/package.json`, `README.md`
- 初始化后端 Python 虚拟环境和 `requirements.txt`：`fastapi`, `uvicorn`, `langchain`, `langchain-openai`, `langchain-anthropic`, `langchain-community`, `chromadb`, `pypdf`, `python-multipart`, `python-dotenv`
- 初始化前端 Vite + React 项目
- 创建 `.env.example` 含所有可配置项说明
- **Verification:** `uvicorn main:app` 能启动，`npm run dev` 能启动

### Step 2: 后端配置与模型抽象层
**Files:** `backend/config.py`
- 实现 `Settings` 类，从 `.env` 读取：`LLM_PROVIDER` (openai/anthropic/ollama), `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `OLLAMA_BASE_URL`, `EMBEDDING_MODEL`, `CHROMA_PERSIST_DIR`
- 实现 `get_llm()` 工厂函数：根据 `LLM_PROVIDER` 返回 `ChatOpenAI` / `ChatAnthropic` / `ChatOllama`
- 实现 `get_embeddings()` 工厂函数：返回对应 Embedding 实例
- **Verification:** 切换 `.env` 中的 `LLM_PROVIDER` 分别测试三个模型能正常初始化

### Step 3: RAG 管道
**Files:** `backend/rag.py`
- `DocumentLoader`: 支持 PDF (`PyPDFLoader`) 和 TXT (`TextLoader`)
- `split_documents()`: 使用 `RecursiveCharacterTextSplitter` (chunk_size=1000, chunk_overlap=200)
- `create_vectorstore()`: 从文档列表创建 Chroma 向量库
- `get_retriever()`: 返回配置好的 retriever (k=4)
- `create_rag_tool()`: 用 `create_retriever_tool` 创建 LangChain Tool，name="retrieve_documents", description 描述何时使用
- **Verification:** 上传一个测试 PDF，检查 Chroma 持久化目录有数据，retriever 能返回相关 chunk

### Step 4: Agent 定义
**Files:** `backend/agent.py`
- 使用 `create_tool_calling_agent()` 创建 Agent，绑定 RAG tool
- 使用 `AgentExecutor` 包装，设置 `verbose=True`（学习目的）
- System prompt 明确指导 Agent 的决策规则：涉及文档内容→检索；通用知识→直接回答
- `ask_agent()` 函数：接收问题和 session_id，返回答案
- **Verification:** 用测试问题验证 Agent 正确决策（文档问题调用 tool，通用问题不调用）

### Step 5: FastAPI 路由
**Files:** `backend/main.py`, `backend/models.py`
- `models.py`: Pydantic 模型 — `ChatRequest(question, session_id)`, `ChatResponse(answer, sources)`, `UploadResponse(filename, chunks_count)`
- `POST /upload`: 接收文件 → 保存临时文件 → 加载/分块 → 存入 Chroma（用 session_id 做 collection 隔离）
- `POST /chat`: 接收问题 → 调用 `ask_agent()` → 返回答案 + 来源引用
- CORS 配置允许前端跨域
- **Verification:** 用 curl/httpx 测试两个端点

### Step 6: React 前端
**Files:** `frontend/src/App.jsx`, `frontend/src/components/ChatWindow.jsx`, `frontend/src/components/FileUpload.jsx`, `frontend/src/components/Message.jsx`, `frontend/src/api.js`
- `api.js`: 封装 `/upload` 和 `/chat` API 调用
- `FileUpload.jsx`: 拖拽/点击上传 PDF/TXT，显示上传状态
- `ChatWindow.jsx`: 对话列表 + 输入框 + 发送按钮
- `Message.jsx`: 单条消息组件（区分用户/AI，AI 消息显示来源引用）
- `App.jsx`: 组合 FileUpload + ChatWindow，管理状态
- **Verification:** 完整走通：上传文档 → 提问 → 看到回答

### Step 7: 学习性注释补全
**涉及文件:** `agent.py`, `rag.py`, `config.py`
- Agent 决策流程注释：解释 Agent 如何决定调用工具
- RAG 管道注释：解释 Document → Chunk → Embedding → VectorStore → Retrieve 的数据流
- 工具定义注释：解释 tool name/description 如何影响 Agent 行为
- 配置切换注释：解释工厂函数模式

### Step 8: 端到端测试与优化
- 准备 2-3 个测试 PDF/TXT 文档（中英文）
- 设计 5 个测试用例覆盖 AC1-AC9
- 测试 LLM 切换功能（至少测试 OpenAI + 一个其他）
- 确保错误处理（上传非 PDF/TXT 文件、空问题、LLM API 错误）

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| LangChain 版本 API 变化 | Medium | Medium | 锁定 `langchain>=0.3,<0.4`，关键 import 加版本注释 |
| Chroma 持久化路径问题（Windows） | Low | Low | 使用 `Path` 处理路径，`CHROMA_PERSIST_DIR` 可配置 |
| Ollama 本地模型速度慢/不可用 | Medium | Low | 默认 OpenAI，Ollama 作为可选方案，配置切换即可 |
| PDF 中文解析乱码 | Medium | Medium | PyPDFLoader 对中文支持一般，必要时换 `pdfplumber` |
| Agent 工具决策不稳定 | Medium | Medium | System prompt 中明确决策规则，降低 temperature |

## Verification Steps
1. 启动后端：`cd backend && uvicorn main:app --reload`
2. 启动前端：`cd frontend && npm run dev`
3. 通过 Web UI 上传一个 PDF 文件，确认返回上传成功
4. 提问"这份文档的主要内容是什么？"→ Agent 应检索文档并回答
5. 提问"1+1等于几？"→ Agent 应直接回答，不检索
6. 修改 `.env` 切换 `LLM_PROVIDER=anthropic`，重启后端，重复测试
7. 检查 `agent.py` 和 `rag.py` 是否有学习性注释

## Project Structure
```
agent-rag-kb/
├── backend/
│   ├── main.py              # FastAPI 入口 + CORS + 路由
│   ├── config.py             # 多模型配置切换 (get_llm/get_embeddings)
│   ├── agent.py              # Agent 定义 + create_tool_calling_agent
│   ├── rag.py                # RAG 管道 (load→split→embed→store→retrieve)
│   ├── models.py             # Pydantic request/response 模型
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── App.css
│   │   ├── main.jsx
│   │   ├── components/
│   │   │   ├── ChatWindow.jsx
│   │   │   ├── Message.jsx
│   │   │   └── FileUpload.jsx
│   │   └── api.js
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
├── .env.example
└── README.md
```
