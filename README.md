# 🤖 Your Second Brain (Fewer Hallucinations Than the First)

> Upload documents. Ask questions. Watch a tiny AI librarian scramble through your files and emerge with answers.
> It's ChatGPT, but it actually read the stuff you gave it.

---

## 🧠 What Problem Did We Invent?

You know that folder? The one with 47 PDFs you collected with great ambition and zero follow-through? The one where you're pretty sure the answer to "what was our Q2 strategy again?" is buried somewhere on page 83 of a document whose filename you can't remember?

This project gives every document in that folder a personal trainer. It reads. It remembers. It doesn't complain about overtime.

- Drag a PDF → it chunkifies and indexes it
- Type a question → it searches, then answers with receipts
- Ask something generic → it answers from its own (admittedly vast) knowledge, skipping the search

**The Agent loop is 40 lines of Python. No black-box frameworks. You can read the whole thing before your coffee gets cold.**

---

## 🏗️ Architecture (One Diagram, Zero Fluff)

```
Browser (React) ←→ FastAPI ←→ DeepSeek / Claude / GPT
                       ↓
             Chroma Vector DB ← HuggingFace Embeddings ← Your Documents
```

Translation: **Frontend looks pretty. Backend does work. LLM does thinking. Chroma does remembering.**

---

## 🚀 Go From Zero to "Whoa It Works" in 5 Minutes

### 1. Install Stuff

```bash
cd agent-rag-kb

# Backend
cd backend && pip install -r requirements.txt

# Frontend
cd ../frontend && npm install
```

### 2. Configure (the one step you can't skip)

```bash
cd backend && cp .env.example .env
```

Open `.env` and fill in what matters:

```env
LLM_PROVIDER=deepseek          # deepseek | openai | anthropic | ollama
DEEPSEEK_API_KEY=sk-xxxxxxxx   # your key here
EMBEDDING_PROVIDER=huggingface # free, local, no API bills
HF_ENDPOINT=https://hf-mirror.com  # use a mirror if you're behind the Great Firewall
```

### 3. Launch

```bash
# Terminal 1 — Backend
cd backend && uvicorn backend.main:app --reload --port 8000

# Terminal 2 — Frontend
cd frontend && npm run dev
```

Open http://localhost:5173, drag in a document, and ask it something. Try "summarize this" — it's the "Hello World" of RAG.

---

## 🎮 How to Actually Use This

| Step | Action | What Happens |
|------|--------|--------------|
| 1 | Drag a PDF/TXT/MD into the left panel | File hits the backend, gets chunked into digestible pieces |
| 2 | Wait for "Upload successful" | Each chunk is vectorized and stored in Chroma |
| 3 | Ask a question in the chat | Agent decides: search docs, or just answer? |
| 4 | Watch tokens stream in | Answers arrive word-by-word with source citations |
| 5 | Ask another question | Different session? Different Chroma collection. No cross-contamination. |

**It reads your docs so you don't have to. Finally, technology that enables laziness instead of fighting it.**

---

## 🔧 Tech Stack & Why These Choices Won't Embarrass You Later

| Piece | Choice | The Pitch |
|-------|--------|-----------|
| **LLM** | DeepSeek (swappable) | Cheap, good at Chinese, one config line to switch to GPT-4o / Claude / Ollama |
| **Embedding** | BGE-small-zh (local HF) | Free. 512 dimensions. Works offline. Your CFO will smile. |
| **Vector DB** | Chroma | Lightweight, persistent, session-isolated. Won't wake up and delete your indexes. |
| **Agent Loop** | Hand-rolled, 40 lines | Read the source. Understand every decision. No `AgentExecutor` abstractions that hide 12 layers of indirection. |
| **Backend** | FastAPI + SSE streaming | Async Python. Tokens stream as they're generated. No waiting for the whole answer. |
| **Frontend** | React + Vite | HMR keeps you in flow. No Webpack config trauma. |

### Model Swapping (one line, .env, done)

```env
LLM_PROVIDER=openai     # → gpt-4o
LLM_PROVIDER=deepseek   # → deepseek-chat
LLM_PROVIDER=anthropic  # → claude-sonnet
LLM_PROVIDER=ollama     # → local qwen (no API key, no internet, no excuses)
```

---

## 📂 Project Layout (For When You Need to Find Something)

```
agent-rag-kb/
├── backend/
│   ├── main.py       # FastAPI entry: /upload + /chat (SSE streaming)
│   ├── config.py     # LLM & Embedding factories (swap models here)
│   ├── agent.py      # The 40-line Agent loop (read this first)
│   ├── rag.py        # RAG pipeline: load → chunk → embed → store → retrieve
│   └── models.py     # Pydantic schemas (type safety without TypeScript)
├── frontend/
│   └── src/
│       ├── App.jsx           # Root layout + session management
│       ├── api.js            # SSE stream parser (fetch + ReadableStream)
│       └── components/
│           ├── FileUpload.jsx  # Drag-and-drop upload zone
│           ├── ChatWindow.jsx  # Chat interface with streaming
│           └── Message.jsx     # Message bubbles with Markdown + source links
│   ├── .env.example          # 复制成 .env，填上 key
│   └── requirements.txt
```

---

## 🐛 The "It's Not Working" Section

**Q: Upload says "unsupported file format"?**
A: PDF, TXT, MD only. Your `.docx` isn't welcome here — export to PDF first. Blame Microsoft, not us.

**Q: First query takes forever?**
A: HuggingFace is downloading a ~400MB embedding model. One-time cost. If you're in China, set `HF_ENDPOINT=https://hf-mirror.com` or prepare a snack.

**Q: Agent answers have nothing to do with my document?**
A: The Agent decides whether to search or not based on your question. If you asked about something not in the docs, it'll use general knowledge. That's a feature, not a bug. Try asking "what does my document say about X?"

**Q: Can I run everything locally?**
A: Yes. Point `LLM_PROVIDER=ollama` at a local model, keep `EMBEDDING_PROVIDER=huggingface`, and you're fully offline. No cloud, no API keys, no one watching.

**Q: Why not LangGraph / CrewAI / [insert hype framework]?**
A: Because understanding your own Agent loop is more valuable than importing someone else's. This is a learning project. The 40-line agent in `agent.py` is the curriculum. Read it, break it, rebuild it.

---

## 📜 License

MIT — take it, fork it, ship it. If it makes you money, buy me a coffee. If it breaks, you get to keep both pieces.

---

*"AI doesn't read your documents. But yours can."*
