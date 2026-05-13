import { useState, useRef } from "react";
import { uploadFile } from "../api";

export default function FileUpload({ sessionId, onUploadSuccess }) {
  const [uploading, setUploading] = useState(false);
  const [status, setStatus] = useState(null); // null | { type: "success"|"error", message: string }
  const fileInputRef = useRef(null);

  const handleUpload = async (file) => {
    const ext = file.name.split(".").pop()?.toLowerCase();
    if (!["pdf", "txt", "md"].includes(ext)) {
      setStatus({ type: "error", message: "仅支持 .pdf、.txt 和 .md 文件" });
      return;
    }

    setUploading(true);
    setStatus(null);

    try {
      const result = await uploadFile(file, sessionId);
      setStatus({
        type: "success",
        message: `上传成功！${result.filename} (${result.chunks_count} 个文本块)`,
      });
      onUploadSuccess?.(result);
    } catch (err) {
      setStatus({ type: "error", message: err.message });
    } finally {
      setUploading(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (file) handleUpload(file);
  };

  const handleFileSelect = (e) => {
    const file = e.target.files[0];
    if (file) handleUpload(file);
  };

  return (
    <div className="file-upload">
      <div
        className={`drop-zone ${uploading ? "uploading" : ""}`}
        onDrop={handleDrop}
        onDragOver={(e) => e.preventDefault()}
        onClick={() => fileInputRef.current?.click()}
      >
        {uploading ? (
          <span>正在上传和索引文档...</span>
        ) : (
          <span>拖拽 PDF、TXT 或 MD 文件到这里，或点击上传</span>
        )}
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.txt,.md"
          onChange={handleFileSelect}
          style={{ display: "none" }}
        />
      </div>

      {status && (
        <div className={`upload-status ${status.type}`}>
          {status.type === "success" ? "✅ " : "❌ "}
          {status.message}
        </div>
      )}
    </div>
  );
}
