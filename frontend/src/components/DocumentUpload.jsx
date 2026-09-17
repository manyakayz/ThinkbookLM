import { useState, useRef } from 'react';

const API_BASE = '/api';

export default function DocumentUpload({ notebookId, onUploadComplete }) {
  const [dragActive, setDragActive] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);
  const inputRef = useRef(null);

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = async (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      await uploadFile(e.dataTransfer.files[0]);
    }
  };

  const handleChange = async (e) => {
    e.preventDefault();
    if (e.target.files && e.target.files[0]) {
      await uploadFile(e.target.files[0]);
    }
  };

  const uploadFile = async (file) => {
    if (!notebookId) return;
    
    setUploading(true);
    setError(null);
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
      const res = await fetch(`${API_BASE}/notebooks/${notebookId}/documents`, {
        method: 'POST',
        body: formData,
      });
      
      const data = await res.json();
      
      if (!res.ok) {
        throw new Error(data.detail || "Upload failed");
      }
      
      onUploadComplete(data.document);
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  };

  return (
    <div style={{ marginBottom: '2rem' }}>
      <div 
        className={`upload-area ${dragActive ? 'drag-active' : ''}`}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,.docx,.txt"
          onChange={handleChange}
          style={{ display: 'none' }}
        />
        
        {uploading ? (
          <>
            <div className="upload-icon spin" style={{ fontSize: '2.5rem' }}>⏳</div>
            <p className="upload-text">Uploading and processing document...</p>
          </>
        ) : (
          <>
            <div className="upload-icon" style={{ fontSize: '2.5rem' }}>☁️</div>
            <p className="upload-text">
              <span>Click to upload</span> or drag and drop
            </p>
            <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
              PDF, DOCX, TXT up to 25MB
            </p>
          </>
        )}
      </div>
      
      {error && (
        <div className="error-msg" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span>⚠️</span>
          {error}
        </div>
      )}
    </div>
  );
}
