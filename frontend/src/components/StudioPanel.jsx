import { useState } from 'react';

export default function StudioPanel({
  _notebookId,
  documents = [],
  collapsed = false,
  onToggleCollapse,
}) {
  const [showPromo, setShowPromo] = useState(true);
  const [activeModal, setActiveModal] = useState(null);
  const [notes, setNotes] = useState([
    { id: 1, title: 'Key Takeaways', content: 'Notes and reflections from the uploaded documents.' }
  ]);
  const [newNoteContent, setNewNoteContent] = useState('');
  const [showNoteInput, setShowNoteInput] = useState(false);

  const studioTools = [
    {
      id: 'audio',
      label: 'Audio Overview',
      icon: (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#a8c7fa" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z" />
          <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
          <line x1="12" y1="19" x2="12" y2="22" />
        </svg>
      ),
      description: 'Two AI hosts summarize and discuss your sources in an engaging conversation.',
    },
    {
      id: 'slides',
      label: 'Slide Deck',
      icon: (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#fcd34d" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <rect x="2" y="3" width="20" height="14" rx="2" ry="2" />
          <line x1="8" y1="21" x2="16" y2="21" />
          <line x1="12" y1="17" x2="12" y2="21" />
        </svg>
      ),
      description: 'Generate presentation slides summarizing the main topics from your sources.',
    },
    {
      id: 'video',
      label: 'Video Overview',
      icon: (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#4ade80" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <polygon points="23 7 16 12 23 17 23 7" />
          <rect x="1" y="5" width="15" height="14" rx="2" ry="2" />
        </svg>
      ),
      description: 'Visual video script and storyboard based on your documents.',
    },
    {
      id: 'mindmap',
      label: 'Mind Map',
      icon: (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#c084fc" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="18" cy="5" r="3" />
          <circle cx="6" cy="12" r="3" />
          <circle cx="18" cy="19" r="3" />
          <line x1="8.59" y1="13.51" x2="15.42" y2="17.49" />
          <line x1="15.41" y1="6.51" x2="8.59" y2="10.49" />
        </svg>
      ),
      description: 'Interactive concept map linking key terms and relations from your notebook.',
    },
    {
      id: 'reports',
      label: 'Reports',
      badge: 'New!',
      icon: (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#fb923c" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
          <polyline points="14 2 14 8 20 8" />
          <line x1="16" y1="13" x2="8" y2="13" />
          <line x1="16" y1="17" x2="8" y2="17" />
        </svg>
      ),
      description: 'Detailed synthesized research report with cross-source references.',
    },
    {
      id: 'flashcards',
      label: 'Flashcards',
      icon: (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#38bdf8" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <rect x="3" y="3" width="14" height="14" rx="2" />
          <path d="M7 21h12a2 2 0 0 0 2-2V7" />
        </svg>
      ),
      description: 'Study flashcards generated automatically from definitions and key points.',
    },
    {
      id: 'quiz',
      label: 'Quiz',
      icon: (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#a78bfa" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2" />
          <rect x="8" y="2" width="8" height="4" rx="1" ry="1" />
          <path d="m9 14 2 2 4-4" />
        </svg>
      ),
      description: 'Test your understanding with multiple-choice questions from your sources.',
    },
    {
      id: 'infographic',
      label: 'Infographic',
      icon: (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#f472b6" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <line x1="18" y1="20" x2="18" y2="10" />
          <line x1="12" y1="20" x2="12" y2="4" />
          <line x1="6" y1="20" x2="6" y2="14" />
        </svg>
      ),
      description: 'Visual breakdown and statistical highlights of source documents.',
    },
    {
      id: 'datatable',
      label: 'Data Table',
      icon: (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#60a5fa" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M3 3h18v18H3zM3 9h18M3 15h18M9 3v18M15 3v18" />
        </svg>
      ),
      description: 'Tabular extraction of metrics, dates, entities, and comparisons.',
    },
  ];

  const handleAddNote = () => {
    if (!newNoteContent.trim()) return;
    setNotes((prev) => [
      ...prev,
      {
        id: Date.now(),
        title: `Note #${prev.length + 1}`,
        content: newNoteContent.trim(),
      },
    ]);
    setNewNoteContent('');
    setShowNoteInput(false);
  };

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
        title="Expand Studio"
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
            <line x1="15" y1="3" x2="15" y2="21" />
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
          Studio
        </span>
      </div>
    );
  }

  return (
    <aside className="nlm-panel animate-fade-in" style={{ padding: '0 14px 14px 14px' }}>
      {/* Header */}
      <div className="nlm-panel-header" style={{ padding: '0 2px', borderBottom: 'none' }}>
        <h2 className="nlm-panel-title">Studio</h2>
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
          title="Collapse Studio"
          onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.08)')}
          onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
            <line x1="15" y1="3" x2="15" y2="21" />
          </svg>
        </button>
      </div>

      <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '12px' }}>
        {/* Multilingual Audio Overview Banner (Exact match to screenshot) */}
        <div
          style={{
            backgroundColor: 'var(--bg-card)',
            borderRadius: '12px',
            padding: '12px 14px',
            fontSize: '0.78rem',
            color: 'var(--text-secondary)',
            lineHeight: 1.5,
            border: '1px solid var(--border-subtle)',
          }}
        >
          <span style={{ color: 'var(--text-primary)', fontWeight: 500 }}>Create an Audio Overview in: </span>
          <span>हिन्दी , বাংলা , ગુજરાતી , ಕನ್ನಡ , മലയാളം , मराठी , ਪੰਜਾਬੀ , தமிழ் , తెలుగు</span>
        </div>

        {/* Feature Announcement Card (Exact match to screenshot) */}
        {showPromo && (
          <div
            style={{
              background: 'linear-gradient(135deg, rgba(30, 41, 59, 0.8) 0%, rgba(20, 83, 45, 0.4) 100%)',
              border: '1px solid rgba(255, 255, 255, 0.1)',
              borderRadius: '12px',
              padding: '12px 14px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: '10px',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <span style={{ fontSize: '1.2rem' }}>✨</span>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-primary)', fontWeight: 500 }}>
                New: You can now create Interactive Reports!
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <button
                className="nlm-pill-btn"
                style={{
                  padding: '4px 12px',
                  fontSize: '0.75rem',
                  backgroundColor: 'rgba(255, 255, 255, 0.12)',
                  border: 'none',
                }}
                onClick={() => setActiveModal(studioTools.find((t) => t.id === 'reports'))}
              >
                Try it
              </button>
              <button
                onClick={() => setShowPromo(false)}
                style={{
                  background: 'none',
                  border: 'none',
                  color: 'var(--text-secondary)',
                  cursor: 'pointer',
                  fontSize: '0.85rem',
                  padding: '2px',
                }}
              >
                ✕
              </button>
            </div>
          </div>
        )}

        {/* Studio Grid (2 columns, Exact match to screenshot) */}
        <div className="studio-grid">
          {studioTools.map((tool) => (
            <div
              key={tool.id}
              className="studio-card"
              onClick={() => setActiveModal(tool)}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <div style={{ display: 'flex', alignItems: 'center' }}>{tool.icon}</div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <span style={{ fontSize: '0.82rem', fontWeight: 500, color: 'var(--text-primary)' }}>
                    {tool.label}
                  </span>
                  {tool.badge && (
                    <span
                      style={{
                        fontSize: '0.62rem',
                        fontWeight: 700,
                        color: '#4ade80',
                        backgroundColor: 'rgba(74, 222, 128, 0.15)',
                        padding: '1px 5px',
                        borderRadius: '4px',
                        textTransform: 'uppercase',
                      }}
                    >
                      {tool.badge}
                    </span>
                  )}
                </div>
              </div>

              {/* Chevron > */}
              <div style={{ color: 'var(--text-secondary)', fontSize: '0.8rem' }}>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M9 18l6-6-6-6" />
                </svg>
              </div>
            </div>
          ))}
        </div>

        {/* Saved Notes Section */}
        {notes.length > 0 && (
          <div style={{ marginTop: '10px' }}>
            <div style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '8px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Notebook Notes ({notes.length})
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              {notes.map((note) => (
                <div
                  key={note.id}
                  style={{
                    backgroundColor: 'var(--bg-card)',
                    borderRadius: '10px',
                    padding: '10px 12px',
                    border: '1px solid var(--border-subtle)',
                    fontSize: '0.82rem',
                  }}
                >
                  <div style={{ fontWeight: 600, color: 'var(--text-primary)', marginBottom: '4px' }}>
                    {note.title}
                  </div>
                  <div style={{ color: 'var(--text-secondary)', lineHeight: 1.4 }}>
                    {note.content}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Note Input Inline */}
        {showNoteInput && (
          <div
            style={{
              backgroundColor: 'var(--bg-card)',
              borderRadius: '12px',
              padding: '12px',
              border: '1px solid var(--accent-blue)',
            }}
          >
            <textarea
              rows={3}
              placeholder="Write your note or thoughts here..."
              value={newNoteContent}
              onChange={(e) => setNewNoteContent(e.target.value)}
              style={{
                width: '100%',
                backgroundColor: 'transparent',
                border: 'none',
                outline: 'none',
                color: 'var(--text-primary)',
                fontSize: '0.85rem',
                resize: 'none',
              }}
            />
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: '6px' }}>
              <button
                className="nlm-pill-btn"
                style={{ padding: '4px 12px', fontSize: '0.78rem' }}
                onClick={() => setShowNoteInput(false)}
              >
                Cancel
              </button>
              <button
                className="nlm-pill-btn-white"
                style={{ padding: '4px 14px', fontSize: '0.78rem' }}
                onClick={handleAddNote}
              >
                Save Note
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Bottom Floating Note Action & Info (Exact match to screenshot) */}
      <div
        style={{
          paddingTop: '12px',
          borderTop: '1px solid var(--border-subtle)',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          textAlign: 'center',
          gap: '8px',
        }}
      >
        {/* + Add note white pill button */}
        <button
          onClick={() => setShowNoteInput(true)}
          className="nlm-pill-btn-white"
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '8px',
            padding: '8px 20px',
            fontSize: '0.88rem',
            fontWeight: 500,
            cursor: 'pointer',
            boxShadow: '0 2px 10px rgba(0, 0, 0, 0.3)',
          }}
        >
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <line x1="12" y1="5" x2="12" y2="19" />
            <line x1="5" y1="12" x2="19" y2="12" />
          </svg>
          <span>Add note</span>
        </button>

        {/* Informative text below Add note */}
        <div style={{ fontSize: '0.74rem', color: 'var(--text-secondary)', lineHeight: 1.35, maxWidth: '280px' }}>
          Studio creations will be saved here. After adding sources, create an Audio Overview, Study Guide, Mind Map, and more!
        </div>
      </div>

      {/* Modal Preview for Selected Studio Tool */}
      {activeModal && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.75)',
            backdropFilter: 'blur(4px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
            padding: '20px',
          }}
          onClick={() => setActiveModal(null)}
        >
          <div
            className="animate-fade-in"
            style={{
              backgroundColor: 'var(--bg-panel)',
              border: '1px solid var(--border-subtle)',
              borderRadius: '16px',
              padding: '24px',
              maxWidth: '480px',
              width: '100%',
              display: 'flex',
              flexDirection: 'column',
              gap: '16px',
              boxShadow: '0 16px 40px rgba(0, 0, 0, 0.6)',
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <div style={{ fontSize: '1.5rem' }}>{activeModal.icon}</div>
                <h3 style={{ fontSize: '1.15rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                  {activeModal.label}
                </h3>
              </div>
              <button
                onClick={() => setActiveModal(null)}
                style={{ background: 'none', border: 'none', color: 'var(--text-secondary)', fontSize: '1.2rem', cursor: 'pointer' }}
              >
                ✕
              </button>
            </div>

            <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
              {activeModal.description}
            </p>

            <div
              style={{
                backgroundColor: 'var(--bg-card)',
                borderRadius: '10px',
                padding: '12px 14px',
                fontSize: '0.82rem',
                color: 'var(--text-primary)',
              }}
            >
              <div style={{ fontWeight: 600, marginBottom: '4px' }}>Active Notebook Sources ({documents.length}):</div>
              {documents.length > 0 ? (
                <ul style={{ paddingLeft: '18px', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                  {documents.slice(0, 3).map((d) => (
                    <li key={d.id}>{d.original_filename}</li>
                  ))}
                  {documents.length > 3 && <li>+ {documents.length - 3} more</li>}
                </ul>
              ) : (
                <div style={{ color: '#fbbf24' }}>⚠️ Add sources to generate this studio artifact.</div>
              )}
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '6px' }}>
              <button
                className="nlm-pill-btn"
                onClick={() => setActiveModal(null)}
              >
                Close
              </button>
              <button
                className="nlm-pill-btn-white"
                onClick={() => {
                  alert(`Generating ${activeModal.label} from ${documents.length} sources...`);
                  setActiveModal(null);
                }}
              >
                Generate {activeModal.label}
              </button>
            </div>
          </div>
        </div>
      )}
    </aside>
  );
}
