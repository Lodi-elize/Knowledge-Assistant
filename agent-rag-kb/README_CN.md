# 🤖 你的第二个大脑（比第一个靠谱）

> 上传文档。提问。看着一个小型 AI 图书管理员在你的文件里一通翻找，然后举着答案跑回来。
> 它是 ChatGPT，但它真的读过你给它的东西。

---

## 🧠 这玩意儿解决什么问题？

你一定经历过：

- 收藏了一堆 PDF，"等有空再看"——然后那个"有空"从未到来
- 明明读过某份报告，老板问起时大脑一片空白
- 面对 50 页文档，内心唯一的想法是"说重点"

这个项目就是给你的每个文档配了个不要工资的陪读助理。**它真读，你真问，它真答。**

拖进去 → 它啃完 → 你问 → 它翻书回答。全程你只需要动嘴。

---

## 🏗️ 架构（一张图，不啰嗦）

```
浏览器 (React) ←→ FastAPI ←→ DeepSeek / Claude / GPT
                       ↓
             Chroma 向量库 ← HuggingFace 向量化 ← 你的文档
```

翻译成人话：**前端耍帅，后端干活，大模型动脑，Chroma 记性好。**

---

## 🚀 5 分钟从 "这啥" 到 "卧槽能用"

### 1. 装东西

```bash
cd agent-rag-kb

# 后端
cd backend && pip install -r requirements.txt

# 前端
cd ../frontend && npm install
```

### 2. 配环境（唯一不能跳过的步骤）

```bash
cp .env.example .env
```

打开 `.env`，填关键的：

```env
LLM_PROVIDER=deepseek          # deepseek | openai | anthropic | ollama
DEEPSEEK_API_KEY=sk-xxxxxxxx   # 你的 key
EMBEDDING_PROVIDER=huggingface # 免费本地，不花 API 钱
HF_ENDPOINT=https://hf-mirror.com  # 国内镜像，不然下载到天荒地老
```

### 3. 启动

```bash
# 终端 1 — 后端
cd backend && uvicorn backend.main:app --reload --port 8000

# 终端 2 — 前端
cd frontend && npm run dev
```

打开 http://localhost:5173，拖个文档进去，问它"总结一下"。这是 RAG 界的 Hello World。

---

## 🎮 怎么玩

| 步骤 | 操作 | 背后发生了什么 |
|------|------|---------------|
| 1 | 把 PDF/TXT/MD 拖进左边框 | 文件传给后端，被切成易于消化的小块 |
| 2 | 等"上传成功" | 每个小块被向量化，存入 Chroma |
| 3 | 在右边输入问题 | Agent 自主判断：翻文档，还是直接回答？ |
| 4 | 看答案逐字流出来 | 逐 token 输出，带原文出处链接 |
| 5 | 换个问题继续 | 换 session 就换 collection，文档互不串台 |

**它替你读文档，你替它问问题。分工明确，合作愉快。**

---

## 🔧 技术栈 & 为什么这么选（不坑后来人）

| 东西 | 选型 | 理由 |
|------|------|------|
| **大模型** | DeepSeek（可换） | 便宜大碗，中文溜，改一行配置就能切 GPT-4o / Claude / Ollama |
| **向量化** | BGE-small-zh（HuggingFace 本地） | 免费。512 维。离线跑。你的钱包会感谢你。 |
| **向量库** | Chroma | 轻量、持久化、session 隔离。不会半夜起来删你的索引。 |
| **Agent 循环** | 手写 40 行 | 看懂每一行。拒绝黑盒。没有 12 层抽象的 AgentExecutor。 |
| **后端** | FastAPI + SSE 流式 | Python 异步。token 生成一个就吐一个，不用等整段憋完。 |
| **前端** | React + Vite | 热更新丝滑。不用跟 Webpack 配置搏斗。 |

### 换模型？`.env` 里改一行

```env
LLM_PROVIDER=openai     # → gpt-4o
LLM_PROVIDER=deepseek   # → deepseek-chat
LLM_PROVIDER=anthropic  # → claude-sonnet
LLM_PROVIDER=ollama     # → 本地 qwen（不要 key，不要网，不要借口）
```

---

## 📂 项目结构（找东西时用）

```
agent-rag-kb/
├── backend/
│   ├── main.py       # FastAPI 入口：/upload + /chat（SSE 流式）
│   ├── config.py     # LLM & Embedding 工厂函数（换模型在这改）
│   ├── agent.py      # 40 行手写 Agent 循环（先读这个）
│   ├── rag.py        # RAG 管道：加载→分块→向量化→存储→检索
│   └── models.py     # Pydantic 数据模型（Python 版类型安全）
├── frontend/
│   └── src/
│       ├── App.jsx           # 根布局 + session 管理
│       ├── api.js            # SSE 流解析器（fetch + ReadableStream）
│       └── components/
│           ├── FileUpload.jsx  # 拖拽上传区
│           ├── ChatWindow.jsx  # 对话界面 + 流式显示
│           └── Message.jsx     # 消息气泡（Markdown + 来源引用）
└── .env.example      # 复制这个，填 key，别提交到 git
```

---

## 🐛 "怎么跑不起来" 专区

**Q: 上传说"不支持的文件格式"？**
A: 只收 `.pdf` `.txt` `.md`。`.docx` 请先导出成 PDF。要怪怪微软。

**Q: 头一次查询慢得像在下载片儿？**
A: HuggingFace 在下载约 400MB 的 embedding 模型。一次性投入。国内设 `HF_ENDPOINT=https://hf-mirror.com`，不然真得等到天荒地老。

**Q: Agent 的回答跟我的文档八竿子打不着？**
A: Agent 会根据你的问题判断要不要搜文档。问"Python 怎么学"它会用通用知识回答——这是 feature 不是 bug。试试问"我的文档里关于 X 说了什么？"

**Q: 能完全本地跑吗？**
A: 能。`LLM_PROVIDER=ollama` 指向本地模型，`EMBEDDING_PROVIDER=huggingface` 不联网。全程离线，零 API 费用，没人监控你。

**Q: 为什么不用 LangGraph / CrewAI / [某个热榜框架]？**
A: 因为看懂自己写的 40 行 Agent 循环，比 import 别人 4000 行的抽象更有价值。这是学习项目，`agent.py` 就是教材。读懂它，改崩它，重写它。

---

## 📜 许可证

MIT — 拿走，改，部署，商用。赚了钱请我喝杯咖啡。跑崩了你自己留着修。

---

*"AI 不会读你的文档。但这个会。"*
