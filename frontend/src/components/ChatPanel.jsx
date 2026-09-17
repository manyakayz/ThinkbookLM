import { useState, useRef, useEffect } from 'react';

const API_BASE = '/api';

export default function ChatPanel({
  notebookId,
  selectedDocIds = [],
  documents = [],
}) {
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [messages, setMessages] = useState([]);
  const [topK, setTopK] = useState(5);
  const [showSettings, setShowSettings] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  const handleSend = async (queryText) => {
    const textToSend = (queryText || query).trim();
    if (!textToSend) return;
    if (!notebookId) {
      alert('Please select or create a notebook first.');
      return;
    }

    const userMessage = {
      id: Date.now(),
      sender: 'user',
      text: textToSend,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setQuery('');
    setLoading(true);

    try {
      const res = await fetch(`${API_BASE}/retrieve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: textToSend,
          notebook_id: notebookId,
          document_ids: selectedDocIds,
          top_k: topK,
        }),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || 'Failed to retrieve information');
      }

      const botMessage = {
        id: Date.now() + 1,
        sender: 'assistant',
        query: textToSend,
        results: data.results || [],
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, botMessage]);
    } catch (err) {
      setError(err.message);
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now() + 1,
          sender: 'assistant',
          error: err.message,
          timestamp: new Date(),
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const activeSourcesCount = selectedDocIds.length > 0 ? selectedDocIds.length : documents.length;

  return (
    <main className="nlm-panel animate-fade-in" style={{ padding: '0 0 12px 0' }}>
      {/* Header */}
      <div className="nlm-panel-header" style={{ padding: '0 16px', borderBottom: '1px solid var(--border-subtle)' }}>
        <h2 className="nlm-panel-title">Chat</h2>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', position: 'relative' }}>
          {/* Tune / Settings Icon for Top-K */}
          <button
            onClick={() => setShowSettings(!showSettings)}
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
            title="Retrieval Settings (Top-K)"
            onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.08)')}
            onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="4" y1="21" x2="4" y2="14" />
              <line x1="4" y1="10" x2="4" y2="3" />
              <line x1="12" y1="21" x2="12" y2="12" />
              <line x1="12" y1="8" x2="12" y2="3" />
              <line x1="20" y1="21" x2="20" y2="16" />
              <line x1="20" y1="12" x2="20" y2="3" />
              <line x1="1" y1="14" x2="7" y2="14" />
              <line x1="9" y1="8" x2="15" y2="8" />
              <line x1="17" y1="16" x2="23" y2="16" />
            </svg>
          </button>

          {/* Top-K Dropdown Popup */}
          {showSettings && (
            <div
              className="animate-fade-in"
              style={{
                position: 'absolute',
                top: '100%',
                right: 0,
                marginTop: '6px',
                width: '200px',
                background: 'var(--bg-card)',
                border: '1px solid var(--border-subtle)',
                borderRadius: '12px',
                boxShadow: '0 8px 24px rgba(0, 0, 0, 0.5)',
                padding: '12px',
                zIndex: 100,
              }}
            >
              <div style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '8px' }}>
                Top-K Chunks: {topK}
              </div>
              <input
                type="range"
                min="1"
                max="20"
                value={topK}
                onChange={(e) => setTopK(Number(e.target.value))}
                style={{ width: '100%', accentColor: 'var(--accent-blue)' }}
              />
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.72rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
                <span>1</span>
                <span>5</span>
                <span>10</span>
                <span>20</span>
              </div>
            </div>
          )}

          {/* 3 Dots Menu */}
          <button
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
            title="More options"
            onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.08)')}
            onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="1" />
              <circle cx="12" cy="5" r="1" />
              <circle cx="12" cy="19" r="1" />
            </svg>
          </button>
        </div>
      </div>

      {/* Main Chat Area */}
      <div
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: '24px 20px',
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        {messages.length === 0 ? (
          /* Empty / Welcome State (Exact match to Google NotebookLM screenshot) */
          <div
            style={{
              margin: 'auto 0',
              maxWidth: '620px',
              alignSelf: 'center',
              width: '100%',
              textAlign: 'left',
              padding: '20px 0',
            }}
          >
            {/* Waving Hand 👋 */}
            <div style={{ fontSize: '3rem', marginBottom: '20px', lineHeight: 1 }}>
              👋
            </div>

            {/* Title */}
            <h1
              style={{
                fontSize: '2.1rem',
                fontWeight: 500,
                color: 'var(--text-primary)',
                letterSpacing: '-0.02em',
                marginBottom: '16px',
              }}
            >
              Let's start your notebook...
            </h1>

            {/* Subtitle */}
            <p
              style={{
                fontSize: '0.96rem',
                color: 'var(--text-secondary)',
                lineHeight: 1.55,
                marginBottom: '32px',
              }}
            >
              This is your blank canvas to understand, create, or make progress on something new. I can help you get started or you can go ahead and add your own sources.
            </p>

            {/* Heading for Suggestions */}
            <div
              style={{
                fontSize: '0.9rem',
                fontWeight: 600,
                color: 'var(--text-primary)',
                marginBottom: '14px',
              }}
            >
              What would you like this notebook to help you do?
            </div>

            {/* Suggestion Pills */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', alignItems: 'flex-start' }}>
              <button
                className="nlm-pill-btn"
                style={{
                  padding: '10px 20px',
                  fontSize: '0.88rem',
                  backgroundColor: 'var(--bg-card)',
                  border: '1px solid var(--border-subtle)',
                }}
                onClick={() => handleSend('Explain the core concepts and summarize the main takeaways')}
              >
                Learn about a new topic
              </button>

              <button
                className="nlm-pill-btn"
                style={{
                  padding: '10px 20px',
                  fontSize: '0.88rem',
                  backgroundColor: 'var(--bg-card)',
                  border: '1px solid var(--border-subtle)',
                }}
                onClick={() => handleSend('Generate creative ideas and outline a comprehensive draft')}
              >
                Create something new
              </button>

              <button
                className="nlm-pill-btn"
                style={{
                  padding: '10px 20px',
                  fontSize: '0.88rem',
                  backgroundColor: 'var(--bg-card)',
                  border: '1px solid var(--border-subtle)',
                }}
                onClick={() => handleSend('Extract action items and key milestones from these sources')}
              >
                Make progress on a project
              </button>
            </div>
          </div>
        ) : (
          /* Conversation Thread */
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', width: '100%', maxWidth: '800px', margin: '0 auto' }}>
            {messages.map((m) => (
              <div key={m.id} style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {m.sender === 'user' ? (
                  /* User Bubble */
                  <div
                    style={{
                      alignSelf: 'flex-end',
                      backgroundColor: 'var(--bg-card)',
                      color: 'var(--text-primary)',
                      padding: '12px 18px',
                      borderRadius: '18px 18px 4px 18px',
                      maxWidth: '80%',
                      fontSize: '0.94rem',
                      lineHeight: 1.5,
                      border: '1px solid var(--border-subtle)',
                    }}
                  >
                    {m.text}
                  </div>
                ) : (
                  /* Assistant / Retrieval Response */
                  <div
                    style={{
                      alignSelf: 'flex-start',
                      width: '100%',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '12px',
                    }}
                  >
                    {m.error ? (
                      <div
                        style={{
                          padding: '12px 16px',
                          backgroundColor: 'rgba(239, 68, 68, 0.1)',
                          border: '1px solid rgba(239, 68, 68, 0.25)',
                          borderRadius: '12px',
                          color: '#f87171',
                          fontSize: '0.88rem',
                        }}
                      >
                        ⚠️ {m.error}
                      </div>
                    ) : (
                      <>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                          <span style={{ fontSize: '1.1rem' }}>✨</span>
                          <span>Found {m.results.length} relevant source chunks</span>
                        </div>

                        {m.results.length === 0 ? (
                          <div
                            style={{
                              padding: '16px',
                              backgroundColor: 'var(--bg-panel-subtle)',
                              borderRadius: '12px',
                              color: 'var(--text-secondary)',
                              fontSize: '0.88rem',
                              border: '1px solid var(--border-subtle)',
                            }}
                          >
                            No matching chunks found in the selected sources. Try adding more documents or adjusting your query.
                          </div>
                        ) : (
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                            {m.results.map((r, i) => (
                              <div
                                key={r.vector_id || i}
                                style={{
                                  backgroundColor: 'var(--bg-card)',
                                  borderRadius: '12px',
                                  padding: '14px',
                                  border: '1px solid var(--border-subtle)',
                                  display: 'flex',
                                  flexDirection: 'column',
                                  gap: '8px',
                                }}
                              >
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '6px' }}>
                                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.82rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                                    <span style={{ color: 'var(--accent-blue)' }}>#{i + 1}</span>
                                    <span>{r.document_name}</span>
                                    <span style={{ color: 'var(--text-secondary)', fontWeight: 400 }}>({r.file_type})</span>
                                  </div>

                                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                                    {r.page_number && <span>Page {r.page_number}</span>}
                                    {r.section && <span>• {r.section}</span>}
                                    <span
                                      style={{
                                        backgroundColor: 'rgba(168, 199, 250, 0.12)',
                                        color: 'var(--accent-blue)',
                                        padding: '2px 6px',
                                        borderRadius: '4px',
                                        fontWeight: 500,
                                      }}
                                    >
                                      distance: {r.distance.toFixed(3)}
                                    </span>
                                  </div>
                                </div>

                                <div
                                  style={{
                                    fontSize: '0.88rem',
                                    lineHeight: 1.6,
                                    color: 'var(--text-primary)',
                                    backgroundColor: 'rgba(0, 0, 0, 0.25)',
                                    padding: '10px 12px',
                                    borderRadius: '8px',
                                    borderLeft: '3px solid var(--accent-blue)',
                                    fontFamily: 'inherit',
                                    whiteSpace: 'pre-wrap',
                                  }}
                                >
                                  {r.text}
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                      </>
                    )}
                  </div>
                )}
              </div>
            ))}

            {loading && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', color: 'var(--text-secondary)', fontSize: '0.88rem' }}>
                <span style={{ animation: 'spin 1.5s linear infinite', display: 'inline-block' }}>✨</span>
                <span>Searching source chunks...</span>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Bottom Floating Query Input (Exact match to Google NotebookLM screenshot) */}
      <div style={{ padding: '0 20px', width: '100%', maxWidth: '820px', margin: '0 auto' }}>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSend();
          }}
          className="chat-input-container"
        >
          <input
            type="text"
            placeholder="Ask a question or create something"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            disabled={loading}
            style={{
              flex: 1,
              background: 'transparent',
              border: 'none',
              outline: 'none',
              color: 'var(--text-primary)',
              fontSize: '0.95rem',
              padding: '6px 0',
            }}
          />

          {/* Right actions inside container */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', userSelect: 'none' }}>
              {activeSourcesCount} {activeSourcesCount === 1 ? 'source' : 'sources'}
            </span>

            {/* Circular Send Arrow Button */}
            <button
              type="submit"
              disabled={!query.trim() || loading}
              style={{
                width: '32px',
                height: '32px',
                borderRadius: '50%',
                border: 'none',
                backgroundColor: query.trim() && !loading ? 'var(--text-primary)' : 'rgba(255, 255, 255, 0.08)',
                color: query.trim() && !loading ? '#131314' : 'var(--text-muted)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                cursor: query.trim() && !loading ? 'pointer' : 'default',
                transition: 'all 0.15s ease',
              }}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <line x1="5" y1="12" x2="19" y2="12" />
                <polyline points="12 5 19 12 12 19" />
              </svg>
            </button>
          </div>
        </form>

        {/* Disclaimer Footer (Exact match to screenshot) */}
        <div
          style={{
            textAlign: 'center',
            fontSize: '0.74rem',
            color: 'var(--text-muted)',
            marginTop: '8px',
            userSelect: 'none',
          }}
        >
          Gemini Notebook can be inaccurate; please double check its responses.
        </div>
      </div>
    </main>
  );
}
