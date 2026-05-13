import { useState, useMemo } from "react";
import FileUpload from "./components/FileUpload";
import ChatWindow from "./components/ChatWindow";
import "./App.css";

export default function App() {
  // crypto.randomUUID() 生成唯一 session ID
  // —— 每次页面加载创建新 session，避免多标签页竞争同一 Chroma collection
  const sessionId = useMemo(() => crypto.randomUUID(), []);
  const [docsUploaded, setDocsUploaded] = useState(false);

  return (
    <div className="app">
      <header className="app-header">
        <h1>Agent + RAG 个人知识库助手</h1>
        <span className="session-badge">Session: {sessionId.slice(0, 8)}...</span>
      </header>

      <main className="app-main">
        <aside className="sidebar">
          <h2>知识库</h2>
          <FileUpload
            sessionId={sessionId}
            onUploadSuccess={() => setDocsUploaded(true)}
          />
          {docsUploaded && (
            <p className="docs-ready">文档已就绪，可以开始提问</p>
          )}
        </aside>

        <section className="chat-section">
          <ChatWindow sessionId={sessionId} />
        </section>
      </main>
    </div>
  );
}
