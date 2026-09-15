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
