// Job status types
export type JobStatus = 'new' | 'reviewed' | 'applied' | 'not_interested' | 'deleted';

export const JOB_STATUSES: JobStatus[] = ['new', 'reviewed', 'applied', 'not_interested', 'deleted'];

export const STATUS_LABELS: Record<JobStatus, string> = {
  new: 'New',
  reviewed: 'Reviewed',
  applied: 'Applied',
  not_interested: 'Not Interested',
  deleted: 'Deleted'
};

// Job type
export interface Job {
  id: number;
  title: string;
  company: string;
  url: string;
  description?: string;
  location?: string;
  remote_type?: string;
  salary_min?: number;
  salary_max?: number;
  salary_currency?: string;
  score?: number;
  score_reasoning?: string;
  status?: JobStatus;
  source?: string;
  job_id?: string;
  posted_date?: string;
  found_date?: string;
  created_at?: string;
  updated_at?: string;
  first_seen_run_id?: number;
}

// Search run type
export interface SearchRun {
  id: number;
  run_number: number;
  run_date: string;
  jobs_found: number;
  jobs_new: number;
  jobs_updated?: number;
  status: string;
  error_message?: string;
  duration_seconds?: number;
  source?: string;
  search_queries?: string;
  jobs_in_db?: number;
  avg_score?: number;
  strong_matches?: number;
}

// Log entry type
export interface LogEntry {
  timestamp: string;
  module: string;
  level: 'INFO' | 'WARNING' | 'ERROR' | 'DEBUG';
  message: string;
  raw: string;
}

// API response types
export interface JobsResponse {
  jobs: Job[];
  total: number;
  limit: number;
  offset: number;
}

export interface SuggestedJobsResponse {
  high_rated: Job[];
  top_new: Job[];
  run_id?: number;
}

export interface JobStatsResponse {
  total_jobs: number;
  new_jobs: number;
  score_distribution: {
    excellent: number;
    strong: number;
    good: number;
    moderate: number;
    poor: number;
  };
  source_statistics: Record<string, {
    source: string;
    total: number;
    strong_matches: number;
    avg_score: number;
  }>;
}

export interface LogsResponse {
  logs: LogEntry[];
  total_lines: number;
  returned_lines: number;
  file: string;
  error?: string;
}

export interface RunsResponse {
  runs: SearchRun[];
}
