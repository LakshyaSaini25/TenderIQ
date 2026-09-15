import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../services/api';
import { Source, SourceCreate, OpportunityCollectSummary, RecommendedSource, SourceType, CrawlFrequency } from '../types';
import { SourceFormModal } from '../components/sources/SourceFormModal';
import { STATE_NAMES, getCitiesForState } from '../data/india_locations';

// ─── Type badge colours ────────────────────────────────────────────────────────
const TYPE_COLORS: Record<string, { bg: string; color: string }> = {
  GOVERNMENT:       { bg: '#dbeafe', color: '#1e40af' },
  TENDER_PORTAL:    { bg: '#fef9c3', color: '#854d0e' },
  COMPANY_WEBSITE:  { bg: '#dcfce7', color: '#15803d' },
  PROJECT_PORTAL:   { bg: '#ede9fe', color: '#5b21b6' },
  NEWS:             { bg: '#fee2e2', color: '#991b1b' },
  OTHER:            { bg: '#f1f5f9', color: '#475569' },
};

function TypeBadge({ type }: { type: string }) {
  const colors = TYPE_COLORS[type] ?? TYPE_COLORS.OTHER;
  return (
    <span style={{
      background: colors.bg,
      color: colors.color,
      fontSize: '0.7rem',
      fontWeight: 700,
      padding: '2px 8px',
      borderRadius: '4px',
      textTransform: 'uppercase',
      letterSpacing: '0.03em',
      whiteSpace: 'nowrap',
    }}>
      {type.replace(/_/g, ' ')}
    </span>
  );
}

// ─── Shimmer skeleton card ────────────────────────────────────────────────────
function ShimmerCard() {
  return (
    <div style={{
      background: '#f8fafc',
      border: '1px solid #e2e8f0',
      borderRadius: '10px',
      padding: '16px',
      display: 'flex',
      flexDirection: 'column',
      gap: '10px',
    }}>
      {[100, 60, 80, 40].map((w, i) => (
        <div key={i} style={{
          height: i === 0 ? '16px' : '12px',
          width: `${w}%`,
          background: 'linear-gradient(90deg, #e2e8f0 25%, #f1f5f9 50%, #e2e8f0 75%)',
          backgroundSize: '200% 100%',
          borderRadius: '4px',
          animation: 'shimmer 1.4s infinite',
        }} />
      ))}
      <style>{`@keyframes shimmer { 0%{background-position:200% 0} 100%{background-position:-200% 0} }`}</style>
    </div>
  );
}

// ─── Recommended Source Card ──────────────────────────────────────────────────
function RecommendedCard({
  rec,
  onAdd,
  added,
  adding,
}: {
  rec: RecommendedSource;
  onAdd: () => void;
  added: boolean;
  adding: boolean;
}) {
  return (
    <div style={{
      background: added ? '#f0fdf4' : '#fff',
      border: `1px solid ${added ? '#86efac' : '#e2e8f0'}`,
      borderRadius: '10px',
      padding: '16px',
      display: 'flex',
      flexDirection: 'column',
      gap: '10px',
      transition: 'all 0.2s',
      boxShadow: '0 1px 4px rgba(0,0,0,0.05)',
      position: 'relative',
    }}>
      {/* Curated badge */}
      {rec.is_curated && (
        <span style={{
          position: 'absolute',
          top: '12px',
          right: '12px',
          background: '#e0f2fe',
          color: '#0369a1',
          fontSize: '0.65rem',
          fontWeight: 700,
          padding: '2px 6px',
          borderRadius: '3px',
        }}>
          ✓ CURATED
        </span>
      )}

      {/* Header row */}
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: '10px', paddingRight: '72px' }}>
        <div style={{ flex: 1 }}>
          <div style={{ fontWeight: 700, fontSize: '0.92rem', color: '#1e293b', marginBottom: '2px' }}>
            {rec.name}
          </div>
          <a
            href={rec.url}
            target="_blank"
            rel="noreferrer"
            style={{ fontSize: '0.75rem', color: '#2563eb', textDecoration: 'none', wordBreak: 'break-all' }}
          >
            {rec.url}
          </a>
        </div>
      </div>

      {/* Type badge + relevance */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        <TypeBadge type={rec.type} />
        <span style={{ fontSize: '0.7rem', color: '#64748b' }}>
          Relevance: <strong>{rec.relevance_score}</strong>/100
        </span>
      </div>

      {/* Description */}
      <p style={{ margin: 0, fontSize: '0.82rem', color: '#475569', lineHeight: 1.5 }}>
        {rec.description}
      </p>

      {/* Tags */}
      {rec.tags.filter(Boolean).length > 0 && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
          {rec.tags.filter(Boolean).map((tag, i) => (
            <span key={i} style={{
              background: '#f1f5f9',
              color: '#64748b',
              fontSize: '0.68rem',
              padding: '2px 6px',
              borderRadius: '3px',
              border: '1px solid #e2e8f0',
            }}>
              {tag}
            </span>
          ))}
        </div>
      )}

      {/* Add button */}
      <button
        onClick={onAdd}
        disabled={added || adding}
        style={{
          background: added ? '#059669' : adding ? '#93c5fd' : '#2563eb',
          color: '#fff',
          border: 'none',
          borderRadius: '6px',
          padding: '8px 16px',
          fontSize: '0.82rem',
          fontWeight: 600,
          cursor: added || adding ? 'not-allowed' : 'pointer',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '6px',
          transition: 'background 0.2s',
        }}
      >
        {added ? '✓ Added to Active Sources' : adding ? '⏳ Adding...' : '+ Add to Active Sources'}
      </button>
    </div>
  );
}

// ─── Main Sources Component ───────────────────────────────────────────────────
export function Sources() {
  const navigate = useNavigate();

  // Existing state
  const [sources, setSources] = useState<Source[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingSource, setEditingSource] = useState<Source | null>(null);
  const [collectingTenders, setCollectingTenders] = useState<string | null>(null);
  const [tenderResult, setTenderResult] = useState<Record<string, OpportunityCollectSummary | string>>({});

  // Discovery state
  const [selectedState, setSelectedState] = useState('');
  const [selectedCity, setSelectedCity] = useState('');
  const [discovering, setDiscovering] = useState(false);
  const [recommended, setRecommended] = useState<RecommendedSource[] | null>(null);
  const [discoverError, setDiscoverError] = useState<string | null>(null);
  const [addedUrls, setAddedUrls] = useState<Set<string>>(new Set());
  const [addingUrl, setAddingUrl] = useState<string | null>(null);

  const cities = selectedState ? getCitiesForState(selectedState) : [];

  useEffect(() => {
    loadSources();
  }, []);

  // When state changes, reset city
  useEffect(() => {
    setSelectedCity('');
  }, [selectedState]);

  const loadSources = async () => {
    setLoading(true);
    try {
      const data = await api.getSources();
      setSources(data);
    } catch (error) {
      console.error('Failed to load sources', error);
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
    if (!confirm('Are you sure you want to delete this source?')) return;
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
        [sourceId]: `Error: ${err.message || 'Tender collection failed'}`,
      }));
    } finally {
      setCollectingTenders(null);
    }
  };

  // ── Discovery Handlers ───────────────────────────────────────────────────
  const handleDiscover = async () => {
    if (!selectedState) return;
    setDiscovering(true);
    setDiscoverError(null);
    setRecommended(null);
    try {
      const results = await api.discoverSources(selectedState, selectedCity || undefined);
      setRecommended(results);
    } catch (err: any) {
      setDiscoverError(err.message || 'Discovery failed. Please try again.');
    } finally {
      setDiscovering(false);
    }
  };

  const handleAddRecommended = async (rec: RecommendedSource) => {
    setAddingUrl(rec.url);
    try {
      const sourceType = Object.values(SourceType).includes(rec.type as SourceType)
        ? (rec.type as SourceType)
        : SourceType.OTHER;

      await api.createSource({
        name: rec.name,
        url: rec.url as any,
        type: sourceType,
        crawl_frequency: CrawlFrequency.WEEKLY,
        is_active: true,
      });
      setAddedUrls(prev => new Set([...prev, rec.url]));
      await loadSources();
    } catch (err: any) {
      alert(`Failed to add source: ${err.message}`);
    } finally {
      setAddingUrl(null);
    }
  };

  if (loading) return <div style={{ padding: '32px' }}>Loading sources...</div>;

  // Already-tracked URLs (to show "Already Tracked" badge)
  const trackedUrls = new Set(sources.map(s => s.url));

  return (
    <div>
      {/* ── Page Header ──────────────────────────────────────────────────────── */}
      <div className="header-row">
        <div>
          <h1 style={{ margin: 0 }}>Sources</h1>
          <p style={{ margin: '4px 0 0', color: '#64748b', fontSize: '0.9rem' }}>
            Manage tender portals. Click <strong>Collect Tenders</strong> to automatically discover and extract verified opportunities.
          </p>
        </div>
        <button className="btn" onClick={handleAddClick}>+ Add Manually</button>
      </div>

      {/* ── Location-Based Discovery Panel ───────────────────────────────────── */}
      <div className="card" style={{ marginTop: '20px', border: '1px solid #bfdbfe', background: '#f0f9ff' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '16px' }}>
          <span style={{ fontSize: '1.4rem' }}>🗺️</span>
          <div>
            <h2 style={{ margin: 0, fontSize: '1.1rem', color: '#1e40af' }}>
              Discover Sources by Location
            </h2>
            <p style={{ margin: '2px 0 0', fontSize: '0.82rem', color: '#3b82f6' }}>
              Select your State & City to find all relevant government and private tender portals in your area.
            </p>
          </div>
        </div>

        <div style={{ display: 'flex', gap: '14px', flexWrap: 'wrap', alignItems: 'flex-end' }}>
          {/* State Dropdown */}
          <div style={{ flex: '1', minWidth: '200px' }}>
            <label style={{ display: 'block', fontSize: '0.82rem', fontWeight: 600, marginBottom: '6px', color: '#1e3a8a' }}>
              State / Union Territory *
            </label>
            <select
              className="form-control"
              value={selectedState}
              onChange={e => setSelectedState(e.target.value)}
              style={{ width: '100%', borderColor: '#93c5fd' }}
            >
              <option value="">— Select State —</option>
              {STATE_NAMES.map(s => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </div>

          {/* City Dropdown */}
          <div style={{ flex: '1', minWidth: '200px' }}>
            <label style={{ display: 'block', fontSize: '0.82rem', fontWeight: 600, marginBottom: '6px', color: '#1e3a8a' }}>
              City (optional)
            </label>
            <select
              className="form-control"
              value={selectedCity}
              onChange={e => setSelectedCity(e.target.value)}
              disabled={!selectedState}
              style={{ width: '100%', borderColor: '#93c5fd', opacity: selectedState ? 1 : 0.5 }}
            >
              <option value="">All Cities</option>
              {cities.slice(1).map(c => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          </div>

          {/* Discover Button */}
          <div>
            <button
              className="btn"
              style={{
                background: discovering ? '#93c5fd' : '#2563eb',
                color: '#fff',
                minWidth: '180px',
                fontWeight: 700,
                fontSize: '0.9rem',
                padding: '10px 20px',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                cursor: !selectedState || discovering ? 'not-allowed' : 'pointer',
                opacity: !selectedState ? 0.6 : 1,
              }}
              onClick={handleDiscover}
              disabled={!selectedState || discovering}
            >
              {discovering ? (
                <><span style={{ animation: 'spin 1s linear infinite', display: 'inline-block' }}>🔍</span> Searching...</>
              ) : (
                <>🔍 Discover Sources</>
              )}
            </button>
            <style>{`@keyframes spin { from{transform:rotate(0)} to{transform:rotate(360deg)} }`}</style>
          </div>
        </div>

        {/* Helper hint */}
        {!selectedState && (
          <p style={{ margin: '12px 0 0', fontSize: '0.78rem', color: '#60a5fa' }}>
            💡 Select a state above to discover government portals, state e-procurement systems, PSU tenders, hospital procurement, construction sites and more — specific to your location.
          </p>
        )}
      </div>

      {/* ── Recommended Sources Panel ──────────────────────────────────────── */}
      {(discovering || recommended !== null || discoverError) && (
        <div style={{ marginTop: '24px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px', flexWrap: 'wrap', gap: '8px' }}>
            <div>
              <h2 style={{ margin: 0, fontSize: '1.15rem', color: '#1e293b' }}>
                📡 Recommended Sources
                {selectedState && (
                  <span style={{ marginLeft: '8px', fontSize: '0.85rem', fontWeight: 400, color: '#64748b' }}>
                    for <strong>{selectedCity && selectedCity !== 'All Cities' ? `${selectedCity}, ` : ''}{selectedState}</strong>
                  </span>
                )}
              </h2>
              {recommended && (
                <p style={{ margin: '4px 0 0', fontSize: '0.8rem', color: '#64748b' }}>
                  {recommended.length} sources found — sorted by relevance. Click <strong>"+ Add to Active Sources"</strong> to start tracking.
                </p>
              )}
            </div>
            {recommended && (
              <button
                className="btn btn-secondary"
                style={{ fontSize: '0.8rem', padding: '6px 12px' }}
                onClick={() => { setRecommended(null); setDiscoverError(null); setAddedUrls(new Set()); }}
              >
                ✕ Clear Results
              </button>
            )}
          </div>

          {/* Error state */}
          {discoverError && (
            <div style={{ background: '#fef2f2', border: '1px solid #fca5a5', color: '#991b1b', padding: '14px 18px', borderRadius: '8px', fontSize: '0.875rem' }}>
              ⚠️ {discoverError}
            </div>
          )}

          {/* Shimmer loading */}
          {discovering && (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: '14px' }}>
              {Array.from({ length: 6 }).map((_, i) => <ShimmerCard key={i} />)}
            </div>
          )}

          {/* Results grid */}
          {!discovering && recommended && recommended.length === 0 && (
            <div style={{ textAlign: 'center', padding: '40px', color: '#64748b', background: '#f8fafc', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
              <div style={{ fontSize: '2rem', marginBottom: '8px' }}>🔎</div>
              <p style={{ margin: 0 }}>No additional sources found for this location beyond the national portals.</p>
            </div>
          )}

          {!discovering && recommended && recommended.length > 0 && (
            <>
              {/* Already-tracked notice */}
              {recommended.some(r => trackedUrls.has(r.url)) && (
                <div style={{ background: '#f0fdf4', border: '1px solid #86efac', color: '#166534', padding: '10px 14px', borderRadius: '6px', marginBottom: '14px', fontSize: '0.8rem' }}>
                  ✓ Some portals below are already in your Active Sources — they're highlighted in green.
                </div>
              )}

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: '14px' }}>
                {recommended.map((rec, idx) => {
                  const alreadyTracked = trackedUrls.has(rec.url);
                  const wasAdded = addedUrls.has(rec.url) || alreadyTracked;
                  return (
                    <div key={idx} style={{ position: 'relative' }}>
                      {alreadyTracked && !addedUrls.has(rec.url) && (
                        <div style={{
                          position: 'absolute',
                          top: 0, left: 0, right: 0, bottom: 0,
                          borderRadius: '10px',
                          background: 'rgba(240,253,244,0.85)',
                          zIndex: 2,
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          backdropFilter: 'blur(1px)',
                        }}>
                          <span style={{ background: '#059669', color: '#fff', padding: '6px 14px', borderRadius: '6px', fontSize: '0.82rem', fontWeight: 700 }}>
                            ✓ Already Tracked
                          </span>
                        </div>
                      )}
                      <RecommendedCard
                        rec={rec}
                        onAdd={() => handleAddRecommended(rec)}
                        added={wasAdded}
                        adding={addingUrl === rec.url}
                      />
                    </div>
                  );
                })}
              </div>
            </>
          )}
        </div>
      )}

      {/* ── Active Sources List ────────────────────────────────────────────── */}
      <div style={{ marginTop: '28px' }}>
        <h2 style={{ fontSize: '1.1rem', color: '#1e293b', margin: '0 0 14px' }}>
          📋 Active Sources ({sources.length})
        </h2>

        <div className="card">
          {sources.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '48px 24px' }}>
              <p style={{ color: '#64748b', fontSize: '1.1rem', margin: '0 0 8px' }}>
                No sources are being tracked yet.
              </p>
              <p style={{ color: '#94a3b8', marginBottom: '24px' }}>
                Use "Discover Sources" above to find portals, or add one manually.
              </p>
              <button className="btn" onClick={handleAddClick}>+ Add Manually</button>
            </div>
          ) : (
            <div>
              {sources.map(source => {
                const res = tenderResult[source._id];
                const isCollecting = collectingTenders === source._id;

                return (
                  <div key={source._id} className="source-item">
                    <div className="source-header">
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
                        <div className="source-title">{source.name}</div>
                        <TypeBadge type={source.type} />
                      </div>
                      <div className="source-actions" style={{ gap: '8px', flexWrap: 'wrap' }}>
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
                          ? new Date(source.last_checked_at).toLocaleString('en-IN', { timeZone: 'Asia/Kolkata' })
                          : 'Never'}
                      </span>
                    </div>

                    {/* Collect result feedback */}
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
