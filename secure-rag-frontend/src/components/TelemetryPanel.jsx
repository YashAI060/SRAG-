import React from 'react';

export default function TelemetryPanel({ trace, citations = [], confidence = null }) {
  if (!trace) return null;

  const statusColor = 
    trace.decomposition_status === 'ACTIVE' ? 'success' :
    trace.decomposition_status === 'FALLBACK' ? 'warning' : 'error';

  const totalMs = trace.total_ms ?? trace.total_latency_ms ?? 0;
  const llmMs = trace.llm_ms ?? trace.llm_latency_ms ?? 0;
  const searchMs = trace.retrieval_latency_ms ?? (
    (trace.dense_ms || 0) + (trace.bm25_ms || 0) + (trace.rrf_ms || 0)
  );

  const subqueriesAccepted = trace.subqueries_accepted ?? trace.subquery_count ?? 0;
  const subqueriesRequested = trace.subqueries_requested ?? trace.subquery_count ?? 0;

  const validCitations = Array.isArray(citations) ? citations : [];

  return (
    <div className="telemetry-panel">
      <h3 className="auth-title" style={{fontSize: '1.2rem', marginBottom: '1.5rem'}}>RAG Trace</h3>
      
      <div className="glass-card" style={{padding: '1rem', marginBottom: '1.5rem'}}>
        {confidence && (
          <div className="telemetry-item">
            <div className="telemetry-label">Confidence Gate</div>
            <div className={`telemetry-value ${confidence.decision === 'answer' ? 'success' : 'warning'}`}>
              {(confidence.score * 100).toFixed(0)}% ({confidence.decision === 'answer' ? 'PASSED' : 'ABSTAINED'})
            </div>
          </div>
        )}
        <div className="telemetry-item">
          <div className="telemetry-label">Decomposition Status</div>
          <div className={`telemetry-value ${statusColor}`}>{trace.decomposition_status || 'N/A'}</div>
        </div>
        <div className="telemetry-item">
          <div className="telemetry-label">Subqueries Processed</div>
          <div className="telemetry-value">{subqueriesAccepted} / {subqueriesRequested}</div>
          {trace.subqueries_truncated && (
            <div style={{fontSize: '0.7rem', color: 'var(--accent-rose)', marginTop: '0.2rem'}}>
              ⚠ MAX_SUBQUERIES limit hit
            </div>
          )}
        </div>
        <div className="telemetry-item" style={{borderBottom: 'none', marginBottom: 0, paddingBottom: 0}}>
          <div className="telemetry-label">Total Latency</div>
          <div className="telemetry-value">{Number(totalMs).toFixed(1)} ms</div>
          <div style={{display: 'flex', gap: '1rem', marginTop: '0.5rem', fontSize: '0.75rem', color: 'var(--text-muted)'}}>
            <span>LLM: {Number(llmMs).toFixed(0)}ms</span>
            <span>Search: {Number(searchMs).toFixed(0)}ms</span>
          </div>
        </div>
      </div>

      <h3 className="auth-title" style={{fontSize: '1.2rem', marginBottom: '1rem'}}>
        Citations ({validCitations.length})
      </h3>
      <div style={{display: 'flex', flexDirection: 'column', gap: '0.8rem'}}>
        {validCitations.map((cite, i) => {
          const fileName = cite.source_file || cite.filename || 'Document';
          const textPreview = cite.chunk_preview || cite.text || '';
          return (
            <div key={i} className="glass-card" style={{padding: '0.8rem', fontSize: '0.85rem'}}>
              <div style={{display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem'}}>
                <span style={{color: 'var(--accent-cyan)', fontWeight: 600}}>📄 {fileName}</span>
                {cite.page_number != null && (
                  <span style={{color: 'var(--text-muted)'}}>Pg {cite.page_number}</span>
                )}
              </div>
              {textPreview && (
                <div style={{color: 'var(--text-secondary)', lineHeight: 1.4, fontStyle: 'italic'}}>
                  "{textPreview.length > 150 ? textPreview.substring(0, 150) + '...' : textPreview}"
                </div>
              )}
            </div>
          );
        })}
        {validCitations.length === 0 && (
          <div className="telemetry-value" style={{fontSize: '0.85rem'}}>No citations for this response.</div>
        )}
      </div>
    </div>
  );
}
