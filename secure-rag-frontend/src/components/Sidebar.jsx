import React, { useState, useEffect } from 'react';
import { client } from '../api/client';

export default function Sidebar({ onLogout }) {
  const [docs, setDocs] = useState([]);
  const [uploading, setUploading] = useState(false);

  useEffect(() => {
    fetchDocs();
  }, []);

  useEffect(() => {
    const hasProcessing = docs.some(d => d.status === 'processing');
    if (!hasProcessing) return;

    const timer = setTimeout(() => {
      fetchDocs();
    }, 3000);
    return () => clearTimeout(timer);
  }, [docs]);

  const fetchDocs = async () => {
    try {
      const data = await client.getDocuments();
      setDocs(data.documents || []);
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
              <div key={doc.document_id} className="glass-card doc-item" style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
                <span style={{overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: '170px'}}>📄 {doc.filename}</span>
                <span style={{
                  fontSize: '0.65rem',
                  padding: '0.15rem 0.4rem',
                  borderRadius: '4px',
                  background: doc.status === 'ready' ? 'rgba(16, 185, 129, 0.2)' : 'rgba(245, 158, 11, 0.2)',
                  color: doc.status === 'ready' ? 'var(--accent-emerald)' : '#f59e0b'
                }}>
                  {doc.status || 'ready'}
                </span>
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
