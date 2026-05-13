"""
FastAPI 入口 —— REST API 路由 + SSE 流式响应

端点:
- GET  /health      — 健康检查
- POST /upload      — 上传文档（PDF/TXT），索引到 Chroma
- POST /chat        — 发送问题，Agent 流式回答（SSE）

CORS: 允许前端开发服务器 http://localhost:5173 跨域访问
"""
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import StreamingResponse
from .models import ChatRequest, UploadResponse
from .rag import load_document, split_documents, create_vectorstore
from .agent import ask_agent

app = FastAPI(
    title="Agent + RAG 个人知识库助手",
    description="上传文档 → Agent 智能检索 → 流式回答",
    version="1.0.0",
)

# CORS: 允许前端 Vite 开发服务器跨域请求
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 上传文件暂存目录
UPLOAD_DIR = Path(__file__).resolve().parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB
ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md"}


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/upload", response_model=UploadResponse)
async def upload_file(file: UploadFile = File(...), session_id: str = Form("default")):
    """
    上传文档 → 加载 → 分块 → 索引到 Chroma。

    支持 PDF 和 TXT，按 session_id 隔离到独立的 Chroma collection。
    首次上传创建 collection，再次上传追加文档。
    """
    # 1. 验证文件扩展名
    ext = Path(file.filename).suffix.lower() if file.filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件格式: {ext or '未知'}。仅支持 .pdf、.txt 和 .md",
        )

    # 2. 检查文件大小（先尝试从 Content-Length 获取，避免不必要的大文件读取）
    if file.size and file.size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"文件过大 ({file.size / 1024 / 1024:.1f} MB)，最大 50 MB",
        )

    content = await file.read()

    # 3. 保存到临时目录（按 session 隔离）
    # 安全：清洗 session_id 和 filename，防止路径穿越攻击
    # Path().name 只取文件名部分，丢弃任何目录路径
    safe_session = "".join(c for c in session_id if c.isalnum() or c in "_-")[:32] or "default"
    safe_filename = Path(file.filename).name
    session_dir = UPLOAD_DIR / safe_session
    session_dir.mkdir(exist_ok=True)
    file_path = session_dir / safe_filename

    with open(file_path, "wb") as f:
        f.write(content)

    # 4. RAG 管道：加载 → 分块 → 索引
    try:
        docs = load_document(str(file_path))
        chunks = split_documents(docs)
    except Exception as e:
        raise HTTPException(
            status_code=422,
            detail=f"文档解析失败: {e}",
        )

    try:
        create_vectorstore(chunks, session_id)
    except Exception as e:
        raise HTTPException(
            status_code=422,
            detail=f"向量存储创建失败: {e}",
        )

    return UploadResponse(
        filename=file.filename,
        chunks_count=len(chunks),
        session_id=session_id,
    )


@app.post("/chat")
async def chat(request: ChatRequest):
    """
    Agent 对话端点 —— SSE 流式响应。

    前端用 fetch + ReadableStream 读取 SSE 事件流，
    每个事件格式: data: {"type": "...", "content": "..."}\n\n

    事件类型:
    - thinking: Agent 开始思考
    - tool_call: Agent 决定检索文档
    - answer: 逐 token 答案文本
    - done: 回答完成
    - error: 出错
    """
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="问题不能为空")

    return StreamingResponse(
        ask_agent(request.question, request.session_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # 禁用 nginx 缓冲
        },
    )
