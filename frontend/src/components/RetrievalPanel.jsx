import { useState, useEffect } from 'react';

const API_BASE = '/api';

export default function RetrievalPanel({ notebookId }) {
  const [query, setQuery] = useState('');
  const [topK, setTopK] = useState(5);
  const [documents, setDocuments] = useState([]);
  const [selectedDocIds, setSelectedDocIds] = useState([]);
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!notebookId) return;
    setResults(null);
    setError(null);
    setSelectedDocIds([]);
    fetch(`${API_BASE}/notebooks/${notebookId}/documents`)
      .then(r => r.json())
      .then(data => setDocuments(data.filter(d => d.indexing_status === 'indexed')))
      .catch(() => {});
  }, [notebookId]);

  const toggleDoc = (id) => {
    setSelectedDocIds(prev =>
      prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]
    );
  };

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!query.trim() || !notebookId) return;

    setLoading(true);
    setError(null);
    setResults(null);

    try {
      const res = await fetch(`${API_BASE}/retrieve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: query.trim(),
          notebook_id: notebookId,
          document_ids: selectedDocIds,
          top_k: topK,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Retrieval failed');
      setResults(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  if (!notebookId) {
    return (
      <div className="empty-state">
        <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>🔍</div>
        <h3>Select a Notebook</h3>
        <p>Choose a notebook to run semantic retrieval queries.</p>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      <div>
        <h1 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span>🔍</span> Semantic Retrieval
        </h1>
        <p className="subtitle">Test vector search over indexed document chunks. Results show distance scores (lower = more relevant).</p>
      </div>

      <form onSubmit={handleSearch} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        {/* Query input */}
        <div>
          <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 500 }}>Query</label>
          <input
            type="text"
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder="Ask a question or describe what you're looking for..."
            style={{ fontSize: '1rem' }}
          />
        </div>

        {/* Controls row */}
        <div style={{ display: 'flex', gap: '1rem', alignItems: 'flex-end', flexWrap: 'wrap' }}>
          <div>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 500, fontSize: '0.875rem' }}>
              Top-K results
            </label>
            <select
              value={topK}
              onChange={e => setTopK(Number(e.target.value))}
              style={{
                background: 'rgba(15,23,42,0.6)', color: 'var(--text-primary)',
                border: '1px solid var(--glass-border)', padding: '0.6rem 1rem',
                borderRadius: '0.5rem', fontFamily: 'inherit', cursor: 'pointer',
              }}
            >
              {[3, 5, 10, 20].map(k => <option key={k} value={k}>{k}</option>)}
            </select>
          </div>
          <button type="submit" disabled={loading || !query.trim()} style={{ height: '42px' }}>
            {loading ? '⏳ Searching...' : '🔍 Search'}
          </button>
        </div>

        {/* Document scope filter */}
        {documents.length > 0 && (
          <div>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 500, fontSize: '0.875rem' }}>
              Scope (leave empty to search all indexed documents)
            </label>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
              {documents.map(doc => (
                <label
                  key={doc.id}
                  style={{
                    display: 'flex', alignItems: 'center', gap: '0.4rem',
                    padding: '0.4rem 0.75rem', borderRadius: '0.5rem', cursor: 'pointer',
                    background: selectedDocIds.includes(doc.id)
                      ? 'rgba(59,130,246,0.25)' : 'rgba(255,255,255,0.05)',
                    border: `1px solid ${selectedDocIds.includes(doc.id) ? 'var(--accent-color)' : 'var(--glass-border)'}`,
                    fontSize: '0.8rem', transition: 'all 0.15s',
                  }}
                >
                  <input
                    type="checkbox"
                    checked={selectedDocIds.includes(doc.id)}
                    onChange={() => toggleDoc(doc.id)}
                    style={{ accentColor: 'var(--accent-color)' }}
                  />
                  {doc.original_filename}
                  <span className="doc-type" style={{ fontSize: '0.65rem' }}>{doc.file_type}</span>
                </label>
              ))}
            </div>
          </div>
        )}

        {documents.length === 0 && (
          <div style={{ padding: '0.75rem 1rem', background: 'rgba(245,158,11,0.1)', borderRadius: '0.5rem', border: '1px solid rgba(245,158,11,0.3)', fontSize: '0.875rem', color: '#fbbf24' }}>
            ⚠️ No indexed documents found in this notebook. Upload a document — it will be automatically embedded and indexed.
          </div>
        )}
      </form>

      {/* Error */}
      {error && (
        <div className="error-msg">⚠️ {error}</div>
      )}

      {/* Results */}
      {results && (
        <div>
          <h3 style={{ marginBottom: '1rem' }}>
            Results — {results.results.length} chunk{results.results.length !== 1 ? 's' : ''} retrieved
            {results.document_ids.length > 0 && ` (scoped to ${results.document_ids.length} document${results.document_ids.length !== 1 ? 's' : ''})`}
          </h3>

          {results.results.length === 0 ? (
            <div className="empty-state">
              <div style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>📭</div>
              <p>No matching chunks found. Try a different query or upload more documents.</p>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              {results.results.map((r, i) => (
                <div key={r.vector_id} className="document-card" style={{ gap: '0.75rem' }}>
                  {/* Header */}
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.5rem' }}>
                    <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                      <span style={{ fontWeight: 700, color: 'var(--accent-color)' }}>#{i + 1}</span>
                      <span style={{ fontWeight: 600 }}>{r.document_name}</span>
                      <span className="doc-type">{r.file_type}</span>
                    </div>
                    <div style={{ display: 'flex', gap: '0.5rem', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                      {r.page_number && <span>📄 Page {r.page_number}</span>}
                      {r.section && <span>📑 {r.section}</span>}
                      <span>Chunk #{r.chunk_index}</span>
                    </div>
                  </div>

                  {/* Distance badge */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <span style={{
                      background: 'rgba(59,130,246,0.15)', color: '#60a5fa',
                      padding: '0.2rem 0.6rem', borderRadius: '0.25rem', fontSize: '0.75rem', fontWeight: 600,
                    }}>
                      distance: {r.distance.toFixed(4)}
                    </span>
                    <span style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>
                      (cosine, lower = more relevant)
                    </span>
                  </div>

                  {/* Text */}
                  <div style={{
                    background: 'rgba(0,0,0,0.3)', padding: '1rem', borderRadius: '0.5rem',
                    fontFamily: 'monospace', fontSize: '0.85rem', lineHeight: 1.7,
                    color: 'var(--text-primary)', whiteSpace: 'pre-wrap', wordBreak: 'break-word',
                    borderLeft: '3px solid var(--accent-color)',
                  }}>
                    {r.text}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
