# coding: utf-8
import os

src_dir = os.path.join("e:\\SRAG\\secure-rag-frontend", "src")
api_dir = os.path.join(src_dir, "api")
comp_dir = os.path.join(src_dir, "components")
os.makedirs(api_dir, exist_ok=True)
os.makedirs(comp_dir, exist_ok=True)

css = """
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap');

:root {
  --bg-main: #0B0F19;
  --bg-panel: rgba(20, 27, 45, 0.6);
  --bg-card: rgba(30, 41, 59, 0.8);
  
  --text-primary: #F8FAFC;
  --text-secondary: #94A3B8;
  --text-muted: #475569;
  
  --accent-cyan: #06B6D4;
  --accent-indigo: #6366F1;
  --accent-emerald: #10B981;
  --accent-rose: #F43F5E;
  
  --border-glass: rgba(255, 255, 255, 0.1);
  --border-glow: rgba(6, 182, 212, 0.3);
  
  --shadow-glow: 0 0 20px rgba(99, 102, 241, 0.15);
}

* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

body {
  font-family: 'Outfit', sans-serif;
  background-color: var(--bg-main);
  background-image: 
    radial-gradient(circle at 15% 50%, rgba(99, 102, 241, 0.08) 0%, transparent 50%),
    radial-gradient(circle at 85% 30%, rgba(6, 182, 212, 0.08) 0%, transparent 50%);
  color: var(--text-primary);
  min-height: 100vh;
  overflow: hidden;
}

/* Glassmorphism Utilities */
.glass-panel {
  background: var(--bg-panel);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border: 1px solid var(--border-glass);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
}

.glass-card {
  background: var(--bg-card);
  backdrop-filter: blur(8px);
  border: 1px solid var(--border-glass);
  border-radius: 12px;
  transition: all 0.3s ease;
}

.glass-card:hover {
  border-color: var(--border-glow);
  box-shadow: var(--shadow-glow);
  transform: translateY(-2px);
}

/* Layout */
.app-container {
  display: flex;
  height: 100vh;
  width: 100vw;
}

.sidebar {
  width: 320px;
  height: 100%;
  border-right: 1px solid var(--border-glass);
  padding: 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 2rem;
  z-index: 10;
}

.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  height: 100%;
  position: relative;
}

.chat-container {
  flex: 1;
  overflow-y: auto;
  padding: 2rem;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.telemetry-panel {
  width: 350px;
  border-left: 1px solid var(--border-glass);
  background: var(--bg-panel);
  padding: 1.5rem;
  overflow-y: auto;
}

/* Auth View */
.auth-container {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100vh;
  width: 100vw;
}

.auth-card {
  width: 400px;
  padding: 2.5rem;
  border-radius: 16px;
}

.auth-title {
  font-size: 1.8rem;
  font-weight: 600;
  margin-bottom: 0.5rem;
  background: linear-gradient(135deg, var(--text-primary), var(--text-secondary));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.auth-subtitle {
  color: var(--text-muted);
  font-size: 0.9rem;
  margin-bottom: 2rem;
}

/* Forms */
.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin-bottom: 1.5rem;
}

.form-group label {
  font-size: 0.85rem;
  color: var(--text-secondary);
  font-weight: 500;
}

.glass-input {
  background: rgba(15, 23, 42, 0.5);
  border: 1px solid var(--border-glass);
  color: var(--text-primary);
  padding: 0.75rem 1rem;
  border-radius: 8px;
  font-family: 'Outfit', sans-serif;
  font-size: 0.95rem;
  transition: all 0.2s ease;
  outline: none;
}

.glass-input:focus {
  border-color: var(--accent-cyan);
  box-shadow: 0 0 0 2px rgba(6, 182, 212, 0.2);
}

.glass-button {
  background: linear-gradient(135deg, var(--accent-indigo), var(--accent-cyan));
  color: white;
  border: none;
  padding: 0.75rem 1.5rem;
  border-radius: 8px;
  font-family: 'Outfit', sans-serif;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  width: 100%;
}

.glass-button:hover {
  opacity: 0.9;
  transform: translateY(-1px);
  box-shadow: 0 4px 15px rgba(6, 182, 212, 0.4);
}

.glass-button.secondary {
  background: transparent;
  border: 1px solid var(--border-glass);
  color: var(--text-secondary);
}

.glass-button.secondary:hover {
  border-color: var(--text-primary);
  color: var(--text-primary);
  box-shadow: none;
}

/* Chat Messages */
.message {
  max-width: 80%;
  padding: 1.25rem;
  border-radius: 12px;
  line-height: 1.5;
  animation: slideUp 0.3s ease forwards;
}

.message.user {
  align-self: flex-end;
  background: rgba(99, 102, 241, 0.15);
  border: 1px solid rgba(99, 102, 241, 0.3);
  border-bottom-right-radius: 4px;
}

.message.assistant {
  align-self: flex-start;
  background: var(--bg-card);
  border: 1px solid var(--border-glass);
  border-bottom-left-radius: 4px;
}

/* Input Area */
.input-area {
  padding: 1.5rem 2rem;
  border-top: 1px solid var(--border-glass);
  background: var(--bg-panel);
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.input-controls {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.toggle-group {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  background: rgba(15, 23, 42, 0.5);
  padding: 0.4rem;
  border-radius: 8px;
  border: 1px solid var(--border-glass);
}

.toggle-btn {
  background: transparent;
  border: none;
  color: var(--text-secondary);
  padding: 0.4rem 0.8rem;
  border-radius: 6px;
  font-family: inherit;
  font-size: 0.85rem;
  cursor: pointer;
  transition: all 0.2s;
}

.toggle-btn.active {
  background: rgba(255, 255, 255, 0.1);
  color: var(--text-primary);
  font-weight: 500;
}

.input-box {
  display: flex;
  gap: 1rem;
}

/* Telemetry styles */
.telemetry-item {
  margin-bottom: 1rem;
  padding-bottom: 1rem;
  border-bottom: 1px dashed var(--border-glass);
}

.telemetry-label {
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 1px;
  color: var(--text-muted);
  margin-bottom: 0.25rem;
}

.telemetry-value {
  font-size: 0.95rem;
  color: var(--accent-cyan);
  font-family: monospace;
}
.telemetry-value.success { color: var(--accent-emerald); }
.telemetry-value.warning { color: #F59E0B; }
.telemetry-value.error { color: var(--accent-rose); }

/* Animations */
@keyframes slideUp {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

.typing-indicator {
  display: flex;
  gap: 0.4rem;
  padding: 0.5rem 1rem;
}

.typing-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--text-secondary);
  animation: pulse 1.5s infinite;
}
.typing-dot:nth-child(2) { animation-delay: 0.2s; }
.typing-dot:nth-child(3) { animation-delay: 0.4s; }

@keyframes pulse {
  0%, 100% { transform: scale(0.8); opacity: 0.5; }
  50% { transform: scale(1.2); opacity: 1; }
}

/* Utilities */
.doc-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.doc-item {
  padding: 0.75rem;
  font-size: 0.85rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
"""

api_client = """
const API_URL = 'http://localhost:8000/api/v1';

export const client = {
  token: localStorage.getItem('srag_token'),

  setToken(token) {
    this.token = token;
    localStorage.setItem('srag_token', token);
  },

  logout() {
    this.token = null;
    localStorage.removeItem('srag_token');
  },

  async request(endpoint, options = {}) {
    const headers = {
      'Content-Type': 'application/json',
      ...options.headers,
    };

    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }
    
    // For FormData, let browser set Content-Type with boundary
    if (options.body instanceof FormData) {
      delete headers['Content-Type'];
    }

    const response = await fetch(`${API_URL}${endpoint}`, {
      ...options,
      headers,
    });

    if (!response.ok) {
      if (response.status === 401) {
        this.logout();
        window.location.reload();
      }
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || `HTTP Error ${response.status}`);
    }

    return response.json();
  },

  // Auth
  async login(username, password) {
    const formData = new URLSearchParams();
    formData.append('username', username);
    formData.append('password', password);
    
    const response = await fetch('http://localhost:8000/api/v1/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: formData
    });
    
    if (!response.ok) throw new Error('Login failed');
    const data = await response.json();
    this.setToken(data.access_token);
    return data;
  },

  async register(username, email, password) {
    return this.request('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ username, email, password, role: 'user' })
    });
  },

  // Documents
  async getDocuments() {
    return this.request('/docs/');
  },

  async uploadDocument(file) {
    const formData = new FormData();
    formData.append('file', file);
    return this.request('/docs/upload', {
      method: 'POST',
      body: formData
    });
  },

  // Chat
  async ask(query, mode = 'hybrid', decompose = true) {
    return this.request('/chat/ask', {
      method: 'POST',
      body: JSON.stringify({ query, mode, decompose })
    });
  }
};
"""

app_jsx = """
import React, { useState, useEffect } from 'react';
import { client } from './api/client';
import Auth from './components/Auth';
import Sidebar from './components/Sidebar';
import Chat from './components/Chat';
import TelemetryPanel from './components/TelemetryPanel';
import './index.css';

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(!!client.token);
  const [activeTrace, setActiveTrace] = useState(null);
  const [activeCitations, setActiveCitations] = useState([]);

  useEffect(() => {
    // Check if token is still valid (could add a /me endpoint call here)
  }, []);

  const handleLogin = () => {
    setIsAuthenticated(true);
  };

  const handleLogout = () => {
    client.logout();
    setIsAuthenticated(false);
  };

  if (!isAuthenticated) {
    return <Auth onLogin={handleLogin} />;
  }

  return (
    <div className="app-container">
      <Sidebar onLogout={handleLogout} />
      <div className="main-content">
        <Chat 
          onNewTrace={(trace, citations) => {
            setActiveTrace(trace);
            setActiveCitations(citations);
          }} 
        />
      </div>
      {(activeTrace || activeCitations.length > 0) && (
        <TelemetryPanel trace={activeTrace} citations={activeCitations} />
      )}
    </div>
  );
}

export default App;
"""

auth_jsx = """
import React, { useState } from 'react';
import { client } from '../api/client';

export default function Auth({ onLogin }) {
  const [isLogin, setIsLogin] = useState(true);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [email, setEmail] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      if (isLogin) {
        await client.login(username, password);
        onLogin();
      } else {
        await client.register(username, email, password);
        // Auto login after register
        await client.login(username, password);
        onLogin();
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-container">
      <div className="glass-panel auth-card">
        <h1 className="auth-title">Secure RAG</h1>
        <p className="auth-subtitle">
          {isLogin ? 'Sign in to access your tenant' : 'Create a new isolated tenant'}
        </p>

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Username</label>
            <input 
              type="text" 
              className="glass-input" 
              value={username}
              onChange={e => setUsername(e.target.value)}
              required
            />
          </div>

          {!isLogin && (
            <div className="form-group">
              <label>Email</label>
              <input 
                type="email" 
                className="glass-input" 
                value={email}
                onChange={e => setEmail(e.target.value)}
                required
              />
            </div>
          )}

          <div className="form-group">
            <label>Password</label>
            <input 
              type="password" 
              className="glass-input" 
              value={password}
              onChange={e => setPassword(e.target.value)}
              required
            />
          </div>

          {error && <div className="telemetry-value error" style={{marginBottom: '1rem'}}>{error}</div>}

          <button type="submit" className="glass-button" disabled={loading}>
            {loading ? 'Authenticating...' : (isLogin ? 'Sign In' : 'Create Account')}
          </button>
        </form>

        <div style={{ marginTop: '1.5rem', textAlign: 'center' }}>
          <button 
            className="toggle-btn"
            onClick={() => setIsLogin(!isLogin)}
          >
            {isLogin ? 'Need an account? Register' : 'Already have an account? Sign in'}
          </button>
        </div>
      </div>
    </div>
  );
}
"""

sidebar_jsx = """
import React, { useState, useEffect } from 'react';
import { client } from '../api/client';

export default function Sidebar({ onLogout }) {
  const [docs, setDocs] = useState([]);
  const [uploading, setUploading] = useState(false);

  useEffect(() => {
    fetchDocs();
  }, []);

  const fetchDocs = async () => {
    try {
      const data = await client.getDocuments();
      setDocs(data);
    } catch (err) {
      console.error(err);
    }
  };

  const handleUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setUploading(true);
    try {
      await client.uploadDocument(file);
      await fetchDocs();
    } catch (err) {
      alert('Upload failed: ' + err.message);
    } finally {
      setUploading(false);
      e.target.value = null;
    }
  };

  return (
    <div className="sidebar glass-panel">
      <div>
        <h2 className="auth-title" style={{fontSize: '1.5rem'}}>SRAG</h2>
        <div className="telemetry-label" style={{marginTop: '0.5rem'}}>Tenant Workpsace</div>
      </div>

      <div style={{flex: 1}}>
        <h3 className="telemetry-label" style={{marginBottom: '1rem'}}>Corpus Documents ({docs.length})</h3>
        
        <div className="doc-list">
          {docs.map(doc => (
            <div key={doc.document_id} className="glass-card doc-item">
              📄 {doc.filename}
            </div>
          ))}
          {docs.length === 0 && (
            <div className="telemetry-value">No documents uploaded.</div>
          )}
        </div>
      </div>

      <div style={{display: 'flex', flexDirection: 'column', gap: '1rem'}}>
        <div>
          <input 
            type="file" 
            id="file-upload" 
            style={{display: 'none'}} 
            accept=".pdf"
            onChange={handleUpload}
            disabled={uploading}
          />
          <label htmlFor="file-upload" className="glass-button secondary" style={{display: 'block', textAlign: 'center'}}>
            {uploading ? 'Processing...' : 'Upload PDF'}
          </label>
        </div>
        <button onClick={onLogout} className="toggle-btn" style={{width: '100%', border: '1px solid var(--border-glass)'}}>
          Logout
        </button>
      </div>
    </div>
  );
}
"""

chat_jsx = """
import React, { useState, useRef, useEffect } from 'react';
import { client } from '../api/client';

export default function Chat({ onNewTrace }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [decompose, setDecompose] = useState(true);
  const [mode, setMode] = useState('hybrid');
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const query = input.trim();
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: query }]);
    setLoading(true);

    try {
      const response = await client.ask(query, mode, decompose);
      
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        content: response.answer,
        citeCount: response.citations.length 
      }]);
      
      onNewTrace(response.trace, response.citations);
      
    } catch (err) {
      setMessages(prev => [...prev, { role: 'assistant', content: `Error: ${err.message}` }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="chat-container">
      <div style={{flex: 1, display: 'flex', flexDirection: 'column', gap: '1.5rem', paddingBottom: '2rem'}}>
        {messages.length === 0 && (
          <div style={{margin: 'auto', textAlign: 'center', color: 'var(--text-muted)'}}>
            <h2>Secure RAG Terminal</h2>
            <p>Upload a document and ask a question.</p>
          </div>
        )}
        
        {messages.map((msg, i) => (
          <div key={i} className={`message ${msg.role}`}>
            {msg.content}
            {msg.citeCount > 0 && (
              <div style={{marginTop: '0.8rem', fontSize: '0.75rem', color: 'var(--accent-cyan)'}}>
                [{msg.citeCount} citations retrieved]
              </div>
            )}
          </div>
        ))}
        
        {loading && (
          <div className="message assistant typing-indicator">
            <div className="typing-dot"></div>
            <div className="typing-dot"></div>
            <div className="typing-dot"></div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="input-area glass-card" style={{margin: '0 2rem'}}>
        <div className="input-controls">
          <div className="toggle-group">
            <span className="telemetry-label" style={{margin: '0 0.5rem', marginBottom: 0}}>Mode:</span>
            {['hybrid', 'dense', 'bm25'].map(m => (
              <button 
                key={m}
                className={`toggle-btn ${mode === m ? 'active' : ''}`}
                onClick={() => setMode(m)}
              >
                {m.toUpperCase()}
              </button>
            ))}
          </div>
          
          <div className="toggle-group" style={{marginLeft: 'auto'}}>
            <span className="telemetry-label" style={{margin: '0 0.5rem', marginBottom: 0}}>Decomposition (V2.3):</span>
            <button 
              className={`toggle-btn ${decompose ? 'active' : ''}`}
              onClick={() => setDecompose(true)}
              style={{color: decompose ? 'var(--accent-emerald)' : ''}}
            >
              ON
            </button>
            <button 
              className={`toggle-btn ${!decompose ? 'active' : ''}`}
              onClick={() => setDecompose(false)}
            >
              OFF
            </button>
          </div>
        </div>
        
        <form onSubmit={handleSubmit} className="input-box">
          <input 
            type="text" 
            className="glass-input" 
            style={{flex: 1}}
            placeholder="Ask a question about your documents..."
            value={input}
            onChange={e => setInput(e.target.value)}
            disabled={loading}
          />
          <button type="submit" className="glass-button" style={{width: 'auto'}} disabled={loading}>
            Send
          </button>
        </form>
      </div>
    </div>
  );
}
"""

telemetry_jsx = """
import React from 'react';

export default function TelemetryPanel({ trace, citations }) {
  if (!trace) return null;

  const statusColor = 
    trace.decomposition_status === 'ACTIVE' ? 'success' :
    trace.decomposition_status === 'FALLBACK' ? 'warning' : 'error';

  return (
    <div className="telemetry-panel">
      <h3 className="auth-title" style={{fontSize: '1.2rem', marginBottom: '1.5rem'}}>RAG Trace</h3>
      
      <div className="glass-card" style={{padding: '1rem', marginBottom: '1.5rem'}}>
        <div className="telemetry-item">
          <div className="telemetry-label">Decomposition Status</div>
          <div className={`telemetry-value ${statusColor}`}>{trace.decomposition_status}</div>
        </div>
        <div className="telemetry-item">
          <div className="telemetry-label">Subqueries Processed</div>
          <div className="telemetry-value">{trace.subqueries_accepted} / {trace.subqueries_requested}</div>
          {trace.subqueries_truncated && (
            <div style={{fontSize: '0.7rem', color: 'var(--accent-rose)', marginTop: '0.2rem'}}>
              ⚠ MAX_SUBQUERIES limit hit
            </div>
          )}
        </div>
        <div className="telemetry-item" style={{borderBottom: 'none', marginBottom: 0, paddingBottom: 0}}>
          <div className="telemetry-label">Total Latency</div>
          <div className="telemetry-value">{trace.total_latency_ms.toFixed(1)} ms</div>
          <div style={{display: 'flex', gap: '1rem', marginTop: '0.5rem', fontSize: '0.75rem', color: 'var(--text-muted)'}}>
            <span>LLM: {trace.llm_latency_ms.toFixed(0)}ms</span>
            <span>Search: {trace.retrieval_latency_ms.toFixed(0)}ms</span>
          </div>
        </div>
      </div>

      <h3 className="auth-title" style={{fontSize: '1.2rem', marginBottom: '1rem'}}>Citations</h3>
      <div style={{display: 'flex', flexDirection: 'column', gap: '0.8rem'}}>
        {citations.map((cite, i) => (
          <div key={i} className="glass-card" style={{padding: '0.8rem', fontSize: '0.85rem'}}>
            <div style={{display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem'}}>
              <span style={{color: 'var(--accent-cyan)', fontWeight: 600}}>📄 {cite.filename}</span>
              <span style={{color: 'var(--text-muted)'}}>Pg {cite.page_number}</span>
            </div>
            <div style={{color: 'var(--text-secondary)', lineHeight: 1.4, fontStyle: 'italic'}}>
              "{cite.text.substring(0, 150)}{cite.text.length > 150 ? '...' : ''}"
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
"""

main_jsx = """
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
"""

files = {
    os.path.join(src_dir, "index.css"): css,
    os.path.join(src_dir, "App.jsx"): app_jsx,
    os.path.join(src_dir, "main.jsx"): main_jsx,
    os.path.join(api_dir, "client.js"): api_client,
    os.path.join(comp_dir, "Auth.jsx"): auth_jsx,
    os.path.join(comp_dir, "Sidebar.jsx"): sidebar_jsx,
    os.path.join(comp_dir, "Chat.jsx"): chat_jsx,
    os.path.join(comp_dir, "TelemetryPanel.jsx"): telemetry_jsx,
}

for path, content in files.items():
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content.strip() + "\n")
    print(f"Generated {path}")

