import { useState, useEffect, useCallback } from 'react';
import { api } from '../services/api';
import { ScrapedTender, ScraperStats } from '../types';

function formatIndianCurrency(val?: number | null): string {
  if (val === undefined || val === null || isNaN(val) || val === 0) return 'Not Specified';
  if (val >= 10000000) {
    return `₹ ${(val / 10000000).toLocaleString('en-IN', { maximumFractionDigits: 2 })} Cr`;
  }
  if (val >= 100000) {
    return `₹ ${(val / 100000).toLocaleString('en-IN', { maximumFractionDigits: 2 })} Lakhs`;
  }
  return `₹ ${val.toLocaleString('en-IN')}`;
}

function formatDate(dateStr?: string | null): string {
  if (!dateStr) return 'N/A';
  try {
    const d = new Date(dateStr);
    return d.toLocaleDateString('en-IN', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  } catch {
    return dateStr;
  }
}

const CATEGORY_OPTIONS = [
  'ALL',
  'Works',
  'Goods',
  'Services',
  'Civil Works',
  'Electrical',
  'Mechanical',
  'Information Technology',
  'Security & CCTV',
  'Medical / Hospital'
];

export function TenderScraper() {
  // Scraped tenders data
  const [tenders, setTenders] = useState<ScrapedTender[]>([]);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState<ScraperStats | null>(null);

  // Filter state
  const [keyword, setKeyword] = useState('');
  const [source, setSource] = useState('ALL');
  const [status, setStatus] = useState('ALL');
  const [category, setCategory] = useState('ALL');
  const [state, setState] = useState('');
  const [minValue, setMinValue] = useState<string>('');
  const [maxValue, setMaxValue] = useState<string>('');
  const [sortBy, setSortBy] = useState('closing_date');
  const [page, setPage] = useState(1);
  const [limit] = useState(15);

  // Selected tender modal
  const [selectedTender, setSelectedTender] = useState<ScrapedTender | null>(null);

  // Scraper run trigger state
  const [runningScraper, setRunningScraper] = useState(false);
  const [scrapeMessage, setScrapeMessage] = useState<string | null>(null);

  // Fetch Stats
  const loadStats = useCallback(async () => {
    try {
      const s = await api.getScraperStats();
      setStats(s);
    } catch (e) {
      console.error('Failed to load scraper stats', e);
    }
  }, []);

  // Fetch Tenders
  const loadTenders = useCallback(async (targetPage = page) => {
    setLoading(true);
    try {
      const params: Record<string, any> = {
        page: targetPage,
        limit,
        sort_by: sortBy,
        sort_order: sortBy === 'closing_date' ? 1 : -1,
      };

      if (keyword.trim()) params.keyword = keyword.trim();
      if (source !== 'ALL') params.source = source;
      if (status !== 'ALL') params.status = status;
      if (category !== 'ALL') params.category = category;
      if (state.trim()) params.state = state.trim();
      if (minValue) params.min_value = parseFloat(minValue);
      if (maxValue) params.max_value = parseFloat(maxValue);

      const res = await api.getScrapedTenders(params);
      setTenders(res.items);
      setTotal(res.total);
      setTotalPages(res.total_pages);
    } catch (err: any) {
      console.error('Error fetching scraped tenders', err);
    } finally {
      setLoading(false);
    }
  }, [page, limit, sortBy, keyword, source, status, category, state, minValue, maxValue]);

  useEffect(() => {
    loadStats();
    loadTenders(1);
  }, []);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    loadTenders(1);
  };

  const handleClearFilters = () => {
    setKeyword('');
    setSource('ALL');
    setStatus('ALL');
    setCategory('ALL');
    setState('');
    setMinValue('');
    setMaxValue('');
    setSortBy('closing_date');
    setPage(1);
    setTimeout(() => loadTenders(1), 50);
  };

  const handleTriggerScraper = async (scraperSource = 'CPPP') => {
    setRunningScraper(true);
    setScrapeMessage(`Initiating ${scraperSource} Scraper background worker...`);
    try {
      await api.triggerScraper(scraperSource, 1, true);
      setScrapeMessage(`✅ ${scraperSource} scraper running! Fetching active tenders & solving CAPTCHAs in background...`);
      
      // Poll stats and list after 4s
      setTimeout(() => {
        loadStats();
        loadTenders(1);
        setRunningScraper(false);
      }, 4000);
    } catch (err: any) {
      setScrapeMessage(`❌ Failed to start scraper: ${err.message}`);
      setRunningScraper(false);
    }
  };

  return (
    <div style={{ padding: '24px', maxWidth: '1440px', margin: '0 auto', color: '#1e293b' }}>
      {/* ── Header ── */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '20px', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <h1 style={{ fontSize: '1.75rem', fontWeight: 700, margin: 0 }}>Tender Scraper Platform</h1>
            <span style={{ background: '#10b981', color: '#fff', fontSize: '0.75rem', padding: '3px 8px', borderRadius: '12px', fontWeight: 600 }}>
              Direct DB
            </span>
          </div>
          <p style={{ margin: '6px 0 0', color: '#64748b', fontSize: '0.9rem' }}>
            Normalized, deduplicated tender intelligence collected directly by your scrapers from government portals.
          </p>
        </div>

        {/* Action Buttons */}
        <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
          <button
            onClick={() => { loadStats(); loadTenders(page); }}
            style={{
              padding: '8px 14px',
              border: '1px solid #cbd5e1',
              borderRadius: '6px',
              background: '#fff',
              cursor: 'pointer',
              fontWeight: 500,
              fontSize: '0.85rem'
            }}
          >
            🔄 Refresh
          </button>

          <button
            onClick={() => handleTriggerScraper('CPPP')}
            disabled={runningScraper}
            style={{
              padding: '8px 16px',
              background: runningScraper ? '#94a3b8' : '#2563eb',
              color: '#fff',
              border: 'none',
              borderRadius: '6px',
              cursor: runningScraper ? 'not-allowed' : 'pointer',
              fontWeight: 600,
              fontSize: '0.85rem',
              display: 'flex',
              alignItems: 'center',
              gap: '6px'
            }}
          >
            {runningScraper ? '⏳ Scraping CPPP...' : '⚡ Run CPPP Scraper'}
          </button>
        </div>
      </div>

      {/* Scraper Status Notification */}
      {scrapeMessage && (
        <div style={{
          background: scrapeMessage.startsWith('❌') ? '#fef2f2' : '#f0fdf4',
          color: scrapeMessage.startsWith('❌') ? '#991b1b' : '#166534',
          padding: '12px 16px',
          borderRadius: '8px',
          border: '1px solid currentColor',
          marginBottom: '20px',
          fontSize: '0.875rem',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}>
          <span>{scrapeMessage}</span>
          <button
            onClick={() => setScrapeMessage(null)}
            style={{ background: 'transparent', border: 'none', cursor: 'pointer', fontSize: '1rem', color: 'inherit' }}
          >
            ✕
          </button>
        </div>
      )}

      {/* ── Stats Metric Cards ── */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
        gap: '16px',
        marginBottom: '24px'
      }}>
        <div style={{ background: '#fff', padding: '16px 20px', borderRadius: '10px', border: '1px solid #e2e8f0', boxShadow: '0 1px 3px rgba(0,0,0,0.04)' }}>
          <div style={{ fontSize: '0.8rem', color: '#64748b', fontWeight: 600, textTransform: 'uppercase' }}>Total Tenders in DB</div>
          <div style={{ fontSize: '1.6rem', fontWeight: 700, color: '#0f172a', marginTop: '4px' }}>
            {stats ? stats.total_tenders.toLocaleString() : '0'}
          </div>
        </div>

        <div style={{ background: '#fff', padding: '16px 20px', borderRadius: '10px', border: '1px solid #e2e8f0', boxShadow: '0 1px 3px rgba(0,0,0,0.04)' }}>
          <div style={{ fontSize: '0.8rem', color: '#64748b', fontWeight: 600, textTransform: 'uppercase' }}>CPPP Portal Count</div>
          <div style={{ fontSize: '1.6rem', fontWeight: 700, color: '#2563eb', marginTop: '4px' }}>
            {stats?.by_source?.CPPP ? stats.by_source.CPPP.toLocaleString() : '0'}
          </div>
        </div>

        <div style={{ background: '#fff', padding: '16px 20px', borderRadius: '10px', border: '1px solid #e2e8f0', boxShadow: '0 1px 3px rgba(0,0,0,0.04)' }}>
          <div style={{ fontSize: '0.8rem', color: '#64748b', fontWeight: 600, textTransform: 'uppercase' }}>Active / Open</div>
          <div style={{ fontSize: '1.6rem', fontWeight: 700, color: '#16a34a', marginTop: '4px' }}>
            {stats?.by_status?.OPEN ? stats.by_status.OPEN.toLocaleString() : '0'}
          </div>
        </div>

        <div style={{ background: '#fff', padding: '16px 20px', borderRadius: '10px', border: '1px solid #e2e8f0', boxShadow: '0 1px 3px rgba(0,0,0,0.04)' }}>
          <div style={{ fontSize: '0.8rem', color: '#64748b', fontWeight: 600, textTransform: 'uppercase' }}>Filter Matches</div>
          <div style={{ fontSize: '1.6rem', fontWeight: 700, color: '#9333ea', marginTop: '4px' }}>
            {total.toLocaleString()}
          </div>
        </div>
      </div>

      {/* ── Search & Filter Controls ── */}
      <div style={{
        background: '#fff',
        padding: '20px',
        borderRadius: '10px',
        border: '1px solid #e2e8f0',
        marginBottom: '24px',
        boxShadow: '0 1px 3px rgba(0,0,0,0.04)'
      }}>
        <form onSubmit={handleSearchSubmit}>
          <div style={{ display: 'flex', gap: '12px', marginBottom: '16px', flexWrap: 'wrap' }}>
            <div style={{ flex: 1, minWidth: '280px' }}>
              <input
                type="text"
                placeholder="Search title, description, reference number, or organisation..."
                value={keyword}
                onChange={e => setKeyword(e.target.value)}
                style={{
                  width: '100%',
                  padding: '10px 14px',
                  borderRadius: '6px',
                  border: '1px solid #cbd5e1',
                  fontSize: '0.9rem',
                  outline: 'none',
                  boxSizing: 'border-box'
                }}
              />
            </div>
            <button
              type="submit"
              style={{
                padding: '10px 20px',
                background: '#0f172a',
                color: '#fff',
                border: 'none',
                borderRadius: '6px',
                fontWeight: 600,
                cursor: 'pointer',
                fontSize: '0.9rem'
              }}
            >
              Search Tenders
            </button>
            <button
              type="button"
              onClick={handleClearFilters}
              style={{
                padding: '10px 16px',
                background: '#f1f5f9',
                color: '#475569',
                border: '1px solid #cbd5e1',
                borderRadius: '6px',
                cursor: 'pointer',
                fontWeight: 500,
                fontSize: '0.9rem'
              }}
            >
              Reset
            </button>
          </div>

          {/* Secondary Filter Row */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
            gap: '12px',
            paddingTop: '12px',
            borderTop: '1px solid #f1f5f9'
          }}>
            <div>
              <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: '#64748b', marginBottom: '4px' }}>SOURCE PORTAL</label>
              <select
                value={source}
                onChange={e => { setSource(e.target.value); setPage(1); }}
                style={{ width: '100%', padding: '8px 10px', borderRadius: '6px', border: '1px solid #cbd5e1', fontSize: '0.85rem' }}
              >
                <option value="ALL">All Sources</option>
                <option value="CPPP">CPPP (Central Portal)</option>
                <option value="GeM">GeM Portal</option>
              </select>
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: '#64748b', marginBottom: '4px' }}>CATEGORY</label>
              <select
                value={category}
                onChange={e => { setCategory(e.target.value); setPage(1); }}
                style={{ width: '100%', padding: '8px 10px', borderRadius: '6px', border: '1px solid #cbd5e1', fontSize: '0.85rem' }}
              >
                {CATEGORY_OPTIONS.map(c => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: '#64748b', marginBottom: '4px' }}>STATUS</label>
              <select
                value={status}
                onChange={e => { setStatus(e.target.value); setPage(1); }}
                style={{ width: '100%', padding: '8px 10px', borderRadius: '6px', border: '1px solid #cbd5e1', fontSize: '0.85rem' }}
              >
                <option value="ALL">All Statuses</option>
                <option value="OPEN">Open Tenders</option>
                <option value="CLOSED">Closed Tenders</option>
              </select>
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: '#64748b', marginBottom: '4px' }}>LOCATION / CITY</label>
              <input
                type="text"
                placeholder="e.g. Delhi, Hyderabad"
                value={state}
                onChange={e => setState(e.target.value)}
                style={{ width: '100%', padding: '8px 10px', borderRadius: '6px', border: '1px solid #cbd5e1', fontSize: '0.85rem', boxSizing: 'border-box' }}
              />
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: '#64748b', marginBottom: '4px' }}>MIN VALUE (₹)</label>
              <input
                type="number"
                placeholder="Min ₹"
                value={minValue}
                onChange={e => setMinValue(e.target.value)}
                style={{ width: '100%', padding: '8px 10px', borderRadius: '6px', border: '1px solid #cbd5e1', fontSize: '0.85rem', boxSizing: 'border-box' }}
              />
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: '#64748b', marginBottom: '4px' }}>SORT BY</label>
              <select
                value={sortBy}
                onChange={e => { setSortBy(e.target.value); setPage(1); }}
                style={{ width: '100%', padding: '8px 10px', borderRadius: '6px', border: '1px solid #cbd5e1', fontSize: '0.85rem' }}
              >
                <option value="closing_date">Closing Date (Earliest)</option>
                <option value="publication_date">Publication Date (Newest)</option>
                <option value="tender_value">Tender Value (Highest)</option>
                <option value="scraped_at">Recently Scraped</option>
              </select>
            </div>
          </div>
        </form>
      </div>

      {/* ── Results List ── */}
      {loading ? (
        <div style={{ textAlign: 'center', padding: '60px 20px', color: '#64748b' }}>
          <div style={{ fontSize: '1.2rem', fontWeight: 600 }}>Loading tenders from database...</div>
          <p style={{ marginTop: '8px' }}>Fetching normalized tender intelligence.</p>
        </div>
      ) : tenders.length === 0 ? (
        <div style={{
          background: '#fff',
          padding: '48px 24px',
          borderRadius: '10px',
          border: '1px solid #e2e8f0',
          textAlign: 'center'
        }}>
          <div style={{ fontSize: '2.5rem', marginBottom: '12px' }}>📂</div>
          <h3 style={{ fontSize: '1.2rem', margin: '0 0 8px', color: '#1e293b' }}>No Scraped Tenders Found</h3>
          <p style={{ color: '#64748b', maxWidth: '460px', margin: '0 auto 20px', fontSize: '0.9rem' }}>
            Your database doesn't have any tenders matching this criteria yet.
            Click <strong>"Run CPPP Scraper"</strong> above to scrape live tenders from the portal right now!
          </p>
          <button
            onClick={() => handleTriggerScraper('CPPP')}
            disabled={runningScraper}
            style={{
              padding: '10px 24px',
              background: '#2563eb',
              color: '#fff',
              border: 'none',
              borderRadius: '6px',
              fontWeight: 600,
              cursor: 'pointer'
            }}
          >
            🚀 Run CPPP Scraper Now
          </button>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          {tenders.map(t => (
            <div
              key={t.id || t._id}
              style={{
                background: '#fff',
                borderRadius: '8px',
                border: '1px solid #e2e8f0',
                padding: '20px',
                boxShadow: '0 1px 2px rgba(0,0,0,0.03)',
                transition: 'border-color 0.2s',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '12px', flexWrap: 'wrap' }}>
                <div style={{ display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
                  {/* Source Badge */}
                  <span style={{
                    background: '#ede9fe',
                    color: '#6d28d9',
                    fontSize: '0.75rem',
                    fontWeight: 700,
                    padding: '3px 8px',
                    borderRadius: '4px'
                  }}>
                    {t.source}
                  </span>

                  {/* Category Badge */}
                  {t.category && (
                    <span style={{
                      background: '#f1f5f9',
                      color: '#475569',
                      fontSize: '0.75rem',
                      fontWeight: 600,
                      padding: '3px 8px',
                      borderRadius: '4px'
                    }}>
                      {t.category}
                    </span>
                  )}

                  {/* Status Badge */}
                  <span style={{
                    background: t.status === 'OPEN' ? '#dcfce7' : '#f1f5f9',
                    color: t.status === 'OPEN' ? '#15803d' : '#64748b',
                    fontSize: '0.75rem',
                    fontWeight: 600,
                    padding: '3px 8px',
                    borderRadius: '4px'
                  }}>
                    {t.status}
                  </span>

                  {/* Detail Solved Badge */}
                  {t.detail_solved && (
                    <span style={{
                      background: '#e0f2fe',
                      color: '#0369a1',
                      fontSize: '0.7rem',
                      fontWeight: 600,
                      padding: '2px 6px',
                      borderRadius: '4px'
                    }}>
                      ⚡ Details Enriched
                    </span>
                  )}
                </div>

                {/* Estimated Value */}
                <div style={{ textAlign: 'right' }}>
                  <div style={{ fontSize: '0.75rem', color: '#64748b', fontWeight: 600 }}>ESTIMATED VALUE</div>
                  <div style={{ fontSize: '1.1rem', fontWeight: 700, color: '#0f172a' }}>
                    {formatIndianCurrency(t.tender_value)}
                  </div>
                </div>
              </div>

              {/* Title */}
              <h3 style={{ fontSize: '1.05rem', fontWeight: 600, margin: '12px 0 6px', color: '#0f172a', lineHeight: 1.4 }}>
                {t.title}
              </h3>

              {/* Organisation & Department */}
              <div style={{ fontSize: '0.875rem', color: '#475569', marginBottom: '12px' }}>
                🏢 <strong>{t.organisation || 'Organisation Not Specified'}</strong>
                {t.department && <span style={{ color: '#64748b' }}> • {t.department}</span>}
                {t.location && <span style={{ color: '#64748b' }}> • 📍 {t.location}</span>}
              </div>

              {/* Reference & Key Metadata */}
              <div style={{
                display: 'flex',
                gap: '20px',
                fontSize: '0.8rem',
                color: '#64748b',
                background: '#f8fafc',
                padding: '10px 14px',
                borderRadius: '6px',
                flexWrap: 'wrap',
                marginBottom: '14px'
              }}>
                <div>
                  <span style={{ fontWeight: 600, color: '#475569' }}>Ref No: </span>
                  {t.reference_no || t.source_id}
                </div>
                {t.closing_date && (
                  <div>
                    <span style={{ fontWeight: 600, color: '#b91c1c' }}>Deadline: </span>
                    {formatDate(t.closing_date)}
                  </div>
                )}
                {t.opening_date && (
                  <div>
                    <span style={{ fontWeight: 600, color: '#475569' }}>Opening: </span>
                    {formatDate(t.opening_date)}
                  </div>
                )}
                {t.emd_amount && (
                  <div>
                    <span style={{ fontWeight: 600, color: '#475569' }}>EMD: </span>
                    {formatIndianCurrency(t.emd_amount)}
                  </div>
                )}
                {t.documents && t.documents.length > 0 && (
                  <div>
                    <span style={{ fontWeight: 600, color: '#2563eb' }}>📄 Docs: </span>
                    {t.documents.length} File(s)
                  </div>
                )}
              </div>

              {/* Actions */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <a
                  href={t.source_url}
                  target="_blank"
                  rel="noreferrer"
                  style={{ fontSize: '0.85rem', color: '#2563eb', textDecoration: 'none', fontWeight: 500 }}
                >
                  🔗 View on Portal ↗
                </a>

                <button
                  onClick={() => setSelectedTender(t)}
                  style={{
                    padding: '6px 14px',
                    background: '#0f172a',
                    color: '#fff',
                    border: 'none',
                    borderRadius: '5px',
                    fontSize: '0.85rem',
                    fontWeight: 600,
                    cursor: 'pointer'
                  }}
                >
                  View Full Details
                </button>
              </div>
            </div>
          ))}

          {/* ── Pagination ── */}
          <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            padding: '16px 0',
            flexWrap: 'wrap',
            gap: '12px'
          }}>
            <div style={{ fontSize: '0.85rem', color: '#64748b' }}>
              Showing {((page - 1) * limit) + 1} to {Math.min(page * limit, total)} of {total} tenders
            </div>

            <div style={{ display: 'flex', gap: '6px' }}>
              <button
                disabled={page <= 1}
                onClick={() => { const p = page - 1; setPage(p); loadTenders(p); }}
                style={{
                  padding: '6px 12px',
                  borderRadius: '5px',
                  border: '1px solid #cbd5e1',
                  background: page <= 1 ? '#f8fafc' : '#fff',
                  cursor: page <= 1 ? 'not-allowed' : 'pointer',
                  color: page <= 1 ? '#94a3b8' : '#334155'
                }}
              >
                Previous
              </button>

              <span style={{ padding: '6px 12px', fontWeight: 600, fontSize: '0.875rem' }}>
                Page {page} of {totalPages}
              </span>

              <button
                disabled={page >= totalPages}
                onClick={() => { const p = page + 1; setPage(p); loadTenders(p); }}
                style={{
                  padding: '6px 12px',
                  borderRadius: '5px',
                  border: '1px solid #cbd5e1',
                  background: page >= totalPages ? '#f8fafc' : '#fff',
                  cursor: page >= totalPages ? 'not-allowed' : 'pointer',
                  color: page >= totalPages ? '#94a3b8' : '#334155'
                }}
              >
                Next
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Detail Modal ── */}
      {selectedTender && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(15, 23, 42, 0.6)',
          backdropFilter: 'blur(3px)',
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          zIndex: 9999,
          padding: '20px'
        }}>
          <div style={{
            background: '#fff',
            borderRadius: '12px',
            maxWidth: '850px',
            width: '100%',
            maxHeight: '90vh',
            overflowY: 'auto',
            padding: '28px',
            boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.2)',
            position: 'relative'
          }}>
            <button
              onClick={() => setSelectedTender(null)}
              style={{
                position: 'absolute',
                top: '20px',
                right: '20px',
                background: '#f1f5f9',
                border: 'none',
                borderRadius: '50%',
                width: '32px',
                height: '32px',
                cursor: 'pointer',
                fontWeight: 700,
                fontSize: '1rem',
                color: '#475569'
              }}
            >
              ✕
            </button>

            <div style={{ display: 'flex', gap: '8px', alignItems: 'center', marginBottom: '10px' }}>
              <span style={{ background: '#ede9fe', color: '#6d28d9', fontSize: '0.8rem', fontWeight: 700, padding: '3px 8px', borderRadius: '4px' }}>
                {selectedTender.source}
              </span>
              <span style={{ background: '#f1f5f9', color: '#475569', fontSize: '0.8rem', fontWeight: 600, padding: '3px 8px', borderRadius: '4px' }}>
                {selectedTender.category || 'General'}
              </span>
              <span style={{ background: selectedTender.status === 'OPEN' ? '#dcfce7' : '#f1f5f9', color: selectedTender.status === 'OPEN' ? '#15803d' : '#64748b', fontSize: '0.8rem', fontWeight: 600, padding: '3px 8px', borderRadius: '4px' }}>
                {selectedTender.status}
              </span>
            </div>

            <h2 style={{ fontSize: '1.3rem', fontWeight: 700, margin: '0 0 12px', lineHeight: 1.4, color: '#0f172a' }}>
              {selectedTender.title}
            </h2>

            <div style={{ fontSize: '0.95rem', color: '#475569', marginBottom: '20px' }}>
              🏢 <strong>{selectedTender.organisation}</strong>
              {selectedTender.department && <div>{selectedTender.department}</div>}
            </div>

            {/* Key Specs Grid */}
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
              gap: '12px',
              background: '#f8fafc',
              padding: '16px',
              borderRadius: '8px',
              marginBottom: '20px'
            }}>
              <div>
                <div style={{ fontSize: '0.75rem', color: '#64748b', fontWeight: 600 }}>ESTIMATED VALUE</div>
                <div style={{ fontSize: '1.1rem', fontWeight: 700, color: '#0f172a' }}>
                  {formatIndianCurrency(selectedTender.tender_value)}
                </div>
              </div>

              <div>
                <div style={{ fontSize: '0.75rem', color: '#64748b', fontWeight: 600 }}>EMD AMOUNT</div>
                <div style={{ fontSize: '1rem', fontWeight: 600, color: '#0f172a' }}>
                  {formatIndianCurrency(selectedTender.emd_amount)}
                </div>
              </div>

              <div>
                <div style={{ fontSize: '0.75rem', color: '#64748b', fontWeight: 600 }}>TENDER FEE</div>
                <div style={{ fontSize: '1rem', fontWeight: 600, color: '#0f172a' }}>
                  {formatIndianCurrency(selectedTender.tender_fee)}
                </div>
              </div>

              <div>
                <div style={{ fontSize: '0.75rem', color: '#64748b', fontWeight: 600 }}>REFERENCE NO</div>
                <div style={{ fontSize: '0.85rem', fontWeight: 600, color: '#0f172a', wordBreak: 'break-all' }}>
                  {selectedTender.reference_no || selectedTender.source_id}
                </div>
              </div>

              <div>
                <div style={{ fontSize: '0.75rem', color: '#64748b', fontWeight: 600 }}>BID SUBMISSION CLOSING</div>
                <div style={{ fontSize: '0.85rem', fontWeight: 600, color: '#b91c1c' }}>
                  {formatDate(selectedTender.closing_date)}
                </div>
              </div>

              <div>
                <div style={{ fontSize: '0.75rem', color: '#64748b', fontWeight: 600 }}>BID OPENING DATE</div>
                <div style={{ fontSize: '0.85rem', fontWeight: 600, color: '#0f172a' }}>
                  {formatDate(selectedTender.opening_date)}
                </div>
              </div>

              <div>
                <div style={{ fontSize: '0.75rem', color: '#64748b', fontWeight: 600 }}>LOCATION & PINCODE</div>
                <div style={{ fontSize: '0.85rem', fontWeight: 600, color: '#0f172a' }}>
                  {selectedTender.location || 'N/A'} {selectedTender.pincode ? `(${selectedTender.pincode})` : ''}
                </div>
              </div>

              <div>
                <div style={{ fontSize: '0.75rem', color: '#64748b', fontWeight: 600 }}>TENDER TYPE</div>
                <div style={{ fontSize: '0.85rem', fontWeight: 600, color: '#0f172a' }}>
                  {selectedTender.tender_type || 'Open Tender'}
                </div>
              </div>
            </div>

            {/* Description */}
            <div style={{ marginBottom: '20px' }}>
              <h4 style={{ fontSize: '0.95rem', fontWeight: 700, margin: '0 0 8px', color: '#0f172a' }}>Work Description / Scope</h4>
              <p style={{
                fontSize: '0.9rem',
                lineHeight: 1.6,
                color: '#334155',
                whiteSpace: 'pre-wrap',
                background: '#fafafa',
                padding: '14px',
                borderRadius: '6px',
                border: '1px solid #f1f5f9'
              }}>
                {selectedTender.description || 'No detailed description available.'}
              </p>
            </div>

            {/* Inviting Authority */}
            {(selectedTender.inviting_authority_name || selectedTender.inviting_authority_address) && (
              <div style={{ marginBottom: '20px' }}>
                <h4 style={{ fontSize: '0.95rem', fontWeight: 700, margin: '0 0 8px', color: '#0f172a' }}>Tender Inviting Authority</h4>
                <div style={{ fontSize: '0.85rem', color: '#475569', background: '#f8fafc', padding: '12px', borderRadius: '6px' }}>
                  {selectedTender.inviting_authority_name && <div><strong>Authority:</strong> {selectedTender.inviting_authority_name}</div>}
                  {selectedTender.inviting_authority_address && <div><strong>Address:</strong> {selectedTender.inviting_authority_address}</div>}
                </div>
              </div>
            )}

            {/* Documents */}
            {selectedTender.documents && selectedTender.documents.length > 0 && (
              <div style={{ marginBottom: '24px' }}>
                <h4 style={{ fontSize: '0.95rem', fontWeight: 700, margin: '0 0 8px', color: '#0f172a' }}>Supporting Documents & NIT</h4>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {selectedTender.documents.map((doc, idx) => (
                    <a
                      key={idx}
                      href={doc.url}
                      target="_blank"
                      rel="noreferrer"
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        padding: '10px 14px',
                        background: '#f8fafc',
                        border: '1px solid #e2e8f0',
                        borderRadius: '6px',
                        textDecoration: 'none',
                        color: '#2563eb',
                        fontSize: '0.85rem',
                        fontWeight: 500
                      }}
                    >
                      <span>📄 {doc.name}</span>
                      <span style={{ fontSize: '0.75rem', color: '#64748b' }}>Download ↗</span>
                    </a>
                  ))}
                </div>
              </div>
            )}

            {/* Footer Buttons */}
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
              <a
                href={selectedTender.source_url}
                target="_blank"
                rel="noreferrer"
                style={{
                  padding: '9px 18px',
                  background: '#2563eb',
                  color: '#fff',
                  borderRadius: '6px',
                  textDecoration: 'none',
                  fontWeight: 600,
                  fontSize: '0.875rem'
                }}
              >
                Open Official Portal ↗
              </a>
              <button
                onClick={() => setSelectedTender(null)}
                style={{
                  padding: '9px 16px',
                  background: '#f1f5f9',
                  color: '#475569',
                  border: '1px solid #cbd5e1',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  fontWeight: 500,
                  fontSize: '0.875rem'
                }}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
