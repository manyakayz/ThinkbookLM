import { useState, useEffect } from 'react';
import DocumentUpload from './DocumentUpload';

const API_BASE = '/api';

export default function DocumentList({ notebookId }) {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchDocuments = async () => {
    if (!notebookId) return;
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/notebooks/${notebookId}/documents`);
      const data = await res.json();
      setDocuments(data);
    } catch (e) {
      console.error("Failed to fetch documents", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDocuments();
  }, [notebookId]);

  const handleUploadComplete = (newDoc) => {
    setDocuments([newDoc, ...documents]);
  };

  if (!notebookId) {
    return (
      <div className="empty-state">
        <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>👈</div>
        <h3>Select a Notebook</h3>
        <p>Choose a notebook from the sidebar or create a new one to get started.</p>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div className="doc-header" style={{ marginBottom: '2rem' }}>
        <div>
          <h1 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span>📂</span> Notebook Documents
          </h1>
          <p className="subtitle">Upload and manage source documents for this notebook.</p>
        </div>
      </div>

      <DocumentUpload notebookId={notebookId} onUploadComplete={handleUploadComplete} />

      <h3 style={{ marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
        <span>📄</span> Documents ({documents.length})
      </h3>

      {loading ? (
        <div className="empty-state">Loading documents...</div>
      ) : documents.length === 0 ? (
        <div className="empty-state">
          <div style={{ fontSize: '2.5rem', marginBottom: '1rem' }}>📭</div>
          <p>No documents found in this notebook.</p>
        </div>
      ) : (
        <div className="document-grid">
          {documents.map(doc => (
            <div key={doc.id} className="document-card">
              <div className="doc-header">
                <div className="doc-title" title={doc.original_filename}>
                  {doc.original_filename.length > 40 
                    ? doc.original_filename.substring(0, 40) + '...' 
                    : doc.original_filename}
                </div>
                <div className="doc-type">{doc.file_type}</div>
              </div>
              
              <div className="doc-meta">
                <span>{(doc.file_size / 1024 / 1024).toFixed(2)} MB</span>
                <span>Uploaded {new Date(doc.created_at).toLocaleDateString()}</span>
                {doc.page_count && <span>{doc.page_count} pages</span>}
              </div>
              
              <div style={{ marginTop: 'auto', paddingTop: '1rem', display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
                <span className={`status-badge status-${doc.processing_status}`}>
                  {doc.processing_status === 'pending' && '⏳'}
                  {doc.processing_status === 'processing' && '🔄'}
                  {doc.processing_status === 'completed' && '✅'}
                  {doc.processing_status === 'failed' && '❌'}
                  {' '}
                  {doc.processing_status.charAt(0).toUpperCase() + doc.processing_status.slice(1)}
                </span>

                {/* Indexing status — only show when processing completed */}
                {doc.processing_status === 'completed' && (
                  <span className={`status-badge status-idx-${doc.indexing_status}`}>
                    {doc.indexing_status === 'pending'   && '🕐'}
                    {doc.indexing_status === 'indexing'  && '🔄'}
                    {doc.indexing_status === 'indexed'   && '🗂️'}
                    {doc.indexing_status === 'failed'    && '⚠️'}
                    {' '}
                    {doc.indexing_status === 'indexed' ? 'Indexed' : doc.indexing_status.charAt(0).toUpperCase() + doc.indexing_status.slice(1)}
                  </span>
                )}
                
                {doc.error_message && (
                  <div className="error-msg" style={{ fontSize: '0.75rem', padding: '0.5rem' }}>
                    {doc.error_message}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
