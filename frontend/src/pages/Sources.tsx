import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../services/api';
import { Source, SourceCreate, OpportunityCollectSummary } from '../types';
import { SourceFormModal } from '../components/sources/SourceFormModal';

export function Sources() {
  const navigate = useNavigate();
  const [sources, setSources] = useState<Source[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingSource, setEditingSource] = useState<Source | null>(null);
  const [collectingTenders, setCollectingTenders] = useState<string | null>(null);
  const [tenderResult, setTenderResult] = useState<Record<string, OpportunityCollectSummary | string>>({});

  useEffect(() => {
    loadSources();
  }, []);

  const loadSources = async () => {
    setLoading(true);
    try {
      const data = await api.getSources();
      setSources(data);
    } catch (error) {
      console.error('Failed to load sources', error);
      alert('Failed to load sources');
    } finally {
      setLoading(false);
    }
  };

  const handleAddClick = () => {
    setEditingSource(null);
    setShowModal(true);
  };

  const handleEditClick = (source: Source) => {
    setEditingSource(source);
    setShowModal(true);
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Are you sure you want to delete this website?')) return;
    try {
      await api.deleteSource(id);
      await loadSources();
    } catch (_e) {
      alert('Failed to delete source');
    }
  };

  const handleToggleActive = async (source: Source) => {
    try {
      await api.updateSource(source._id, { is_active: !source.is_active });
      await loadSources();
    } catch (_e) {
      alert('Failed to update source');
    }
  };

  const handleSave = async (data: SourceCreate) => {
    if (editingSource) {
      await api.updateSource(editingSource._id, data);
    } else {
      await api.createSource(data);
    }
    setShowModal(false);
    await loadSources();
  };

  const handleCollectTenders = async (sourceId: string) => {
    setCollectingTenders(sourceId);
    setTenderResult(prev => ({ ...prev, [sourceId]: '' }));
    try {
      const summary: OpportunityCollectSummary = await api.collectOpportunities(sourceId);
      setTenderResult(prev => ({ ...prev, [sourceId]: summary }));
      await loadSources();
    } catch (err: any) {
      setTenderResult(prev => ({
        ...prev,
        [sourceId]: `Error: ${err.message || 'Tender collection failed'}`
      }));
    } finally {
      setCollectingTenders(null);
    }
  };

  if (loading) return <div style={{ padding: '32px' }}>Loading sources...</div>;

  return (
    <div>
      <div className="header-row">
        <div>
          <h1 style={{ margin: 0 }}>Sources</h1>
          <p style={{ margin: '4px 0 0', color: '#64748b', fontSize: '0.9rem' }}>
            Manage tender portals. Click <strong>Collect Tenders</strong> to automatically discover and extract verified opportunities.
          </p>
        </div>
        <button className="btn" onClick={handleAddClick}>+ Add Website</button>
      </div>

      <div className="card">
        {sources.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '48px 24px' }}>
            <p style={{ color: '#64748b', fontSize: '1.1rem', margin: '0 0 8px' }}>
              No websites are being tracked yet.
            </p>
            <p style={{ color: '#94a3b8', marginBottom: '24px' }}>
              Add your first website to start monitoring it.
            </p>
            <button className="btn" onClick={handleAddClick}>+ Add Website</button>
          </div>
        ) : (
          <div>
            {sources.map(source => {
              const res = tenderResult[source._id];
              const isCollecting = collectingTenders === source._id;

              return (
                <div key={source._id} className="source-item">
                  <div className="source-header">
                    <div className="source-title">{source.name}</div>
                    <div className="source-actions" style={{ gap: '8px', flexWrap: 'wrap' }}>
                      {/* One simplified primary action button */}
                      <button
                        className="btn"
                        style={{
                          backgroundColor: isCollecting ? '#9333ea' : '#059669',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '6px',
                          fontWeight: 600,
                        }}
                        onClick={() => handleCollectTenders(source._id)}
                        disabled={isCollecting || !source.is_active}
                        title={!source.is_active ? 'Source must be active to collect' : ''}
                      >
                        {isCollecting ? '⏳ Extracting Tenders…' : '📥 Collect Tenders'}
                      </button>

                      <button className="btn btn-secondary" onClick={() => handleEditClick(source)}>
                        Edit
                      </button>
                      <button
                        className="btn btn-secondary"
                        onClick={() => handleToggleActive(source)}
                      >
                        {source.is_active ? 'Disable' : 'Enable'}
                      </button>
                      <button
                        className="btn btn-danger"
                        onClick={() => handleDelete(source._id)}
                      >
                        Delete
                      </button>
                    </div>
                  </div>

                  <div className="source-url">
                    <a href={source.url} target="_blank" rel="noreferrer" style={{ color: '#2563eb' }}>
                      {source.url}
                    </a>
                  </div>

                  <div className="source-meta">
                    <span><strong>Type:</strong> {source.type.replace(/_/g, ' ')}</span>
                    <span>
                      <strong>Status:</strong>{' '}
                      <span className={`badge ${source.is_active ? 'active' : 'inactive'}`}>
                        {source.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </span>
                    <span><strong>Frequency:</strong> {source.crawl_frequency.replace(/_/g, ' ')}</span>
                    <span>
                      <strong>Last Checked:</strong>{' '}
                      {source.last_checked_at
                        ? new Date(source.last_checked_at).toLocaleString()
                        : 'Never'}
                    </span>
                  </div>

                  {/* Scraper Adapter Collect Tenders Feedback */}
                  {res && (
                    <div
                      style={{
                        marginTop: '12px',
                        fontSize: '0.875rem',
                        padding: '12px 16px',
                        borderRadius: '6px',
                        color: typeof res === 'string' && res.startsWith('Error') ? '#991b1b' : '#065f46',
                        background: typeof res === 'string' && res.startsWith('Error') ? '#fef2f2' : '#ecfdf5',
                        border: '1px solid ' + (typeof res === 'string' && res.startsWith('Error') ? '#fca5a5' : '#a7f3d0'),
                      }}
                    >
                      {typeof res === 'string' ? (
                        res
                      ) : (
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
                          <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap' }}>
                            <span><strong>✓ Discovered:</strong> {res.discovered}</span>
                            <span><strong>Created:</strong> {res.created}</span>
                            <span><strong>Updated:</strong> {res.updated}</span>
                            <span><strong>Unchanged:</strong> {res.unchanged}</span>
                            {res.failed > 0 && <span><strong>Failed:</strong> {res.failed}</span>}
                          </div>
                          <button
                            className="btn btn-secondary"
                            style={{ fontSize: '0.8rem', padding: '4px 10px' }}
                            onClick={() => navigate('/opportunities')}
                          >
                            View Opportunities →
                          </button>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {showModal && (
        <SourceFormModal
          source={editingSource}
          onClose={() => setShowModal(false)}
          onSave={handleSave}
        />
      )}
    </div>
  );
}
