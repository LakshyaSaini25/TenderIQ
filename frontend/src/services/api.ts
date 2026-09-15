import { Source, SourceCreate, SourceUpdate, Category, AIProcessResult, AIHealthResult, RecommendedSource } from '../types';


const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

class ApiService {
  private async request<T>(endpoint: string, options?: RequestInit): Promise<T> {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `API error: ${response.statusText}`);
    }

    if (response.status === 204) {
      return {} as T;
    }

    return response.json();
  }

  // System Health
  checkHealth() {
    return this.request<{ status: string }>('/health');
  }
  
  checkDbHealth() {
    return this.request<{ status: string; database: string }>('/health/db');
  }

  // Sources
  getSources() {
    return this.request<Source[]>('/sources');
  }

  getSource(id: string) {
    return this.request<Source>(`/sources/${id}`);
  }

  createSource(data: SourceCreate) {
    return this.request<Source>('/sources', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  updateSource(id: string, data: SourceUpdate) {
    return this.request<Source>(`/sources/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  deleteSource(id: string) {
    return this.request<void>(`/sources/${id}`, {
      method: 'DELETE',
    });
  }

  discoverSources(state: string, city?: string) {
    return this.request<RecommendedSource[]>('/sources/discover', {
      method: 'POST',
      body: JSON.stringify({ state, city: city && city !== 'All Cities' ? city : undefined }),
    });
  }

  // Content
  collectContent(sourceId: string) {
    return this.request<any>(`/content/collect/${sourceId}`, {
      method: 'POST',
    });
  }

  getContents(skip = 0, limit = 100) {
    return this.request<any[]>(`/content?skip=${skip}&limit=${limit}`);
  }

  getContent(id: string) {
    return this.request<any>(`/content/${id}`);
  }

  // Opportunities
  collectOpportunities(sourceId: string) {
    return this.request<any>(`/opportunities/collect/${sourceId}`, {
      method: 'POST',
    });
  }

  processSingleContent(contentId: string) {
    return this.request<any>(`/opportunities/process/${contentId}`, {
      method: 'POST',
    });
  }

  processSourceContent(sourceId: string) {
    return this.request<any>(`/opportunities/process-source/${sourceId}`, {
      method: 'POST',
    });
  }

  getOpportunities(sourceId?: string, type?: string, status?: string, categoryId?: string, skip = 0, limit = 100) {
    const params = new URLSearchParams();
    if (sourceId) params.append('source_id', sourceId);
    if (type) params.append('type', type);
    if (status) params.append('status', status);
    if (categoryId) params.append('category_id', categoryId);
    params.append('skip', skip.toString());
    params.append('limit', limit.toString());

    return this.request<any[]>(`/opportunities?${params.toString()}`);
  }

  getOpportunitiesCount(sourceId?: string, type?: string, status?: string, categoryId?: string) {
    const params = new URLSearchParams();
    if (sourceId) params.append('source_id', sourceId);
    if (type) params.append('type', type);
    if (status) params.append('status', status);
    if (categoryId) params.append('category_id', categoryId);

    return this.request<number>(`/opportunities/count?${params.toString()}`);
  }

  getOpportunity(id: string) {
    return this.request<any>(`/opportunities/${id}`);
  }

  refreshOpportunityDetail(id: string) {
    return this.request<any>(`/opportunities/${id}/refresh-detail`, {
      method: 'POST',
    });
  }

  batchRefreshOpportunities() {
    return this.request<{ status: string; queued: number; message: string }>('/opportunities/batch-refresh', {
      method: 'POST',
    });
  }

  getDocumentDownloadUrl(opportunityId: string, docIndex: number) {
    return `${API_BASE_URL}/opportunities/${opportunityId}/documents/${docIndex}/download`;
  }

  // Categories & Locations
  getCategories() {
    return this.request<Category[]>('/categories');
  }

  getLocations() {
    return this.request<any[]>('/locations');
  }

  // AI
  analyzeWithAI(contentId: string) {
    return this.request<AIProcessResult>(`/opportunities/ai-process/${contentId}`, {
      method: 'POST',
    });
  }

  checkAIHealth() {
    return this.request<AIHealthResult>('/ai/health');
  }
}

export const api = new ApiService();
