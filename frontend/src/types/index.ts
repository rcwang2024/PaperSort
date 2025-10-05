export interface Paper {
  id: number;
  title: string;
  authors: string[];
  year?: number;
  path: string;
  abstract?: string;
  full_text?: string;
  doi?: string;
  arxiv_id?: string;
  url?: string;
  source?: string;
}

export interface Topic {
  name: string;
  count: number;
  papers: Paper[];
  summary?: string;
}

export interface OrganizeRequest {
  folder_path: string;
  num_topics?: number;
  custom_topics?: string[];
  copy_mode: boolean;
  enhance_metadata: boolean;
}

export interface OrganizeResponse {
  success: boolean;
  input_folder: string;
  total_papers: number;
  processed_papers: number;
  topics: Record<string, Paper[]>;
  bibtex_file?: string;
  errors: string[];
}

export interface ProgressUpdate {
  status: 'starting' | 'processing' | 'completed' | 'failed';
  progress: number;
  message: string;
  results?: any;
}

export interface MindMapRequest {
  paper_id?: number;
  paper_title: string;
  abstract: string;
  full_text?: string;
  include_methodology?: boolean;
  include_results?: boolean;
  max_depth?: number;
}

export interface MindMapNode {
  id: string;
  label: string;
  type: string;
  children: MindMapNode[];
}

export interface MindMapResponse {
  paper_id?: number;
  paper_title: string;
  root_node: MindMapNode;
  svg_data: string;
  summary?: string;
  generation_time: number;
}
