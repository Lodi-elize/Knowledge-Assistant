# Implementation Plan: Agent + RAG 个人知识库助手

## Metadata
- Plan ID: plan-agent-rag-20260513
- Source Spec: `.omc/specs/deep-interview-agent-rag-tool-calling.md`
- Consensus Rounds: 3
- Status: APPROVED (Critic accepted with reservations resolved)
- Type: greenfield

---

## RALPLAN-DR Summary

### Principles (3-5)
1. **学习优先 (Learn First)**: 代码结构清晰、关键路径有注释，宁可多写几行也不要过度抽象
2. **最小可行 Agent (Minimal Viable Agent)**: 单工具 Agent 已足够演示工具调用+决策逻辑，不加多余工具
3. **关注点分离 (Separation of Concerns)**: Agent 逻辑 / RAG 管道 / API 路由 / 前端组件各自在独立文件中
4. **模型不可知 (Model Agnostic)**: 通过配置切换 LLM，不硬编码任何提供商
5. **渐进式可扩展 (Progressive Extensibility)**: 模型切换只需改配置；新增工具/换向量库通过插件式模块扩展，改动范围限定在对应文件中

### Decision Drivers (Top 3)
1. **可学习性**: 代码必须能让人看懂 Agent 决策流程、RAG 检索流程
2. **功能完整性**: 上传→索引→Agent决策→检索→生成→流式输出的完整链路必须跑通
3. **开发速度**: 学习项目不需要过度工程化，尽快跑通全链路

### Viable Options

#### Option A: Hybrid — LangChain RAG 管道 + 手写 Agent 决策循环（推荐）
**Approach:** LangChain 负责 RAG 管道（文档加载、分块、Embedding、Chroma 向量库），Agent 决策循环手写 30-40 行 while loop 显式处理 LLM tool call → 执行 → 结果回传 → 生成回答
**Pros:**
- Agent 决策流程完全透明，每步可打印/日志，完美满足 Principle 1
- LangChain 处理 RAG 底层脏活（PDF 解析、chunking、Chroma CRUD），不减开发速度
- 避免了 `AgentExecutor` 抽象泄漏问题（架构评审已识别此风险）
- 手写循环中处理 OpenAI/Anthropic/Ollama 不同 tool calling JSON 格式，恰好是学习目标
**Cons:**
- 失去了学习 LangChain `create_tool_calling_agent` API 的机会
- 手写循环约 30-40 行，比调 AgentExecutor 多 20 行代码
- 需要手动处理三个 LLM 提供商的 tool call 格式差异
**Verdict:** 对单工具学习项目，手写循环是更强的教学选择。Architect 和 Critic 一致推荐此方案。

#### Option B: LangChain create_tool_calling_agent + AgentExecutor + Chroma
**Approach:** 使用 LangChain 内置的 `create_tool_calling_agent` + `AgentExecutor`，Chroma 本地向量库
**Pros:**
- LangChain 原生支持，API 简洁（~15 行完成 Agent 定义）
- Chroma 零配置本地运行
**Cons:**
- `AgentExecutor` 封装了 tool call → execute → observe → synthesize 循环，Principle 1 明确要求"宁可多写几行也不要过度抽象"
- 调试时需要阅读 LangChain 内部代码
**Why rejected:** 核心矛盾：Principle 1 要求透明，`AgentExecutor` 恰恰隐藏了 Agent 决策流程。对单工具 Agent，手写循环的 30 行代码教学价值远超 15 行 API 调用。

#### Option C: LangGraph Agent + Pinecone（云向量库）
**Approach:** 使用 LangGraph 构建有状态 Agent，Pinecone 托管向量库
**Pros:**
- LangGraph 提供显式状态图，比 AgentExecutor 更透明
- Pinecone 免运维
**Cons:**
- LangGraph 学习曲线陡，对单工具 Agent 明显过度
- Pinecone 需要注册账号+网络，增加学习环境依赖
**Why rejected:** 不必要的复杂度。单工具 Agent 用 LangGraph 是杀鸡用牛刀。未来添加多工具时可升级。

---

## Requirements Summary
构建个人知识库助手：用户通过 React Web UI 上传 PDF/TXT 文档 → FastAPI 后端处理并索引到 Chroma 向量库（按 session_id 隔离）→ 用户提问时，手写 Agent 决策循环自主判断是否需要用 RAG 检索文档 → 流式输出答案（SSE）+ 来源引用 → 支持 OpenAI/Anthropic/Ollama 三套 LLM 通过配置切换。

## Acceptance Criteria
- [ ] AC1: 用户可通过 Web UI 上传 PDF/TXT 文档（至少测试 1 个 PDF + 1 个 TXT）
- [ ] AC2: 用 8 个测试问题（4 个需检索文档 + 4 个通用知识）验证 Agent 决策正确率 ≥ 7/8（88%）。后端日志记录每次 tool call 决策
- [ ] AC3: 文档相关问题的回答必须包含至少 1 个来源引用（chunk 内容片段），且来源片段可在已上传文档中验证到
- [ ] AC4: 通用知识问题不触发检索，直接回答（AC2 测试集中 4 个通用知识问题全部不触发 tool call）
- [ ] AC5: React 前端完成：文件上传（含进度/状态）、消息发送、对话历史展示、流式逐字显示、Agent 思考中状态提示
- [ ] AC6: FastAPI `POST /upload` 和 `POST /chat`（SSE 流式）API 完整可用，含错误响应
- [ ] AC7: 通过 `.env` 切换 `LLM_PROVIDER` 后重启后端，Agent 正常工作（至少验证 OpenAI + Anthropic 或 Ollama）
- [ ] AC8: 代码模块化：`agent.py` / `rag.py` / `main.py` / `config.py` 各自独立，单一职责
- [ ] AC9: 关键路径有学习性注释：Agent 决策循环 / RAG 数据流 / 工具定义 / LLM 工厂函数

## Implementation Steps

### Step 1: 项目骨架搭建
**Files:** `backend/requirements.txt`, `frontend/package.json`, `.env.example`
- 初始化后端 Python 虚拟环境和 `requirements.txt`：`fastapi`, `uvicorn`, `langchain`, `langchain-openai`, `langchain-anthropic`, `langchain-community`, `chromadb`, `pypdf`, `pdfplumber`, `python-multipart`, `python-dotenv`, `sse-starlette`
- 初始化前端：`npm create vite@latest frontend -- --template react`
- 创建 `.env.example` 含所有可配置项及说明注释
- **Verification:** `uvicorn main:app` 能启动，`npm run dev` 能启动

### Step 2: 后端配置与模型抽象层
**Files:** `backend/config.py`
- `Settings` 类（基于 `pydantic-settings` 或 `os.getenv`）从 `.env` 读取：
  - `LLM_PROVIDER`: `openai` | `anthropic` | `ollama`
  - `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `OLLAMA_BASE_URL`
  - `LLM_MODEL_NAME`（各提供商的默认模型名）
  - `EMBEDDING_MODEL`（默认 `text-embedding-3-small`）
  - `CHROMA_PERSIST_DIR`（默认 `./chroma_data`）
  - `LLM_TEMPERATURE`（默认 0.0，降低 Agent 决策随机性）
- `get_llm()`: 工厂函数，返回 `ChatOpenAI` / `ChatAnthropic` / `ChatOllama`，统一设置 `temperature`
- `get_embeddings()`: 工厂函数，返回对应 Embedding 实例
- **Verification:** 切换 `.env` 中的 `LLM_PROVIDER` 分别测试三个模型能正常初始化（print 类型确认）

### Step 3: RAG 管道
**Files:** `backend/rag.py`
- `load_document(file_path: str)` → 根据扩展名选择 `PyPDFLoader`（PDF）/ `pdfplumber`（中文 PDF 备选）/ `TextLoader`（TXT）
- `split_documents(docs)`: `RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)`
- `create_vectorstore(docs, session_id: str)`: 创建 Chroma collection，命名 `session_{session_id}`，持久化到 `CHROMA_PERSIST_DIR`
- `get_retriever(session_id: str)`: 加载指定 session 的 Chroma collection，返回 retriever (k=4, search_type="similarity")
- `create_rag_tool(session_id: str)`: 用 `create_retriever_tool(get_retriever(session_id))` 创建 LangChain Tool
  - `name="retrieve_documents"`
  - `description="在用户已上传的文档中搜索相关内容。当用户询问的问题涉及文档内容、需要查找特定信息、或问题中提到'文档'/'资料'/'上传'等关键词时，应使用此工具。当问题是通用知识（如数学计算、常识问答、编程问题）时不要使用。"`
- **Verification:** 上传一个测试 PDF，检查 Chroma 持久化目录有 `session_xxx` 子目录，retriever 返回相关 chunk 及相似度分数

### Step 4: Agent 决策循环（手写）
**Files:** `backend/agent.py`

**System Prompt (中文):**
```
你是一个个人知识库助手。你可以使用以下工具来检索用户上传的文档：

{tools}

使用规则：
1. 用户询问文档内容、文件信息、或需要查找特定信息时 → 调用 retrieve_documents 工具
2. 用户问通用知识（数学、常识、编程、问候等）→ 直接回答，不使用工具
3. 检索到相关内容后，基于检索结果回答，并引用原文片段
4. 如果检索不到相关内容，诚实告知"文档中未找到相关信息"

当前可检索的文档来自用户的上传。请用中文回答。
```

**决策循环伪代码:**
```python
async def run_agent(question: str, session_id: str) -> AsyncGenerator[str, None]:
    llm = get_llm()
    tools = [create_rag_tool(session_id)]
    llm_with_tools = llm.bind_tools(tools)
    messages = [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=question)]
    
    # Round 1: LLM decides tool or not (must use invoke for complete tool_call response)
    try:
        response = await llm_with_tools.ainvoke(messages)
    except Exception as e:
        yield "data: " + json.dumps({"type": "error", "content": f"LLM 调用失败: {e}"}) + "\n\n"
        return
    messages.append(response)
    
    # Signal thinking state to frontend
    yield "data: " + json.dumps({"type": "thinking", "content": "正在思考..."}) + "\n\n"
    
    if response.tool_calls:
        tool_call = response.tool_calls[0]
        log_decision(session_id, question, tool_call)  # 记录决策，满足 AC2
        yield "data: " + json.dumps({"type": "tool_call", "content": "正在搜索文档..."}) + "\n\n"
        
        try:
            tool_result = await tools[0].ainvoke(tool_call['args'])
        except Exception as e:
            yield "data: " + json.dumps({"type": "error", "content": f"检索失败: {e}"}) + "\n\n"
            return
        
        messages.append(ToolMessage(content=str(tool_result), tool_call_id=tool_call['id']))
        
        # Round 2: synthesize with retrieved docs — use astream for token-by-token streaming
        # Unbind tools for synthesis round to prevent hallucinated tool calls
        synthesis_llm = llm  # no tools bound
        async for chunk in synthesis_llm.astream(messages):
            if chunk.content:
                yield "data: " + json.dumps({"type": "answer", "content": chunk.content}) + "\n\n"
        yield "data: " + json.dumps({"type": "done", "content": ""}) + "\n\n"
    else:
        # Direct answer: stream token-by-token
        async for chunk in llm.astream(messages):
            if chunk.content:
                yield "data: " + json.dumps({"type": "answer", "content": chunk.content}) + "\n\n"
        yield "data: " + json.dumps({"type": "done", "content": ""}) + "\n\n"
```

关键点：
- Round 1 使用 `ainvoke`（需完整响应才能提取 tool_call），Round 2 使用 `astream`（逐 token 流式输出）
- Round 2 解除 tools 绑定（`llm` 而非 `llm_with_tools`），防止 LLM 在合成阶段幻觉出多余 tool call
- 手写最多 2 轮（决策 + 合成），单工具场景无需多轮
- 每轮 tool call 决策通过 `log_decision()` 记录（满足 AC2 可验证性）
- tool 调用失败时 yield error 事件
- SSE 事件格式：`{"type": "tool_call"|"answer"|"done"|"error", "content": "..."}`

**`ask_agent(question, session_id)`**: 异步生成器，逐 token yield SSE JSON 事件。`agent.py` 中也包含 `log_decision()` 辅助函数，将每次 tool call 决策追加写入 `backend/logs/decisions_{session_id}.jsonl`（JSON Lines 格式，每行：`{"timestamp": "...", "session_id": "...", "question": "...", "tool_name": "...", "args": {...}}`），用于 AC2 验证。

- **Verification:** 用测试问题验证 Agent 正确决策（4 个文档问题调用 tool、4 个通用问题不调用），日志文件记录决策过程

### Step 5: FastAPI 路由 + SSE 流式
**Files:** `backend/main.py`, `backend/models.py`

**models.py:**
```python
class ChatRequest(BaseModel):
    question: str
    session_id: str = "default"

class UploadResponse(BaseModel):
    filename: str
    chunks_count: int
    session_id: str

class ErrorResponse(BaseModel):
    error: str
    detail: str | None = None
```

**main.py:**
- `POST /upload`: 
  - 接收 `UploadFile` → 验证扩展名（仅 .pdf/.txt） → 保存到 `uploads/{session_id}/` → `load_document()` → `split_documents()` → `create_vectorstore(docs, session_id)` → 返回 `UploadResponse`
  - 错误处理：不支持的文件格式 → 400、文件过大(>50MB) → 413、PDF 解析失败 → 422
- **`StreamingResponse`** from `starlette.responses`（FastAPI 自动兼容）
- `POST /chat`（SSE 流式）:
  - 接收 `ChatRequest` → `StreamingResponse(run_agent(question, session_id), media_type="text/event-stream")`
  - 每个 chunk 以 `data: {json}\n\n` 格式输出，包含 `{"type": "thinking"|"tool_call"|"answer"|"done", "content": "..."}`
  - 错误处理：LLM API 失败 → SSE error event、空问题 → 400、session 无文档 + 需要检索 → 提示先上传
- CORS 配置允许 `http://localhost:5173`
- **Verification:** 用 curl 测试 `/upload` 和 `/chat`（SSE 事件流），确认 error case 返回正确错误码

### Step 6: React 前端
**Files:** `frontend/src/App.jsx`, `frontend/src/api.js`, `frontend/src/components/ChatWindow.jsx`, `frontend/src/components/Message.jsx`, `frontend/src/components/FileUpload.jsx`

- `api.js`:
  - `uploadFile(file, sessionId)` → POST `/upload` (FormData)
  - `chatStream(question, sessionId, onChunk, onDone, onError)` → 使用 `fetch` + `ReadableStream` 读取 POST `/chat` 的 SSE 流（注意：不能用 `EventSource`，因为 `EventSource` 不支持 POST 请求）。解析每行 `data: {...}`，按 `type` 字段分发回调
- `FileUpload.jsx`:
  - 拖拽/点击上传区域，仅接受 `.pdf,.txt`
  - 上传中显示进度条，完成后显示绿色勾 + chunks_count
  - 错误显示红色提示
- `ChatWindow.jsx`:
  - 消息列表（用户消息右对齐、AI 消息左对齐）
  - 输入框 + 发送按钮（回车发送）
  - AI 消息流式逐字显示
  - **状态指示器**: "正在搜索文档..."（tool_call 时）/ "正在生成回答..."（answer 时）
- `Message.jsx`:
  - 用户消息：气泡样式、右对齐
  - AI 消息：气泡样式、左对齐，含来源引用块（可折叠），区分 tool_call 状态文本和最终回答
- `App.jsx`:
  - 组合 `FileUpload` + `ChatWindow`
  - 管理状态：`sessionId`（使用 `crypto.randomUUID()` 生成，每次页面加载创建新 session，避免多标签页竞争同一 collection）、`messages[]`
- **Verification:** 完整走通：上传文档 → 提问"这份文档讲了什么？" → 看到 Agent 思考状态 → 流式显示回答 → 来源引用可点击查看

### Step 7: 学习性注释补全
**涉及文件:** `backend/agent.py`, `backend/rag.py`, `backend/config.py`

- `agent.py` — Agent 决策循环注释（每行关键逻辑）：
  - 解释 `bind_tools` 如何让 LLM 输出 tool call JSON
  - 解释 tool call → execute → observe → synthesize 的循环
  - 解释为什么最多 2 轮（单工具场景无需多轮）
- `rag.py` — RAG 数据流注释：
  - Document → Chunk → Embedding → VectorStore → Similarity Search 的全链路
  - 解释为什么 chunk_size=1000, chunk_overlap=200（平衡语义完整性和检索精度）
- `config.py` — 工厂函数模式注释：
  - 解释工厂函数如何实现模型切换的解耦
- **Verification:** 代码审查——每个标注的函数体有至少一个解释性注释

### Step 8: 端到端测试与验证
- 准备 2 个测试文档：1 个中文 PDF（2-5 页，如一篇技术文章）、1 个 TXT（如项目 README 或新闻稿）
- 执行 8 题测试集（AC2），具体题目：
  - **文档类（期望 trigger tool_call）**:
    1. "这篇文档的主要内容是什么？"（概括）
    2. "文档中提到了哪些具体的数据/数字？"（细节检索）
    3. "文档的作者或来源是什么？"（元数据）
    4. "文档中关于 [某个主题] 是怎么说的？"（定向检索）
  - **通用知识类（期望 NO tool_call）**:
    5. "1+1等于几？"（数学）
    6. "什么是 Python？"（常识）
    7. "你好，今天天气怎么样？"（闲聊）
    8. "请写一个 Python 的 Hello World 程序"（编程）
  - 通过标准：文档问题 4/4 触发 tool_call + 通用问题 4/4 不触发 = 8/8；允许 1 题偏差（7/8 即通过）
  - 后端日志记录每次决策，用于验证
- 测试 AC7 LLM 切换：修改 `.env` 切换提供商，重新测试 2-3 个问题
- 测试错误处理：上传 .exe 文件 → 400、空问题 → 400、无文档时问文档问题 → 提示上传
- 检查 AC3 来源引用：每个文档类回答至少 1 个引用，原文字段可在上传文档中找到

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| LangChain 版本 API 变化 | Medium | Medium | 锁定 `langchain>=0.3,<0.4`，`requirements.txt` 中指定版本范围 |
| 手写 Agent 循环中 tool call 格式因 LLM 而异 | High | Medium | `bind_tools` 统一处理格式差异；分别测试 OpenAI/Anthropic/Ollama 的 tool call 流程 |
| Chroma 持久化路径问题（Windows） | Low | Low | 使用 `pathlib.Path` 处理路径，`CHROMA_PERSIST_DIR` 可在 `.env` 中覆盖 |
| Ollama 本地模型 tool calling 能力弱 | Medium | Medium | 默认推荐 OpenAI，Ollama 标注为实验性支持；需要 `llama3.1+` 或 `qwen2.5+` |
| PDF 中文解析乱码 | Medium | Medium | 优先 `pdfplumber`（中文支持更好），`PyPDFLoader` 作为备选 |
| SSE 连接中断/超时 | Low | Low | 前端实现自动重连；后端设置合理的超时时间 |
| 空 collection 时 Agent 仍调用 tool | Low | Medium | tool 函数内检查 collection 是否存在，返回"暂无文档"提示 |

## ADR: Agent 决策循环实现方式

### Decision
手写 Agent 决策循环（while loop with explicit tool dispatch），而非使用 LangChain 的 `create_tool_calling_agent` + `AgentExecutor`。

### Drivers
- Principle 1 (学习优先): 要求代码透明，能看到 Agent 的每一步决策
- 单工具场景: 决策逻辑简单（调用 or 不调用），AgentExecutor 的复杂功能用不上
- 多模型支持: 需要理解不同 LLM 的 tool calling 机制

### Alternatives Considered
- **Option B:** `create_tool_calling_agent` + `AgentExecutor` — 被拒绝：封装了决策循环，违背 Principle 1
- **Option C:** LangGraph Agent — 被拒绝：对单工具场景过度设计

### Why Chosen
手写循环约 30-40 行，完全透明地展示了 tool call → execute → observe → synthesize 的 Agent 核心循环。利用 `llm.bind_tools()` 消除跨提供商 tool call 格式差异。教学价值远超 API 调用。

### Consequences
- **正面**: 代码学习者能看到 Agent 决策的每一步；调试时不需要阅读 LangChain 源码；为以后升级到 LangGraph 打下概念基础
- **负面**: 失去了学习 `create_tool_calling_agent` API 的机会；手写代码约多 20 行；需自行处理 tool call 的边缘情况
- **缓解**: 在注释中提及如果使用 `create_tool_calling_agent` 可替代手写循环部分，供读者对比

### Follow-ups
- 如果未来添加第 2 个工具，需要在 while 循环中增加多工具调度的逻辑；届时可重新评估是否迁移到 LangGraph
- 如果 LLM tool calling 格式出现重大变化，只需修改 `agent.py` 中的 dispatch 逻辑

## Verification Steps
1. 启动后端：`cd backend && uvicorn main:app --reload`
2. 启动前端：`cd frontend && npm run dev`
3. 通过 Web UI 上传一个 PDF 文件，确认返回上传成功 + chunks_count > 0
4. 提问"这份文档的主要内容是什么？"→ 显示"正在搜索文档..." → 流式显示回答 + 来源引用
5. 提问"1+1等于几？"→ 不显示搜索状态，直接流式回答
6. 执行全部 8 题测试集，检查后端日志确认 Agent 决策正确率 ≥ 7/8
7. 修改 `.env` 切换 `LLM_PROVIDER=anthropic`（或 `ollama`），重启后端，重复测试 2-3 问题
8. 上传 `.exe` 文件 → 确认返回 400 错误
9. 检查 `agent.py` 和 `rag.py` 关键路径是否有学习性注释

## Project Structure
```
agent-rag-kb/
├── backend/
│   ├── main.py              # FastAPI 入口 + CORS + /upload + /chat(SSE)
│   ├── config.py             # Settings + get_llm() + get_embeddings() 工厂函数
│   ├── agent.py              # 手写 Agent 决策循环 (bind_tools → while loop)
│   ├── rag.py                # RAG 管道 (load→split→embed→store→retrieve→tool)
│   ├── models.py             # Pydantic request/response/error 模型
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.jsx           # 根组件：组合 FileUpload + ChatWindow，管理 sessionId + messages
│   │   ├── App.css
│   │   ├── main.jsx
│   │   ├── components/
│   │   │   ├── ChatWindow.jsx   # 对话列表 + 输入框 + 流式显示 + 状态指示器
│   │   │   ├── Message.jsx      # 单条消息（用户/AI + 来源引用折叠）
│   │   │   └── FileUpload.jsx   # 拖拽上传 + 进度 + 状态
│   │   └── api.js            # uploadFile() + chatStream() (SSE EventSource)
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
├── .env.example
└── README.md
```

## Changelog

### Round 3 (Critic accept-with-reservations — 6 minor fixes)
- **FIX**: SSE yield 格式统一添加 `"data: "` 前缀 + `"\n\n"` 结尾，与 Step 5/Step 6 的 `data: {json}\n\n` 格式一致
- **FIX**: Round 1 `ainvoke` 添加 try/except 错误处理（LLM API 失败时 yield error event）
- **FIX**: `tools[0].invoke` → `tools[0].ainvoke`（避免同步调用阻塞 asyncio event loop）
- **FIX**: 移除 dead code `full_response` 变量
- **FIX**: 添加 `thinking` 事件到伪代码（Round 1 前 yield "正在思考..."），与 Step 5 事件类型一致
- **FIX**: 明确 `log_decision()` 写入路径和格式：`backend/logs/decisions_{session_id}.jsonl` (JSON Lines)
- **ADDED**: `StreamingResponse` import 来源标注（`starlette.responses`）

### Round 2 (Critic feedback)
- **MAJOR FIX**: Step 4 伪代码改用 `ainvoke` (Round 1, 提取 tool_call) + `astream` (Round 2, 逐 token 流式)，解决 SSE 实际不流式的问题
- **MAJOR FIX**: Round 2 解除 tools 绑定（`llm` 替代 `llm_with_tools`），防止合成阶段幻觉多余 tool call（Architect 建议）
- **Minor FIX**: `api.js` 明确使用 `fetch` + `ReadableStream`（不能用 `EventSource`，不支持 POST）
- **Minor FIX**: Step 4 新增 tool 调用异常处理（yield error event）
- **Minor FIX**: Step 8 列出 8 道具体测试题（4 文档类 + 4 通用知识），消除测试集模糊性
- **Minor FIX**: `App.jsx` 明确 `sessionId` 使用 `crypto.randomUUID()` 生成，避免多标签页 collection 冲突

### Round 1 (Architect + Critic feedback)
- **CRITICAL FIX**: Option A 改为 Hybrid（LangChain RAG + 手写 Agent 循环），消除 Principle 1 与 Agent 实现方式的矛盾。原 Option A 降级为 Option B 并标注 rejected
- **MAJOR FIX**: Step 5 新增 SSE 流式响应（`StreamingResponse` + `text/event-stream`），匹配 spec 中的 SSE 需求
- **MAJOR FIX**: `get_retriever(session_id)` / `create_vectorstore(docs, session_id)` / `create_rag_tool(session_id)` 全链路添加 session_id 参数，修复 collection 隔离中断
- **MAJOR FIX**: AC2 量化（8 题测试集，通过阈值 ≥7/8）；AC3 增加可验证性条件（来源引用可在文档中找到）
- **Minor FIX**: Principle 5 措辞修正（从"只需改配置"改为"模型切换只需改配置；工具/向量库通过插件式模块扩展"）
- **Minor FIX**: 新增 3 条风险（手写循环格式差异、SSE 断连、空 collection 调用 tool）
- **ADDED**: ADR 章节（Agent 决策循环实现方式）
- **ADDED**: Step 4 提供具体 System Prompt 中文文本和决策循环伪代码
- **ADDED**: Step 6 前端增加状态指示器（"正在搜索文档..." / "正在生成回答..."）
