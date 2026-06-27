export interface PageSummary {
  id: string;
  page_number: number;
  status: string;
  original_path: string;
  cleaned_path?: string;
  translated_path?: string;
}

export interface ProjectDetail {
  id: string;
  name: string;
  source_language?: string;
  status: string;
  total_pages: number;
  processed_pages: number;
  created_at: string;
  updated_at: string;
  pages: PageSummary[];
}

export interface TranslationEntry {
  id: string;
  page_id: string;
  bubble_index: number;
  original_text: string;
  translated_text: string;
  x: number;
  y: number;
  w: number;
  h: number;
}

export interface Character {
  id: string;
  name_original: string;
  name_translated: string;
  description?: string;
  first_seen_page?: number;
}

export interface GlossaryEntry {
  id: string;
  term_original: string;
  term_translated: string;
  category: string;
}

export interface Bubble {
  x: number;
  y: number;
  w: number;
  h: number;
  confidence?: number;
  class?: string;
}

export interface ProgressEvent {
  stage: string;
  page_number?: number;
}

export type ProcessingStage =
  | "idle"
  | "bubble_detection"
  | "ocr"
  | "context_built"
  | "translation"
  | "inpainting"
  | "typesetting"
  | "completed"
  | "error";
