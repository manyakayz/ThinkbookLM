import { useState, useRef, useEffect } from 'react';
import { chatRagApi } from '../api/client';

export default function ChatPanel({
  notebookId,
  selectedDocIds = [],
  documents = [],
}) {
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [messages, setMessages] = useState([]);
  const [topK, setTopK] = useState(5);
  const [temperature, setTemperature] = useState(0.3);
  const [showSettings, setShowSettings] = useState(false);
  const [expandedSources, setExpandedSources] = useState({});
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  // Reset chat thread when switching notebooks to ensure frontend data isolation
  useEffect(() => {
    setMessages([]);
    setExpandedSources({});
  }, [notebookId]);

  const toggleSources = (msgId) => {
    setExpandedSources((prev) => ({
      ...prev,
      [msgId]: !prev[msgId],
    }));
  };

  const handleSend = async (queryText) => {
    const textToSend = (queryText || query).trim();
    if (!textToSend || loading) return;
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

    // Build multi-turn history from previous turns
    const history = messages
      .filter((m) => !m.error && (m.sender === 'user' || m.sender === 'assistant'))
      .map((m) => ({
        role: m.sender === 'user' ? 'user' : 'assistant',
        content: m.sender === 'user' ? m.text : (m.answer || ''),
      }));

    setMessages((prev) => [...prev, userMessage]);
    setQuery('');
    setLoading(true);

    try {
      const data = await chatRagApi({
        message: textToSend,
        notebookId,
        documentIds: selectedDocIds,
        history,
        topK,
        temperature,
      });

      const botMessage = {
        id: Date.now() + 1,
        sender: 'assistant',
        answer: data.answer,
        sources: data.sources || [],
        grounded: Boolean(data.grounded),
        retrievedCount: data.retrieved_count || 0,
        model: data.model || 'qwen3:1.7b',
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, botMessage]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now() + 1,
          sender: 'assistant',
          error: err.message || 'Failed to generate answer from local assistant.',
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
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <h2 className="nlm-panel-title">Chat</h2>
          <span
            style={{
              fontSize: '0.72rem',
              color: 'var(--text-secondary)',
              backgroundColor: 'rgba(255, 255, 255, 0.05)',
              padding: '2px 8px',
              borderRadius: '9999px',
              border: '1px solid var(--border-subtle)',
            }}
          >
            Qwen3 1.7B • RAG
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', position: 'relative' }}>
          {/* Settings Toggle Button */}
          <button
            onClick={() => setShowSettings(!showSettings)}
            style={{
              background: showSettings ? 'rgba(255, 255, 255, 0.08)' : 'transparent',
              border: 'none',
              color: 'var(--text-secondary)',
              cursor: 'pointer',
              padding: '6px',
              borderRadius: '6px',
              display: 'flex',
              alignItems: 'center',
            }}
            title="RAG Generation & Retrieval Settings"
            onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.08)')}
            onMouseLeave={(e) => {
              if (!showSettings) e.currentTarget.style.backgroundColor = 'transparent';
            }}
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

          {/* Settings Popover */}
          {showSettings && (
            <div
              className="animate-fade-in"
              style={{
                position: 'absolute',
                top: '100%',
                right: 0,
                marginTop: '6px',
                width: '230px',
                background: 'var(--bg-card)',
                border: '1px solid var(--border-subtle)',
                borderRadius: '12px',
                boxShadow: '0 8px 24px rgba(0, 0, 0, 0.5)',
                padding: '14px',
                zIndex: 100,
                display: 'flex',
                flexDirection: 'column',
                gap: '12px',
              }}
            >
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '6px' }}>
                  <span>Top-K Sources</span>
                  <span style={{ color: 'var(--accent-blue)' }}>{topK}</span>
                </div>
                <input
                  type="range"
                  min="1"
                  max="10"
                  value={topK}
                  onChange={(e) => setTopK(Number(e.target.value))}
                  style={{ width: '100%', accentColor: 'var(--accent-blue)' }}
                />
              </div>

              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '6px' }}>
                  <span>Temperature</span>
                  <span style={{ color: 'var(--accent-blue)' }}>{temperature}</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.1"
                  value={temperature}
                  onChange={(e) => setTemperature(Number(e.target.value))}
                  style={{ width: '100%', accentColor: 'var(--accent-blue)' }}
                />
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                  <span>Factual (0.0)</span>
                  <span>Creative (1.0)</span>
                </div>
              </div>
            </div>
          )}
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
          /* Empty / Welcome State */
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
            <div style={{ fontSize: '3rem', marginBottom: '20px', lineHeight: 1 }}>
              👋
            </div>

            <h1
              style={{
                fontSize: '2.1rem',
                fontWeight: 500,
                color: 'var(--text-primary)',
                letterSpacing: '-0.02em',
                marginBottom: '16px',
              }}
            >
              Let's start your research...
            </h1>

            <p
              style={{
                fontSize: '0.96rem',
                color: 'var(--text-secondary)',
                lineHeight: 1.55,
                marginBottom: '32px',
              }}
            >
              Ask questions grounded directly in your uploaded notebook documents. The assistant retrieves relevant evidence and provides authentic source citations.
            </p>

            <div
              style={{
                fontSize: '0.9rem',
                fontWeight: 600,
                color: 'var(--text-primary)',
                marginBottom: '14px',
              }}
            >
              Suggested prompts:
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', alignItems: 'flex-start' }}>
              <button
                className="nlm-pill-btn"
                style={{
                  padding: '10px 20px',
                  fontSize: '0.88rem',
                  backgroundColor: 'var(--bg-card)',
                  border: '1px solid var(--border-subtle)',
                }}
                onClick={() => handleSend('Summarize the key findings and main ideas from my documents')}
              >
                Summarize the key findings from these documents
              </button>

              <button
                className="nlm-pill-btn"
                style={{
                  padding: '10px 20px',
                  fontSize: '0.88rem',
                  backgroundColor: 'var(--bg-card)',
                  border: '1px solid var(--border-subtle)',
                }}
                onClick={() => handleSend('What are the main topics and concepts discussed across the sources?')}
              >
                What are the core concepts covered?
              </button>

              <button
                className="nlm-pill-btn"
                style={{
                  padding: '10px 20px',
                  fontSize: '0.88rem',
                  backgroundColor: 'var(--bg-card)',
                  border: '1px solid var(--border-subtle)',
                }}
                onClick={() => handleSend('Extract important dates, figures, and factual claims')}
              >
                Extract key facts, dates, and figures
              </button>
            </div>
          </div>
        ) : (
          /* Conversation Thread */
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', width: '100%', maxWidth: '820px', margin: '0 auto' }}>
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
                  /* Assistant Response */
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
                      /* Error Message */
                      <div
                        style={{
                          padding: '14px 16px',
                          backgroundColor: 'rgba(239, 68, 68, 0.08)',
                          border: '1px solid rgba(239, 68, 68, 0.25)',
                          borderRadius: '12px',
                          color: '#f87171',
                          fontSize: '0.88rem',
                          display: 'flex',
                          alignItems: 'flex-start',
                          gap: '10px',
                        }}
                      >
                        <span style={{ fontSize: '1.2rem', lineHeight: 1 }}>⚠️</span>
                        <div style={{ flex: 1 }}>
                          <div style={{ fontWeight: 600, marginBottom: '2px' }}>Request Failed</div>
                          <div>{m.error}</div>
                        </div>
                      </div>
                    ) : (
                      <div
                        style={{
                          backgroundColor: 'var(--bg-panel-subtle)',
                          borderRadius: '16px',
                          padding: '18px',
                          border: '1px solid var(--border-subtle)',
                          display: 'flex',
                          flexDirection: 'column',
                          gap: '14px',
                        }}
                      >
                        {/* Grounding Status Header */}
                        {m.grounded && (
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.84rem', color: 'var(--accent-blue)' }}>
                            <span style={{ fontSize: '1.1rem' }}>✨</span>
                            <span style={{ fontWeight: 600 }}>Grounded Answer</span>
                            {m.sources && m.sources.length > 0 && (
                              <span style={{ color: 'var(--text-secondary)', fontSize: '0.78rem' }}>
                                ({m.sources.length} {m.sources.length === 1 ? 'source cited' : 'sources cited'})
                              </span>
                            )}
                          </div>
                        )}

                        {/* Answer Text */}
                        <div
                          style={{
                            fontSize: '0.94rem',
                            lineHeight: 1.65,
                            color: 'var(--text-primary)',
                            whiteSpace: 'pre-wrap',
                            wordBreak: 'break-word',
                          }}
                        >
                          {m.answer}
                        </div>

                        {/* Verified Sources / Citations Block */}
                        {m.sources && m.sources.length > 0 && (
                          <div style={{ marginTop: '4px', borderTop: '1px solid var(--border-subtle)', paddingTop: '12px' }}>
                            <button
                              onClick={() => toggleSources(m.id)}
                              style={{
                                background: 'transparent',
                                border: 'none',
                                color: 'var(--accent-blue)',
                                fontSize: '0.82rem',
                                fontWeight: 600,
                                cursor: 'pointer',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '6px',
                                padding: '4px 0',
                              }}
                            >
                              <span>{expandedSources[m.id] ? '▾' : '▸'}</span>
                              <span>Verified Source References ({m.sources.length})</span>
                            </button>

                            {/* Expanded Source Details */}
                            {expandedSources[m.id] && (
                              <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginTop: '10px' }}>
                                {m.sources.map((s, idx) => (
                                  <div
                                    key={s.chunk_id || idx}
                                    style={{
                                      backgroundColor: 'var(--bg-card)',
                                      borderRadius: '8px',
                                      padding: '10px 12px',
                                      border: '1px solid var(--border-subtle)',
                                      display: 'flex',
                                      justifyContent: 'space-between',
                                      alignItems: 'center',
                                      flexWrap: 'wrap',
                                      gap: '8px',
                                    }}
                                  >
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.84rem' }}>
                                      <span style={{ color: 'var(--accent-blue)', fontWeight: 600 }}>#{idx + 1}</span>
                                      <span style={{ color: 'var(--text-primary)', fontWeight: 500 }}>{s.document_name}</span>
                                    </div>

                                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.76rem', color: 'var(--text-secondary)' }}>
                                      {s.page_number !== null && s.page_number !== undefined && (
                                        <span style={{ backgroundColor: 'rgba(255, 255, 255, 0.05)', padding: '2px 6px', borderRadius: '4px' }}>
                                          Page {s.page_number}
                                        </span>
                                      )}
                                      {s.section && (
                                        <span style={{ backgroundColor: 'rgba(255, 255, 255, 0.05)', padding: '2px 6px', borderRadius: '4px' }}>
                                          {s.section}
                                        </span>
                                      )}
                                      <span style={{ backgroundColor: 'rgba(255, 255, 255, 0.05)', padding: '2px 6px', borderRadius: '4px' }}>
                                        Chunk #{s.chunk_index + 1}
                                      </span>
                                      <span
                                        style={{
                                          backgroundColor: 'rgba(168, 199, 250, 0.12)',
                                          color: 'var(--accent-blue)',
                                          padding: '2px 6px',
                                          borderRadius: '4px',
                                          fontWeight: 500,
                                        }}
                                        title="Cosine distance (lower is closer)"
                                      >
                                        dist: {s.distance.toFixed(3)}
                                      </span>
                                    </div>
                                  </div>
                                ))}
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}

            {loading && (
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '10px',
                  color: 'var(--text-secondary)',
                  fontSize: '0.88rem',
                  padding: '8px 0',
                }}
              >
                <div
                  style={{
                    width: '16px',
                    height: '16px',
                    borderRadius: '50%',
                    border: '2px solid var(--accent-blue)',
                    borderTopColor: 'transparent',
                    animation: 'spin 0.8s linear infinite',
                  }}
                />
                <span>Retrieving document evidence & generating answer with Qwen3...</span>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Bottom Floating Query Input */}
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
            placeholder={
              loading
                ? 'Generating answer...'
                : activeSourcesCount > 0
                ? `Ask a question about ${activeSourcesCount} ${activeSourcesCount === 1 ? 'source' : 'sources'}...`
                : 'Ask a question or explore this notebook...'
            }
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            disabled={loading || !notebookId}
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

            {/* Circular Send Button */}
            <button
              type="submit"
              disabled={!query.trim() || loading || !notebookId}
              style={{
                width: '32px',
                height: '32px',
                borderRadius: '50%',
                border: 'none',
                backgroundColor: query.trim() && !loading && notebookId ? 'var(--text-primary)' : 'rgba(255, 255, 255, 0.08)',
                color: query.trim() && !loading && notebookId ? '#131314' : 'var(--text-muted)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                cursor: query.trim() && !loading && notebookId ? 'pointer' : 'default',
                transition: 'all 0.15s ease',
              }}
              title={loading ? 'Generating...' : 'Send message'}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <line x1="5" y1="12" x2="19" y2="12" />
                <polyline points="12 5 19 12 12 19" />
              </svg>
            </button>
          </div>
        </form>

        {/* Disclaimer Footer */}
        <div
          style={{
            textAlign: 'center',
            fontSize: '0.74rem',
            color: 'var(--text-muted)',
            marginTop: '8px',
            userSelect: 'none',
          }}
        >
          ThinkbookLM answers are generated locally by Qwen3 1.7B from your notebook sources.
        </div>
      </div>
    </main>
  );
}
