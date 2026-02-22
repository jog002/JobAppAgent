import { useState } from 'react';
import { Box, Alert, Snackbar } from '@mui/material';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import JobListPanel from '../components/JobListPanel';
import { getSuggestedJobs, updateJobStatus } from '../api/jobs';
import { getLatestRun } from '../api/logs';
import type { JobStatus } from '../types';

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
        message: `Status updated to "${status}"`,
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
        <Alert severity="error">
          Failed to load suggested jobs: {(error as Error).message}
        </Alert>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3, height: 'calc(100vh - 120px)' }}>
      <Box
        sx={{
          display: 'flex',
          gap: 3,
          height: '100%',
          flexDirection: { xs: 'column', md: 'row' },
        }}
      >
        {/* High Rated from Latest Run */}
        <Box sx={{ flex: 1, minWidth: 0 }}>
          <JobListPanel
            title="High Rated from Latest Run"
            subtitle={`Score ≥ 80${latestRun ? ` • Run #${latestRun.run_number}` : ''}`}
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
            title="Top 20 New Jobs"
            subtitle="Jobs with status 'New'"
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
          sx={{ width: '100%' }}
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
}
