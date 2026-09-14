import { useEffect, useState } from 'react';
import { api } from '../services/api';
import { Opportunity, Source, Category, AIProcessResult } from '../types';

// ─── AI Analysis Panel ────────────────────────────────────────────────────────
type AIState = 'idle' | 'loading' | 'success' | 'unavailable' | 'error';

function AIAnalysisSection({
  opp,
  onRefresh,
}: {
  opp: Opportunity;
  onRefresh: (updated: Opportunity) => void;
}) {
  const [aiState, setAIState] = useState<AIState>('idle');
  const [result, setResult] = useState<AIProcessResult | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // If already AI-processed, show success straight away
  useEffect(() => {
    if (opp.ai?.processed) {
      setAIState('success');
    }
  }, [opp._id]);

  const handleAnalyze = async () => {
    if (!opp.content_id) {
      setErrorMsg('No content item linked to this opportunity.');
      setAIState('error');
      return;
    }
    setAIState('loading');
    setErrorMsg(null);
    try {
      const res = await api.analyzeWithAI(opp.content_id);
      setResult(res);
      if (res.ai_status === 'SUCCESS') {
        setAIState('success');
        // Refresh the opportunity in the parent so new fields are visible
        if (res.opportunity_id) {
          try {
            const updated = await api.getOpportunity(res.opportunity_id);
            onRefresh(updated);
          } catch (_) {}
        }
      } else if (res.ai_status === 'UNAVAILABLE') {
        setAIState('unavailable');
      } else {
        setErrorMsg(res.message || 'AI processing failed.');
        setAIState('error');
      }
    } catch (err: any) {
      const msg: string = err.message || 'AI processing request failed.';
      if (msg.toLowerCase().includes('unavailable') || msg.toLowerCase().includes('connect')) {
        setAIState('unavailable');
      } else {
        setErrorMsg(msg);
        setAIState('error');
      }
    }
  };

  const ai = opp.ai;

  const ListBlock = ({ label, items }: { label: string; items?: string[] }) => {
    if (!items || items.length === 0) return null;
    return (
      <div style={{ marginBottom: '14px' }}>
        <strong style={{ fontSize: '0.875rem', color: '#374151' }}>{label}:</strong>
        <ul style={{ margin: '6px 0 0 0', paddingLeft: '20px', fontSize: '0.875rem', color: '#374151' }}>
          {items.map((item, i) => <li key={i}>{item}</li>)}
        </ul>
      </div>
    );
  };

  return (
    <div style={{ marginTop: '16px' }}>
      {/* Header card */}
      <div className="card" style={{ borderLeft: '4px solid #7c3aed' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
          <div>
            <h3 style={{ margin: 0, fontSize: '1.05rem', color: '#1e293b' }}>🤖 AI Analysis</h3>
            {ai?.processed && (
              <p style={{ margin: '4px 0 0', fontSize: '0.8rem', color: '#64748b' }}>
                Model: <strong>{ai.model || '—'}</strong> &nbsp;·&nbsp; Prompt: <strong>{ai.prompt_version || 'v1'}</strong>
                {ai.processed_at && <>&nbsp;·&nbsp; Processed: <strong>{new Date(ai.processed_at).toLocaleString()}</strong></>}
              </p>
            )}
          </div>

          <button
            className="btn"
            style={{
              background: aiState === 'loading' ? '#a78bfa' : '#7c3aed',
              color: '#fff',
              minWidth: '150px',
              opacity: aiState === 'loading' ? 0.8 : 1,
              cursor: aiState === 'loading' ? 'not-allowed' : 'pointer',
            }}
            onClick={handleAnalyze}
            disabled={aiState === 'loading'}
          >
            {aiState === 'loading' ? '⏳ Analyzing…' : aiState === 'success' ? '🔄 Re-analyze with AI' : '🤖 Analyze with AI'}
          </button>
        </div>

        {/* State feedback */}
        {aiState === 'loading' && (
          <div style={{ marginTop: '12px', padding: '10px 14px', background: '#ede9fe', borderRadius: '6px', color: '#5b21b6', fontSize: '0.875rem' }}>
            Sending content to Ollama for AI extraction. This may take 10–60 seconds depending on your hardware…
          </div>
        )}

        {aiState === 'unavailable' && (
          <div style={{ marginTop: '12px', padding: '10px 14px', background: '#fef3c7', borderRadius: '6px', color: '#92400e', fontSize: '0.875rem' }}>
            ⚠️ Ollama service is not reachable. Make sure Ollama is running and the model is pulled.<br />
            <code style={{ fontSize: '0.8rem' }}>docker compose up ollama -d &amp;&amp; docker exec tendermate-ollama ollama pull {import.meta.env.VITE_OLLAMA_MODEL || 'llama3.2:3b'}</code>
          </div>
        )}

        {aiState === 'error' && errorMsg && (
          <div style={{ marginTop: '12px', padding: '10px 14px', background: '#fef2f2', borderRadius: '6px', color: '#991b1b', fontSize: '0.875rem' }}>
            ❌ {errorMsg}
          </div>
        )}

        {aiState === 'success' && result && (
          <div style={{ marginTop: '12px', padding: '10px 14px', background: '#f0fdf4', borderRadius: '6px', color: '#166534', fontSize: '0.875rem' }}>
            ✅ AI extraction complete.
            {result.enriched_fields.length > 0 && (
              <> Enriched fields: <strong>{result.enriched_fields.join(', ')}</strong>.</>
            )}
            {result.processing_duration > 0 && (
              <> Took <strong>{result.processing_duration.toFixed(1)}s</strong>.</>
            )}
          </div>
        )}

        {aiState === 'idle' && !ai?.processed && (
          <div style={{ marginTop: '12px', color: '#64748b', fontSize: '0.875rem' }}>
            AI analysis has not been run yet. Click <strong>Analyze with AI</strong> to extract structured fields using Ollama.
          </div>
        )}
      </div>

      {/* AI-extracted fields (only shown when processed) */}
      {ai?.processed && (
        <div className="card" style={{ marginTop: '12px' }}>
          <h3 style={{ borderBottom: '1px solid #e2e8f0', paddingBottom: '8px', fontSize: '1.05rem', color: '#1e293b', marginTop: 0 }}>
            AI-Extracted Intelligence
          </h3>

          {opp.description && (
            <div style={{ marginBottom: '16px' }}>
              <strong style={{ fontSize: '0.875rem', color: '#374151' }}>AI Summary / Description:</strong>
              <div style={{ background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: '6px', padding: '12px', marginTop: '6px', fontSize: '0.875rem', color: '#334155', whiteSpace: 'pre-wrap' }}>
                {opp.description}
              </div>
            </div>
          )}

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '0 24px' }}>
            <ListBlock label="Scope of Work" items={(opp as any).scope} />
            <ListBlock label="Eligibility Criteria" items={(opp as any).eligibility} />
            <ListBlock label="Requirements" items={(opp as any).requirements} />
            <ListBlock label="Certifications Required" items={(opp as any).certifications} />
            <ListBlock label="Experience Requirements" items={(opp as any).experience_requirements} />
            <ListBlock label="Equipment Requirements" items={(opp as any).equipment_requirements} />
          </div>

          {/* Show "nothing extracted" message if all lists are empty */}
          {!(opp as any).scope?.length &&
            !(opp as any).eligibility?.length &&
            !(opp as any).requirements?.length &&
            !(opp as any).certifications?.length &&
            !(opp as any).experience_requirements?.length &&
            !(opp as any).equipment_requirements?.length && (
              <p style={{ color: '#64748b', fontSize: '0.875rem' }}>
                No additional AI-extracted fields available. The content may not contain structured eligibility or requirements text.
              </p>
            )}
        </div>
      )}
    </div>
  );
}

// ─── Main Opportunities Page ──────────────────────────────────────────────────
export function Opportunities() {
  const [opportunities, setOpportunities] = useState<Opportunity[]>([]);
  const [totalCount, setTotalCount] = useState<number>(0);
  const [sources, setSources] = useState<Record<string, string>>({});
  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [sourceFilter, setSourceFilter] = useState<string>('');
  const [typeFilter, setTypeFilter] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [categoryFilter, setCategoryFilter] = useState<string>('');

  // Pagination & Detail View
  const [page, setPage] = useState(0);
  const [limit, setLimit] = useState(10);
  const [selectedOpp, setSelectedOpp] = useState<Opportunity | null>(null);
  const [refreshingTender, setRefreshingTender] = useState(false);
  const [refreshSuccessMsg, setRefreshSuccessMsg] = useState<string | null>(null);
  const [batchEnriching, setBatchEnriching] = useState(false);
  const [batchMsg, setBatchMsg] = useState<string | null>(null);

  useEffect(() => {
    loadMetaData();
  }, []);

  useEffect(() => {
    loadOpportunities();
  }, [page, limit, sourceFilter, typeFilter, statusFilter, categoryFilter]);

  // Polling effect: while any opportunities are currently enriching in the background,
  // silently re-fetch the list every 2.5 seconds so records update in real time without refreshing!
  useEffect(() => {
    const hasEnriching = opportunities.some(o => o.detail_enriching);
    if (!hasEnriching) return;

    const interval = setInterval(async () => {
      try {
        const data = await api.getOpportunities(
          sourceFilter || undefined,
          typeFilter || undefined,
          statusFilter || undefined,
          categoryFilter || undefined,
          page * limit,
          limit
        );
        setOpportunities(data);

        // If an opportunity is currently open in detail view, keep it in sync live
        if (selectedOpp) {
          const fresh = data.find(o => o._id === selectedOpp._id);
          if (fresh && (fresh.detail_solved !== selectedOpp.detail_solved || fresh.documents?.length !== selectedOpp.documents?.length || fresh.description !== selectedOpp.description)) {
            setSelectedOpp(fresh);
          }
        }
      } catch (_) {}
    }, 2500);

    return () => clearInterval(interval);
  }, [opportunities, page, limit, sourceFilter, typeFilter, statusFilter, categoryFilter, selectedOpp]);

  const loadMetaData = async () => {
    try {
      const [sourceList, catList] = await Promise.all([
        api.getSources(),
        api.getCategories().catch(() => [])
      ]);
      const map: Record<string, string> = {};
      (sourceList as Source[]).forEach(s => { map[s._id] = s.name; });
      setSources(map);
      setCategories(catList as Category[]);
    } catch (_e) {
      console.error('Failed to load metadata');
    }
  };

  const loadOpportunities = async () => {
    setLoading(true);
    setError(null);
    try {
      const [data, count] = await Promise.all([
        api.getOpportunities(
          sourceFilter || undefined,
          typeFilter || undefined,
          statusFilter || undefined,
          categoryFilter || undefined,
          page * limit,
          limit
        ),
        api.getOpportunitiesCount(
          sourceFilter || undefined,
          typeFilter || undefined,
          statusFilter || undefined,
          categoryFilter || undefined
        )
      ]);
      setOpportunities(data);
      setTotalCount(count);
    } catch (err: any) {
      setError(err.message || 'Failed to load opportunities');
    } finally {
      setLoading(false);
    }
  };

  const handleRefreshTender = async (oppId: string) => {
    setRefreshingTender(true);
    setRefreshSuccessMsg(null);
    try {
      const updated = await api.refreshOpportunityDetail(oppId);
      setSelectedOpp(updated);
      setOpportunities(prev => prev.map(o => o._id === updated._id ? updated : o));
      setRefreshSuccessMsg('Successfully connected to portal, solved CAPTCHA, and updated all tender specifications & documents!');
    } catch (err: any) {
      alert(err.message || 'Failed to refresh tender details from portal. The portal may be temporarily busy.');
    } finally {
      setRefreshingTender(false);
    }
  };

  const handleBatchEnrich = async () => {
    setBatchEnriching(true);
    setBatchMsg(null);
    try {
      const res = await api.batchRefreshOpportunities();
      setBatchMsg(`🚀 ${res.message || 'Background batch queue started.'} Records will update automatically.`);
      // Optimistically mark unenriched records as enriching
      setOpportunities(prev => prev.map(o => !o.detail_solved ? { ...o, detail_enriching: true } : o));
    } catch (err: any) {
      alert(err.message || 'Failed to trigger batch enrichment.');
    } finally {
      setBatchEnriching(false);
    }
  };

  const fmtDate = (d?: string | null) => d ? new Date(d).toLocaleString() : '—';

  const fmtValue = (opp: Opportunity) => {
    if (opp.value_text) return opp.value_text;
    if (opp.value !== null && opp.value !== undefined) {
      const num = typeof opp.value === 'number' ? opp.value : parseFloat(opp.value as string);
      if (!isNaN(num)) {
        if (num >= 10000000) return `${opp.currency || '₹'} ${(num / 10000000).toFixed(2)} Cr`;
        if (num >= 100000) return `${opp.currency || '₹'} ${(num / 100000).toFixed(2)} Lakh`;
        return `${opp.currency || '₹'} ${num.toLocaleString()}`;
      }
    }
    return '—';
  };

  const totalPages = Math.max(1, Math.ceil(totalCount / limit));

  const renderPaginationButtons = () => {
    const pages = [];
    const maxButtons = 5;
    let start = Math.max(0, page - 2);
    let end = Math.min(totalPages, start + maxButtons);
    if (end - start < maxButtons) {
      start = Math.max(0, end - maxButtons);
    }
    for (let i = start; i < end; i++) {
      pages.push(
        <button
          key={i}
          className="btn"
          style={{
            padding: '6px 12px',
            background: page === i ? '#2563eb' : '#fff',
            color: page === i ? '#fff' : '#374151',
            border: '1px solid #d1d5db',
            fontWeight: page === i ? 700 : 400,
            cursor: 'pointer',
            borderRadius: '4px',
            minWidth: '36px'
          }}
          onClick={() => setPage(i)}
        >
          {i + 1}
        </button>
      );
    }
    return pages;
  };

  // Detail View
  if (selectedOpp) {
    return (
      <div>
        <div className="header-row">
          <h1 style={{ margin: 0 }}>Opportunity Details</h1>
          <button className="btn btn-secondary" onClick={() => { setSelectedOpp(null); setRefreshSuccessMsg(null); }}>
            ← Back to List
          </button>
        </div>

        {refreshSuccessMsg && (
          <div style={{ color: '#065f46', background: '#d1fae5', padding: '12px', borderRadius: '6px', marginTop: '16px' }}>
            ✓ {refreshSuccessMsg}
          </div>
        )}

        {/* Section 1: Basic Information */}
        <div className="card" style={{ marginTop: '16px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '12px', marginBottom: '16px' }}>
            <h2 style={{ marginTop: 0, flex: 1 }}>{selectedOpp.title}</h2>
            <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
              <span className="badge" style={{ background: '#e0e7ff', color: '#3730a3', fontSize: '0.85rem' }}>{selectedOpp.type}</span>
              <span className={`badge ${selectedOpp.status === 'OPEN' ? 'active' : 'inactive'}`} style={{ fontSize: '0.85rem' }}>
                {selectedOpp.status}
              </span>
              {selectedOpp.detail_solved && (
                <span className="badge" style={{ background: '#dcfce7', color: '#15803d', fontSize: '0.85rem' }}>
                  ✓ Captcha Solved & Enriched
                </span>
              )}
              {(selectedOpp as any).ai?.processed && (
                <span className="badge" style={{ background: '#ede9fe', color: '#5b21b6', fontSize: '0.85rem' }}>🤖 AI Enhanced</span>
              )}
            </div>
          </div>

          <h3 style={{ borderBottom: '1px solid #e2e8f0', paddingBottom: '8px', marginTop: 0, fontSize: '1.05rem', color: '#1e293b' }}>
            Basic Information
          </h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '12px', marginBottom: '20px' }}>
            <div><strong>Title:</strong> {selectedOpp.title}</div>
            <div><strong>Type:</strong> {selectedOpp.type}</div>
            <div><strong>Reference No:</strong> {selectedOpp.reference_number || selectedOpp.reference_number_raw || 'N/A'}</div>
            <div><strong>Organization:</strong> {selectedOpp.organization || 'N/A'}</div>
            <div><strong>Department:</strong> {selectedOpp.department || 'N/A'}</div>
          </div>

          {/* Section 2: Opportunity Details */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid #e2e8f0', paddingBottom: '8px' }}>
            <h3 style={{ margin: 0, fontSize: '1.05rem', color: '#1e293b' }}>
              Opportunity Specifications & Fees
            </h3>
            {selectedOpp.detail_enriching && (
              <span style={{ fontSize: '0.8rem', color: '#0284c7', background: '#e0f2fe', padding: '2px 8px', borderRadius: '4px', display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                🔄 Auto-Enriching in Background
              </span>
            )}
          </div>

          {selectedOpp.detail_enriching && (
            <div style={{ background: '#f0f9ff', border: '1px solid #7dd3fc', padding: '12px 16px', borderRadius: '8px', margin: '14px 0', display: 'flex', alignItems: 'center', gap: '10px' }}>
              <span style={{ fontSize: '1.3rem' }}>⏳</span>
              <div>
                <strong style={{ color: '#0369a1', fontSize: '0.9rem' }}>Auto-Enriching Details & CAPTCHA in Background...</strong>
                <p style={{ margin: '2px 0 0', color: '#0c4a6e', fontSize: '0.8rem' }}>
                  Solving portal CAPTCHA to automatically retrieve tender fees, EMD, work specifications, and official documents. This view will update live automatically!
                </p>
              </div>
            </div>
          )}

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '12px', margin: '16px 0 20px' }}>
            <div><strong>Category:</strong> {selectedOpp.category_name || selectedOpp.tender_category || (selectedOpp.detail_enriching ? '⏳ Fetching...' : 'General')}</div>
            <div><strong>Product Category:</strong> {selectedOpp.product_category || (selectedOpp.detail_enriching ? '⏳ Fetching...' : 'General')}</div>
            <div><strong>Location:</strong> {selectedOpp.location || (selectedOpp.detail_enriching ? '⏳ Fetching...' : 'N/A')} {selectedOpp.pincode ? `(PIN: ${selectedOpp.pincode})` : ''}</div>
            <div><strong>Tender Fee:</strong> {selectedOpp.tender_fee ? `₹ ${selectedOpp.tender_fee}` : (selectedOpp.detail_enriching ? '⏳ Fetching...' : 'Free / Not Specified')}</div>
            <div><strong>EMD Amount:</strong> {selectedOpp.emd_amount ? `₹ ${selectedOpp.emd_amount}` : (selectedOpp.detail_enriching ? '⏳ Fetching...' : 'Not Specified')}</div>
            <div><strong>Estimated Value:</strong> {fmtValue(selectedOpp)}</div>
            <div><strong>Published Date:</strong> {fmtDate(selectedOpp.published_at)}</div>
            <div><strong>Deadline:</strong> {fmtDate(selectedOpp.deadline)}</div>
          </div>

          {selectedOpp.description && (
            <div style={{ marginBottom: '20px' }}>
              <strong>Work Description / Scope:</strong>
              <div style={{ background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: '6px', padding: '14px', marginTop: '6px', whiteSpace: 'pre-wrap', fontSize: '0.875rem', color: '#334155' }}>
                {selectedOpp.description}
              </div>
            </div>
          )}

          {/* Section 3: Supporting Documents */}
          <div style={{ marginBottom: '24px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid #e2e8f0', paddingBottom: '8px', flexWrap: 'wrap', gap: '8px' }}>
              <h3 style={{ margin: 0, fontSize: '1.05rem', color: '#1e293b' }}>
                📎 Official Tender Documents ({selectedOpp.documents?.length || 0})
              </h3>
              {selectedOpp.documents && selectedOpp.documents.length > 0 && (
                <span style={{ fontSize: '0.78rem', color: '#059669', background: '#dcfce7', padding: '2px 8px', borderRadius: '4px' }}>
                  ✓ Direct Server Download Available
                </span>
              )}
            </div>

            {selectedOpp.documents && selectedOpp.documents.length > 0 ? (
              <>
                <div style={{ display: 'grid', gap: '8px', marginTop: '12px' }}>
                  {selectedOpp.documents.map((doc, idx) => (
                    <div
                      key={idx}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        background: '#f8fafc',
                        padding: '12px 14px',
                        borderRadius: '6px',
                        border: '1px solid #e2e8f0',
                        flexWrap: 'wrap',
                        gap: '10px'
                      }}
                    >
                      <span style={{ fontSize: '0.875rem', fontWeight: 500, color: '#1e293b', wordBreak: 'break-all', flex: 1, minWidth: '220px' }}>
                        📄 {doc.title || `Tender Document ${idx + 1}`}
                      </span>
                      <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                        {/* Primary Download via backend proxy to bypass portal Unauthorized error */}
                        <a
                          href={api.getDocumentDownloadUrl(selectedOpp._id, idx)}
                          download
                          className="btn btn-sm"
                          style={{
                            background: '#059669',
                            color: '#fff',
                            fontSize: '0.8rem',
                            padding: '6px 12px',
                            textDecoration: 'none',
                            borderRadius: '4px',
                            whiteSpace: 'nowrap',
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '4px'
                          }}
                          title="Downloads document directly via TenderMate backend session"
                        >
                          📥 Download Document
                        </a>

                        {/* Direct portal link */}
                        <a
                          href={doc.url}
                          target="_blank"
                          rel="noopener"
                          referrerPolicy="no-referrer-when-downgrade"
                          className="btn btn-sm btn-secondary"
                          style={{
                            fontSize: '0.8rem',
                            padding: '6px 10px',
                            textDecoration: 'none',
                            borderRadius: '4px',
                            whiteSpace: 'nowrap'
                          }}
                          title="Open portal document link in new tab"
                        >
                          ↗ Open Portal Link
                        </a>
                      </div>
                    </div>
                  ))}
                </div>

                <div style={{ marginTop: '12px', padding: '10px 14px', background: '#eff6ff', borderRadius: '6px', fontSize: '0.8rem', color: '#1e40af', lineHeight: 1.4 }}>
                  💡 <strong>Document Access Note:</strong> Government portals (such as NTPC, Coal India, or CPPP) protect direct document links with session security and show an <em>"Unauthorized Page"</em> if accessed directly from external links. Always click <strong>"📥 Download Document"</strong> to download directly through TenderMate's authenticated session proxy.
                </div>
              </>
            ) : selectedOpp.detail_enriching ? (
              <div style={{ marginTop: '12px', padding: '16px', background: '#f0f9ff', borderRadius: '6px', border: '1px solid #bae6fd', color: '#0369a1' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{ fontSize: '1.2rem' }}>🔄</span>
                  <strong>Solving CAPTCHA and extracting official documents...</strong>
                </div>
                <p style={{ margin: '6px 0 0 28px', fontSize: '0.82rem', color: '#0c4a6e' }}>
                  Documents will appear here automatically once the background queue solves the portal challenge.
                </p>
              </div>
            ) : (
              <p style={{ color: '#64748b', fontSize: '0.875rem', marginTop: '12px' }}>
                No documents extracted yet. Click <strong>"Re-fetch / Get More Details"</strong> below to connect to the portal and retrieve them.
              </p>
            )}
          </div>

          {/* Section 4: Tender Inviting Authority */}
          {(selectedOpp.inviting_authority_name || selectedOpp.inviting_authority_address || selectedOpp.contacts?.emails?.length) && (
            <div style={{ marginBottom: '20px' }}>
              <h3 style={{ borderBottom: '1px solid #e2e8f0', paddingBottom: '8px', fontSize: '1.05rem', color: '#1e293b' }}>
                🏛️ Tender Inviting Authority & Contacts
              </h3>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '12px', marginBottom: '10px' }}>
                {selectedOpp.inviting_authority_name && (
                  <div><strong>Authority Name:</strong> {selectedOpp.inviting_authority_name}</div>
                )}
                {selectedOpp.inviting_authority_address && (
                  <div><strong>Authority Address:</strong> {selectedOpp.inviting_authority_address}</div>
                )}
              </div>
              <p style={{ margin: '4px 0' }}>
                <strong>Emails:</strong> {selectedOpp.contacts?.emails?.length ? selectedOpp.contacts.emails.join(', ') : 'None listed'}
              </p>
              <p style={{ margin: '4px 0' }}>
                <strong>Phones:</strong> {selectedOpp.contacts?.phones?.length ? selectedOpp.contacts.phones.join(', ') : 'None listed'}
              </p>
            </div>
          )}

          {/* Section 5: Source Information & Session Expiry Handling */}
          <h3 style={{ borderBottom: '1px solid #e2e8f0', paddingBottom: '8px', fontSize: '1.05rem', color: '#1e293b' }}>
            Portal Source & Session Link Handling
          </h3>
          <div style={{ marginBottom: '20px' }}>
            <p><strong>Source Name:</strong> {sources[selectedOpp.source_id] || selectedOpp.source_id}</p>

            <div style={{ background: '#f0f9ff', border: '1px solid #bae6fd', padding: '14px', borderRadius: '8px', marginTop: '12px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
                <span style={{ fontSize: '1.2rem' }}>ℹ️</span>
                <strong style={{ color: '#0369a1', fontSize: '0.95rem' }}>Government CPPP Portal Session Notice</strong>
              </div>
              <p style={{ margin: '0 0 12px', fontSize: '0.875rem', color: '#0c4a6e', lineHeight: 1.5 }}>
                CPPP portal detail links contain time-limited session tokens. Opening an expired link directly in a new tab causes the portal to return an <em>"Invalid URL"</em> error.
                TenderMate bypasses this by solving the CAPTCHA in an active session and saving all tender specifications, work descriptions, and document links above.
              </p>
              <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap', alignItems: 'center' }}>
                <button
                  className="btn"
                  style={{ background: '#0284c7', color: '#fff', fontSize: '0.85rem' }}
                  onClick={() => handleRefreshTender(selectedOpp._id)}
                  disabled={refreshingTender}
                >
                  {refreshingTender ? '🔄 Solving Captcha & Refreshing...' : '🔄 Re-fetch / Get More Details'}
                </button>
                <a
                  href="https://eprocure.gov.in/cppp/latestactivetendersnew/cpppdata"
                  target="_blank"
                  rel="noreferrer"
                  className="btn btn-secondary"
                  style={{ fontSize: '0.85rem' }}
                >
                  🏛️ Open CPPP Portal Homepage
                </a>
              </div>
            </div>
          </div>

          {/* Section 6: Detection Logic */}
          <h3 style={{ borderBottom: '1px solid #e2e8f0', paddingBottom: '8px', fontSize: '1.05rem', color: '#1e293b' }}>
            Detection & Rule Explanation
          </h3>
          <div>
            <p><strong>Rule Detection Reason:</strong> {selectedOpp.detection_reason || 'Matched opportunity keywords'}</p>
          </div>
        </div>

        {/* Section 7: AI Analysis */}
        <AIAnalysisSection
          opp={selectedOpp}
          onRefresh={(updated) => setSelectedOpp(updated)}
        />
      </div>
    );
  }

  const pendingEnrichCount = opportunities.filter(o => !o.detail_solved).length;

  return (
    <div>
      <div className="header-row" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
        <h1 style={{ margin: 0 }}>Opportunities & Tenders</h1>
        {pendingEnrichCount > 0 && (
          <button
            className="btn"
            style={{
              background: '#0284c7',
              color: '#fff',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              fontSize: '0.85rem'
            }}
            onClick={handleBatchEnrich}
            disabled={batchEnriching}
          >
            {batchEnriching ? '⏳ Queuing Batch...' : `⚡ Auto-Enrich All Pending (${pendingEnrichCount})`}
          </button>
        )}
      </div>

      {batchMsg && (
        <div style={{ background: '#f0fdf4', border: '1px solid #86efac', color: '#166534', padding: '10px 14px', borderRadius: '6px', margin: '14px 0', fontSize: '0.875rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span>{batchMsg}</span>
          <button style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: '#166534', fontWeight: 'bold' }} onClick={() => setBatchMsg(null)}>✕</button>
        </div>
      )}

      {/* Filter Bar */}
      <div className="card" style={{ marginBottom: '20px', padding: '16px' }}>
        <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap', alignItems: 'center' }}>
          <div>
            <label style={{ fontSize: '0.85rem', fontWeight: 600, display: 'block', marginBottom: '4px' }}>Source Portal</label>
            <select
              className="form-control"
              value={sourceFilter}
              onChange={e => { setSourceFilter(e.target.value); setPage(0); }}
              style={{ minWidth: '160px' }}
            >
              <option value="">All Sources</option>
              {Object.entries(sources).map(([id, name]) => (
                <option key={id} value={id}>{name}</option>
              ))}
            </select>
          </div>

          <div>
            <label style={{ fontSize: '0.85rem', fontWeight: 600, display: 'block', marginBottom: '4px' }}>Type</label>
            <select
              className="form-control"
              value={typeFilter}
              onChange={e => { setTypeFilter(e.target.value); setPage(0); }}
              style={{ minWidth: '140px' }}
            >
              <option value="">All Types</option>
              <option value="TENDER">TENDER</option>
              <option value="PROJECT">PROJECT</option>
              <option value="PROCUREMENT">PROCUREMENT</option>
              <option value="NEWS">NEWS</option>
              <option value="BUSINESS_OPPORTUNITY">BUSINESS OPPORTUNITY</option>
              <option value="OTHER">OTHER</option>
            </select>
          </div>

          <div>
            <label style={{ fontSize: '0.85rem', fontWeight: 600, display: 'block', marginBottom: '4px' }}>Status</label>
            <select
              className="form-control"
              value={statusFilter}
              onChange={e => { setStatusFilter(e.target.value); setPage(0); }}
              style={{ minWidth: '120px' }}
            >
              <option value="">All Statuses</option>
              <option value="OPEN">OPEN</option>
              <option value="CLOSED">CLOSED</option>
              <option value="ARCHIVED">ARCHIVED</option>
            </select>
          </div>

          {categories.length > 0 && (
            <div>
              <label style={{ fontSize: '0.85rem', fontWeight: 600, display: 'block', marginBottom: '4px' }}>Category</label>
              <select
                className="form-control"
                value={categoryFilter}
                onChange={e => { setCategoryFilter(e.target.value); setPage(0); }}
                style={{ minWidth: '150px' }}
              >
                <option value="">All Categories</option>
                {categories.map(c => (
                  <option key={c._id} value={c._id}>{c.name}</option>
                ))}
              </select>
            </div>
          )}

          {(sourceFilter || typeFilter || statusFilter || categoryFilter) && (
            <button
              className="btn btn-secondary"
              style={{ marginTop: '20px' }}
              onClick={() => { setSourceFilter(''); setTypeFilter(''); setStatusFilter(''); setCategoryFilter(''); setPage(0); }}
            >
              Reset Filters
            </button>
          )}
        </div>
      </div>

      {/* Main List */}
      <div className="card">
        {error && (
          <div style={{ color: '#991b1b', background: '#fef2f2', padding: '12px', borderRadius: '6px', marginBottom: '16px' }}>
            {error}
          </div>
        )}

        {loading && opportunities.length === 0 ? (
          <div style={{ padding: '40px', textAlign: 'center', color: '#64748b' }}>Loading opportunities...</div>
        ) : opportunities.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '48px', color: '#64748b' }}>
            <p style={{ fontSize: '1.1rem', marginBottom: '8px' }}>No opportunities found.</p>
            <p>Go to <strong>Sources</strong> and click <strong>Collect Tenders</strong> to extract opportunities from live portals.</p>
          </div>
        ) : (
          <>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.9rem' }}>
              <thead>
                <tr style={{ borderBottom: '2px solid #e2e8f0', background: '#f8fafc' }}>
                  <th style={{ padding: '12px 10px', width: '45px', textAlign: 'center' }}>#</th>
                  <th style={{ padding: '12px 10px' }}>Title</th>
                  <th style={{ padding: '12px 10px' }}>Type</th>
                  <th style={{ padding: '12px 10px' }}>Ref No / ID</th>
                  <th style={{ padding: '12px 10px' }}>Organization</th>
                  <th style={{ padding: '12px 10px' }}>Location</th>
                  <th style={{ padding: '12px 10px' }}>Value / EMD</th>
                  <th style={{ padding: '12px 10px' }}>Deadline</th>
                  <th style={{ padding: '12px 10px' }}>Status</th>
                  <th style={{ padding: '12px 10px', textAlign: 'center' }}>Docs</th>
                  <th style={{ padding: '12px 10px', textAlign: 'center' }}>AI</th>
                </tr>
              </thead>
              <tbody>
                {opportunities.map((opp, idx) => {
                  const isEnriching = opp.detail_enriching;
                  return (
                    <tr
                      key={opp._id}
                      style={{
                        borderBottom: '1px solid #e2e8f0',
                        cursor: 'pointer',
                        background: isEnriching ? '#f0f9ff' : undefined,
                        transition: 'background-color 0.2s ease'
                      }}
                      onClick={() => setSelectedOpp(opp)}
                      onMouseEnter={e => (e.currentTarget.style.background = isEnriching ? '#e0f2fe' : '#f8fafc')}
                      onMouseLeave={e => (e.currentTarget.style.background = isEnriching ? '#f0f9ff' : '')}
                    >
                      {/* Synchronized Row Number */}
                      <td style={{ padding: '12px 10px', textAlign: 'center', fontWeight: 600, color: '#64748b' }}>
                        {page * limit + idx + 1}
                      </td>
                      <td style={{ padding: '12px 10px', maxWidth: '280px', fontWeight: 500 }}>
                        <div style={{ overflow: 'hidden', textOverflow: 'ellipsis', display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical' }}>
                          {opp.title}
                        </div>
                        {isEnriching && (
                          <div style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', color: '#0284c7', fontSize: '0.72rem', marginTop: '2px', background: '#e0f2fe', padding: '1px 6px', borderRadius: '4px' }}>
                            <span>🔄</span> Solving CAPTCHA...
                          </div>
                        )}
                      </td>
                      <td style={{ padding: '12px 10px', whiteSpace: 'nowrap' }}>
                        <span className="badge" style={{ background: '#e0e7ff', color: '#3730a3', fontSize: '0.75rem' }}>
                          {opp.type}
                        </span>
                      </td>
                      <td style={{ padding: '12px 10px', whiteSpace: 'nowrap', color: '#64748b', fontSize: '0.85rem' }}>
                        {opp.reference_number || opp.reference_number_raw || '—'}
                      </td>
                      <td style={{ padding: '12px 10px', maxWidth: '160px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {opp.organization || '—'}
                      </td>
                      <td style={{ padding: '12px 10px', whiteSpace: 'nowrap' }}>
                        {opp.location || (isEnriching ? '⏳ Fetching...' : '—')}
                      </td>
                      <td style={{ padding: '12px 10px', whiteSpace: 'nowrap', fontWeight: 600, color: '#059669' }}>
                        {opp.emd_amount ? `EMD: ₹ ${opp.emd_amount}` : fmtValue(opp)}
                      </td>
                      <td style={{ padding: '12px 10px', whiteSpace: 'nowrap', fontSize: '0.85rem' }}>
                        {fmtDate(opp.deadline)}
                      </td>
                      <td style={{ padding: '12px 10px', whiteSpace: 'nowrap' }}>
                        <span className={`badge ${opp.status === 'OPEN' ? 'active' : 'inactive'}`}>
                          {opp.status}
                        </span>
                      </td>
                      <td style={{ padding: '12px 10px', textAlign: 'center' }}>
                        {isEnriching ? (
                          <span title="Auto-fetching official documents in background..." style={{ color: '#0284c7', fontSize: '0.8rem', fontWeight: 600 }}>
                            🔄
                          </span>
                        ) : opp.documents && opp.documents.length > 0 ? (
                          <span title={`${opp.documents.length} document(s)`} style={{ color: '#2563eb', fontWeight: 600 }}>
                            📎 {opp.documents.length}
                          </span>
                        ) : (
                          <span style={{ color: '#cbd5e1' }}>—</span>
                        )}
                      </td>
                      <td style={{ padding: '12px 10px', textAlign: 'center' }}>
                        {(opp as any).ai?.processed
                          ? <span title="AI Enhanced" style={{ fontSize: '1rem' }}>🤖</span>
                          : <span title="Not analyzed" style={{ fontSize: '0.75rem', color: '#94a3b8' }}>—</span>
                        }
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>

            {/* Enhanced Pagination Controls */}
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                marginTop: '24px',
                flexWrap: 'wrap',
                gap: '16px',
                paddingTop: '16px',
                borderTop: '1px solid #e2e8f0'
              }}
            >
              {/* Results count label */}
              <div style={{ color: '#64748b', fontSize: '0.875rem' }}>
                Showing <strong>{totalCount === 0 ? 0 : page * limit + 1}</strong> to{' '}
                <strong>{Math.min((page + 1) * limit, totalCount)}</strong> of{' '}
                <strong>{totalCount}</strong> opportunities
              </div>

              {/* Numbered Pagination Buttons */}
              <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
                <button
                  className="btn btn-secondary"
                  style={{ padding: '6px 10px', fontSize: '0.85rem' }}
                  disabled={page === 0 || loading}
                  onClick={() => setPage(0)}
                  title="First Page"
                >
                  « First
                </button>
                <button
                  className="btn btn-secondary"
                  style={{ padding: '6px 12px', fontSize: '0.85rem' }}
                  disabled={page === 0 || loading}
                  onClick={() => setPage(p => Math.max(0, p - 1))}
                >
                  ‹ Prev
                </button>

                {renderPaginationButtons()}

                <button
                  className="btn btn-secondary"
                  style={{ padding: '6px 12px', fontSize: '0.85rem' }}
                  disabled={page >= totalPages - 1 || loading}
                  onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))}
                >
                  Next ›
                </button>
                <button
                  className="btn btn-secondary"
                  style={{ padding: '6px 10px', fontSize: '0.85rem' }}
                  disabled={page >= totalPages - 1 || loading}
                  onClick={() => setPage(totalPages - 1)}
                  title="Last Page"
                >
                  Last »
                </button>
              </div>

              {/* Items Per Page Selector */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ color: '#64748b', fontSize: '0.85rem' }}>Per page:</span>
                <select
                  className="form-control"
                  style={{ width: '80px', padding: '4px 8px', fontSize: '0.85rem' }}
                  value={limit}
                  onChange={e => {
                    setLimit(Number(e.target.value));
                    setPage(0);
                  }}
                >
                  <option value={10}>10</option>
                  <option value={20}>20</option>
                  <option value={50}>50</option>
                  <option value={100}>100</option>
                </select>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

