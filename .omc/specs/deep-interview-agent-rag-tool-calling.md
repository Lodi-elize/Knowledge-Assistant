# Deep Interview Spec: Agent + RAG 个人知识库助手

## Metadata
- Interview ID: d7b8f1a2-3c4e-5d6f-7a8b-9c0d1e2f3a4b
- Rounds: 8
- Final Ambiguity Score: 14%
- Type: greenfield
- Generated: 2026-05-13
- Threshold: 0.2
- Initial Context Summarized: no
- Status: PASSED

## Clarity Breakdown
| Dimension | Score | Weight | Weighted |
|-----------|-------|--------|----------|
| Goal Clarity | 0.90 | 40% | 0.36 |
| Constraint Clarity | 0.85 | 30% | 0.255 |
| Success Criteria | 0.80 | 30% | 0.24 |
| **Total Clarity** | | | **0.855** |
| **Ambiguity** | | | **14%** |

## Goal
构建一个**个人知识库助手**，用户通过 Web 界面上传文档，Agent 根据问题自动判断是否需要用 RAG 检索文档内容来回答。核心技术栈：**LangChain Agent + RAG + 工具调用**，支持多 LLM 可切换（OpenAI / Anthropic / Ollama 本地模型）。

## Constraints
- 前后端分离：**FastAPI** (后端) + **React + Vite** (前端)
- LLM 通过 LangChain ChatModel 抽象层，支持 OpenAI GPT-4o / Anthropic Claude / Ollama 本地模型切换
- Agent 只配备 1 个工具：**文档检索 (RAG)**，Agent 自主决定是否调用
- 向量库默认使用 **Chroma**（本地嵌入式）
- 文档格式优先支持 **PDF 和 TXT**
- Embedding 模型默认 `text-embedding-3-small`（OpenAI），可配置切换
- Python 全栈学习项目，代码需具备可读性和可扩展性

## Non-Goals
- 不实现用户认证/多用户系统
- 不实现数据库持久化（除向量库外）
- 不部署到生产环境
- 不实现网络搜索工具（单工具 Agent）
- 不实现文档对比/总结的独立工具（可用基础 RAG 自然实现）

## Acceptance Criteria
- [ ] 用户可以通过 Web UI 上传 PDF/TXT 文档到知识库
- [ ] 用户输入问题后，Agent 能正确判断是否需要检索文档（工具决策正确性）
- [ ] 当问题涉及文档内容时，Agent 检索并基于检索结果准确回答（RAG 问答准确性）
- [ ] 当问题是通用知识时，Agent 直接回答而不无意义地检索文档
- [ ] React 前端能完成：文件上传、发送消息、显示对话历史
- [ ] FastAPI 后端提供完整的 `/upload` 和 `/chat` API
- [ ] 可以通过配置文件切换 LLM 提供商（OpenAI ↔ Anthropic ↔ Ollama）
- [ ] 代码结构模块化：Agent 逻辑、RAG 管道、API 路由、前端组件各自独立
- [ ] 代码中关键位置（Agent 决策逻辑、检索流程、工具定义）有学习性注释

## Assumptions Exposed & Resolved
| Assumption | Challenge | Resolution |
|------------|-----------|------------|
| "Agent + RAG 是什么样的项目？" | 提供了 4 种场景选项 | 确定为个人知识库助手 |
| "应该用一体化方案（Streamlit）" | Contrarian 模式质疑 | 坚持前后端分离（FastAPI + React） |
| "后端只能用 FastAPI" | 用户主动询问替代方案 | 对比 4 个框架后选择 FastAPI |
| "Agent 需要多个工具" | Simplifier 模式质疑 | 确认只需 1 个工具：文档检索 |
| "只绑定一个 LLM" | 多模型选项 | 选择 LangChain 抽象层，支持多模型切换 |

## Technical Context

### 推荐技术栈
| 层 | 技术 | 用途 |
|----|------|------|
| 前端 | React + Vite | 聊天界面、文件上传 |
| 后端 | FastAPI | REST API、文件上传、SSE 流式响应 |
| Agent 框架 | LangChain | Agent 定义、工具管理、Chain 编排 |
| RAG | LangChain + Chroma | 文档加载、分块、Embedding、检索 |
| LLM | OpenAI / Anthropic / Ollama | 通过 `ChatOpenAI` / `ChatAnthropic` / `ChatOllama` 切换 |
| 向量库 | Chroma | 本地嵌入式向量存储 |
| Embedding | OpenAI `text-embedding-3-small` | 文档和查询向量化 |

### 项目结构建议
```
project/
├── backend/
│   ├── main.py              # FastAPI 入口
│   ├── agent.py              # Agent 定义 + 工具
│   ├── rag.py                # RAG 管道（加载、分块、检索）
│   ├── models.py             # Pydantic 模型
│   └── config.py             # LLM/Embedding 配置切换
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── components/
│   │   │   ├── ChatWindow.jsx
│   │   │   ├── FileUpload.jsx
│   │   │   └── Message.jsx
│   │   └── api.js            # 后端 API 调用
│   └── vite.config.js
└── requirements.txt
```

## Ontology (Key Entities)

| Entity | Type | Fields | Relationships |
|--------|------|--------|---------------|
| User | core domain | [documents] | uploads Document, asks Question |
| Document | core domain | [content, type, metadata] | belongs to User, stored in KnowledgeBase |
| KnowledgeBase | core domain | [documents, embeddings] | contains Documents, retrieved by Agent |
| Agent | core domain | [tools, llm] | processes Question, selects Tool, retrieves from KnowledgeBase |
| Tool | supporting | [name, description, function] | used by Agent (specifically: DocumentRetrieval) |
| WebUI | supporting | [chat_interface, file_upload] | serves User |
| ApiService | supporting | [endpoints: /upload, /chat] | connects WebUI to Agent |

## Ontology Convergence

| Round | Entity Count | New | Changed | Stable | Stability Ratio |
|-------|-------------|-----|---------|--------|----------------|
| 1 | 4 | 4 | - | - | N/A |
| 2 | 6 | 2 (WebUI, ApiService) | 0 | 4 | 67% |
| 3 | 7 | 1 (Tool) | 0 | 6 | 86% |
| 4 | 7 | 0 | 0 | 7 | 100% |
| 5 | 7 | 0 | 0 | 7 | 100% |
| 6 | 7 | 0 | 0 | 7 | 100% |
| 7 | 7 | 0 | 0 | 7 | 100% |
| 8 | 7 | 0 | 0 | 7 | 100% |

领域模型从 Round 4 开始完全收敛，7 个实体连续 5 轮无变化。

## Interview Transcript
<details>
<summary>Full Q&A (8 rounds)</summary>

### Round 1
**Q:** 当你说 "Agent + RAG（工具调用）" 时，你心中想的具体场景是什么？
**A:** 个人知识库助手
**Ambiguity:** 77% (Goal: 0.35, Constraints: 0.15, Criteria: 0.15)

### Round 2
**Q:** 这个知识库助手以什么形式运行和交互？
**A:** Web 界面 + API 服务
**Ambiguity:** 66% (Goal: 0.45, Constraints: 0.35, Criteria: 0.20)

### Round 3
**Q:** 对你来说，"学会了、做完了" 的标准是什么？
**A:** 工具决策正确性, RAG 问答准确性, UI + API 功能完整, 理解和可解释性
**Ambiguity:** 48% (Goal: 0.55, Constraints: 0.40, Criteria: 0.60)

### Round 4
**Q:** [Contrarian] 你坚持前后端分离吗？还是用 Streamlit 一体化方案更符合学习初衷？
**A:** 坚持前后端分离，希望看到技术选型方案
**Ambiguity:** 42% (Goal: 0.60, Constraints: 0.50, Criteria: 0.65)

### Round 5
**Q:** Python 后端框架你倾向哪个？
**A:** FastAPI
**Ambiguity:** 35% (Goal: 0.65, Constraints: 0.60, Criteria: 0.70)

### Round 6
**Q:** [Simplifier] Agent 需要配备哪些工具？
**A:** 只选文档检索 (RAG)
**Ambiguity:** 28% (Goal: 0.80, Constraints: 0.65, Criteria: 0.70)

### Round 7
**Q:** Agent 使用哪个 LLM？
**A:** 多模型可切换
**Ambiguity:** 21% (Goal: 0.85, Constraints: 0.75, Criteria: 0.75)

### Round 8
**Q:** 前端用什么框架？
**A:** React + Vite
**Ambiguity:** 14% (Goal: 0.90, Constraints: 0.85, Criteria: 0.80)

</details>
