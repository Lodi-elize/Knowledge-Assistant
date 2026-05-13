import { useState, useRef, useEffect } from "react";
import Message from "./Message";
import { chatStream } from "../api";

export default function ChatWindow({ sessionId }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const chatEndRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // 发送后自动聚焦输入框
  useEffect(() => {
    if (!streaming) inputRef.current?.focus();
  }, [streaming]);

  const handleSend = async () => {
    const question = input.trim();
    if (!question || streaming) return;

    const userMsg = { role: "user", content: question };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setStreaming(true);

    const aiMsg = { role: "ai", content: "", status: "正在思考..." };
    setMessages((prev) => [...prev, aiMsg]);

    await chatStream(question, sessionId, {
      onThinking: (text) => {
        setMessages((prev) =>
          prev.map((m, i) => (i === prev.length - 1 ? { ...m, status: text } : m))
        );
      },
      onToolCall: (text) => {
        setMessages((prev) =>
          prev.map((m, i) => (i === prev.length - 1 ? { ...m, status: text } : m))
        );
      },
      onAnswer: (chunk) => {
        setMessages((prev) =>
          prev.map((m, i) =>
            i === prev.length - 1
              ? { ...m, content: m.content + chunk, status: "" }
              : m
          )
        );
      },
      onDone: () => {
        setMessages((prev) =>
          prev.map((m, i) => (i === prev.length - 1 ? { ...m, status: "" } : m))
        );
        setStreaming(false);
      },
      onError: (err) => {
        setMessages((prev) =>
          prev.map((m, i) =>
            i === prev.length - 1
              ? { ...m, content: m.content || err, status: `❌ ${err}` }
              : m
          )
        );
        setStreaming(false);
      },
    });
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const hasDoc = messages.some((m) => m.status === "正在搜索文档...");

  return (
    <div className="chat-window">
      <div className="messages-container">
        {messages.length === 0 && (
          <div className="empty-state">
            <div className="empty-icon">📄</div>
            <h3>开始对话</h3>
            <p>上传 PDF、TXT 或 MD 文档后，向 AI 提问文档中的内容</p>
            <div className="example-prompts">
              <button
                className="example-btn"
                onClick={() => setInput("请总结这份文档的主要内容")}
              >
                请总结这份文档的主要内容
              </button>
              <button
                className="example-btn"
                onClick={() => setInput("文档中提到了哪些关键概念？")}
              >
                文档中提到了哪些关键概念？
              </button>
            </div>
          </div>
        )}
        {messages.map((msg, i) => (
          <Message key={i} message={msg} />
        ))}
        <div ref={chatEndRef} />
      </div>

      <div className="input-area">
        <textarea
          ref={inputRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="输入问题，Enter 发送，Shift+Enter 换行"
          disabled={streaming}
          rows={2}
        />
        <button
          onClick={handleSend}
          disabled={streaming || !input.trim()}
        >
          {streaming ? "⏳" : "发送"}
        </button>
      </div>
    </div>
  );
}
