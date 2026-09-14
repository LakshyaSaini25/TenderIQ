import { useEffect, useState } from 'react';
import { api } from '../services/api';
import { Source, Opportunity } from '../types';
import { Link } from 'react-router-dom';

export function Dashboard() {
  const [sources, setSources] = useState<Source[]>([]);
  const [opportunities, setOpportunities] = useState<Opportunity[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    try {
      const [sourceData, oppData] = await Promise.all([
        api.getSources(),
        api.getOpportunities().catch(() => [])
      ]);
      setSources(sourceData);
      setOpportunities(oppData);
    } catch (error) {
      console.error('Failed to load dashboard data', error);
    } finally {
      setLoading(false);
    }
  };

  const todayCount = opportunities.filter(o => {
    if (!o.created_at) return false;
    const d = new Date(o.created_at);
    const today = new Date();
    return d.toDateString() === today.toDateString();
  }).length;

  if (loading) return <div style={{ padding: '32px' }}>Loading dashboard...</div>;

  return (
    <div>
      <h1 style={{ marginTop: 0 }}>Dashboard</h1>
      
      <div className="stat-grid">
        <div className="stat-card">
          <h3>Sources Tracked</h3>
          <div className="value">{sources.length}</div>
        </div>
        <div className="stat-card">
          <h3>Opportunities</h3>
          <div className="value">{opportunities.length}</div>
        </div>
        <div className="stat-card">
          <h3>New Today</h3>
          <div className="value">{todayCount}</div>
        </div>
        <div className="stat-card">
          <h3>Matches</h3>
          <div className="value">0</div>
        </div>
      </div>

      <div className="card">
        <div className="header-row">
          <h2 style={{ margin: 0 }}>Recently Added Sources</h2>
          <Link to="/sources" className="btn btn-secondary" style={{ textDecoration: 'none' }}>View All</Link>
        </div>
        
        {sources.length === 0 ? (
          <p>No websites are being tracked yet.</p>
        ) : (
          <div>
            {sources.slice(0, 5).map(source => (
              <div key={source._id} className="source-item">
                <div className="source-header">
                  <div className="source-title">{source.name}</div>
                  <div className={`badge ${source.is_active ? 'active' : 'inactive'}`}>
                    {source.is_active ? 'Active' : 'Inactive'}
                  </div>
                </div>
                <div className="source-url">{source.url}</div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
