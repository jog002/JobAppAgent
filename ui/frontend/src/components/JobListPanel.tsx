import { Box, Paper, Typography, CircularProgress, Chip } from '@mui/material';
import WorkOutlineIcon from '@mui/icons-material/WorkOutline';
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
        border: '1px solid #e2e8f0',
        borderRadius: 3,
      }}
    >
      {/* Header */}
      <Box
        sx={{
          px: 2.5,
          py: 2,
          borderBottom: '1px solid #e2e8f0',
          background: 'linear-gradient(135deg, #6366f1 0%, #8b5cf6 50%, #a855f7 100%)',
          color: 'white',
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Typography variant="h6" sx={{ fontWeight: 600, fontSize: '1rem' }}>
            {title}
          </Typography>
          <Chip
            label={jobs.length}
            size="small"
            sx={{
              backgroundColor: 'rgba(255,255,255,0.2)',
              color: 'white',
              fontWeight: 700,
              fontSize: '0.75rem',
              height: 24,
              minWidth: 32,
            }}
          />
        </Box>
        {subtitle && (
          <Typography variant="caption" sx={{ opacity: 0.85, display: 'block', mt: 0.5 }}>
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
          backgroundColor: '#f8fafc',
        }}
      >
        {isLoading ? (
          <Box
            sx={{
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'center',
              alignItems: 'center',
              py: 6,
              gap: 2,
            }}
          >
            <CircularProgress size={36} sx={{ color: '#6366f1' }} />
            <Typography variant="body2" color="text.secondary">
              Loading jobs...
            </Typography>
          </Box>
        ) : jobs.length === 0 ? (
          <Box
            sx={{
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'center',
              alignItems: 'center',
              py: 6,
              gap: 1.5,
            }}
          >
            <WorkOutlineIcon sx={{ fontSize: 48, color: '#cbd5e1' }} />
            <Typography
              variant="body2"
              sx={{ color: '#94a3b8', textAlign: 'center' }}
            >
              {emptyMessage}
            </Typography>
          </Box>
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
    </Paper>
  );
}
