import { useState, useRef } from 'react';

const API_BASE = '/api';

export default function SourcesPanel({
  notebookId,
  documents = [],
  selectedDocIds = [],
  onToggleDoc,
  onSelectAllDocs,
  onUploadComplete,
  collapsed = false,
  onToggleCollapse,
}) {
  const [dragActive, setDragActive] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState(null);
  const [webSearchQuery, setWebSearchQuery] = useState('');
  const [showWebSearchInput, setShowWebSearchInput] = useState(false);
  const fileInputRef = useRef(null);

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
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

  const handleFileChange = async (e) => {
    if (e.target.files && e.target.files[0]) {
      await uploadFile(e.target.files[0]);
    }
  };

  const uploadFile = async (file) => {
    if (!notebookId) {
      alert('Please select or create a notebook first.');
      return;
    }

    setUploading(true);
    setUploadError(null);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await fetch(`${API_BASE}/notebooks/${notebookId}/documents`, {
        method: 'POST',
        body: formData,
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || 'Upload failed');
      }
      if (onUploadComplete) onUploadComplete(data.document);
    } catch (err) {
      setUploadError(err.message);
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const allSelected = documents.length > 0 && selectedDocIds.length === documents.length;

  if (collapsed) {
    return (
      <div
        className="nlm-panel"
        style={{
          width: '56px',
          alignItems: 'center',
          padding: '16px 0',
          cursor: 'pointer',
        }}
        onClick={onToggleCollapse}
        title="Expand Sources"
      >
        <button
          style={{
            background: 'transparent',
            border: 'none',
            color: 'var(--text-secondary)',
            cursor: 'pointer',
          }}
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
            <line x1="9" y1="3" x2="9" y2="21" />
          </svg>
        </button>
        <span
          style={{
            writingMode: 'vertical-rl',
            transform: 'rotate(180deg)',
            marginTop: '24px',
            color: 'var(--text-secondary)',
            fontSize: '0.85rem',
            fontWeight: 500,
            letterSpacing: '0.05em',
          }}
        >
          Sources ({documents.length})
        </span>
      </div>
    );
  }

  return (
    <aside className="nlm-panel animate-fade-in" style={{ padding: '0 12px 14px 12px' }}>
      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf,.docx,.txt"
        onChange={handleFileChange}
        style={{ display: 'none' }}
      />

      {/* Header */}
      <div className="nlm-panel-header" style={{ padding: '0 4px', borderBottom: 'none' }}>
        <h2 className="nlm-panel-title">Sources</h2>
        <button
          onClick={onToggleCollapse}
          style={{
            background: 'transparent',
            border: 'none',
            color: 'var(--text-secondary)',
            cursor: 'pointer',
            padding: '6px',
            borderRadius: '6px',
            display: 'flex',
            alignItems: 'center',
          }}
          title="Collapse Sources"
          onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.08)')}
          onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
            <line x1="9" y1="3" x2="9" y2="21" />
          </svg>
        </button>
      </div>

      {/* + Add sources pill button */}
      <div style={{ margin: '8px 0 16px 0' }}>
        <button
          onClick={() => fileInputRef.current?.click()}
          disabled={uploading}
          className="nlm-pill-btn"
          style={{
            width: '100%',
            padding: '10px 16px',
            gap: '8px',
            backgroundColor: 'var(--pill-bg)',
            fontSize: '0.9rem',
            fontWeight: 500,
            cursor: 'pointer',
          }}
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
            <line x1="12" y1="5" x2="12" y2="19" />
            <line x1="5" y1="12" x2="19" y2="12" />
          </svg>
          <span>{uploading ? 'Uploading source...' : 'Add sources'}</span>
        </button>
      </div>

      {/* Search the web for new sources */}
      <div style={{ marginBottom: '16px' }}>
        <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '8px', fontWeight: 500 }}>
          Search the web for new sources
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <button
            className="nlm-pill-btn"
            style={{
              padding: '6px 12px',
              fontSize: '0.78rem',
              backgroundColor: 'var(--bg-panel-subtle)',
              border: '1px solid var(--border-subtle)',
              gap: '6px',
            }}
          >
            <span>🌐 Web</span>
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M6 9l6 6 6-6" />
            </svg>
          </button>

          <button
            className="nlm-pill-btn"
            style={{
              padding: '6px 12px',
              fontSize: '0.78rem',
              backgroundColor: 'var(--bg-panel-subtle)',
              border: '1px solid var(--border-subtle)',
              gap: '6px',
            }}
          >
            <span>🔍 Fast Research</span>
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M6 9l6 6 6-6" />
            </svg>
          </button>

          <button
            onClick={() => setShowWebSearchInput(!showWebSearchInput)}
            style={{
              background: 'var(--bg-panel-subtle)',
              border: '1px solid var(--border-subtle)',
              color: 'var(--text-secondary)',
              borderRadius: '50%',
              width: '32px',
              height: '32px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              cursor: 'pointer',
            }}
            title="Search Web Sources"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
              <circle cx="11" cy="11" r="8" />
              <line x1="21" y1="21" x2="16.65" y2="16.65" />
            </svg>
          </button>
        </div>

        {showWebSearchInput && (
          <div style={{ marginTop: '8px' }}>
            <input
              type="text"
              placeholder="Enter URL or search topic..."
              value={webSearchQuery}
              onChange={(e) => setWebSearchQuery(e.target.value)}
              style={{
                width: '100%',
                backgroundColor: 'var(--bg-canvas)',
                border: '1px solid var(--border-subtle)',
                borderRadius: '8px',
                padding: '6px 10px',
                fontSize: '0.8rem',
                color: 'var(--text-primary)',
                outline: 'none',
              }}
            />
          </div>
        )}
      </div>

      {/* Upload Error Banner */}
      {uploadError && (
        <div
          style={{
            padding: '8px 10px',
            backgroundColor: 'rgba(239, 68, 68, 0.15)',
            border: '1px solid rgba(239, 68, 68, 0.3)',
            borderRadius: '8px',
            fontSize: '0.78rem',
            color: '#f87171',
            marginBottom: '12px',
          }}
        >
          {uploadError}
        </div>
      )}

      {/* Sources Body: Empty State or Document List */}
      <div
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        style={{
          flex: 1,
          overflowY: 'auto',
          display: 'flex',
          flexDirection: 'column',
          borderRadius: '12px',
          border: dragActive ? '2px dashed var(--accent-blue)' : '1px solid transparent',
          backgroundColor: dragActive ? 'rgba(168, 199, 250, 0.05)' : 'transparent',
          transition: 'all 0.2s ease',
        }}
      >
        {documents.length === 0 ? (
          /* Empty State (Pixel-matched to screenshot) */
          <div
            style={{
              flex: 1,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              textAlign: 'center',
              padding: '24px 16px',
            }}
          >
            {/* Document icon */}
            <div style={{ color: 'var(--text-muted)', marginBottom: '14px' }}>
              <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                <polyline points="14 2 14 8 20 8" />
                <line x1="16" y1="13" x2="8" y2="13" />
                <line x1="16" y1="17" x2="8" y2="17" />
                <polyline points="10 9 9 9 8 9" />
              </svg>
            </div>

            <div style={{ fontSize: '0.9rem', fontWeight: 500, color: 'var(--text-primary)', marginBottom: '6px' }}>
              Saved sources will appear here
            </div>

            <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', lineHeight: 1.4, marginBottom: '12px' }}>
              Add files, websites, or more. Then ask questions or create things based on these sources.
            </div>

            <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
              Drop files here or{' '}
              <button
                onClick={() => fileInputRef.current?.click()}
                style={{
                  background: 'none',
                  border: 'none',
                  color: 'var(--accent-blue)',
                  cursor: 'pointer',
                  textDecoration: 'underline',
                  padding: 0,
                  fontSize: '0.8rem',
                }}
              >
                add a source
              </button>
            </div>
          </div>
        ) : (
          /* Source list with selection & metadata */
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            {/* Scope select header */}
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '4px 6px 8px 6px',
                borderBottom: '1px solid var(--border-subtle)',
                fontSize: '0.78rem',
                color: 'var(--text-secondary)',
              }}
            >
              <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={allSelected}
                  onChange={onSelectAllDocs}
                  style={{ accentColor: 'var(--accent-blue)' }}
                />
                <span>Select all ({documents.length})</span>
              </label>
              <span>{selectedDocIds.length} active</span>
            </div>

            {/* Document cards */}
            {documents.map((doc) => {
              const isSelected = selectedDocIds.includes(doc.id);
              const isIndexed = doc.indexing_status === 'indexed';
              const isFailed = doc.indexing_status === 'failed' || doc.processing_status === 'failed';

              return (
                <div
                  key={doc.id}
                  onClick={() => onToggleDoc(doc.id)}
                  style={{
                    display: 'flex',
                    alignItems: 'flex-start',
                    gap: '10px',
                    padding: '8px 10px',
                    borderRadius: '10px',
                    cursor: 'pointer',
                    backgroundColor: isSelected ? 'rgba(168, 199, 250, 0.08)' : 'var(--bg-panel-subtle)',
                    border: `1px solid ${isSelected ? 'rgba(168, 199, 250, 0.3)' : 'var(--border-subtle)'}`,
                    transition: 'all 0.15s ease',
                  }}
                  onMouseEnter={(e) => {
                    if (!isSelected) e.currentTarget.style.backgroundColor = 'var(--bg-card-hover)';
                  }}
                  onMouseLeave={(e) => {
                    if (!isSelected) e.currentTarget.style.backgroundColor = 'var(--bg-panel-subtle)';
                  }}
                >
                  <input
                    type="checkbox"
                    checked={isSelected}
                    onChange={(e) => {
                      e.stopPropagation();
                      onToggleDoc(doc.id);
                    }}
                    style={{ accentColor: 'var(--accent-blue)', marginTop: '3px' }}
                  />

                  {/* Icon */}
                  <div style={{ fontSize: '1.2rem', lineHeight: 1 }}>
                    {doc.file_type === 'pdf' ? '📕' : doc.file_type === 'docx' ? '📘' : '📄'}
                  </div>

                  {/* Details */}
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div
                      style={{
                        fontSize: '0.84rem',
                        fontWeight: 500,
                        color: 'var(--text-primary)',
                        textOverflow: 'ellipsis',
                        overflow: 'hidden',
                        whiteSpace: 'nowrap',
                      }}
                      title={doc.original_filename}
                    >
                      {doc.original_filename}
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginTop: '3px', fontSize: '0.72rem', color: 'var(--text-secondary)' }}>
                      <span>{(doc.file_size / 1024 / 1024).toFixed(1)} MB</span>
                      {doc.page_count && <span>• {doc.page_count} pgs</span>}
                      <span>•</span>
                      {isIndexed && <span style={{ color: '#86efac' }}>Indexed</span>}
                      {!isIndexed && !isFailed && <span style={{ color: '#fcd34d' }}>Processing</span>}
                      {isFailed && <span style={{ color: '#f87171' }}>Failed</span>}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </aside>
  );
}
