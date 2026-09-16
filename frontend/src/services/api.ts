import { Source, SourceCreate, SourceUpdate, Category, AIProcessResult, AIHealthResult, RecommendedSource, ExploreAISearchResponse, ExploreSearchResponse, ExploreSearchPayload } from '../types';


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

  getCuratedSources(category?: string, search?: string) {
    const params = new URLSearchParams();
    if (category && category !== 'All') params.append('category', category);
    if (search && search.trim()) params.append('search', search.trim());
    const query = params.toString() ? `?${params.toString()}` : '';
    return this.request<RecommendedSource[]>(`/sources/curated${query}`);
  }

  getSchedulerStatus() {
    return this.request<any>('/sources/scheduler/status');
  }

  triggerSchedulerNow() {
    return this.request<{ success: boolean; message: string; triggered: any[] }>('/sources/scheduler/run-now', {
      method: 'POST',
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

  // Explore Tenders
  getExploreStates() {
    return this.request<{ state_id: number; state_name: string }[]>('/explore/states');
  }

  getExploreCities(stateId: string | number) {
    return this.request<{ city_id: number; city_name: string }[]>(`/explore/cities?state_id=${stateId}`);
  }

  exploreAISearch(query: string, variables: any = {}) {
    return this.request<ExploreAISearchResponse>('/explore/ai-search', {
      method: 'POST',
      body: JSON.stringify({ query, variables }),
    });
  }

  exploreSearchTenders(payload: ExploreSearchPayload) {
    return this.request<ExploreSearchResponse>('/explore/search', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  exploreCountTenders(payload: ExploreSearchPayload) {
    return this.request<{ Success: boolean; Data: { tendercount: number }[]; StatusCode: number }>('/explore/count', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  exploreAISearchWithResults(query: string, variables: any = {}) {
    return this.request<{
      status: string;
      ai_data: ExploreAISearchResponse;
      search_result: ExploreSearchResponse;
      count_result: any;
      payload: ExploreSearchPayload;
    }>('/explore/ai-search-with-results', {
      method: 'POST',
      body: JSON.stringify({ query, variables }),
    });
  }

  importExploredTender(tender: any) {
    return this.request<{ success: boolean; message: string; opportunity_id?: string }>('/explore/import', {
      method: 'POST',
      body: JSON.stringify({ tender }),
    });
  }
}

export const api = new ApiService();
