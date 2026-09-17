import { useState, useEffect } from 'react';
import Navbar from './components/Navbar';
import SourcesPanel from './components/SourcesPanel';
import ChatPanel from './components/ChatPanel';
import StudioPanel from './components/StudioPanel';
import CreateNotebookModal from './components/CreateNotebookModal';
import './index.css';

const API_BASE = '/api';

export default function App() {
  const [notebooks, setNotebooks] = useState([]);
  const [activeNotebook, setActiveNotebook] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [selectedDocIds, setSelectedDocIds] = useState([]);
  const [sourcesCollapsed, setSourcesCollapsed] = useState(false);
  const [studioCollapsed, setStudioCollapsed] = useState(false);
  const [showCreateModal, setShowCreateModal] = useState(false);

  // Fetch all notebooks
  const fetchNotebooks = async () => {
    try {
      const res = await fetch(`${API_BASE}/notebooks`);
      if (!res.ok) throw new Error(`HTTP error ${res.status}`);
      const data = await res.json();
      setNotebooks(data);
      if (data.length > 0 && !activeNotebook) {
        setActiveNotebook(data[0].id);
      }
    } catch (e) {
      console.error('Failed to fetch notebooks', e);
    }
  };

  useEffect(() => {
    fetchNotebooks();
  }, []);

  // Fetch documents when activeNotebook changes
  const fetchDocuments = async () => {
    if (!activeNotebook) {
      setDocuments([]);
      setSelectedDocIds([]);
      return;
    }
    try {
      const res = await fetch(`${API_BASE}/notebooks/${activeNotebook}/documents`);
      if (!res.ok) throw new Error(`Failed to fetch documents: ${res.status}`);
      const data = await res.json();
      setDocuments(data);
      // By default, select all documents
      setSelectedDocIds(data.map((d) => d.id));
    } catch (e) {
      console.error('Failed to fetch documents', e);
    }
  };

  useEffect(() => {
    fetchDocuments();
  }, [activeNotebook]);

  // Handle notebook creation
  const handleCreateNotebook = async (name) => {
    try {
      const res = await fetch(`${API_BASE}/notebooks`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name }),
      });
      if (!res.ok) throw new Error(`Failed to create notebook: ${res.status}`);
      const data = await res.json();
      setNotebooks((prev) => [data, ...prev]);
      setActiveNotebook(data.id);
    } catch (e) {
      console.error('Failed to create notebook', e);
    }
  };

  // Toggle selection of a single document
  const handleToggleDoc = (docId) => {
    setSelectedDocIds((prev) =>
      prev.includes(docId) ? prev.filter((id) => id !== docId) : [...prev, docId]
    );
  };

  // Toggle select all
  const handleSelectAllDocs = () => {
    if (selectedDocIds.length === documents.length) {
      setSelectedDocIds([]);
    } else {
      setSelectedDocIds(documents.map((d) => d.id));
    }
  };

  // Callback when a document is uploaded
  const handleUploadComplete = (newDoc) => {
    setDocuments((prev) => [newDoc, ...prev]);
    setSelectedDocIds((prev) => [...prev, newDoc.id]);
    // Refresh notebooks list to update document counts
    fetchNotebooks();
  };

  const gridTemplateColumns = `${sourcesCollapsed ? '56px' : '280px'} 1fr ${
    studioCollapsed ? '56px' : '340px'
  }`;

  return (
    <div style={{ height: '100vh', display: 'flex', flexDirection: 'column', backgroundColor: 'var(--bg-canvas)' }}>
      {/* Google NotebookLM Top Navbar */}
      <Navbar
        notebooks={notebooks}
        activeNotebook={activeNotebook}
        onSelectNotebook={(id) => setActiveNotebook(id)}
        onCreateNotebook={() => setShowCreateModal(true)}
      />

      {/* 3-Column Workspace: Sources, Chat, Studio */}
      <div
        className="nlm-workspace"
        style={{
          gridTemplateColumns,
          transition: 'grid-template-columns 0.25s cubic-bezier(0.16, 1, 0.3, 1)',
        }}
      >
        {/* Left Column: Sources */}
        <SourcesPanel
          notebookId={activeNotebook}
          documents={documents}
          selectedDocIds={selectedDocIds}
          onToggleDoc={handleToggleDoc}
          onSelectAllDocs={handleSelectAllDocs}
          onUploadComplete={handleUploadComplete}
          collapsed={sourcesCollapsed}
          onToggleCollapse={() => setSourcesCollapsed(!sourcesCollapsed)}
        />

        {/* Middle Column: Chat / Semantic Retrieval Canvas */}
        <ChatPanel
          notebookId={activeNotebook}
          selectedDocIds={selectedDocIds}
          documents={documents}
        />

        {/* Right Column: Studio */}
        <StudioPanel
          notebookId={activeNotebook}
          documents={documents}
          collapsed={studioCollapsed}
          onToggleCollapse={() => setStudioCollapsed(!studioCollapsed)}
        />
      </div>

      {/* Create Notebook Modal */}
      <CreateNotebookModal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        onCreate={handleCreateNotebook}
      />
    </div>
  );
}
