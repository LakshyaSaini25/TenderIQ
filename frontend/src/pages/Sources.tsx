import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../services/api';
import { Source, SourceCreate, OpportunityCollectSummary, RecommendedSource, SourceType, CrawlFrequency } from '../types';
import { SourceFormModal } from '../components/sources/SourceFormModal';

// ─── Type Badge Colors ─────────────────────────────────────────────────────────
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
      padding: '18px',
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

      <div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px', paddingRight: '70px' }}>
          <TypeBadge type={rec.type} />
        </div>
        <h4 style={{ margin: '4px 0 2px 0', fontSize: '0.95rem', fontWeight: 600, color: '#1e293b' }}>
          {rec.name}
        </h4>
        <a
          href={rec.url}
          target="_blank"
          rel="noreferrer"
          style={{ fontSize: '0.75rem', color: '#2563eb', wordBreak: 'break-all', textDecoration: 'none' }}
        >
          {rec.url}
        </a>
      </div>

      <p style={{ margin: 0, fontSize: '0.8rem', color: '#64748b', lineHeight: 1.4, flex: 1 }}>
        {rec.description}
      </p>

      {/* Tags */}
      {rec.tags && rec.tags.length > 0 && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
          {rec.tags.filter(Boolean).slice(0, 4).map((t, idx) => (
            <span key={idx} style={{
              background: '#f1f5f9',
              color: '#475569',
              fontSize: '0.68rem',
              padding: '2px 6px',
              borderRadius: '3px',
            }}>
              #{t}
            </span>
          ))}
        </div>
      )}

      {/* Action Button */}
      <button
        className="btn"
        style={{
          width: '100%',
          marginTop: '4px',
          background: added ? '#059669' : '#2563eb',
          color: '#fff',
          fontSize: '0.8rem',
          fontWeight: 600,
          cursor: added || adding ? 'default' : 'pointer',
          padding: '7px 12px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '6px',
        }}
        onClick={() => !added && !adding && onAdd()}
        disabled={added || adding}
      >
        {adding ? (
          <>⏳ Adding...</>
        ) : added ? (
          <>✓ Actively Tracked</>
        ) : (
          <>+ Add to Active Sources</>
        )}
      </button>
    </div>
  );
}

// ─── Main Sources Component ───────────────────────────────────────────────────
export function Sources() {
  const navigate = useNavigate();
  const [sources, setSources] = useState<Source[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingSource, setEditingSource] = useState<Source | null>(null);

  // Per-source tender collection state
  const [collectingTenders, setCollectingTenders] = useState<string | null>(null);
  const [tenderResult, setTenderResult] = useState<Record<string, OpportunityCollectSummary | string>>({});

  // Curated Recommended Sources
  const [curatedSources, setCuratedSources] = useState<RecommendedSource[]>([]);
  const [loadingCurated, setLoadingCurated] = useState(false);
  const [curatedSearch, setCuratedSearch] = useState('');
  const [selectedCuratedCategory, setSelectedCuratedCategory] = useState('All');
  const [addingUrl, setAddingUrl] = useState<string | null>(null);
  const [addedUrls, setAddedUrls] = useState<Set<string>>(new Set());

  // Automated Crawler Scheduler Status
  const [schedulerStatus, setSchedulerStatus] = useState<any>(null);
  const [runningCheckNow, setRunningCheckNow] = useState(false);
  const [schedulerNotice, setSchedulerNotice] = useState<string | null>(null);

  // Set of tracked URLs
  const trackedUrls = new Set(sources.map(s => s.url.replace(/\/$/, '')));

  useEffect(() => {
    loadSources();
    loadCuratedSources();
    loadSchedulerStatus();
  }, []);

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

  const loadCuratedSources = async (category = 'All', search = '') => {
    setLoadingCurated(true);
    try {
      const data = await api.getCuratedSources(category, search);
      setCuratedSources(data || []);
    } catch (err) {
      console.error('Failed to load curated sources', err);
    } finally {
      setLoadingCurated(false);
    }
  };

  const loadSchedulerStatus = async () => {
    try {
      const status = await api.getSchedulerStatus();
      setSchedulerStatus(status);
    } catch (err) {
      console.warn('Could not fetch scheduler status', err);
    }
  };

  const handleRunCheckNow = async () => {
    setRunningCheckNow(true);
    setSchedulerNotice(null);
    try {
      const res = await api.triggerSchedulerNow();
      setSchedulerNotice(res.message);
      await loadSchedulerStatus();
      await loadSources();
      setTimeout(() => setSchedulerNotice(null), 5000);
    } catch (err: any) {
      setSchedulerNotice(`Scheduler trigger failed: ${err.message}`);
    } finally {
      setRunningCheckNow(false);
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
      await loadSchedulerStatus();
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
    await loadSchedulerStatus();
  };

  const handleCollectTenders = async (sourceId: string) => {
    setCollectingTenders(sourceId);
    setTenderResult(prev => ({ ...prev, [sourceId]: '' }));
    try {
      const summary: OpportunityCollectSummary = await api.collectOpportunities(sourceId);
      setTenderResult(prev => ({ ...prev, [sourceId]: summary }));
      await loadSources();
      await loadSchedulerStatus();
    } catch (err: any) {
      setTenderResult(prev => ({
        ...prev,
        [sourceId]: `Error: ${err.message || 'Tender collection failed'}`,
      }));
    } finally {
      setCollectingTenders(null);
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
      await loadSchedulerStatus();
    } catch (err: any) {
      alert(`Failed to add source: ${err.message}`);
    } finally {
      setAddingUrl(null);
    }
  };

  const handleCuratedFilterChange = (cat: string) => {
    setSelectedCuratedCategory(cat);
    loadCuratedSources(cat, curatedSearch);
  };

  const handleCuratedSearchChange = (val: string) => {
    setCuratedSearch(val);
    loadCuratedSources(selectedCuratedCategory, val);
  };

  const CATEGORY_TABS = [
    'All',
    'Government',
    'PSU',
    'Railways',
    'Power',
    'Healthcare'
  ];

  if (loading && sources.length === 0) {
    return <div style={{ padding: '32px' }}>Loading sources...</div>;
  }

  return (
    <div style={{ maxWidth: '1400px', margin: '0 auto' }}>
      {/* ── Page Header ──────────────────────────────────────────────────────── */}
      <div className="header-row" style={{ marginBottom: '20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
        <div>
          <h1 style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span>📡 Tracked Sources</span>
          </h1>
          <p style={{ margin: '4px 0 0', color: '#64748b', fontSize: '0.9rem' }}>
            Manage active procurement portals and discover recommended sources for automated crawling.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
          <button
            className="btn btn-secondary"
            onClick={() => {
              loadSources();
              loadSchedulerStatus();
            }}
            style={{ fontSize: '0.85rem' }}
          >
            🔄 Refresh
          </button>
          <button className="btn btn-primary" onClick={handleAddClick}>
            + Add Source
          </button>
        </div>
      </div>

      {/* ── Automated Crawl Scheduler Banner ─────────────────────────────────── */}
      <div className="card" style={{
        background: '#f8fafc',
        border: '1px solid #cbd5e1',
        borderRadius: '10px',
        padding: '14px 20px',
        marginBottom: '24px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: '12px'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{
            width: '10px',
            height: '10px',
            borderRadius: '50%',
            background: schedulerStatus?.scheduler_running ? '#10b981' : '#f59e0b',
            boxShadow: schedulerStatus?.scheduler_running ? '0 0 8px #10b981' : 'none'
          }} />
          <div>
            <div style={{ fontSize: '0.9rem', fontWeight: 600, color: '#1e293b' }}>
              Automated Background Crawler: {schedulerStatus?.scheduler_running ? 'Active & Running' : 'Enabled'}
            </div>
            <div style={{ fontSize: '0.78rem', color: '#64748b' }}>
              Continuously crawls active sources based on their defined frequency (Hourly, 6-Hours, Daily, Weekly).
              {schedulerStatus?.last_check_at && (
                <> · Last system check: {new Date(schedulerStatus.last_check_at).toLocaleTimeString('en-IN')}</>
              )}
            </div>
          </div>
        </div>

        <button
          className="btn btn-secondary"
          style={{ fontSize: '0.8rem', padding: '6px 14px', background: '#fff' }}
          onClick={handleRunCheckNow}
          disabled={runningCheckNow}
        >
          {runningCheckNow ? '⏳ Checking Due Sources...' : '⚡ Check & Crawl Due Sources Now'}
        </button>
      </div>

      {schedulerNotice && (
        <div style={{ background: '#f0fdf4', border: '1px solid #86efac', color: '#166534', padding: '10px 16px', borderRadius: '8px', marginBottom: '16px', fontSize: '0.85rem' }}>
          {schedulerNotice}
        </div>
      )}

      {/* ── Section 1: Actively Tracked Sources ──────────────────────────────── */}
      <div style={{ marginBottom: '40px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <h2 style={{ margin: 0, fontSize: '1.15rem', color: '#1e293b', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span>📋 Active Sources</span>
            <span style={{ fontSize: '0.8rem', background: '#e2e8f0', color: '#475569', padding: '2px 8px', borderRadius: '12px', fontWeight: 700 }}>
              {sources.length}
            </span>
          </h2>
        </div>

        {sources.length === 0 ? (
          <div className="card" style={{ textAlign: 'center', padding: '40px 20px', color: '#64748b' }}>
            <p>No active sources yet. Add a custom portal above or pick from the Curated Recommended Sources below!</p>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {sources.map(source => {
              const res = tenderResult[source._id];
              const isCollecting = collectingTenders === source._id;

              return (
                <div
                  key={source._id}
                  className="card"
                  style={{
                    padding: '16px 20px',
                    borderRadius: '10px',
                    border: '1px solid #e2e8f0',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '12px'
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '12px' }}>
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '4px', flexWrap: 'wrap' }}>
                        <span style={{ fontWeight: 700, fontSize: '1rem', color: '#0f172a' }}>
                          {source.name}
                        </span>
                        <TypeBadge type={source.type} />
                        <span style={{
                          fontSize: '0.72rem',
                          fontWeight: 600,
                          padding: '2px 8px',
                          borderRadius: '4px',
                          background: source.is_active ? '#dcfce7' : '#fee2e2',
                          color: source.is_active ? '#166534' : '#991b1b',
                        }}>
                          {source.is_active ? 'Active' : 'Disabled'}
                        </span>
                        <span style={{
                          fontSize: '0.72rem',
                          fontWeight: 600,
                          padding: '2px 8px',
                          borderRadius: '4px',
                          background: '#f1f5f9',
                          color: '#475569',
                        }}>
                          ⏱ {source.crawl_frequency}
                        </span>
                      </div>

                      <a
                        href={source.url}
                        target="_blank"
                        rel="noreferrer"
                        style={{ fontSize: '0.8rem', color: '#2563eb', textDecoration: 'none', wordBreak: 'break-all' }}
                      >
                        {source.url}
                      </a>
                    </div>

                    <div style={{ display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
                      <button
                        className="btn"
                        style={{
                          background: '#059669',
                          color: '#fff',
                          fontSize: '0.8rem',
                          padding: '6px 14px',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '6px',
                          cursor: isCollecting ? 'not-allowed' : 'pointer',
                        }}
                        onClick={() => handleCollectTenders(source._id)}
                        disabled={isCollecting || !source.is_active}
                      >
                        {isCollecting ? '⏳ Fetching...' : '📥 Collect Tenders'}
                      </button>

                      <button
                        className="btn btn-secondary"
                        style={{ fontSize: '0.8rem', padding: '6px 12px' }}
                        onClick={() => handleEditClick(source)}
                      >
                        ✏️ Edit
                      </button>

                      <button
                        className="btn btn-secondary"
                        style={{ fontSize: '0.8rem', padding: '6px 12px' }}
                        onClick={() => handleToggleActive(source)}
                      >
                        {source.is_active ? '⏸ Disable' : '▶ Enable'}
                      </button>

                      <button
                        className="btn btn-secondary"
                        style={{ fontSize: '0.8rem', padding: '6px 12px', color: '#dc2626' }}
                        onClick={() => handleDelete(source._id)}
                      >
                        🗑 Delete
                      </button>
                    </div>
                  </div>

                  {/* Metadata Row */}
                  <div style={{ display: 'flex', gap: '20px', fontSize: '0.78rem', color: '#64748b', borderTop: '1px solid #f1f5f9', paddingTop: '8px', flexWrap: 'wrap' }}>
                    <span>
                      <strong>Last Crawled:</strong>{' '}
                      {source.last_checked_at
                        ? new Date(source.last_checked_at).toLocaleString('en-IN', {
                            timeZone: 'Asia/Kolkata',
                            dateStyle: 'medium',
                            timeStyle: 'medium',
                          })
                        : 'Never'}
                    </span>
                    <span>
                      <strong>Scheduled Crawl:</strong> Runs automatically every {source.crawl_frequency.toLowerCase().replace(/_/g, ' ')}
                    </span>
                  </div>

                  {/* Result Banner after collection */}
                  {res && (
                    <div style={{
                      marginTop: '4px',
                      padding: '10px 14px',
                      borderRadius: '6px',
                      fontSize: '0.82rem',
                      background: typeof res === 'string' && res.startsWith('Error') ? '#fef2f2' : '#f0fdf4',
                      color: typeof res === 'string' && res.startsWith('Error') ? '#991b1b' : '#166534',
                      border: `1px solid ${typeof res === 'string' && res.startsWith('Error') ? '#fca5a5' : '#86efac'}`,
                    }}>
                      {typeof res === 'string' ? (
                        res
                      ) : (
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px' }}>
                          <span>
                            ✓ Collection Complete: Discovered {res.discovered} tenders ({res.created} new, {res.updated} updated, {res.unchanged} unchanged).
                          </span>
                          <button
                            className="btn btn-secondary"
                            style={{ fontSize: '0.75rem', padding: '3px 8px' }}
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

      {/* ── Section 2: Curated Recommended Sources ──────────────────────────── */}
      <div>
        <div style={{ marginBottom: '16px' }}>
          <h2 style={{ margin: '0 0 4px 0', fontSize: '1.15rem', color: '#1e293b', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span>🌟 Curated Recommended Sources</span>
            <span style={{ fontSize: '0.8rem', background: '#dbeafe', color: '#1e40af', padding: '2px 8px', borderRadius: '12px', fontWeight: 700 }}>
              {curatedSources.length} Portals
            </span>
          </h2>
          <p style={{ margin: 0, color: '#64748b', fontSize: '0.85rem' }}>
            Verified government e-procurement portals, PSUs, and sector tender authorities ready to track with one click.
          </p>
        </div>

        {/* Filter and Search Bar */}
        <div className="card" style={{ padding: '14px 18px', marginBottom: '20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
          {/* Category Tabs */}
          <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
            {CATEGORY_TABS.map(tab => (
              <button
                key={tab}
                type="button"
                onClick={() => handleCuratedFilterChange(tab)}
                style={{
                  background: selectedCuratedCategory === tab ? '#2563eb' : '#f1f5f9',
                  color: selectedCuratedCategory === tab ? '#fff' : '#475569',
                  border: 'none',
                  borderRadius: '6px',
                  padding: '5px 12px',
                  fontSize: '0.8rem',
                  fontWeight: 600,
                  cursor: 'pointer',
                  transition: 'all 0.15s ease'
                }}
              >
                {tab}
              </button>
            ))}
          </div>

          {/* Search Input */}
          <div style={{ minWidth: '240px' }}>
            <input
              type="text"
              className="form-control"
              placeholder="Search portals (e.g. NTPC, AIIMS, Railway, UP...)"
              value={curatedSearch}
              onChange={(e) => handleCuratedSearchChange(e.target.value)}
              style={{ fontSize: '0.82rem', padding: '6px 12px', width: '100%' }}
            />
          </div>
        </div>

        {/* Curated Portals Grid */}
        {loadingCurated ? (
          <div style={{ padding: '30px', textAlign: 'center', color: '#64748b' }}>
            Loading recommended portals...
          </div>
        ) : curatedSources.length === 0 ? (
          <div className="card" style={{ padding: '30px', textAlign: 'center', color: '#64748b' }}>
            No portals matched your search criteria.
          </div>
        ) : (
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))',
            gap: '16px',
          }}>
            {curatedSources.map((rec, idx) => {
              const cleanUrl = rec.url.replace(/\/$/, '');
              const isAdded = trackedUrls.has(cleanUrl) || addedUrls.has(rec.url);
              const isAdding = addingUrl === rec.url;

              return (
                <RecommendedCard
                  key={idx}
                  rec={rec}
                  onAdd={() => handleAddRecommended(rec)}
                  added={isAdded}
                  adding={isAdding}
                />
              );
            })}
          </div>
        )}
      </div>

      {/* Modal for adding/editing a source manually */}
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
