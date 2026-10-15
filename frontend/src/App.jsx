import { useState, useEffect } from 'react';
import Navbar from './components/Navbar';
import SourcesPanel from './components/SourcesPanel';
import ChatPanel from './components/ChatPanel';
import StudioPanel from './components/StudioPanel';
import CreateNotebookModal from './components/CreateNotebookModal';
import LoginPage from './components/LoginPage';
import SignupPage from './components/SignupPage';
import { AuthProvider, useAuth } from './context/AuthContext';
import { apiFetch } from './api/client';
import './index.css';

const API_BASE = '/api';

function WorkspaceView() {
  const { user } = useAuth();
  const [notebooks, setNotebooks] = useState([]);
  const [activeNotebook, setActiveNotebook] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [selectedDocIds, setSelectedDocIds] = useState([]);
  const [sourcesCollapsed, setSourcesCollapsed] = useState(false);
  const [studioCollapsed, setStudioCollapsed] = useState(false);
  const [showCreateModal, setShowCreateModal] = useState(false);

  // Fetch all notebooks belonging to the current user
  const fetchNotebooks = async () => {
    try {
      const res = await apiFetch(`${API_BASE}/notebooks`);
      if (!res.ok) throw new Error(`HTTP error ${res.status}`);
      const data = await res.json();
      setNotebooks(data);
      if (data.length > 0) {
        // Keep activeNotebook if it's still in the list, otherwise select first
        setActiveNotebook((prev) => (data.some((nb) => nb.id === prev) ? prev : data[0].id));
      } else {
        setActiveNotebook(null);
      }
    } catch (e) {
      console.error('Failed to fetch notebooks', e);
    }
  };

  useEffect(() => {
    // Clear state when user changes to ensure complete data isolation
    setNotebooks([]);
    setActiveNotebook(null);
    setDocuments([]);
    setSelectedDocIds([]);
    fetchNotebooks();
  }, [user?.id]);

  // Fetch documents when activeNotebook changes
  const fetchDocuments = async () => {
    if (!activeNotebook) {
      setDocuments([]);
      setSelectedDocIds([]);
      return;
    }
    try {
      const res = await apiFetch(`${API_BASE}/notebooks/${activeNotebook}/documents`);
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
      const res = await apiFetch(`${API_BASE}/notebooks`, {
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

function AppContent() {
  const { user, loading } = useAuth();
  const [authView, setAuthView] = useState('login');

  if (loading) {
    return (
      <div
        style={{
          height: '100vh',
          width: '100vw',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          backgroundColor: 'var(--bg-canvas)',
          gap: '16px',
        }}
      >
        <div
          style={{
            width: '48px',
            height: '48px',
            borderRadius: '50%',
            background: 'linear-gradient(135deg, #1a73e8 0%, #38bdf8 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 4px 16px rgba(26, 115, 232, 0.4)',
            animation: 'pulse 1.8s ease-in-out infinite',
          }}
        >
          <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#ffffff" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 2a10 10 0 1 0 10 10" />
            <path d="M12 6a6 6 0 1 0 6 6" />
            <path d="M12 10a2 2 0 1 0 2 2" />
          </svg>
        </div>
        <div style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', fontWeight: 500 }}>
          Loading ThinkbookLM...
        </div>
      </div>
    );
  }

  if (!user) {
    if (authView === 'signup') {
      return <SignupPage onSwitchToLogin={() => setAuthView('login')} />;
    }
    return <LoginPage onSwitchToSignup={() => setAuthView('signup')} />;
  }

  return <WorkspaceView />;
}

export default function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}
