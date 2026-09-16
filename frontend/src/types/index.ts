export enum SourceType {
  GOVERNMENT = "GOVERNMENT",
  TENDER_PORTAL = "TENDER_PORTAL",
  COMPANY_WEBSITE = "COMPANY_WEBSITE",
  NEWS = "NEWS",
  PROJECT_PORTAL = "PROJECT_PORTAL",
  OTHER = "OTHER"
}

export enum CrawlFrequency {
  HOURLY = "HOURLY",
  EVERY_6_HOURS = "EVERY_6_HOURS",
  DAILY = "DAILY",
  WEEKLY = "WEEKLY"
}

export interface Source {
  _id: string;
  name: string;
  url: string;
  type: SourceType;
  crawl_frequency: CrawlFrequency;
  is_active: boolean;
  last_checked_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface SourceCreate {
  name: string;
  url: string;
  type: SourceType;
  crawl_frequency: CrawlFrequency;
  is_active: boolean;
}

export interface SourceUpdate {
  name?: string;
  url?: string;
  type?: SourceType;
  crawl_frequency?: CrawlFrequency;
  is_active?: boolean;
}

export enum ContentStatus {
  ACTIVE = "ACTIVE",
  ARCHIVED = "ARCHIVED"
}

export interface Content {
  _id: string;
  source_id: string;
  url: string;
  title: string;
  content: string;
  content_hash: string;
  published_at: string | null;
  last_seen_at: string;
  first_seen_at: string;
  status: ContentStatus;
  created_at: string;
  updated_at: string;
}

export interface CollectResult {
  status: string; // CREATED | UNCHANGED | UPDATED | FAILED
  source_id: string;
  url: string;
  content_id?: string;
  error?: string;
}

export enum OpportunityType {
  TENDER = "TENDER",
  PROJECT = "PROJECT",
  PROCUREMENT = "PROCUREMENT",
  NEWS = "NEWS",
  BUSINESS_OPPORTUNITY = "BUSINESS_OPPORTUNITY",
  OTHER = "OTHER"
}

export enum OpportunityStatus {
  OPEN = "OPEN",
  CLOSED = "CLOSED",
  ARCHIVED = "ARCHIVED"
}

export interface Contacts {
  emails: string[];
  phones: string[];
}

export interface TenderDocument {
  title: string;
  url: string;
}

export interface Opportunity {
  _id: string;
  source_id: string;
  content_id?: string | null;
  type: OpportunityType;
  title: string;
  reference_number?: string | null;
  reference_number_raw?: string | null;
  description?: string | null;
  organization?: string | null;
  department?: string | null;
  location?: string | null;
  category_id?: string | null;
  category_name?: string | null;
  value?: number | string | null;
  currency?: string | null;
  value_text?: string | null;
  published_at?: string | null;
  deadline?: string | null;
  contacts?: Contacts;
  source_url: string;
  status: OpportunityStatus;
  is_opportunity?: boolean;
  detection_reason?: string | null;

  // Enriched detail fields
  tender_fee?: string | null;
  emd_amount?: string | null;
  tender_category?: string | null;
  product_category?: string | null;
  pincode?: string | null;
  inviting_authority_name?: string | null;
  inviting_authority_address?: string | null;
  documents?: TenderDocument[];
  detail_solved?: boolean;
  detail_enriching?: boolean;

  // Phase 6 AI fields
  eligibility?: string[];
  requirements?: string[];
  scope?: string[];
  certifications?: string[];
  experience_requirements?: string[];
  equipment_requirements?: string[];
  ai?: AIMetadata | null;

  created_at: string;
  updated_at: string;
}

export interface AIMetadata {
  processed: boolean;
  model?: string | null;
  prompt_version?: string | null;
  processed_at?: string | null;
  confidence?: number | null;
  error?: string | null;
}

export interface Category {
  _id: string;
  name: string;
  parent_id?: string | null;
}

export interface OpportunityCollectSummary {
  source_id: string;
  discovered: number;
  created: number;
  updated: number;
  unchanged: number;
  failed: number;
}

export interface ProcessSourceSummary {
  source_id: string;
  processed: number;
  opportunities_created: number;
  opportunities_updated: number;
  not_opportunities: number;
  failed: number;
}

export interface AIProcessResult {
  content_id: string;
  opportunity_id?: string | null;
  ai_status: string; // "SUCCESS" | "UNAVAILABLE" | "SKIPPED" | "FAILED"
  ai_model?: string | null;
  processing_duration: number;
  enriched_fields: string[];
  message?: string | null;
}

export interface AIHealthResult {
  available: boolean;
  model?: string | null;
  models_loaded: string[];
  error?: string | null;
}

// ─── Source Discovery ─────────────────────────────────────────────────────────

export interface RecommendedSource {
  name: string;
  url: string;
  type: string;
  description: string;
  tags: string[];
  relevance_score: number;
  is_curated: boolean;
}

// ─── Explore Tenders (Tender247) ─────────────────────────────────────────────

export interface ExploreTenderItem {
  tender_id: number;
  requirement_workbrief?: string;
  estimatedcost?: number;
  tender_endsubmission_datetime?: string;
  site_location?: string;
  organization_name?: string;
  doc_uploaded?: boolean;
  security_code?: string;
  earnest_money_deposite?: number;
  is_favourite?: boolean | null;
  ai_summary?: boolean;
  show_tender_endsubmission?: boolean;
  boq_line_item?: string;
  is_boq_line_item?: number;
  submission_enddate?: string;
}

export interface ExploreSearchPayload {
  tab_id?: number;
  tender_id?: number;
  tender_number?: string;
  search_text?: string;
  refine_search_text?: string;
  boq?: boolean;
  city_ids?: string;
  closing_date_from?: string;
  closing_date_to?: string;
  exact_search?: boolean;
  exact_search_text?: boolean;
  gem?: number;
  guest_user_id?: number;
  is_ai_summary?: boolean;
  is_tender_doc_uploaded?: boolean;
  keyword_id?: number;
  mfa?: string;
  msme?: number;
  nameof_website?: string;
  organization_ids?: number;
  organization_name?: string;
  organization_type_id?: number;
  organization_type_fallback?: string;
  page_no?: number;
  product_id?: number;
  publication_date_from?: string;
  publication_date_to?: string;
  quantity?: string;
  quantityOperator?: number;
  record_per_page?: number;
  search_by?: number;
  search_by_location?: boolean;
  search_by_split_word?: boolean;
  sort_by?: number;
  sort_type?: number;
  startup?: number;
  state_ids?: string;
  statezone_ids?: string;
  sub_industry_id?: number;
  tender_typeid?: number;
  tender_value_from?: number;
  tender_value_operator?: number;
  tender_value_to?: number;
  [key: string]: any;
}

export interface ExploreAISearchResponse {
  status: string;
  data?: {
    url?: string;
    test_url?: string;
    payload?: ExploreSearchPayload;
  };
  meta?: any;
}

export interface ExploreSearchResponse {
  Success: boolean;
  Message: string;
  TotalRecord: number;
  IsAuthFailure?: boolean;
  Data: ExploreTenderItem[];
  StatusCode?: number;
  used_search_by?: number;
}
