import { useMemo, useState } from 'react';
import {
  Box,
  Alert,
  Snackbar,
  Typography,
  Chip,
  Link,
  FormControlLabel,
  Switch,
  Paper,
} from '@mui/material';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import {
  MaterialReactTable,
  useMaterialReactTable,
  type MRT_ColumnDef,
  type MRT_ColumnFiltersState,
  type MRT_SortingState,
  type MRT_PaginationState,
} from 'material-react-table';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import ScoreBadge from '../components/ScoreBadge';
import StatusDropdown from '../components/StatusDropdown';
import { getJobs, updateJobStatus } from '../api/jobs';
import type { Job, JobStatus } from '../types';
import { STATUS_LABELS } from '../types';

export default function AllJobs() {
  const queryClient = useQueryClient();

  // Table state
  const [columnFilters, setColumnFilters] = useState<MRT_ColumnFiltersState>([]);
  const [sorting, setSorting] = useState<MRT_SortingState>([{ id: 'score', desc: true }]);
  const [pagination, setPagination] = useState<MRT_PaginationState>({ pageIndex: 0, pageSize: 25 });
  const [showDeleted, setShowDeleted] = useState(false);

  // Snackbar state
  const [snackbar, setSnackbar] = useState<{ open: boolean; message: string; severity: 'success' | 'error' }>({
    open: false,
    message: '',
    severity: 'success',
  });

  // Fetch jobs
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['jobs', showDeleted, pagination.pageIndex, pagination.pageSize],
    queryFn: () =>
      getJobs({
        excludeDeleted: !showDeleted,
        limit: pagination.pageSize,
        offset: pagination.pageIndex * pagination.pageSize,
      }),
    refetchInterval: 30000,
  });

  // Status update mutation
  const statusMutation = useMutation({
    mutationFn: ({ jobId, status }: { jobId: number; status: JobStatus }) =>
      updateJobStatus(jobId, status),
    onSuccess: (_, { status }) => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] });
      queryClient.invalidateQueries({ queryKey: ['suggestedJobs'] });
      setSnackbar({
        open: true,
        message: `Status updated to "${STATUS_LABELS[status]}"`,
        severity: 'success',
      });
    },
    onError: (error: Error) => {
      setSnackbar({
        open: true,
        message: `Failed to update: ${error.message}`,
        severity: 'error',
      });
    },
  });

  // Column definitions
  const columns = useMemo<MRT_ColumnDef<Job>[]>(
    () => [
      {
        accessorKey: 'title',
        header: 'Title',
        size: 250,
        Cell: ({ row }) => (
          <Link
            href={row.original.url}
            target="_blank"
            rel="noopener noreferrer"
            sx={{
              display: 'flex',
              alignItems: 'center',
              gap: 0.5,
              color: '#333',
              textDecoration: 'none',
              fontWeight: 500,
              '&:hover': {
                color: '#667eea',
                textDecoration: 'underline',
              },
            }}
          >
            {row.original.title}
            <OpenInNewIcon sx={{ fontSize: 14, opacity: 0.6 }} />
          </Link>
        ),
      },
      {
        accessorKey: 'company',
        header: 'Company',
        size: 150,
        filterVariant: 'multi-select',
        enableSorting: false,
      },
      {
        accessorKey: 'score',
        header: 'Score',
        size: 80,
        Cell: ({ cell }) => <ScoreBadge score={cell.getValue<number>()} size="small" />,
        filterVariant: 'range-slider',
        filterFn: 'betweenInclusive',
        muiFilterSliderProps: {
          min: 0,
          max: 100,
          step: 5,
        },
      },
      {
        accessorKey: 'status',
        header: 'Status',
        size: 140,
        Cell: ({ row }) => (
          <StatusDropdown
            status={row.original.status as JobStatus}
            onChange={(newStatus) =>
              statusMutation.mutate({ jobId: row.original.id, status: newStatus })
            }
            disabled={statusMutation.isPending}
            size="small"
          />
        ),
        filterVariant: 'select',
        filterSelectOptions: [
          { value: 'new', label: 'New' },
          { value: 'reviewed', label: 'Reviewed' },
          { value: 'applied', label: 'Applied' },
          { value: 'not_interested', label: 'Not Interested' },
          { value: 'deleted', label: 'Deleted' },
        ],
      },
      {
        accessorKey: 'location',
        header: 'Location',
        size: 150,
        filterVariant: 'multi-select',
        enableSorting: false,
      },
      {
        accessorKey: 'remote_type',
        header: 'Remote',
        size: 100,
        Cell: ({ cell }) => {
          const value = cell.getValue<string>();
          if (!value || value === 'Unknown') return null;
          return (
            <Chip
              label={value}
              size="small"
              sx={{
                backgroundColor: value === 'Remote' ? '#d4edda' : '#fff3cd',
                color: value === 'Remote' ? '#155724' : '#856404',
                fontWeight: 500,
              }}
            />
          );
        },
        filterVariant: 'multi-select',
        filterSelectOptions: ['Remote', 'Hybrid', 'On-site', 'Unknown'],
        enableSorting: false,
      },
      {
        accessorKey: 'source',
        header: 'Source',
        size: 100,
        Cell: ({ cell }) => {
          const value = cell.getValue<string>();
          return (
            <Chip
              label={value || 'Unknown'}
              size="small"
              sx={{
                backgroundColor: '#e9ecef',
                color: '#495057',
              }}
            />
          );
        },
        filterVariant: 'multi-select',
        filterSelectOptions: ['web_scraping', 'linkedin', 'greenhouse', 'indeed', 'glassdoor'],
        enableSorting: false,
      },
      {
        accessorKey: 'found_date',
        header: 'Found',
        size: 140,
        Cell: ({ cell }) => {
          const date = cell.getValue<string>();
          if (!date) return null;
          const d = new Date(date);
          return d.toLocaleDateString() + ' ' + d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        },
      },
    ],
    [statusMutation]
  );

  const table = useMaterialReactTable({
    columns,
    data: data?.jobs ?? [],
    manualPagination: true,
    manualFiltering: false, // Client-side filtering for now
    manualSorting: false, // Client-side sorting for now
    rowCount: data?.total ?? 0,
    state: {
      columnFilters,
      sorting,
      pagination,
      isLoading,
      showAlertBanner: isError,
    },
    onColumnFiltersChange: setColumnFilters,
    onSortingChange: setSorting,
    onPaginationChange: setPagination,
    enableColumnResizing: true,
    enableRowSelection: false,
    enableDensityToggle: true,
    enableFullScreenToggle: true,
    enableColumnOrdering: true,
    enableGlobalFilter: true,
    positionGlobalFilter: 'left',
    initialState: {
      density: 'compact',
      showGlobalFilter: true,
    },
    muiTableContainerProps: {
      sx: { maxHeight: 'calc(100vh - 240px)' },
    },
    muiToolbarAlertBannerProps: isError
      ? {
          color: 'error',
          children: `Error loading jobs: ${(error as Error)?.message}`,
        }
      : undefined,
    renderDetailPanel: ({ row }) => (
      <Box sx={{ p: 2, backgroundColor: '#f8f9fa' }}>
        <Typography variant="subtitle2" gutterBottom>
          Score Reasoning:
        </Typography>
        <Typography variant="body2" sx={{ color: '#666', whiteSpace: 'pre-wrap' }}>
          {row.original.score_reasoning || 'No reasoning available'}
        </Typography>
        {row.original.description && (
          <>
            <Typography variant="subtitle2" sx={{ mt: 2 }} gutterBottom>
              Job Description:
            </Typography>
            <Typography
              variant="body2"
              sx={{
                color: '#666',
                maxHeight: 200,
                overflow: 'auto',
                whiteSpace: 'pre-wrap',
              }}
            >
              {row.original.description.substring(0, 1000)}
              {row.original.description.length > 1000 && '...'}
            </Typography>
          </>
        )}
      </Box>
    ),
  });

  return (
    <Box sx={{ p: 3 }}>
      {/* Controls */}
      <Paper sx={{ p: 2, mb: 2, display: 'flex', alignItems: 'center', gap: 2 }}>
        <Typography variant="h6" sx={{ flex: 1 }}>
          All Jobs
          {data?.total !== undefined && (
            <Typography component="span" sx={{ ml: 1, color: '#666', fontWeight: 400 }}>
              ({data.total} total)
            </Typography>
          )}
        </Typography>
        <FormControlLabel
          control={
            <Switch
              checked={showDeleted}
              onChange={(e) => setShowDeleted(e.target.checked)}
            />
          }
          label="Show Deleted"
        />
      </Paper>

      {/* Table */}
      <Paper>
        <MaterialReactTable table={table} />
      </Paper>

      {/* Snackbar */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={3000}
        onClose={() => setSnackbar((s) => ({ ...s, open: false }))}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <Alert
          onClose={() => setSnackbar((s) => ({ ...s, open: false }))}
          severity={snackbar.severity}
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
}
