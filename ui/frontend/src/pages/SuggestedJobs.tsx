import { useState } from 'react';
import { Box, Alert, Snackbar, Typography, Paper, Stack } from '@mui/material';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import JobListPanel from '../components/JobListPanel';
import { getSuggestedJobs, updateJobStatus } from '../api/jobs';
import { getLatestRun } from '../api/logs';
import type { JobStatus } from '../types';
import { STATUS_LABELS } from '../types';

export default function SuggestedJobs() {
  const queryClient = useQueryClient();
  const [updatingJobId, setUpdatingJobId] = useState<number | undefined>();
  const [snackbar, setSnackbar] = useState<{ open: boolean; message: string; severity: 'success' | 'error' }>({
    open: false,
    message: '',
    severity: 'success',
  });

  // Fetch latest run info
  const { data: latestRun } = useQuery({
    queryKey: ['latestRun'],
    queryFn: getLatestRun,
    retry: false,
  });

  // Fetch suggested jobs
  const { data, isLoading, error } = useQuery({
    queryKey: ['suggestedJobs'],
    queryFn: () => getSuggestedJobs(80),
    refetchInterval: 30000, // Refresh every 30 seconds
  });

  // Mutation for status updates
  const statusMutation = useMutation({
    mutationFn: ({ jobId, status }: { jobId: number; status: JobStatus }) =>
      updateJobStatus(jobId, status),
    onMutate: ({ jobId }) => {
      setUpdatingJobId(jobId);
    },
    onSuccess: (_, { status }) => {
      queryClient.invalidateQueries({ queryKey: ['suggestedJobs'] });
      queryClient.invalidateQueries({ queryKey: ['jobs'] });
      setSnackbar({
        open: true,
        message: `Status updated to "${STATUS_LABELS[status]}"`,
        severity: 'success',
      });
    },
    onError: (error: Error) => {
      setSnackbar({
        open: true,
        message: `Failed to update status: ${error.message}`,
        severity: 'error',
      });
    },
    onSettled: () => {
      setUpdatingJobId(undefined);
    },
  });

  const handleStatusChange = (jobId: number, newStatus: JobStatus) => {
    statusMutation.mutate({ jobId, status: newStatus });
  };

  if (error) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error" sx={{ borderRadius: 2 }}>
          Failed to load suggested jobs: {(error as Error).message}
        </Alert>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3, height: 'calc(100vh - 120px)' }}>
      {/* Page Header */}
      <Paper
        sx={{
          p: 2.5,
          mb: 3,
          border: '1px solid #e2e8f0',
          display: 'flex',
          alignItems: 'center',
          gap: 2,
        }}
      >
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            width: 48,
            height: 48,
            borderRadius: 2,
            background: 'linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)',
            color: 'white',
          }}
        >
          <TrendingUpIcon sx={{ fontSize: 28 }} />
        </Box>
        <Box sx={{ flex: 1 }}>
          <Typography variant="h5" fontWeight={600} color="text.primary">
            Dashboard
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Your best job matches and recent discoveries
          </Typography>
        </Box>
        {latestRun && (
          <Stack direction="row" spacing={2}>
            <Box sx={{ textAlign: 'right' }}>
              <Typography variant="caption" color="text.secondary" display="block">
                Latest Run
              </Typography>
              <Typography variant="body2" fontWeight={600} color="text.primary">
                #{latestRun.run_number}
              </Typography>
            </Box>
            {latestRun.jobs_new !== undefined && (
              <Box sx={{ textAlign: 'right' }}>
                <Typography variant="caption" color="text.secondary" display="block">
                  New Jobs Found
                </Typography>
                <Typography variant="body2" fontWeight={600} color="#10b981">
                  +{latestRun.jobs_new}
                </Typography>
              </Box>
            )}
          </Stack>
        )}
      </Paper>

      {/* Job Panels */}
      <Box
        sx={{
          display: 'flex',
          gap: 3,
          height: 'calc(100% - 100px)',
          flexDirection: { xs: 'column', lg: 'row' },
        }}
      >
        {/* High Rated from Latest Run */}
        <Box sx={{ flex: 1, minWidth: 0 }}>
          <JobListPanel
            title="High Rated Jobs"
            subtitle={`Score ≥ 80${latestRun ? ` from Run #${latestRun.run_number}` : ''}`}
            jobs={data?.high_rated || []}
            isLoading={isLoading}
            emptyMessage="No high-rated jobs from the latest run"
            onStatusChange={handleStatusChange}
            updatingJobId={updatingJobId}
          />
        </Box>

        {/* Top 20 New Jobs */}
        <Box sx={{ flex: 1, minWidth: 0 }}>
          <JobListPanel
            title="Top New Jobs"
            subtitle="Highest scoring jobs awaiting review"
            jobs={data?.top_new || []}
            isLoading={isLoading}
            emptyMessage="No new jobs to review"
            onStatusChange={handleStatusChange}
            updatingJobId={updatingJobId}
          />
        </Box>
      </Box>

      {/* Snackbar for notifications */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={3000}
        onClose={() => setSnackbar((s) => ({ ...s, open: false }))}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <Alert
          onClose={() => setSnackbar((s) => ({ ...s, open: false }))}
          severity={snackbar.severity}
          sx={{ borderRadius: 2 }}
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
}
