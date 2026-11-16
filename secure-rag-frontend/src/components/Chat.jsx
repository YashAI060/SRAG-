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
      const citations = Array.isArray(response?.citations) ? response.citations : [];
      const answer = response?.answer || 'No answer generated.';

      setMessages(prev => [...prev, {
        role: 'assistant',
        content: answer,
        citeCount: citations.length
      }]);

      onNewTrace(response?.trace, citations, response?.confidence);

    } catch (err) {
      setMessages(prev => [...prev, { role: 'assistant', content: `Error: ${err.message}` }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="chat-container">
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '1.5rem', paddingBottom: '2rem' }}>
        {messages.length === 0 && (
          <div style={{ margin: 'auto', textAlign: 'center', color: 'var(--text-muted)' }}>
            <h2>Secure RAG Terminal</h2>
            <p>Upload a document and ask a question.</p>
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={`message ${msg.role}`}>
            {typeof msg.content === 'string' ? msg.content : JSON.stringify(msg.content)}
            {msg.citeCount > 0 && (
              <div style={{ marginTop: '0.8rem', fontSize: '0.75rem', color: 'var(--accent-cyan)' }}>
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

      <div className="input-area glass-card" style={{ margin: '0 2rem' }}>
        <div className="input-controls">
          <div className="toggle-group">
            <span className="telemetry-label" style={{ margin: '0 0.5rem', marginBottom: 0 }}>Mode:</span>
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

          <div className="toggle-group" style={{ marginLeft: 'auto' }}>
            <span className="telemetry-label" style={{ margin: '0 0.5rem', marginBottom: 0 }}>Decomposition (V2.3):</span>
            <button
              className={`toggle-btn ${decompose ? 'active' : ''}`}
              onClick={() => setDecompose(true)}
              style={{ color: decompose ? 'var(--accent-emerald)' : '' }}
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
            style={{ flex: 1 }}
            placeholder="Ask a question about your documents..."
            value={input}
            onChange={e => setInput(e.target.value)}
            disabled={loading}
          />
          <button type="submit" className="glass-button" style={{ width: 'auto' }} disabled={loading}>
            Send
          </button>
        </form>
      </div>
    </div>
  );
}
