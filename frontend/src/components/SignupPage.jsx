import { useState } from 'react';
import { useAuth } from '../context/AuthContext';

export default function SignupPage({ onSwitchToLogin }) {
  const { register } = useAuth();
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Password requirement checks
  const hasMinLength = password.length >= 8;
  const hasLetter = /[A-Za-z]/.test(password);
  const hasNumber = /\d/.test(password);
  const passwordsMatch = password.length > 0 && password === confirmPassword;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (!fullName.trim() || !email.trim() || !password || !confirmPassword) {
      setError('Please fill in all fields.');
      return;
    }

    if (fullName.trim().length < 2) {
      setError('Full name must be at least 2 characters.');
      return;
    }

    if (!hasMinLength || !hasLetter || !hasNumber) {
      setError('Please fulfill all password requirements.');
      return;
    }

    if (!passwordsMatch) {
      setError('Passwords do not match.');
      return;
    }

    setLoading(true);
    try {
      await register(fullName.trim(), email.trim(), password, confirmPassword);
    } catch (err) {
      setError(err.message || 'Registration failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        minHeight: '100vh',
        width: '100vw',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: 'var(--bg-canvas)',
        padding: '24px 16px',
      }}
    >
      <div
        className="animate-fade-in"
        style={{
          width: '100%',
          maxWidth: '460px',
          backgroundColor: 'var(--bg-panel)',
          border: '1px solid var(--border-subtle)',
          borderRadius: '20px',
          padding: '36px 32px',
          boxShadow: '0 12px 40px rgba(0, 0, 0, 0.45)',
        }}
      >
        {/* Brand Header */}
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', marginBottom: '24px' }}>
          <div
            style={{
              width: '44px',
              height: '44px',
              borderRadius: '50%',
              background: 'linear-gradient(135deg, #1a73e8 0%, #38bdf8 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 4px 14px rgba(26, 115, 232, 0.35)',
              marginBottom: '12px',
            }}
          >
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#ffffff" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 2a10 10 0 1 0 10 10" />
              <path d="M12 6a6 6 0 1 0 6 6" />
              <path d="M12 10a2 2 0 1 0 2 2" />
            </svg>
          </div>
          <span style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--text-secondary)', letterSpacing: '0.03em' }}>
            THINKBOOK LM
          </span>
          <h1 style={{ fontSize: '1.65rem', fontWeight: 600, color: 'var(--text-primary)', marginTop: '6px', textAlign: 'center' }}>
            Create your account
          </h1>
          <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginTop: '4px', textAlign: 'center' }}>
            Start building your private AI research workspace
          </p>
        </div>

        {/* Error message alert */}
        {error && (
          <div
            style={{
              backgroundColor: 'rgba(239, 68, 68, 0.12)',
              border: '1px solid rgba(239, 68, 68, 0.3)',
              borderRadius: '10px',
              padding: '10px 14px',
              marginBottom: '18px',
              color: '#f87171',
              fontSize: '0.85rem',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
            }}
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
            <span>{error}</span>
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
          <div>
            <label
              htmlFor="signup-name"
              style={{ display: 'block', fontSize: '0.82rem', fontWeight: 500, color: 'var(--text-secondary)', marginBottom: '5px' }}
            >
              Full name
            </label>
            <input
              id="signup-name"
              type="text"
              autoComplete="name"
              required
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              placeholder="Jane Doe"
              disabled={loading}
              style={{
                width: '100%',
                padding: '10px 14px',
                borderRadius: '10px',
                backgroundColor: 'rgba(255, 255, 255, 0.04)',
                border: '1px solid rgba(255, 255, 255, 0.14)',
                color: 'var(--text-primary)',
                fontSize: '0.9rem',
                outline: 'none',
                transition: 'border-color 0.15s ease, box-shadow 0.15s ease',
              }}
              onFocus={(e) => {
                e.currentTarget.style.borderColor = 'var(--accent-blue)';
                e.currentTarget.style.boxShadow = '0 0 0 1px var(--accent-blue)';
              }}
              onBlur={(e) => {
                e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.14)';
                e.currentTarget.style.boxShadow = 'none';
              }}
            />
          </div>

          <div>
            <label
              htmlFor="signup-email"
              style={{ display: 'block', fontSize: '0.82rem', fontWeight: 500, color: 'var(--text-secondary)', marginBottom: '5px' }}
            >
              Email address
            </label>
            <input
              id="signup-email"
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="name@example.com"
              disabled={loading}
              style={{
                width: '100%',
                padding: '10px 14px',
                borderRadius: '10px',
                backgroundColor: 'rgba(255, 255, 255, 0.04)',
                border: '1px solid rgba(255, 255, 255, 0.14)',
                color: 'var(--text-primary)',
                fontSize: '0.9rem',
                outline: 'none',
                transition: 'border-color 0.15s ease, box-shadow 0.15s ease',
              }}
              onFocus={(e) => {
                e.currentTarget.style.borderColor = 'var(--accent-blue)';
                e.currentTarget.style.boxShadow = '0 0 0 1px var(--accent-blue)';
              }}
              onBlur={(e) => {
                e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.14)';
                e.currentTarget.style.boxShadow = 'none';
              }}
            />
          </div>

          <div>
            <label
              htmlFor="signup-password"
              style={{ display: 'block', fontSize: '0.82rem', fontWeight: 500, color: 'var(--text-secondary)', marginBottom: '5px' }}
            >
              Password
            </label>
            <div style={{ position: 'relative' }}>
              <input
                id="signup-password"
                type={showPassword ? 'text' : 'password'}
                autoComplete="new-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="At least 8 characters"
                disabled={loading}
                style={{
                  width: '100%',
                  padding: '10px 42px 10px 14px',
                  borderRadius: '10px',
                  backgroundColor: 'rgba(255, 255, 255, 0.04)',
                  border: '1px solid rgba(255, 255, 255, 0.14)',
                  color: 'var(--text-primary)',
                  fontSize: '0.9rem',
                  outline: 'none',
                  transition: 'border-color 0.15s ease, box-shadow 0.15s ease',
                }}
                onFocus={(e) => {
                  e.currentTarget.style.borderColor = 'var(--accent-blue)';
                  e.currentTarget.style.boxShadow = '0 0 0 1px var(--accent-blue)';
                }}
                onBlur={(e) => {
                  e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.14)';
                  e.currentTarget.style.boxShadow = 'none';
                }}
              />
              <button
                type="button"
                aria-label={showPassword ? 'Hide password' : 'Show password'}
                onClick={() => setShowPassword(!showPassword)}
                tabIndex={-1}
                style={{
                  position: 'absolute',
                  right: '10px',
                  top: '50%',
                  transform: 'translateY(-50%)',
                  background: 'transparent',
                  border: 'none',
                  color: 'var(--text-secondary)',
                  padding: '6px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  cursor: 'pointer',
                  borderRadius: '6px',
                }}
              >
                {showPassword ? (
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
                    <line x1="1" y1="1" x2="23" y2="23" />
                  </svg>
                ) : (
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                    <circle cx="12" cy="12" r="3" />
                  </svg>
                )}
              </button>
            </div>
          </div>

          <div>
            <label
              htmlFor="signup-confirm-password"
              style={{ display: 'block', fontSize: '0.82rem', fontWeight: 500, color: 'var(--text-secondary)', marginBottom: '5px' }}
            >
              Confirm password
            </label>
            <div style={{ position: 'relative' }}>
              <input
                id="signup-confirm-password"
                type={showConfirmPassword ? 'text' : 'password'}
                autoComplete="new-password"
                required
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="Re-enter your password"
                disabled={loading}
                style={{
                  width: '100%',
                  padding: '10px 42px 10px 14px',
                  borderRadius: '10px',
                  backgroundColor: 'rgba(255, 255, 255, 0.04)',
                  border: '1px solid rgba(255, 255, 255, 0.14)',
                  color: 'var(--text-primary)',
                  fontSize: '0.9rem',
                  outline: 'none',
                  transition: 'border-color 0.15s ease, box-shadow 0.15s ease',
                }}
                onFocus={(e) => {
                  e.currentTarget.style.borderColor = 'var(--accent-blue)';
                  e.currentTarget.style.boxShadow = '0 0 0 1px var(--accent-blue)';
                }}
                onBlur={(e) => {
                  e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.14)';
                  e.currentTarget.style.boxShadow = 'none';
                }}
              />
              <button
                type="button"
                aria-label={showConfirmPassword ? 'Hide password' : 'Show password'}
                onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                tabIndex={-1}
                style={{
                  position: 'absolute',
                  right: '10px',
                  top: '50%',
                  transform: 'translateY(-50%)',
                  background: 'transparent',
                  border: 'none',
                  color: 'var(--text-secondary)',
                  padding: '6px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  cursor: 'pointer',
                  borderRadius: '6px',
                }}
              >
                {showConfirmPassword ? (
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
                    <line x1="1" y1="1" x2="23" y2="23" />
                  </svg>
                ) : (
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                    <circle cx="12" cy="12" r="3" />
                  </svg>
                )}
              </button>
            </div>
          </div>

          {/* Password Requirements Feedback */}
          {password.length > 0 && (
            <div
              style={{
                backgroundColor: 'rgba(255, 255, 255, 0.03)',
                border: '1px solid rgba(255, 255, 255, 0.06)',
                borderRadius: '8px',
                padding: '8px 12px',
                fontSize: '0.78rem',
                display: 'flex',
                flexDirection: 'column',
                gap: '4px',
              }}
            >
              <div style={{ color: hasMinLength ? '#4ade80' : 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span>{hasMinLength ? '✓' : '•'}</span>
                <span>At least 8 characters</span>
              </div>
              <div style={{ color: hasLetter ? '#4ade80' : 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span>{hasLetter ? '✓' : '•'}</span>
                <span>Contains at least one letter</span>
              </div>
              <div style={{ color: hasNumber ? '#4ade80' : 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span>{hasNumber ? '✓' : '•'}</span>
                <span>Contains at least one number</span>
              </div>
              {confirmPassword.length > 0 && (
                <div style={{ color: passwordsMatch ? '#4ade80' : '#f87171', display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <span>{passwordsMatch ? '✓' : '•'}</span>
                  <span>Passwords match</span>
                </div>
              )}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            style={{
              marginTop: '8px',
              padding: '12px 16px',
              borderRadius: '10px',
              backgroundColor: 'var(--accent-blue)',
              color: '#041e49',
              fontWeight: 600,
              fontSize: '0.95rem',
              border: 'none',
              cursor: loading ? 'not-allowed' : 'pointer',
              opacity: loading ? 0.75 : 1,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '8px',
              transition: 'background-color 0.15s ease, opacity 0.15s ease',
            }}
            onMouseEnter={(e) => {
              if (!loading) e.currentTarget.style.backgroundColor = '#c2e7ff';
            }}
            onMouseLeave={(e) => {
              if (!loading) e.currentTarget.style.backgroundColor = 'var(--accent-blue)';
            }}
          >
            {loading ? (
              <>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" style={{ animation: 'spin 1s linear infinite' }}>
                  <path d="M21 12a9 9 0 1 1-6.219-8.56" />
                </svg>
                <span>Creating account...</span>
              </>
            ) : (
              <span>Create account</span>
            )}
          </button>
        </form>

        {/* Switch to Login */}
        <div style={{ marginTop: '20px', textAlign: 'center', fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
          Already have an account?{' '}
          <button
            type="button"
            onClick={onSwitchToLogin}
            style={{
              background: 'transparent',
              border: 'none',
              color: 'var(--accent-blue)',
              fontWeight: 500,
              cursor: 'pointer',
              textDecoration: 'underline',
              padding: 0,
            }}
          >
            Sign in
          </button>
        </div>
      </div>
    </div>
  );
}
