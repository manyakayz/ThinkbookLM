import { useState, useRef, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';

export default function Navbar({
  notebooks = [],
  activeNotebook,
  onSelectNotebook,
  onCreateNotebook,
}) {
  const { user, logout } = useAuth();
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const dropdownRef = useRef(null);
  const profileRef = useRef(null);

  const currentNotebook = notebooks.find((n) => n.id === activeNotebook);
  const currentTitle = currentNotebook ? currentNotebook.name : 'Untitled notebook';

  const getInitials = (name) => {
    if (!name) return 'U';
    const parts = name.trim().split(/\s+/);
    if (parts.length >= 2) {
      return (parts[0][0] + parts[1][0]).toUpperCase();
    }
    return name.slice(0, 2).toUpperCase();
  };

  useEffect(() => {
    function handleClickOutside(e) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setDropdownOpen(false);
      }
      if (profileRef.current && !profileRef.current.contains(e.target)) {
        setProfileOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <header className="nlm-header">
      {/* Left: Logo + Notebook Title & Switcher */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', position: 'relative' }}>
        {/* NotebookLM Logo */}
        <div
          style={{
            width: '32px',
            height: '32px',
            borderRadius: '50%',
            background: 'linear-gradient(135deg, #1a73e8 0%, #38bdf8 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 2px 8px rgba(26, 115, 232, 0.4)',
            cursor: 'pointer',
          }}
          title="ThinkBook LM"
        >
          {/* Swirl / Spiral icon SVG */}
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#ffffff" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 2a10 10 0 1 0 10 10" />
            <path d="M12 6a6 6 0 1 0 6 6" />
            <path d="M12 10a2 2 0 1 0 2 2" />
          </svg>
        </div>

        {/* Title / Switcher */}
        <div ref={dropdownRef} style={{ position: 'relative' }}>
          <button
            onClick={() => setDropdownOpen(!dropdownOpen)}
            style={{
              background: 'transparent',
              border: 'none',
              color: 'var(--text-primary)',
              fontSize: '1.15rem',
              fontWeight: 500,
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '6px 10px',
              borderRadius: '8px',
              cursor: 'pointer',
            }}
            onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.06)')}
            onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
          >
            <span>{currentTitle}</span>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M6 9l6 6 6-6" />
            </svg>
          </button>

          {/* Notebook Switcher Dropdown */}
          {dropdownOpen && (
            <div
              className="animate-fade-in"
              style={{
                position: 'absolute',
                top: '100%',
                left: 0,
                marginTop: '6px',
                width: '260px',
                background: 'var(--bg-card)',
                border: '1px solid var(--border-subtle)',
                borderRadius: '12px',
                boxShadow: '0 8px 24px rgba(0, 0, 0, 0.5)',
                padding: '6px',
                zIndex: 100,
              }}
            >
              <div style={{ padding: '8px 10px', fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Your Notebooks ({notebooks.length})
              </div>

              <div style={{ maxHeight: '220px', overflowY: 'auto' }}>
                {notebooks.map((nb) => (
                  <div
                    key={nb.id}
                    onClick={() => {
                      onSelectNotebook(nb.id);
                      setDropdownOpen(false);
                    }}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      padding: '8px 10px',
                      borderRadius: '8px',
                      cursor: 'pointer',
                      backgroundColor: nb.id === activeNotebook ? 'rgba(168, 199, 250, 0.12)' : 'transparent',
                      color: nb.id === activeNotebook ? 'var(--accent-blue)' : 'var(--text-primary)',
                      fontSize: '0.875rem',
                      fontWeight: nb.id === activeNotebook ? 600 : 400,
                    }}
                    onMouseEnter={(e) => {
                      if (nb.id !== activeNotebook) e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.05)';
                    }}
                    onMouseLeave={(e) => {
                      if (nb.id !== activeNotebook) e.currentTarget.style.backgroundColor = 'transparent';
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', overflow: 'hidden' }}>
                      <span>📓</span>
                      <span style={{ textOverflow: 'ellipsis', overflow: 'hidden', whiteSpace: 'nowrap' }}>{nb.name}</span>
                    </div>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>{nb.document_count || 0}</span>
                  </div>
                ))}
              </div>

              <div style={{ borderTop: '1px solid var(--border-subtle)', margin: '6px 0', paddingTop: '6px' }}>
                <button
                  onClick={() => {
                    setDropdownOpen(false);
                    onCreateNotebook();
                  }}
                  style={{
                    width: '100%',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    padding: '8px 10px',
                    borderRadius: '8px',
                    background: 'transparent',
                    border: 'none',
                    color: 'var(--accent-blue)',
                    fontSize: '0.85rem',
                    fontWeight: 500,
                    cursor: 'pointer',
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = 'rgba(168, 199, 250, 0.08)')}
                  onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
                >
                  <span>➕</span>
                  <span>New Notebook</span>
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Right: Actions & User Profile */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        {/* + Create notebook pill */}
        <button
          onClick={onCreateNotebook}
          className="nlm-pill-btn-white"
          style={{ display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer' }}
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
            <line x1="12" y1="5" x2="12" y2="19" />
            <line x1="5" y1="12" x2="19" y2="12" />
          </svg>
          <span>Create notebook</span>
        </button>

        {/* Copy button */}
        <button
          className="nlm-pill-btn"
          style={{ padding: '6px 12px', fontSize: '0.82rem', gap: '6px', color: 'var(--text-secondary)' }}
          title="Copy Link"
          onClick={() => {
            navigator.clipboard?.writeText(window.location.href);
            alert('Notebook link copied to clipboard!');
          }}
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
            <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
          </svg>
          <span>Copy</span>
        </button>

        {/* Analytics */}
        <button
          className="nlm-pill-btn"
          style={{ padding: '6px 12px', fontSize: '0.82rem', gap: '6px', color: 'var(--text-secondary)' }}
          title="Analytics"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
          </svg>
          <span>Analytics</span>
        </button>

        {/* Share */}
        <button
          className="nlm-pill-btn"
          style={{ padding: '6px 12px', fontSize: '0.82rem', gap: '6px', color: 'var(--text-secondary)' }}
          title="Share"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="18" cy="5" r="3" />
            <circle cx="6" cy="12" r="3" />
            <circle cx="18" cy="19" r="3" />
            <line x1="8.59" y1="13.51" x2="15.42" y2="17.49" />
            <line x1="15.41" y1="6.51" x2="8.59" y2="10.49" />
          </svg>
          <span>Share</span>
        </button>

        {/* Settings */}
        <button
          className="nlm-pill-btn"
          style={{ padding: '6px 12px', fontSize: '0.82rem', gap: '6px', color: 'var(--text-secondary)' }}
          title="Settings"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="3" />
            <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
          </svg>
          <span>Settings</span>
        </button>

        {/* 3x3 App grid icon */}
        <button
          style={{
            background: 'transparent',
            border: 'none',
            color: 'var(--text-secondary)',
            padding: '8px',
            borderRadius: '50%',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
          title="Google apps"
          onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.08)')}
          onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
            <circle cx="5" cy="5" r="2" />
            <circle cx="12" cy="5" r="2" />
            <circle cx="19" cy="5" r="2" />
            <circle cx="5" cy="12" r="2" />
            <circle cx="12" cy="12" r="2" />
            <circle cx="19" cy="12" r="2" />
            <circle cx="5" cy="19" r="2" />
            <circle cx="12" cy="19" r="2" />
            <circle cx="19" cy="19" r="2" />
          </svg>
        </button>

        {/* User profile avatar & dropdown */}
        <div ref={profileRef} style={{ position: 'relative' }}>
          <button
            onClick={() => setProfileOpen(!profileOpen)}
            style={{
              width: '32px',
              height: '32px',
              borderRadius: '50%',
              backgroundColor: '#1b3a6b',
              color: 'var(--accent-blue)',
              border: '1px solid rgba(168, 199, 250, 0.4)',
              fontWeight: 600,
              fontSize: '0.85rem',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              cursor: 'pointer',
              transition: 'transform 0.15s ease, box-shadow 0.15s ease',
            }}
            title={user ? `${user.full_name} (${user.email})` : 'Account'}
            onMouseEnter={(e) => (e.currentTarget.style.boxShadow = '0 0 0 2px rgba(168, 199, 250, 0.35)')}
            onMouseLeave={(e) => (e.currentTarget.style.boxShadow = 'none')}
          >
            {getInitials(user?.full_name)}
          </button>

          {profileOpen && (
            <div
              className="animate-fade-in"
              style={{
                position: 'absolute',
                top: '100%',
                right: 0,
                marginTop: '8px',
                width: '280px',
                backgroundColor: 'var(--bg-card)',
                border: '1px solid var(--border-subtle)',
                borderRadius: '16px',
                boxShadow: '0 12px 36px rgba(0, 0, 0, 0.55)',
                padding: '16px',
                zIndex: 1000,
              }}
            >
              {/* Profile Card Header */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '14px' }}>
                <div
                  style={{
                    width: '44px',
                    height: '44px',
                    borderRadius: '50%',
                    backgroundColor: '#1b3a6b',
                    color: 'var(--accent-blue)',
                    border: '1px solid rgba(168, 199, 250, 0.4)',
                    fontWeight: 600,
                    fontSize: '1.1rem',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    flexShrink: 0,
                  }}
                >
                  {getInitials(user?.full_name)}
                </div>
                <div style={{ overflow: 'hidden' }}>
                  <div style={{ fontWeight: 600, color: 'var(--text-primary)', fontSize: '0.95rem', textOverflow: 'ellipsis', overflow: 'hidden', whiteSpace: 'nowrap' }}>
                    {user?.full_name || 'User'}
                  </div>
                  <div style={{ color: 'var(--text-secondary)', fontSize: '0.8rem', textOverflow: 'ellipsis', overflow: 'hidden', whiteSpace: 'nowrap' }}>
                    {user?.email || ''}
                  </div>
                </div>
              </div>

              {/* Status pill */}
              <div
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '6px',
                  backgroundColor: 'rgba(74, 222, 128, 0.1)',
                  border: '1px solid rgba(74, 222, 128, 0.25)',
                  borderRadius: '9999px',
                  padding: '3px 10px',
                  fontSize: '0.75rem',
                  color: '#4ade80',
                  marginBottom: '14px',
                }}
              >
                <span style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: '#4ade80' }}></span>
                <span>Active Session</span>
              </div>

              <div style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: '10px' }}>
                <button
                  onClick={() => {
                    setProfileOpen(false);
                    logout();
                  }}
                  style={{
                    width: '100%',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '10px',
                    padding: '10px 12px',
                    borderRadius: '10px',
                    backgroundColor: 'rgba(239, 68, 68, 0.08)',
                    border: '1px solid rgba(239, 68, 68, 0.2)',
                    color: '#f87171',
                    fontSize: '0.88rem',
                    fontWeight: 500,
                    cursor: 'pointer',
                    transition: 'background-color 0.15s ease',
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = 'rgba(239, 68, 68, 0.16)')}
                  onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'rgba(239, 68, 68, 0.08)')}
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
                    <polyline points="16 17 21 12 16 7" />
                    <line x1="21" y1="12" x2="9" y2="12" />
                  </svg>
                  <span>Sign out</span>
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
