import { useEffect, useState } from 'react';
import { api } from '../services/api';
import { Content as ContentType, Source } from '../types';

export function Content() {
  const [contents, setContents] = useState<ContentType[]>([]);
  const [sources, setSources] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(0);
  const [selected, setSelected] = useState<ContentType | null>(null);
  const [processingId, setProcessingId] = useState<string | null>(null);
  const [processStatus, setProcessStatus] = useState<Record<string, string>>({});
  const limit = 20;

  useEffect(() => {
    loadData();
  }, [page]);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [contentData, sourceData] = await Promise.all([
        api.getContents(page * limit, limit),
        api.getSources(),
      ]);
      setContents(contentData);
      const sourceMap: Record<string, string> = {};
      (sourceData as Source[]).forEach(s => { sourceMap[s._id] = s.name; });
      setSources(sourceMap);
    } catch (err: any) {
      setError(err.message || 'Failed to load content');
    } finally {
      setLoading(false);
    }
  };

  const handleProcessItem = async (contentId: string, e?: React.MouseEvent) => {
    if (e) e.stopPropagation();
    setProcessingId(contentId);
    setProcessStatus(prev => ({ ...prev, [contentId]: 'Processing...' }));
    try {
      const res = await api.processSingleContent(contentId);
      if (res.is_opportunity) {
        setProcessStatus(prev => ({
          ...prev,
          [contentId]: `✓ Opportunity Detected (${res.type}) — ${res.status}`
        }));
      } else {
        setProcessStatus(prev => ({
          ...prev,
          [contentId]: `Not an opportunity`
        }));
      }
    } catch (err: any) {
      setProcessStatus(prev => ({
        ...prev,
        [contentId]: `Error: ${err.message || 'Processing failed'}`
      }));
    } finally {
      setProcessingId(null);
    }
  };

  const fmt = (d: string | null) => d ? new Date(d).toLocaleString() : '—';

  if (selected) {
    return (
      <div>
        <div className="header-row">
          <h1 style={{ margin: 0 }}>Content Detail</h1>
          <div style={{ display: 'flex', gap: '8px' }}>
            <button
              className="btn"
              style={{ backgroundColor: '#059669' }}
              onClick={() => handleProcessItem(selected._id)}
              disabled={processingId === selected._id}
            >
              {processingId === selected._id ? 'Processing...' : 'Process Opportunity'}
            </button>
            <button className="btn btn-secondary" onClick={() => setSelected(null)}>← Back</button>
          </div>
        </div>

        {processStatus[selected._id] && (
          <div style={{
            background: processStatus[selected._id].startsWith('✓') ? '#ecfdf5' : '#f8fafc',
            border: '1px solid #a7f3d0',
            color: processStatus[selected._id].startsWith('✓') ? '#065f46' : '#475569',
            padding: '10px 14px',
            borderRadius: '6px',
            marginBottom: '16px'
          }}>
            {processStatus[selected._id]}
          </div>
        )}

        <div className="card">
          <h2 style={{ marginTop: 0 }}>{selected.title || '(No Title)'}</h2>
          <p><strong>URL:</strong> <a href={selected.url} target="_blank" rel="noreferrer" style={{ color: '#2563eb' }}>{selected.url}</a></p>
          <p><strong>Source:</strong> {sources[selected.source_id] || selected.source_id}</p>
          <p><strong>Status:</strong> <span className="badge active">{selected.status}</span></p>
          <p><strong>First Seen:</strong> {fmt(selected.first_seen_at)}</p>
          <p><strong>Last Seen:</strong> {fmt(selected.last_seen_at)}</p>
          <p><strong>Content Hash:</strong> <code style={{ fontSize: '0.8rem', wordBreak: 'break-all' }}>{selected.content_hash}</code></p>
          <hr />
          <h3>Extracted Content</h3>
          <div style={{ background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: '6px', padding: '16px', whiteSpace: 'pre-wrap', fontSize: '0.875rem', maxHeight: '400px', overflowY: 'auto' }}>
            {selected.content || '(empty)'}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="header-row">
        <h1 style={{ margin: 0 }}>Content Collection</h1>
        <button className="btn btn-secondary" onClick={loadData} disabled={loading}>
          {loading ? 'Loading...' : 'Refresh'}
        </button>
      </div>

      <div className="card">
        {error && (
          <div style={{ color: '#991b1b', background: '#fef2f2', padding: '12px', borderRadius: '6px', marginBottom: '16px' }}>
            {error}
          </div>
        )}

        {loading && contents.length === 0 ? (
          <div style={{ padding: '40px', textAlign: 'center', color: '#64748b' }}>Loading...</div>
        ) : contents.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '48px', color: '#64748b' }}>
            <p style={{ fontSize: '1.1rem', marginBottom: '8px' }}>No content collected yet.</p>
            <p>Go to <strong>Sources</strong> and click <strong>Collect Page</strong> to fetch content.</p>
          </div>
        ) : (
          <>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.9rem' }}>
              <thead>
                <tr style={{ borderBottom: '2px solid #e2e8f0', background: '#f8fafc' }}>
                  <th style={{ padding: '12px 10px' }}>Title</th>
                  <th style={{ padding: '12px 10px' }}>Source</th>
                  <th style={{ padding: '12px 10px' }}>Status</th>
                  <th style={{ padding: '12px 10px' }}>Last Seen</th>
                  <th style={{ padding: '12px 10px', textAlign: 'right' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {contents.map(item => (
                  <tr
                    key={item._id}
                    style={{ borderBottom: '1px solid #e2e8f0', cursor: 'pointer' }}
                    onClick={() => setSelected(item)}
                    onMouseEnter={e => (e.currentTarget.style.background = '#f8fafc')}
                    onMouseLeave={e => (e.currentTarget.style.background = '')}
                  >
                    <td style={{ padding: '12px 10px', maxWidth: '280px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {item.title || '(No Title)'}
                    </td>
                    <td style={{ padding: '12px 10px' }}>
                      {sources[item.source_id] || '—'}
                    </td>
                    <td style={{ padding: '12px 10px' }}>
                      <span className="badge active">{item.status}</span>
                    </td>
                    <td style={{ padding: '12px 10px', whiteSpace: 'nowrap' }}>{fmt(item.last_seen_at)}</td>
                    <td style={{ padding: '12px 10px', textAlign: 'right' }}>
                      <button
                        className="btn btn-secondary"
                        style={{ fontSize: '0.75rem', padding: '4px 8px' }}
                        onClick={(e) => handleProcessItem(item._id, e)}
                        disabled={processingId === item._id}
                      >
                        {processingId === item._id ? 'Processing...' : 'Process Rule'}
                      </button>
                      {processStatus[item._id] && (
                        <div style={{ fontSize: '0.75rem', color: processStatus[item._id].startsWith('✓') ? '#059669' : '#64748b', marginTop: '2px' }}>
                          {processStatus[item._id]}
                        </div>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '20px' }}>
              <button
                className="btn btn-secondary"
                disabled={page === 0 || loading}
                onClick={() => setPage(p => p - 1)}
              >
                ← Previous
              </button>
              <span style={{ color: '#64748b', fontSize: '0.875rem' }}>Page {page + 1}</span>
              <button
                className="btn btn-secondary"
                disabled={contents.length < limit || loading}
                onClick={() => setPage(p => p + 1)}
              >
                Next →
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
