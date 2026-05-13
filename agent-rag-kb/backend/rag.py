"""
RAG 管道：文档加载 → 分块 → Embedding → 向量存储 → 检索

数据流全景（每一步都在这一个文件中，便于追踪）:
  Document (PDF/TXT/MD)
    ↓ load_document()
  LangChain Document[] (page-by-page)
    ↓ split_documents()
  Document Chunk[] (~1000 chars each, 200 overlap)
    ↓ create_vectorstore()
  Chroma Collection (session 隔离，持久化到磁盘)
    ↓ get_retriever()
  LangChain Retriever (k=4, similarity search)
    ↓ create_rag_tool()
  LangChain Tool → Agent 可调用

为什么选这些参数:
- chunk_size=1000: 中文约 500 字，足够承载一个完整段落
- chunk_overlap=200: 防止关键信息刚好落在 chunk 边界被切断
- k=4: 返回 4 个最相关 chunk，太多会稀释答案，太少可能漏信息
"""
from pathlib import Path

# 必须在 langchain_community import 之前加载 config，
# 因为 chromadb → huggingface_hub 在 import 时就会读取 HF_ENDPOINT
from .config import settings, get_embeddings

from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_core.tools import tool


def load_document(file_path: str):
    """
    根据文件扩展名选择合适的 Document Loader。

    支持格式:
    - .pdf → PyPDFLoader
    - .txt → TextLoader（纯文本，自动检测编码）
    - .md  → TextLoader（Markdown 即纯文本）

    返回 LangChain Document 列表（PDF 每页一个 Document）。
    """
    ext = Path(file_path).suffix.lower()

    if ext == ".pdf":
        loader = PyPDFLoader(file_path)
    elif ext in (".txt", ".md"):
        loader = TextLoader(file_path, autodetect_encoding=True)
    else:
        raise ValueError(f"不支持的文件格式: {ext}，仅支持 .pdf、.txt 和 .md")

    return loader.load()


def split_documents(docs):
    """
    将长文档切分为适合检索的 Chunk。

    RecursiveCharacterTextSplitter 的递归策略:
    - 先按段落(\n\n)切 → 太长的再按句子(\n)切 → 还长的按空格切
    - 这比固定长度切分更能保持语义完整性

    chunk_overlap=200 的用意:
    - 假设一句话被切在 chunk N 的末尾，chunk N+1 的 overlap 区域会包含它
    - embedding 搜索时两个 chunk 都能匹配到
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1500,
        chunk_overlap=300,
        separators=["\n\n", "\n", "。", "，", " ", ""],  # 中文友好
    )
    return splitter.split_documents(docs)


def _collection_name(session_id: str) -> str:
    """
    将 session_id 转换为 Chroma collection 名称。

    Chroma collection 名只能包含字母、数字、下划线、连字符，
    长度限制 3-63 字符。UUID 中的连字符是安全的。
    """
    # 清洗 session_id 中可能的不安全字符，只保留安全字符
    safe = "".join(c for c in session_id if c.isalnum() or c in "_-")
    return f"session_{safe}"[:63]


def create_vectorstore(docs, session_id: str):
    """
    从文档 Chunk 列表创建 Chroma 向量库，按 session 隔离。

    每个 session 一个独立的 Chroma Collection:
    - 不同用户/浏览器标签页的文档互不干扰
    - Collection 命名规则: session_{session_id}
    - 持久化路径: CHROMA_PERSIST_DIR（.env 可配置）

    首次上传时会创建新 collection，再次上传会追加文档。
    """
    embeddings = get_embeddings()
    collection = _collection_name(session_id)
    persist_dir = settings.CHROMA_PERSIST_DIR

    vectorstore = Chroma.from_documents(
        documents=docs,
        embedding=embeddings,
        collection_name=collection,
        persist_directory=persist_dir,
    )
    return vectorstore


def get_retriever(session_id: str):
    """
    获取指定 session 的 Retriever。

    从 Chroma 持久化目录加载对应 collection，
    返回 k=4 的 similarity search retriever。

    如果 session 没有任何文档（collection 不存在），
    Chroma 会返回空结果，Agent 自然会提示用户先上传。
    """
    embeddings = get_embeddings()
    collection = _collection_name(session_id)
    persist_dir = settings.CHROMA_PERSIST_DIR

    vectorstore = Chroma(
        embedding_function=embeddings,
        collection_name=collection,
        persist_directory=persist_dir,
    )

    return vectorstore.as_retriever(
        search_type="similarity",
        search_kwargs={"k": 6},
    )


def create_rag_tool(session_id: str):
    """
    创建 RAG 检索工具 —— Agent 可以用它来搜索用户上传的文档。

    LangChain 1.3 中 create_retriever_tool 已被移除，
    改为手动构建 Tool：用 @tool 装饰器包装检索函数。

    Tool description 的设计很关键：
    —— Agent 靠 description（不是 name）来决定何时调用工具。
       所以 description 必须明确描述使用场景和禁忌场景，
       让 LLM 能正确判断"该用"还是"不该用"。
    """
    retriever = get_retriever(session_id)

    @tool
    def retrieve_documents(query: str) -> str:
        """在用户已上传的文档中搜索相关内容。
        当用户询问文档里的信息（"文档说了什么"、"总结"、"有哪些"、"什么是"等），
        或提到'文档'、'文章'、'资料'、'文件'时必须调用此工具。
        只有纯粹的通用知识问题（编程语法、数学公式、闲聊）才跳过。
        检索结果是文档中的原文片段，你需要仔细阅读理解后再回答用户。"""
        docs = retriever.invoke(query)
        if not docs:
            return "文档中未找到与问题相关的内容。"
        parts = []
        for i, doc in enumerate(docs, 1):
            source = doc.metadata.get("source", "未知来源")
            parts.append(f"[来源 {i}: {source}]\n{doc.page_content}")
        return "\n\n---\n\n".join(parts)

    return retrieve_documents
