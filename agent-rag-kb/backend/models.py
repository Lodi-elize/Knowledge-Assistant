"""
Pydantic 请求/响应模型 —— FastAPI 的数据契约。

每个模型定义 API 的输入输出结构，FastAPI 自动生成：
- JSON Schema（OpenAPI 文档）
- 请求体校验（类型不匹配自动返回 422）
- 交互式 API 文档（/docs）
"""
from pydantic import BaseModel


class ChatRequest(BaseModel):
    """POST /chat 的请求体"""
    question: str
    session_id: str = "default"


class UploadResponse(BaseModel):
    """POST /upload 的成功响应"""
    filename: str
    chunks_count: int
    session_id: str


class DeleteResponse(BaseModel):
    """DELETE /clear/{session_id} 的成功响应"""
    session_id: str
    deleted_files: int


class ErrorResponse(BaseModel):
    """API 错误响应"""
    error: str
    detail: str | None = None
