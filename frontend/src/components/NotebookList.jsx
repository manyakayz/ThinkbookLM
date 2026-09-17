import { useState, useEffect } from 'react';

const API_BASE = '/api';

export default function NotebookList({ activeNotebook, onSelectNotebook }) {
  const [notebooks, setNotebooks] = useState([]);
  const [newNotebookName, setNewNotebookName] = useState('');
  const [loading, setLoading] = useState(true);

  const fetchNotebooks = async () => {
    try {
      const res = await fetch(`${API_BASE}/notebooks`);
      if (!res.ok) {
        throw new Error(`Failed to fetch notebooks: ${res.statusText}`);
      }
      const data = await res.json();
      setNotebooks(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchNotebooks();
  }, []);

  const handleCreate = async (e) => {
    e.preventDefault();
    if (!newNotebookName.trim()) return;
    
    try {
      const res = await fetch(`${API_BASE}/notebooks`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: newNotebookName })
      });
      if (!res.ok) {
        throw new Error(`Failed to create notebook: ${res.statusText}`);
      }
      const data = await res.json();
      setNotebooks([data, ...notebooks]);
      setNewNotebookName('');
      if (!activeNotebook) onSelectNotebook(data.id);
    } catch (e) {
      console.error("Failed to create notebook", e);
    }
  };

  return (
    <div className="sidebar">
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
        <div style={{ background: 'var(--accent-color)', padding: '0.5rem', borderRadius: '0.5rem', fontSize: '1.5rem', lineHeight: 1 }}>
          📚
        </div>
        <h2>ThinkBook LM</h2>
      </div>

      <form onSubmit={handleCreate} style={{ display: 'flex', gap: '0.5rem' }}>
        <input 
          type="text" 
          placeholder="New Notebook..." 
          value={newNotebookName}
          onChange={(e) => setNewNotebookName(e.target.value)}
        />
        <button type="submit" style={{ padding: '0.75rem' }} title="Create Notebook">
          ➕
        </button>
      </form>

      {loading ? (
        <div className="empty-state" style={{ padding: '2rem 1rem' }}>Loading notebooks...</div>
      ) : notebooks.length === 0 ? (
        <div className="empty-state" style={{ padding: '2rem 1rem' }}>No notebooks yet.</div>
      ) : (
        <div className="notebook-list">
          {notebooks.map(nb => (
            <div 
              key={nb.id} 
              className={`notebook-item ${activeNotebook === nb.id ? 'active' : ''}`}
              onClick={() => onSelectNotebook(nb.id)}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <span style={{ fontSize: '1.2rem', color: 'var(--text-secondary)' }}>📓</span>
                <span style={{ fontWeight: 500 }}>{nb.name}</span>
              </div>
              <span className="notebook-count">{nb.document_count}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
