import { get, post } from './client';

export interface ConfigResponse {
  database_mode: 'local' | 'turso';
  turso_url?: string;
  turso_token?: string;
}

export interface ConfigUpdate {
  database_mode: 'local' | 'turso';
  turso_url?: string;
  turso_token?: string;
}

export interface ConnectionTestRequest {
  mode: 'local' | 'turso';
  turso_url?: string;
  turso_token?: string;
}

export interface ConnectionTestResponse {
  success: boolean;
  error?: string;
  job_count?: number;
}

// Get current database configuration
export async function getConfig(): Promise<ConfigResponse> {
  return get<ConfigResponse>('/config');
}

// Update database configuration
export async function updateConfig(config: ConfigUpdate): Promise<ConfigResponse> {
  return post<ConfigResponse>('/config', config);
}

// Test database connection
export async function testConnection(params: ConnectionTestRequest): Promise<ConnectionTestResponse> {
  return post<ConnectionTestResponse>('/config/test', params);
}
