import { Box, Paper, Typography, CircularProgress } from '@mui/material';
import JobCard from './JobCard';
import type { Job, JobStatus } from '../types';

interface JobListPanelProps {
  title: string;
  subtitle?: string;
  jobs: Job[];
  isLoading?: boolean;
  emptyMessage?: string;
  onStatusChange?: (jobId: number, newStatus: JobStatus) => void;
  updatingJobId?: number;
  maxHeight?: string | number;
}

export default function JobListPanel({
  title,
  subtitle,
  jobs,
  isLoading = false,
  emptyMessage = 'No jobs found',
  onStatusChange,
  updatingJobId,
  maxHeight = '70vh',
}: JobListPanelProps) {
  return (
    <Paper
      sx={{
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
      }}
    >
      {/* Header */}
      <Box
        sx={{
          px: 2,
          py: 1.5,
          borderBottom: '1px solid #e0e0e0',
          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
          color: 'white',
        }}
      >
        <Typography variant="h6" sx={{ fontWeight: 600, fontSize: '1rem' }}>
          {title}
        </Typography>
        {subtitle && (
          <Typography variant="caption" sx={{ opacity: 0.9 }}>
            {subtitle}
          </Typography>
        )}
      </Box>

      {/* Content */}
      <Box
        sx={{
          flex: 1,
          overflow: 'auto',
          p: 2,
          maxHeight,
        }}
      >
        {isLoading ? (
          <Box
            sx={{
              display: 'flex',
              justifyContent: 'center',
              alignItems: 'center',
              py: 4,
            }}
          >
            <CircularProgress size={32} />
          </Box>
        ) : jobs.length === 0 ? (
          <Typography
            variant="body2"
            sx={{ color: '#888', textAlign: 'center', py: 4 }}
          >
            {emptyMessage}
          </Typography>
        ) : (
          jobs.map((job) => (
            <JobCard
              key={job.id}
              job={job}
              onStatusChange={onStatusChange}
              isUpdating={updatingJobId === job.id}
            />
          ))
        )}
      </Box>

      {/* Footer with count */}
      <Box
        sx={{
          px: 2,
          py: 1,
          borderTop: '1px solid #e0e0e0',
          backgroundColor: '#f8f9fa',
        }}
      >
        <Typography variant="caption" sx={{ color: '#666' }}>
          {jobs.length} job{jobs.length !== 1 ? 's' : ''}
        </Typography>
      </Box>
    </Paper>
  );
}
