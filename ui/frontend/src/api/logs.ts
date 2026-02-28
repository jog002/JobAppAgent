import { get } from './client';
import type { LogsResponse, RunsResponse, SearchRun } from '../types';

// Get latest logs
export async function getLatestLogs(lines = 500, level?: string, source: 'agent' | 'batch' = 'agent'): Promise<LogsResponse> {
  const params = new URLSearchParams({ lines: String(lines), source });
  if (level) {
    params.append('level', level);
  }
  return get<LogsResponse>(`/logs/latest?${params.toString()}`);
}

// Get all search runs
export async function getRuns(): Promise<RunsResponse> {
  return get<RunsResponse>('/runs');
}

// Get latest run
export async function getLatestRun(): Promise<SearchRun> {
  return get<SearchRun>('/runs/latest');
}

// Get run by ID
export async function getRun(runId: number): Promise<SearchRun> {
  return get<SearchRun>(`/runs/${runId}`);
}

// Get jobs from a specific run
export async function getRunJobs(runId: number, limit = 100): Promise<{
  run_id: number;
  jobs: import('../types').Job[];
  total: number;
}> {
  return get(`/runs/${runId}/jobs?limit=${limit}`);
}
