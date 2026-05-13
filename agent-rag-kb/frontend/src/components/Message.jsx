// 轻量 Markdown → HTML 转换（无外部依赖）
function renderMarkdown(text) {
  if (!text) return "";
  let html = text
    // 转义 HTML
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    // 粗体 **text**
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    // 行内代码 `code`
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    // ### 标题
    .replace(/^### (.+)$/gm, "<h3>$1</h3>")
    .replace(/^## (.+)$/gm, "<h2>$1</h2>")
    .replace(/^# (.+)$/gm, "<h1>$1</h1>")
    // - 无序列表
    .replace(/^- (.+)$/gm, "<li>$1</li>")
    // 1. 有序列表
    .replace(/^\d+\.\s+(.+)$/gm, "<li>$1</li>")
    // 连续 li 包进 ul
    .replace(/(<li>.*<\/li>)\n(?=<li>)/g, "$1")
    .replace(/((?:<li>.*<\/li>)+)/g, "<ul>$1</ul>")
    // 引用块 >
    .replace(/^&gt; (.+)$/gm, "<blockquote>$1</blockquote>")
    // 双换行 → 段落
    .replace(/\n\n/g, "</p><p>")
    // 单换行 → <br>
    .replace(/\n/g, "<br>");
  return "<p>" + html + "</p>";
}

export default function Message({ message }) {
  const isUser = message.role === "user";
  const isStreaming = message.status && !message.status.startsWith("❌");
  const isError = message.status?.startsWith("❌");
  const hasContent = message.content?.length > 0;

  return (
    <div className={`message ${isUser ? "message-user" : "message-ai"}${isStreaming ? " streaming" : ""}`}>
      <div className="message-avatar">{isUser ? "👤" : "🤖"}</div>
      <div className="message-body">
        <div className="message-role">{isUser ? "你" : "AI 助手"}</div>

        {hasContent ? (
          isUser ? (
            <div className="message-content">{message.content}</div>
          ) : (
            <div
              className="message-content markdown-body"
              dangerouslySetInnerHTML={{ __html: renderMarkdown(message.content) }}
            />
          )
        ) : isStreaming ? (
          <div className="message-content message-typing">
            <span className="dot-pulse" />
          </div>
        ) : null}

        {isStreaming && (
          <div className="message-status streaming-status">
            <span className="pulse-dot" />
            {message.status}
          </div>
        )}
        {isError && (
          <div className="message-status error-status">{message.status}</div>
        )}
      </div>
    </div>
  );
}
