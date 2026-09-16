import { useState, useEffect } from 'react';
import { api } from '../services/api';
import { ExploreTenderItem, ExploreSearchPayload } from '../types';

// ─── Currency Formatter ────────────────────────────────────────────────────────
function formatIndianCurrency(val?: number): string {
  if (val === undefined || val === null || isNaN(val) || val === 0) return 'Not Specified';
  if (val >= 10000000) {
    return `₹ ${(val / 10000000).toLocaleString('en-IN', { maximumFractionDigits: 2 })} Cr`;
  }
  if (val >= 100000) {
    return `₹ ${(val / 100000).toLocaleString('en-IN', { maximumFractionDigits: 2 })} Lakhs`;
  }
  return `₹ ${val.toLocaleString('en-IN')}`;
}

// ─── Quick Suggestion Chips ───────────────────────────────────────────────────
const QUICK_SEARCH_CHIPS = [
  'Construction',
  'Hospital',
  'Roads & Highway',
  'Solar & Power',
  'Railway',
  'Electrical',
  'Water & Sewage',
  'Security & CCTV'
];

// ─── Shimmer Component ────────────────────────────────────────────────────────
function ShimmerTenderCard() {
  return (
    <div style={{
      background: '#fff',
      border: '1px solid #e2e8f0',
      borderRadius: '8px',
      padding: '20px',
      marginBottom: '16px',
      display: 'flex',
      flexDirection: 'column',
      gap: '12px'
    }}>
      <div style={{ height: '20px', width: '85%', background: '#e2e8f0', borderRadius: '4px', animation: 'pulse 1.5s infinite' }} />
      <div style={{ display: 'flex', gap: '16px' }}>
        <div style={{ height: '16px', width: '120px', background: '#e2e8f0', borderRadius: '4px' }} />
        <div style={{ height: '16px', width: '150px', background: '#e2e8f0', borderRadius: '4px' }} />
        <div style={{ height: '16px', width: '100px', background: '#e2e8f0', borderRadius: '4px' }} />
      </div>
      <div style={{ height: '36px', width: '100%', background: '#f1f5f9', borderRadius: '4px' }} />
      <style>{`@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }`}</style>
    </div>
  );
}

// ─── Default Initial Search Payload (Blank / Default) ─────────────────────────
function getDefaultPayload(): ExploreSearchPayload {
  return {
    tab_id: 1,
    tender_id: 0,
    tender_number: '',
    search_text: '',
    refine_search_text: '',
    boq: false,
    city_ids: '',
    closing_date_from: '',
    closing_date_to: '',
    exact_search: false,
    exact_search_text: false,
    gem: 0,
    guest_user_id: 0,
    is_ai_summary: false,
    is_tender_doc_uploaded: false,
    keyword_id: 0,
    mfa: '',
    msme: 0,
    nameof_website: '',
    organization_ids: 0,
    organization_name: '',
    organization_type_id: 0,
    page_no: 1,
    product_id: 0,
    publication_date_from: '',
    publication_date_to: '',
    quantity: '',
    quantityOperator: 0,
    record_per_page: 20,
    search_by: 0,
    search_by_location: true,
    search_by_split_word: false,
    sort_by: 1,
    sort_type: 2,
    state_ids: '',
    statezone_ids: '',
    sub_industry_id: 0,
    tender_typeid: 0,
    tender_value_from: 0,
    tender_value_operator: 0,
    tender_value_to: 0,
    startup: 0
  };
}

export function ExploreTenders() {
  // Search & Query States
  const [searchQuery, setSearchQuery] = useState('');
  const [activeQueryTitle, setActiveQueryTitle] = useState('All Live Tenders');
  const [loading, setLoading] = useState(false);
  const [tenders, setTenders] = useState<ExploreTenderItem[]>([]);
  const [totalCount, setTotalCount] = useState<number>(0);
  const [error, setError] = useState<string | null>(null);

  // Pagination
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);

  // States & Cities loaded from API
  const [statesList, setStatesList] = useState<{ state_id: number; state_name: string }[]>([]);
  const [citiesList, setCitiesList] = useState<{ city_id: number; city_name: string }[]>([]);
  const [selectedStateId, setSelectedStateId] = useState('');
  const [selectedCityId, setSelectedCityId] = useState('');
  const [loadingCities, setLoadingCities] = useState(false);

  // Value and Date Filters
  const [valuePreset, setValuePreset] = useState('all');
  const [customValueFrom, setCustomValueFrom] = useState('');
  const [customValueTo, setCustomValueTo] = useState('');
  const [dateFilter, setDateFilter] = useState('all');
  const [closingDateFrom, setClosingDateFrom] = useState('');
  const [closingDateTo, setClosingDateTo] = useState('');
  const [sortBy, setSortBy] = useState('1_2'); // 1_2 = Cost High to Low

  // Import Tracker
  const [importingId, setImportingId] = useState<number | null>(null);
  const [importedIds, setImportedIds] = useState<Set<number>>(new Set());
  const [importNotice, setImportNotice] = useState<string | null>(null);

  // Detail Modal
  const [detailModalTender, setDetailModalTender] = useState<ExploreTenderItem | null>(null);

  // ── 1. Initial Load: Fetch Portal States & Execute Blank Default Search ────
  useEffect(() => {
    loadStates();
    executeSearch(getDefaultPayload(), 1);
  }, []);

  // Fetch States from backend
  const loadStates = async () => {
    try {
      const states = await api.getExploreStates();
      setStatesList(states || []);
    } catch (err) {
      console.warn('Could not load states from API:', err);
    }
  };

  // When selected state changes, load corresponding cities
  const handleStateChange = async (stateId: string) => {
    setSelectedStateId(stateId);
    setSelectedCityId('');
    setCitiesList([]);
    if (!stateId) return;

    setLoadingCities(true);
    try {
      const cities = await api.getExploreCities(stateId);
      setCitiesList(cities || []);
    } catch (err) {
      console.warn('Could not load cities for state', stateId, err);
    } finally {
      setLoadingCities(false);
    }
  };

  // ── Core Search Execution ────────────────────────────────────────────────
  const executeSearch = async (payload: ExploreSearchPayload, targetPage: number = 1) => {
    setLoading(true);
    setError(null);

    const fullPayload: ExploreSearchPayload = {
      ...payload,
      page_no: targetPage,
      record_per_page: pageSize
    };

    try {
      const [searchRes, countRes] = await Promise.all([
        api.exploreSearchTenders(fullPayload),
        api.exploreCountTenders(fullPayload)
      ]);

      if (searchRes && searchRes.Success) {
        setTenders(searchRes.Data || []);
        const total = countRes?.Data?.[0]?.tendercount ?? searchRes.TotalRecord ?? 0;
        setTotalCount(total);
      } else {
        setTenders([]);
        setError(searchRes?.Message || 'No tenders found matching your selection.');
      }
    } catch (err: any) {
      setError(err.message || 'Error communicating with tender portal.');
      setTenders([]);
    } finally {
      setLoading(false);
    }
  };

  // ── Build Current Filter Payload ──────────────────────────────────────────
  const buildCurrentPayload = (overrideText?: string, targetPage?: number): ExploreSearchPayload => {
    const [sb, st] = sortBy.split('_').map(Number);

    // Value Range
    let vFrom = 0;
    let vTo = 0;
    if (valuePreset === 'u50l') {
      vTo = 5000000;
    } else if (valuePreset === '50l_2cr') {
      vFrom = 5000000;
      vTo = 20000000;
    } else if (valuePreset === '2cr_10cr') {
      vFrom = 20000000;
      vTo = 100000000;
    } else if (valuePreset === '10cr_plus') {
      vFrom = 100000000;
    } else if (valuePreset === 'custom') {
      vFrom = customValueFrom ? Number(customValueFrom) : 0;
      vTo = customValueTo ? Number(customValueTo) : 0;
    }

    const textToSearch = overrideText !== undefined ? overrideText : searchQuery;

    return {
      tab_id: 1,
      tender_id: 0,
      tender_number: '',
      search_text: textToSearch.trim(),
      refine_search_text: '',
      boq: false,
      city_ids: selectedCityId || '',
      closing_date_from: dateFilter === 'custom' ? closingDateFrom : '',
      closing_date_to: dateFilter === 'custom' ? closingDateTo : '',
      exact_search: false,
      exact_search_text: false,
      gem: 0,
      guest_user_id: 0,
      is_ai_summary: false,
      is_tender_doc_uploaded: false,
      keyword_id: 0,
      mfa: '',
      msme: 0,
      nameof_website: '',
      organization_ids: 0,
      organization_name: '',
      organization_type_id: 0,
      page_no: targetPage || page,
      product_id: 0,
      publication_date_from: '',
      publication_date_to: '',
      quantity: '',
      quantityOperator: 0,
      record_per_page: pageSize,
      search_by: 0,
      search_by_location: true,
      search_by_split_word: false,
      sort_by: sb || 1,
      sort_type: st || 2,
      state_ids: selectedStateId || '',
      statezone_ids: '',
      sub_industry_id: 0,
      tender_typeid: 0,
      tender_value_from: vFrom,
      tender_value_operator: 0,
      tender_value_to: vTo,
      startup: 0
    };
  };

  // ── Trigger Search ────────────────────────────────────────────────────────
  const handleSearchSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    setPage(1);
    const query = searchQuery.trim();
    setActiveQueryTitle(query ? `"${query}"` : 'All Live Tenders');
    const payload = buildCurrentPayload(query, 1);
    executeSearch(payload, 1);
  };

  // ── Quick Chip Click ─────────────────────────────────────────────────────
  const handleChipClick = (chipText: string) => {
    setSearchQuery(chipText);
    setActiveQueryTitle(`"${chipText}"`);
    setPage(1);
    const payload = buildCurrentPayload(chipText, 1);
    executeSearch(payload, 1);
  };

  // ── Apply Filters Button ──────────────────────────────────────────────────
  const handleApplyFilters = () => {
    setPage(1);
    const payload = buildCurrentPayload(undefined, 1);
    executeSearch(payload, 1);
  };

  // ── Reset Filters Button ──────────────────────────────────────────────────
  const handleResetFilters = () => {
    setSelectedStateId('');
    setSelectedCityId('');
    setCitiesList([]);
    setValuePreset('all');
    setCustomValueFrom('');
    setCustomValueTo('');
    setDateFilter('all');
    setClosingDateFrom('');
    setClosingDateTo('');
    setSortBy('1_2');
    setSearchQuery('');
    setActiveQueryTitle('All Live Tenders');
    setPage(1);
    executeSearch(getDefaultPayload(), 1);
  };

  // ── Page Change ──────────────────────────────────────────────────────────
  const handlePageChange = (newPage: number) => {
    setPage(newPage);
    const payload = buildCurrentPayload(undefined, newPage);
    executeSearch(payload, newPage);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  // ── Import Tender into Local Opportunities ────────────────────────────────
  const handleImportTender = async (tender: ExploreTenderItem) => {
    setImportingId(tender.tender_id);
    try {
      const res = await api.importExploredTender(tender);
      if (res.success) {
        setImportedIds(prev => new Set([...prev, tender.tender_id]));
        setImportNotice(`✓ Tender #${tender.tender_id} successfully imported to Opportunities!`);
        setTimeout(() => setImportNotice(null), 5000);
      }
    } catch (err: any) {
      alert(`Failed to import tender: ${err.message}`);
    } finally {
      setImportingId(null);
    }
  };

  const totalPages = Math.max(1, Math.ceil(totalCount / pageSize));

  // Find state & city names for display summary
  const currentStateObj = statesList.find(s => String(s.state_id) === String(selectedStateId));
  const currentCityObj = citiesList.find(c => String(c.city_id) === String(selectedCityId));

  return (
    <div style={{ maxWidth: '1400px', margin: '0 auto' }}>
      {/* ── Header Row ──────────────────────────────────────────────────────── */}
      <div className="header-row" style={{ marginBottom: '16px' }}>
        <div>
          <h1 style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span>🌐 Explore Tenders</span>
            <span style={{ fontSize: '0.75rem', background: '#059669', color: '#fff', padding: '2px 8px', borderRadius: '4px', fontWeight: 600 }}>
              LIVE TENDERS
            </span>
          </h1>
          <p style={{ margin: '4px 0 0', color: '#64748b', fontSize: '0.9rem' }}>
            Browse and search live government and public procurement tenders across India. Filter by location, value, and closing dates.
          </p>
        </div>
      </div>

      {/* ── Import Success Notice ───────────────────────────────────────────── */}
      {importNotice && (
        <div style={{ background: '#f0fdf4', border: '1px solid #86efac', color: '#166534', padding: '12px 16px', borderRadius: '8px', marginBottom: '16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span>{importNotice}</span>
          <button onClick={() => setImportNotice(null)} style={{ background: 'transparent', border: 'none', color: '#166534', cursor: 'pointer', fontWeight: 700 }}>✕</button>
        </div>
      )}

      {/* ── Search Hero Box ─────────────────────────────────────────────────── */}
      <div className="card" style={{
        background: 'linear-gradient(135deg, #0f172a 0%, #1e293b 100%)',
        color: '#fff',
        padding: '24px',
        borderRadius: '12px',
        marginBottom: '24px',
        boxShadow: '0 4px 20px rgba(15, 23, 42, 0.15)'
      }}>
        <div style={{ marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '1.2rem' }}>🔍</span>
          <strong style={{ fontSize: '1rem', letterSpacing: '0.02em' }}>Search Tenders by Keyword or Topic</strong>
        </div>

        <form
          onSubmit={handleSearchSubmit}
          style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}
        >
          <div style={{ flex: 1, minWidth: '280px', position: 'relative' }}>
            <input
              type="text"
              className="form-control"
              placeholder="e.g. Construction, Hospital, Solar, Railway, Pipeline, CCTV, Electrical..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{
                width: '100%',
                padding: '12px 16px',
                fontSize: '0.95rem',
                borderRadius: '8px',
                border: 'none',
                boxShadow: '0 2px 8px rgba(0,0,0,0.1)'
              }}
            />
          </div>

          <button
            type="submit"
            className="btn"
            disabled={loading}
            style={{
              background: '#2563eb',
              color: '#fff',
              padding: '12px 24px',
              fontSize: '0.95rem',
              fontWeight: 700,
              borderRadius: '8px',
              cursor: loading ? 'not-allowed' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              border: 'none',
              boxShadow: '0 2px 8px rgba(37, 99, 235, 0.3)'
            }}
          >
            {loading ? 'Searching...' : 'Search Tenders'}
          </button>
        </form>

        {/* Quick Suggestion Chips */}
        <div style={{ marginTop: '14px', display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
          <span style={{ fontSize: '0.78rem', color: '#94a3b8', fontWeight: 600 }}>Quick Searches:</span>
          {QUICK_SEARCH_CHIPS.map((chip, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => handleChipClick(chip)}
              style={{
                background: searchQuery === chip ? '#2563eb' : 'rgba(255, 255, 255, 0.1)',
                color: '#fff',
                border: '1px solid rgba(255, 255, 255, 0.2)',
                borderRadius: '16px',
                padding: '3px 10px',
                fontSize: '0.75rem',
                cursor: 'pointer',
                transition: 'all 0.15s ease'
              }}
              onMouseEnter={(e) => {
                if (searchQuery !== chip) e.currentTarget.style.background = 'rgba(255, 255, 255, 0.25)';
              }}
              onMouseLeave={(e) => {
                if (searchQuery !== chip) e.currentTarget.style.background = 'rgba(255, 255, 255, 0.1)';
              }}
            >
              {chip}
            </button>
          ))}
        </div>
      </div>

      {/* ── Main Layout: Sidebar Filters + Results Grid ────────────────────── */}
      <div style={{ display: 'grid', gridTemplateColumns: '280px 1fr', gap: '24px', alignItems: 'flex-start' }}>
        
        {/* ── Left Sidebar Filters ─────────────────────────────────────────── */}
        <div className="card" style={{ padding: '20px', borderRadius: '10px', position: 'sticky', top: '20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', borderBottom: '1px solid #e2e8f0', paddingBottom: '10px' }}>
            <h3 style={{ margin: 0, fontSize: '1rem', color: '#1e293b', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span>⚙️</span> Filters
            </h3>
            <button
              onClick={handleResetFilters}
              style={{ background: 'none', border: 'none', color: '#2563eb', fontSize: '0.8rem', cursor: 'pointer', fontWeight: 600 }}
            >
              Reset All
            </button>
          </div>

          {/* State Filter (from API) */}
          <div style={{ marginBottom: '16px' }}>
            <label style={{ fontSize: '0.8rem', fontWeight: 600, color: '#475569', display: 'block', marginBottom: '4px' }}>
              State / Region
            </label>
            <select
              className="form-control"
              value={selectedStateId}
              onChange={(e) => handleStateChange(e.target.value)}
              style={{ width: '100%', fontSize: '0.85rem' }}
            >
              <option value="">All States</option>
              {statesList.map(s => (
                <option key={s.state_id} value={s.state_id}>{s.state_name}</option>
              ))}
            </select>
          </div>

          {/* City Filter (dynamically fetched from API for selected state) */}
          <div style={{ marginBottom: '16px' }}>
            <label style={{ fontSize: '0.8rem', fontWeight: 600, color: '#475569', display: 'block', marginBottom: '4px' }}>
              City {loadingCities && <span style={{ fontSize: '0.72rem', color: '#2563eb' }}>(Loading...)</span>}
            </label>
            <select
              className="form-control"
              value={selectedCityId}
              onChange={(e) => setSelectedCityId(e.target.value)}
              disabled={!selectedStateId || loadingCities}
              style={{ width: '100%', fontSize: '0.85rem', opacity: !selectedStateId ? 0.6 : 1 }}
            >
              <option value="">All Cities</option>
              {citiesList.map(c => (
                <option key={c.city_id} value={c.city_id}>{c.city_name}</option>
              ))}
            </select>
            {!selectedStateId && (
              <span style={{ fontSize: '0.7rem', color: '#94a3b8', display: 'block', marginTop: '2px' }}>
                Select a state first to view cities
              </span>
            )}
          </div>

          {/* Tender Value Filter */}
          <div style={{ marginBottom: '16px' }}>
            <label style={{ fontSize: '0.8rem', fontWeight: 600, color: '#475569', display: 'block', marginBottom: '6px' }}>
              Tender Value
            </label>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              {[
                { id: 'all', label: 'Any Value' },
                { id: 'u50l', label: 'Under ₹ 50 Lakhs' },
                { id: '50l_2cr', label: '₹ 50 Lakhs - ₹ 2 Cr' },
                { id: '2cr_10cr', label: '₹ 2 Cr - ₹ 10 Cr' },
                { id: '10cr_plus', label: 'Above ₹ 10 Cr' },
                { id: 'custom', label: 'Custom Range (₹)' }
              ].map(opt => (
                <label key={opt.id} style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.82rem', color: '#334155', cursor: 'pointer' }}>
                  <input
                    type="radio"
                    name="valuePreset"
                    checked={valuePreset === opt.id}
                    onChange={() => setValuePreset(opt.id)}
                  />
                  {opt.label}
                </label>
              ))}
            </div>

            {valuePreset === 'custom' && (
              <div style={{ marginTop: '8px', display: 'flex', gap: '6px' }}>
                <input
                  type="number"
                  placeholder="Min (₹)"
                  className="form-control"
                  style={{ width: '50%', fontSize: '0.78rem' }}
                  value={customValueFrom}
                  onChange={(e) => setCustomValueFrom(e.target.value)}
                />
                <input
                  type="number"
                  placeholder="Max (₹)"
                  className="form-control"
                  style={{ width: '50%', fontSize: '0.78rem' }}
                  value={customValueTo}
                  onChange={(e) => setCustomValueTo(e.target.value)}
                />
              </div>
            )}
          </div>

          {/* Closing Date Range */}
          <div style={{ marginBottom: '20px' }}>
            <label style={{ fontSize: '0.8rem', fontWeight: 600, color: '#475569', display: 'block', marginBottom: '6px' }}>
              Closing Date
            </label>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              {[
                { id: 'all', label: 'All Dates' },
                { id: 'custom', label: 'Date Range' }
              ].map(opt => (
                <label key={opt.id} style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.82rem', color: '#334155', cursor: 'pointer' }}>
                  <input
                    type="radio"
                    name="datePreset"
                    checked={dateFilter === opt.id}
                    onChange={() => setDateFilter(opt.id)}
                  />
                  {opt.label}
                </label>
              ))}
            </div>

            {dateFilter === 'custom' && (
              <div style={{ marginTop: '8px', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                <div>
                  <span style={{ fontSize: '0.72rem', color: '#64748b' }}>From:</span>
                  <input
                    type="date"
                    className="form-control"
                    style={{ width: '100%', fontSize: '0.78rem' }}
                    value={closingDateFrom}
                    onChange={(e) => setClosingDateFrom(e.target.value)}
                  />
                </div>
                <div>
                  <span style={{ fontSize: '0.72rem', color: '#64748b' }}>To:</span>
                  <input
                    type="date"
                    className="form-control"
                    style={{ width: '100%', fontSize: '0.78rem' }}
                    value={closingDateTo}
                    onChange={(e) => setClosingDateTo(e.target.value)}
                  />
                </div>
              </div>
            )}
          </div>

          {/* Apply Button */}
          <button
            className="btn"
            style={{ width: '100%', background: '#2563eb', color: '#fff', fontWeight: 600, fontSize: '0.85rem' }}
            onClick={handleApplyFilters}
            disabled={loading}
          >
            Apply Filters
          </button>
        </div>

        {/* ── Right Main Tender Results Area ──────────────────────────────── */}
        <div>
          {/* Results Summary Bar */}
          <div className="card" style={{ padding: '14px 20px', marginBottom: '16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
            <div>
              <div style={{ fontSize: '1rem', fontWeight: 700, color: '#1e293b' }}>
                {totalCount.toLocaleString('en-IN')} Tenders Available
              </div>
              <div style={{ fontSize: '0.8rem', color: '#64748b', marginTop: '2px' }}>
                Scope: <strong>{activeQueryTitle}</strong>
                {currentStateObj && <> &nbsp;·&nbsp; State: <strong>{currentStateObj.state_name}</strong></>}
                {currentCityObj && <> &nbsp;·&nbsp; City: <strong>{currentCityObj.city_name}</strong></>}
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span style={{ fontSize: '0.8rem', color: '#64748b', whiteSpace: 'nowrap' }}>Sort:</span>
                <select
                  className="form-control"
                  style={{ fontSize: '0.82rem', padding: '4px 8px' }}
                  value={sortBy}
                  onChange={(e) => {
                    setSortBy(e.target.value);
                    setPage(1);
                    const [sb, st] = e.target.value.split('_').map(Number);
                    const p = buildCurrentPayload(undefined, 1);
                    p.sort_by = sb;
                    p.sort_type = st;
                    executeSearch(p, 1);
                  }}
                >
                  <option value="1_2">Value: High to Low</option>
                  <option value="1_1">Value: Low to High</option>
                  <option value="2_1">Closing: Soonest</option>
                  <option value="3_2">Latest Published</option>
                </select>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span style={{ fontSize: '0.8rem', color: '#64748b', whiteSpace: 'nowrap' }}>Show:</span>
                <select
                  className="form-control"
                  style={{ fontSize: '0.82rem', padding: '4px 8px', width: '70px' }}
                  value={pageSize}
                  onChange={(e) => {
                    const newSize = Number(e.target.value);
                    setPageSize(newSize);
                    setPage(1);
                    const p = buildCurrentPayload(undefined, 1);
                    p.record_per_page = newSize;
                    executeSearch(p, 1);
                  }}
                >
                  <option value={10}>10</option>
                  <option value={20}>20</option>
                  <option value={50}>50</option>
                </select>
              </div>
            </div>
          </div>

          {/* Error Message */}
          {error && (
            <div style={{ background: '#fef2f2', border: '1px solid #fca5a5', color: '#991b1b', padding: '14px 18px', borderRadius: '8px', marginBottom: '16px', fontSize: '0.875rem' }}>
              ⚠️ {error}
            </div>
          )}

          {/* Loading Shimmer */}
          {loading ? (
            <div>
              {Array.from({ length: 5 }).map((_, idx) => (
                <ShimmerTenderCard key={idx} />
              ))}
            </div>
          ) : tenders.length === 0 ? (
            <div className="card" style={{ textAlign: 'center', padding: '60px 20px', color: '#64748b' }}>
              <div style={{ fontSize: '2.5rem', marginBottom: '12px' }}>🔍</div>
              <h3 style={{ margin: '0 0 8px 0', color: '#1e293b' }}>No Tenders Found</h3>
              <p style={{ margin: 0, fontSize: '0.9rem' }}>
                Try modifying your search keywords or loosening the filters.
              </p>
            </div>
          ) : (
            <div>
              {/* Tender Cards */}
              {tenders.map((item) => {
                const isImported = importedIds.has(item.tender_id);
                const isImporting = importingId === item.tender_id;

                return (
                  <div
                    key={item.tender_id}
                    className="card"
                    style={{
                      padding: '20px',
                      marginBottom: '16px',
                      borderRadius: '10px',
                      transition: 'transform 0.15s ease, box-shadow 0.15s ease',
                      border: '1px solid #e2e8f0'
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.boxShadow = '0 4px 14px rgba(0,0,0,0.08)';
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.boxShadow = 'none';
                    }}
                  >
                    {/* Top Info Header */}
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '8px', marginBottom: '8px' }}>
                      <div style={{ display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
                        <span style={{ fontSize: '0.72rem', background: '#f1f5f9', color: '#475569', padding: '2px 8px', borderRadius: '4px', fontWeight: 600 }}>
                          ID: #{item.tender_id}
                        </span>
                        {item.ai_summary && (
                          <span style={{ fontSize: '0.72rem', background: '#ede9fe', color: '#6d28d9', padding: '2px 8px', borderRadius: '4px', fontWeight: 600 }}>
                            AI Summary Available
                          </span>
                        )}
                        {item.doc_uploaded && (
                          <span style={{ fontSize: '0.72rem', background: '#e0f2fe', color: '#0369a1', padding: '2px 8px', borderRadius: '4px', fontWeight: 600 }}>
                            📎 Documents Attached
                          </span>
                        )}
                      </div>

                      {item.tender_endsubmission_datetime && (
                        <div style={{ fontSize: '0.8rem', color: '#dc2626', fontWeight: 600, background: '#fef2f2', padding: '3px 10px', borderRadius: '4px' }}>
                          ⏳ Closes: {item.tender_endsubmission_datetime}
                        </div>
                      )}
                    </div>

                    {/* Tender Title / Work Brief */}
                    <h2 style={{
                      margin: '0 0 12px 0',
                      fontSize: '1rem',
                      fontWeight: 600,
                      color: '#1e293b',
                      lineHeight: 1.45,
                      textTransform: 'capitalize'
                    }}>
                      {item.requirement_workbrief || 'Tender Notice'}
                    </h2>

                    {/* Key Attributes Row */}
                    <div style={{
                      display: 'grid',
                      gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
                      gap: '12px',
                      background: '#f8fafc',
                      padding: '12px 16px',
                      borderRadius: '8px',
                      marginBottom: '16px',
                      fontSize: '0.82rem'
                    }}>
                      <div>
                        <span style={{ color: '#64748b', display: 'block', fontSize: '0.72rem' }}>ESTIMATED VALUE</span>
                        <strong style={{ fontSize: '0.95rem', color: '#059669' }}>
                          {formatIndianCurrency(item.estimatedcost)}
                        </strong>
                      </div>

                      <div>
                        <span style={{ color: '#64748b', display: 'block', fontSize: '0.72rem' }}>EMD AMOUNT</span>
                        <strong style={{ color: '#334155' }}>
                          {formatIndianCurrency(item.earnest_money_deposite)}
                        </strong>
                      </div>

                      <div>
                        <span style={{ color: '#64748b', display: 'block', fontSize: '0.72rem' }}>LOCATION</span>
                        <strong style={{ color: '#334155' }}>
                          📍 {item.site_location || 'Not Specified'}
                        </strong>
                      </div>

                      <div>
                        <span style={{ color: '#64748b', display: 'block', fontSize: '0.72rem' }}>AUTHORITY / ORGANIZATION</span>
                        <strong style={{ color: '#334155', textTransform: 'capitalize' }}>
                          🏛️ {item.organization_name && item.organization_name.toLowerCase() !== 'sss' ? item.organization_name : 'Government Entity'}
                        </strong>
                      </div>
                    </div>

                    {/* Card Actions */}
                    <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', alignItems: 'center', flexWrap: 'wrap' }}>
                      <button
                        className="btn btn-secondary"
                        style={{ fontSize: '0.8rem', padding: '6px 14px' }}
                        onClick={() => setDetailModalTender(item)}
                      >
                        👁️ View Details
                      </button>

                      <button
                        className="btn"
                        style={{
                          background: isImported ? '#059669' : '#2563eb',
                          color: '#fff',
                          fontSize: '0.8rem',
                          padding: '6px 16px',
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '6px',
                          cursor: isImported || isImporting ? 'default' : 'pointer'
                        }}
                        onClick={() => !isImported && handleImportTender(item)}
                        disabled={isImported || isImporting}
                      >
                        {isImported ? '✓ Saved to Opportunities' : isImporting ? '⏳ Importing...' : '📥 Import to Opportunities'}
                      </button>
                    </div>
                  </div>
                );
              })}

              {/* ── Pagination Bar ────────────────────────────────────────────── */}
              <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                marginTop: '24px',
                paddingTop: '16px',
                borderTop: '1px solid #e2e8f0',
                flexWrap: 'wrap',
                gap: '12px'
              }}>
                <div style={{ fontSize: '0.85rem', color: '#64748b' }}>
                  Showing <strong>{(page - 1) * pageSize + 1}</strong> to <strong>{Math.min(page * pageSize, totalCount)}</strong> of <strong>{totalCount.toLocaleString('en-IN')}</strong> tenders
                </div>

                <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
                  <button
                    className="btn btn-secondary"
                    style={{ padding: '6px 10px', fontSize: '0.82rem' }}
                    disabled={page <= 1 || loading}
                    onClick={() => handlePageChange(1)}
                  >
                    « First
                  </button>

                  <button
                    className="btn btn-secondary"
                    style={{ padding: '6px 12px', fontSize: '0.82rem' }}
                    disabled={page <= 1 || loading}
                    onClick={() => handlePageChange(page - 1)}
                  >
                    ‹ Prev
                  </button>

                  <span style={{ fontSize: '0.85rem', fontWeight: 600, padding: '0 8px' }}>
                    Page {page} of {totalPages}
                  </span>

                  <button
                    className="btn btn-secondary"
                    style={{ padding: '6px 12px', fontSize: '0.82rem' }}
                    disabled={page >= totalPages || loading}
                    onClick={() => handlePageChange(page + 1)}
                  >
                    Next ›
                  </button>

                  <button
                    className="btn btn-secondary"
                    style={{ padding: '6px 10px', fontSize: '0.82rem' }}
                    disabled={page >= totalPages || loading}
                    onClick={() => handlePageChange(totalPages)}
                  >
                    Last »
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ── Quick Details Modal ──────────────────────────────────────────────── */}
      {detailModalTender && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(0,0,0,0.5)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000,
          padding: '20px'
        }}>
          <div style={{
            background: '#fff',
            borderRadius: '12px',
            maxWidth: '700px',
            width: '100%',
            maxHeight: '90vh',
            overflowY: 'auto',
            padding: '24px',
            boxShadow: '0 10px 30px rgba(0,0,0,0.2)'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', borderBottom: '1px solid #e2e8f0', paddingBottom: '12px' }}>
              <h2 style={{ margin: 0, fontSize: '1.15rem', color: '#1e293b' }}>
                Tender #{detailModalTender.tender_id} Details
              </h2>
              <button
                onClick={() => setDetailModalTender(null)}
                style={{ background: 'transparent', border: 'none', fontSize: '1.2rem', cursor: 'pointer', color: '#64748b' }}
              >
                ✕
              </button>
            </div>

            <div style={{ marginBottom: '16px' }}>
              <label style={{ fontSize: '0.75rem', fontWeight: 600, color: '#64748b' }}>TITLE / REQUIREMENT BRIEF</label>
              <div style={{ fontSize: '0.95rem', color: '#1e293b', fontWeight: 600, marginTop: '4px' }}>
                {detailModalTender.requirement_workbrief}
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px', marginBottom: '20px' }}>
              <div style={{ background: '#f8fafc', padding: '10px 14px', borderRadius: '6px' }}>
                <span style={{ fontSize: '0.72rem', color: '#64748b', display: 'block' }}>ESTIMATED COST</span>
                <strong style={{ fontSize: '1.05rem', color: '#059669' }}>
                  {formatIndianCurrency(detailModalTender.estimatedcost)}
                </strong>
              </div>

              <div style={{ background: '#f8fafc', padding: '10px 14px', borderRadius: '6px' }}>
                <span style={{ fontSize: '0.72rem', color: '#64748b', display: 'block' }}>EMD AMOUNT</span>
                <strong style={{ fontSize: '1.05rem', color: '#334155' }}>
                  {formatIndianCurrency(detailModalTender.earnest_money_deposite)}
                </strong>
              </div>

              <div style={{ background: '#f8fafc', padding: '10px 14px', borderRadius: '6px' }}>
                <span style={{ fontSize: '0.72rem', color: '#64748b', display: 'block' }}>LOCATION</span>
                <strong style={{ fontSize: '0.9rem', color: '#334155' }}>
                  📍 {detailModalTender.site_location || 'Not Specified'}
                </strong>
              </div>

              <div style={{ background: '#f8fafc', padding: '10px 14px', borderRadius: '6px' }}>
                <span style={{ fontSize: '0.72rem', color: '#64748b', display: 'block' }}>SUBMISSION DEADLINE</span>
                <strong style={{ fontSize: '0.9rem', color: '#dc2626' }}>
                  📅 {detailModalTender.tender_endsubmission_datetime || 'Not Specified'}
                </strong>
              </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '20px', borderTop: '1px solid #e2e8f0', paddingTop: '16px' }}>
              <button
                className="btn btn-secondary"
                onClick={() => setDetailModalTender(null)}
              >
                Close
              </button>

              <button
                className="btn"
                style={{
                  background: importedIds.has(detailModalTender.tender_id) ? '#059669' : '#2563eb',
                  color: '#fff'
                }}
                onClick={() => {
                  handleImportTender(detailModalTender);
                  setDetailModalTender(null);
                }}
                disabled={importedIds.has(detailModalTender.tender_id)}
              >
                {importedIds.has(detailModalTender.tender_id) ? '✓ Already in Opportunities' : '📥 Import to Opportunities'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
