import React from 'react';

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('UI Runtime Error:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          height: '100vh',
          padding: '2rem',
          color: '#f8fafc',
          background: '#090d16',
          fontFamily: 'Inter, sans-serif'
        }}>
          <h2 style={{ color: '#f43f5e', marginBottom: '1rem' }}>Something went wrong</h2>
          <p style={{ color: '#94a3b8', marginBottom: '1.5rem', maxWidth: '600px', textAlign: 'center' }}>
            {this.state.error?.message || 'An unexpected rendering error occurred.'}
          </p>
          <button 
            onClick={() => {
              this.setState({ hasError: false, error: null });
              window.location.reload();
            }}
            className="glass-button"
            style={{ padding: '0.6rem 1.2rem', cursor: 'pointer' }}
          >
            Reload Application
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
