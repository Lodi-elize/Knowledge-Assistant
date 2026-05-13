/**
 * API 模块 —— 封装后端通信
 *
 * 两个核心函数:
 * - uploadFile(): 上传文档（POST /upload, FormData）
 * - chatStream(): 流式对话（POST /chat, SSE 流式读取）
 *
 * 注意: chatStream 不能用浏览器内置的 EventSource API，
 * 因为 EventSource 只支持 GET 请求。我们使用 fetch + ReadableStream
 * 来手动解析 SSE 事件流。
 */

const API_BASE = "http://localhost:8000";

export async function uploadFile(file, sessionId) {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("session_id", sessionId);

  const response = await fetch(`${API_BASE}/upload`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const err = await response.json();
    throw new Error(err.detail || `上传失败 (${response.status})`);
  }

  return await response.json();
}

export async function chatStream(question, sessionId, callbacks) {
  const { onStart, onThinking, onToolCall, onAnswer, onDone, onError } = callbacks;

  try {
    const response = await fetch(`${API_BASE}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, session_id: sessionId }),
    });

    if (!response.ok) {
      const err = await response.json();
      throw new Error(err.detail || `请求失败 (${response.status})`);
    }

    onStart?.();

    // 解析 SSE 流: fetch + ReadableStream
    // —— EventSource 不支持 POST 请求，所以手动解析
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      // SSE 格式: "data: {json}\n\n"
      // 一个 buffer 可能含多个事件，按 \n\n 分割
      const parts = buffer.split("\n\n");
      buffer = parts.pop(); // 最后一段可能不完整，保留给下一次

      for (const part of parts) {
        if (!part.startsWith("data: ")) continue;
        try {
          const event = JSON.parse(part.slice(6)); // 去掉 "data: " 前缀
          switch (event.type) {
            case "thinking":
              onThinking?.(event.content);
              break;
            case "tool_call":
              onToolCall?.(event.content);
              break;
            case "answer":
              onAnswer?.(event.content);
              break;
            case "done":
              onDone?.();
              break;
            case "error":
              onError?.(event.content);
              break;
          }
        } catch {
          // 忽略解析失败的行
        }
      }
    }
  } catch (err) {
    onError?.(err.message || "网络连接失败");
  }
}
