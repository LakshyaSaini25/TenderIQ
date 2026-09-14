import { useState, useEffect } from 'react';
import { Source, SourceCreate, SourceType, CrawlFrequency } from '../../types';

interface SourceFormModalProps {
  source?: Source | null;
  onClose: () => void;
  onSave: (data: SourceCreate) => Promise<void>;
}

export function SourceFormModal({ source, onClose, onSave }: SourceFormModalProps) {
  const [formData, setFormData] = useState<SourceCreate>({
    name: '',
    url: '',
    type: SourceType.COMPANY_WEBSITE,
    crawl_frequency: CrawlFrequency.DAILY,
    is_active: true
  });
  
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (source) {
      setFormData({
        name: source.name,
        url: source.url,
        type: source.type,
        crawl_frequency: source.crawl_frequency,
        is_active: source.is_active
      });
    }
  }, [source]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    
    try {
      // Basic URL validation
      new URL(formData.url);
      await onSave(formData);
    } catch (err: any) {
      setError(err instanceof TypeError ? 'Please enter a valid URL (include http/https)' : err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay">
      <div className="modal-content">
        <h2 style={{ marginTop: 0 }}>{source ? 'Edit Website' : 'Add Website'}</h2>
        
        {error && <div style={{ color: 'red', marginBottom: '16px' }}>{error}</div>}
        
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Website Name</label>
            <input 
              type="text" 
              className="form-control" 
              required
              value={formData.name}
              onChange={e => setFormData({...formData, name: e.target.value})}
              placeholder="e.g., ABC Infrastructure"
            />
          </div>
          
          <div className="form-group">
            <label>Website URL</label>
            <input 
              type="url" 
              className="form-control" 
              required
              value={formData.url}
              onChange={e => setFormData({...formData, url: e.target.value})}
              placeholder="https://example.com"
            />
          </div>
          
          <div className="form-group">
            <label>Source Type</label>
            <select 
              className="form-control"
              value={formData.type}
              onChange={e => setFormData({...formData, type: e.target.value as SourceType})}
            >
              {Object.values(SourceType).map(type => (
                <option key={type} value={type}>{type.replace('_', ' ')}</option>
              ))}
            </select>
          </div>
          
          <div className="form-group">
            <label>Crawl Frequency</label>
            <select 
              className="form-control"
              value={formData.crawl_frequency}
              onChange={e => setFormData({...formData, crawl_frequency: e.target.value as CrawlFrequency})}
            >
              {Object.values(CrawlFrequency).map(freq => (
                <option key={freq} value={freq}>{freq.replace(/_/g, ' ')}</option>
              ))}
            </select>
          </div>
          
          <div className="form-group" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <input 
              type="checkbox" 
              id="is_active"
              checked={formData.is_active}
              onChange={e => setFormData({...formData, is_active: e.target.checked})}
            />
            <label htmlFor="is_active" style={{ marginBottom: 0 }}>Active</label>
          </div>
          
          <div className="form-actions">
            <button type="button" className="btn btn-secondary" onClick={onClose} disabled={loading}>
              Cancel
            </button>
            <button type="submit" className="btn" disabled={loading}>
              {loading ? 'Saving...' : 'Save'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

