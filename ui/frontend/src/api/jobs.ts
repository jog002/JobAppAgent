import { get, patch } from './client';
import type { Job, JobsResponse, SuggestedJobsResponse, JobStatsResponse, JobStatus } from '../types';

// Query params builder - handles arrays by joining with commas
function buildQueryString(params: Record<string, string | string[] | number | boolean | undefined>): string {
  const filtered = Object.entries(params)
    .filter(([, value]) => value !== undefined && value !== null && (Array.isArray(value) ? value.length > 0 : true))
    .map(([key, value]) => {
      const stringValue = Array.isArray(value) ? value.join(',') : String(value);
      return `${encodeURIComponent(key)}=${encodeURIComponent(stringValue)}`;
    });

  return filtered.length > 0 ? `?${filtered.join('&')}` : '';
}

// Get all jobs with filters
export async function getJobs(params: {
  excludeDeleted?: boolean;
  minScore?: number;
  maxScore?: number;
  status?: string[];
  source?: string[];
  location?: string[];
  remoteType?: string[];
  sortBy?: string;
  sortDesc?: boolean;
  limit?: number;
  offset?: number;
} = {}): Promise<JobsResponse> {
  const queryString = buildQueryString({
    exclude_deleted: params.excludeDeleted,
    min_score: params.minScore,
    max_score: params.maxScore,
    status: params.status,
    source: params.source,
    location: params.location,
    remote_type: params.remoteType,
    sort_by: params.sortBy,
    sort_desc: params.sortDesc,
    limit: params.limit,
    offset: params.offset,
  });

  return get<JobsResponse>(`/jobs${queryString}`);
}

// Get suggested jobs for dashboard
export async function getSuggestedJobs(minScore = 80, runId?: number): Promise<SuggestedJobsResponse> {
  const queryString = buildQueryString({
    min_score: minScore,
    run_id: runId,
  });

  return get<SuggestedJobsResponse>(`/jobs/suggested${queryString}`);
}

// Get job statistics
export async function getJobStats(): Promise<JobStatsResponse> {
  return get<JobStatsResponse>('/jobs/stats');
}

// Get single job by ID
export async function getJob(jobId: number): Promise<Job> {
  return get<Job>(`/jobs/${jobId}`);
}

// Update job status
export async function updateJobStatus(
  jobId: number,
  status: JobStatus
): Promise<{ success: boolean; job_id: number; status: string }> {
  return patch(`/jobs/${jobId}/status`, { status });
}
