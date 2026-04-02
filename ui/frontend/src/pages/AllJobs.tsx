import { useEffect, useMemo, useState, useCallback } from 'react';
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
  IconButton,
  Tooltip,
  Collapse,
  Button,
  Stack,
  Slider,
  FormGroup,
  Checkbox,
  FormLabel,
  alpha,
} from '@mui/material';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import FilterListIcon from '@mui/icons-material/FilterList';
import ClearIcon from '@mui/icons-material/Clear';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import {
  MaterialReactTable,
  useMaterialReactTable,
  type MRT_ColumnDef,
  type MRT_SortingState,
  type MRT_PaginationState,
} from 'material-react-table';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import ScoreBadge from '../components/ScoreBadge';
import StatusDropdown from '../components/StatusDropdown';
import { getJobs, updateJobStatus } from '../api/jobs';
import type { Job, JobStatus } from '../types';
import { STATUS_LABELS } from '../types';

// Filter state type
interface Filters {
  scoreRange: [number, number];
  status: string[];
  source: string[];
  remoteType: string[];
}

const defaultFilters: Filters = {
  scoreRange: [0, 100],
  status: [],
  source: [],
  remoteType: [],
};

// Source display names
const sourceLabels: Record<string, string> = {
  web_scraping: 'Web Scraping',
  linkedin: 'LinkedIn',
  greenhouse: 'Greenhouse',
  indeed: 'Indeed',
  glassdoor: 'Glassdoor',
};

// Remote type colors
const remoteTypeColors: Record<string, { bg: string; text: string }> = {
  Remote: { bg: '#ecfdf5', text: '#047857' },
  Hybrid: { bg: '#fffbeb', text: '#b45309' },
  'On-site': { bg: '#fef2f2', text: '#b91c1c' },
  Unknown: { bg: '#f3f4f6', text: '#4b5563' },
};

// Source colors
const sourceColors: Record<string, { bg: string; text: string }> = {
  web_scraping: { bg: '#f0f9ff', text: '#0369a1' },
  linkedin: { bg: '#eff6ff', text: '#1d4ed8' },
  greenhouse: { bg: '#ecfdf5', text: '#047857' },
  indeed: { bg: '#faf5ff', text: '#7c3aed' },
  glassdoor: { bg: '#ecfdf5', text: '#059669' },
};

export default function AllJobs() {
  const queryClient = useQueryClient();

  // Filter panel state
  const [filtersOpen, setFiltersOpen] = useState(true);
  const [filters, setFilters] = useState<Filters>(defaultFilters);
  const [showDeleted, setShowDeleted] = useState(false);

  // Table state
  const [sorting, setSorting] = useState<MRT_SortingState>([{ id: 'score', desc: true }]);
  const [pagination, setPagination] = useState<MRT_PaginationState>({ pageIndex: 0, pageSize: 25 });

  // Snackbar state
  const [snackbar, setSnackbar] = useState<{ open: boolean; message: string; severity: 'success' | 'error' }>({
    open: false,
    message: '',
    severity: 'success',
  });

  // Reset to page 0 when filters change
  useEffect(() => {
    setPagination(prev => ({ ...prev, pageIndex: 0 }));
  }, [filters, showDeleted]);

  // Check if any filters are active
  const hasActiveFilters = useMemo(() => {
    return (
      filters.scoreRange[0] !== 0 ||
      filters.scoreRange[1] !== 100 ||
      filters.status.length > 0 ||
      filters.source.length > 0 ||
      filters.remoteType.length > 0
    );
  }, [filters]);

  // Clear all filters
  const clearFilters = useCallback(() => {
    setFilters(defaultFilters);
  }, []);

  // Toggle filter value in array
  const toggleFilter = useCallback((key: keyof Omit<Filters, 'scoreRange'>, value: string) => {
    setFilters(prev => {
      const current = prev[key];
      if (current.includes(value)) {
        return { ...prev, [key]: current.filter(v => v !== value) };
      } else {
        return { ...prev, [key]: [...current, value] };
      }
    });
  }, []);

  // Fetch jobs with server-side filtering and sorting
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['jobs', showDeleted, pagination, filters, sorting],
    queryFn: () =>
      getJobs({
        excludeDeleted: !showDeleted,
        limit: pagination.pageSize,
        offset: pagination.pageIndex * pagination.pageSize,
        minScore: filters.scoreRange[0] > 0 ? filters.scoreRange[0] : undefined,
        maxScore: filters.scoreRange[1] < 100 ? filters.scoreRange[1] : undefined,
        status: filters.status.length > 0 ? filters.status : undefined,
        source: filters.source.length > 0 ? filters.source : undefined,
        remoteType: filters.remoteType.length > 0 ? filters.remoteType : undefined,
        sortBy: sorting[0]?.id,
        sortDesc: sorting[0]?.desc ?? true,
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
        size: 280,
        enableColumnFilter: false,
        Cell: ({ row }) => (
          <Link
            href={row.original.url}
            target="_blank"
            rel="noopener noreferrer"
            sx={{
              display: 'flex',
              alignItems: 'center',
              gap: 0.5,
              color: '#1e293b',
              textDecoration: 'none',
              fontWeight: 500,
              '&:hover': {
                color: '#6366f1',
                textDecoration: 'underline',
              },
            }}
          >
            {row.original.title}
            <OpenInNewIcon sx={{ fontSize: 14, opacity: 0.5 }} />
          </Link>
        ),
      },
      {
        accessorKey: 'company',
        header: 'Company',
        size: 160,
        enableColumnFilter: false,
        Cell: ({ cell }) => (
          <Typography variant="body2" sx={{ color: '#64748b', fontWeight: 500 }}>
            {cell.getValue<string>()}
          </Typography>
        ),
      },
      {
        accessorKey: 'score',
        header: 'Score',
        size: 90,
        enableColumnFilter: false,
        Cell: ({ cell }) => <ScoreBadge score={cell.getValue<number>()} size="small" />,
      },
      {
        accessorKey: 'status',
        header: 'Status',
        size: 150,
        enableColumnFilter: false,
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
      },
      {
        accessorKey: 'location',
        header: 'Location',
        size: 140,
        enableColumnFilter: false,
        Cell: ({ cell }) => {
          const value = cell.getValue<string>();
          return value ? (
            <Typography variant="body2" sx={{ color: '#64748b' }}>
              {value}
            </Typography>
          ) : null;
        },
      },
      {
        accessorKey: 'remote_type',
        header: 'Remote',
        size: 100,
        enableColumnFilter: false,
        Cell: ({ cell }) => {
          const value = cell.getValue<string>();
          if (!value || value === 'Unknown') return null;
          const colors = remoteTypeColors[value] || remoteTypeColors.Unknown;
          return (
            <Chip
              label={value}
              size="small"
              sx={{
                backgroundColor: colors.bg,
                color: colors.text,
                fontWeight: 500,
                fontSize: '0.75rem',
              }}
            />
          );
        },
      },
      {
        accessorKey: 'source',
        header: 'Source',
        size: 120,
        enableColumnFilter: false,
        Cell: ({ cell }) => {
          const value = cell.getValue<string>();
          const colors = sourceColors[value] || { bg: '#f3f4f6', text: '#4b5563' };
          return (
            <Chip
              label={sourceLabels[value] || value || 'Unknown'}
              size="small"
              sx={{
                backgroundColor: colors.bg,
                color: colors.text,
                fontWeight: 500,
                fontSize: '0.75rem',
              }}
            />
          );
        },
      },
      {
        accessorKey: 'found_date',
        header: 'Found',
        size: 130,
        enableColumnFilter: false,
        Cell: ({ cell }) => {
          const date = cell.getValue<string>();
          if (!date) return null;
          const d = new Date(date);
          const now = new Date();
          const diffDays = Math.floor((now.getTime() - d.getTime()) / (1000 * 60 * 60 * 24));

          let timeAgo = '';
          if (diffDays === 0) {
            timeAgo = 'Today';
          } else if (diffDays === 1) {
            timeAgo = 'Yesterday';
          } else if (diffDays < 7) {
            timeAgo = `${diffDays}d ago`;
          } else {
            timeAgo = d.toLocaleDateString();
          }

          return (
            <Typography variant="body2" sx={{ color: '#64748b', fontSize: '0.8rem' }}>
              {timeAgo}
            </Typography>
          );
        },
      },
    ],
    [statusMutation]
  );

  const table = useMaterialReactTable({
    columns,
    data: data?.jobs ?? [],
    manualPagination: true,
    manualFiltering: true,
    manualSorting: true,
    rowCount: data?.total ?? 0,
    state: {
      sorting,
      pagination,
      isLoading,
      showAlertBanner: isError,
    },
    onSortingChange: setSorting,
    onPaginationChange: setPagination,
    enableColumnResizing: true,
    enableRowSelection: false,
    enableDensityToggle: false,
    enableFullScreenToggle: true,
    enableColumnOrdering: false,
    enableColumnFilters: false,
    enableGlobalFilter: false,
    enableFilters: false,
    initialState: {
      density: 'compact',
    },
    muiTableContainerProps: {
      sx: {
        maxHeight: 'calc(100vh - 320px)',
        '& .MuiTableHead-root': {
          position: 'sticky',
          top: 0,
          zIndex: 1,
        },
      },
    },
    muiTableHeadCellProps: {
      sx: {
        backgroundColor: '#f8fafc',
        fontWeight: 600,
        color: '#475569',
        borderBottom: '2px solid #e2e8f0',
      },
    },
    muiTableBodyCellProps: {
      sx: {
        borderBottom: '1px solid #f1f5f9',
      },
    },
    muiTableBodyRowProps: ({ row }) => ({
      sx: {
        '&:hover': {
          backgroundColor: alpha('#6366f1', 0.04),
        },
        ...(row.original.status === 'deleted' && {
          opacity: 0.5,
        }),
      },
    }),
    muiToolbarAlertBannerProps: isError
      ? {
          color: 'error',
          children: `Error loading jobs: ${(error as Error)?.message}`,
        }
      : undefined,
    muiPaginationProps: {
      rowsPerPageOptions: [10, 25, 50, 100],
      showFirstButton: true,
      showLastButton: true,
    },
    renderDetailPanel: ({ row }) => (
      <Box sx={{ p: 3, backgroundColor: '#f8fafc' }}>
        <Box sx={{ mb: 2 }}>
          <Typography variant="subtitle2" fontWeight={600} color="text.primary" gutterBottom>
            Score Reasoning
          </Typography>
          <Typography variant="body2" sx={{ color: '#64748b', whiteSpace: 'pre-wrap' }}>
            {row.original.score_reasoning || 'No reasoning available'}
          </Typography>
        </Box>
        {row.original.description && (
          <Box>
            <Typography variant="subtitle2" fontWeight={600} color="text.primary" gutterBottom>
              Job Description
            </Typography>
            <Typography
              variant="body2"
              sx={{
                color: '#64748b',
                maxHeight: 200,
                overflow: 'auto',
                whiteSpace: 'pre-wrap',
                backgroundColor: 'white',
                p: 2,
                borderRadius: 1,
                border: '1px solid #e2e8f0',
              }}
            >
              {row.original.description.substring(0, 1500)}
              {row.original.description.length > 1500 && '...'}
            </Typography>
          </Box>
        )}
      </Box>
    ),
  });

  return (
    <Box sx={{ p: 3 }}>
      {/* Header */}
      <Paper
        sx={{
          p: 2.5,
          mb: 2,
          display: 'flex',
          alignItems: 'center',
          gap: 2,
          border: '1px solid #e2e8f0',
        }}
      >
        <Box sx={{ flex: 1 }}>
          <Typography variant="h5" fontWeight={600} color="text.primary">
            All Jobs
          </Typography>
          {data?.total !== undefined && (
            <Typography variant="body2" color="text.secondary">
              {data.total.toLocaleString()} jobs found
            </Typography>
          )}
        </Box>

        <Stack direction="row" spacing={1} alignItems="center">
          <FormControlLabel
            control={
              <Switch
                checked={showDeleted}
                onChange={(e) => setShowDeleted(e.target.checked)}
                size="small"
              />
            }
            label={
              <Typography variant="body2" color="text.secondary">
                Show Deleted
              </Typography>
            }
          />

          <Tooltip title={filtersOpen ? 'Hide filters' : 'Show filters'}>
            <IconButton
              onClick={() => setFiltersOpen(!filtersOpen)}
              sx={{
                backgroundColor: hasActiveFilters ? alpha('#6366f1', 0.1) : 'transparent',
                color: hasActiveFilters ? '#6366f1' : '#64748b',
                '&:hover': {
                  backgroundColor: alpha('#6366f1', 0.15),
                },
              }}
            >
              <FilterListIcon />
              {filtersOpen ? <ExpandLessIcon sx={{ fontSize: 16 }} /> : <ExpandMoreIcon sx={{ fontSize: 16 }} />}
            </IconButton>
          </Tooltip>
        </Stack>
      </Paper>

      {/* Filter Panel */}
      <Collapse in={filtersOpen}>
        <Paper
          sx={{
            p: 2.5,
            mb: 2,
            border: '1px solid #e2e8f0',
          }}
        >
          <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
            <Typography variant="subtitle1" fontWeight={600} sx={{ flex: 1 }}>
              Filters
            </Typography>
            {hasActiveFilters && (
              <Button
                size="small"
                startIcon={<ClearIcon />}
                onClick={clearFilters}
                sx={{ color: '#64748b' }}
              >
                Clear all
              </Button>
            )}
          </Box>

          <Stack direction={{ xs: 'column', md: 'row' }} spacing={3}>
            {/* Score Range */}
            <Box sx={{ minWidth: 200 }}>
              <FormLabel sx={{ fontSize: '0.875rem', fontWeight: 500, color: '#475569', mb: 1, display: 'block' }}>
                Score Range: {filters.scoreRange[0]} - {filters.scoreRange[1]}
              </FormLabel>
              <Slider
                value={filters.scoreRange}
                onChange={(_, value) => setFilters(prev => ({ ...prev, scoreRange: value as [number, number] }))}
                valueLabelDisplay="auto"
                min={0}
                max={100}
                step={5}
                sx={{
                  color: '#6366f1',
                  '& .MuiSlider-thumb': {
                    width: 16,
                    height: 16,
                  },
                }}
              />
            </Box>

            {/* Status Filter */}
            <Box>
              <FormLabel sx={{ fontSize: '0.875rem', fontWeight: 500, color: '#475569', mb: 1, display: 'block' }}>
                Status
              </FormLabel>
              <FormGroup row>
                {(['new', 'reviewed', 'applied', 'not_interested'] as const).map((status) => (
                  <FormControlLabel
                    key={status}
                    control={
                      <Checkbox
                        checked={filters.status.includes(status)}
                        onChange={() => toggleFilter('status', status)}
                        size="small"
                        sx={{ color: '#94a3b8', '&.Mui-checked': { color: '#6366f1' } }}
                      />
                    }
                    label={
                      <Typography variant="body2" color="text.secondary">
                        {STATUS_LABELS[status]}
                      </Typography>
                    }
                  />
                ))}
              </FormGroup>
            </Box>

            {/* Source Filter */}
            <Box>
              <FormLabel sx={{ fontSize: '0.875rem', fontWeight: 500, color: '#475569', mb: 1, display: 'block' }}>
                Source
              </FormLabel>
              <FormGroup row>
                {Object.entries(sourceLabels).map(([value, label]) => (
                  <FormControlLabel
                    key={value}
                    control={
                      <Checkbox
                        checked={filters.source.includes(value)}
                        onChange={() => toggleFilter('source', value)}
                        size="small"
                        sx={{ color: '#94a3b8', '&.Mui-checked': { color: '#6366f1' } }}
                      />
                    }
                    label={
                      <Typography variant="body2" color="text.secondary">
                        {label}
                      </Typography>
                    }
                  />
                ))}
              </FormGroup>
            </Box>

            {/* Remote Type Filter */}
            <Box>
              <FormLabel sx={{ fontSize: '0.875rem', fontWeight: 500, color: '#475569', mb: 1, display: 'block' }}>
                Remote Type
              </FormLabel>
              <FormGroup row>
                {['Remote', 'Hybrid', 'On-site'].map((type) => (
                  <FormControlLabel
                    key={type}
                    control={
                      <Checkbox
                        checked={filters.remoteType.includes(type)}
                        onChange={() => toggleFilter('remoteType', type)}
                        size="small"
                        sx={{ color: '#94a3b8', '&.Mui-checked': { color: '#6366f1' } }}
                      />
                    }
                    label={
                      <Typography variant="body2" color="text.secondary">
                        {type}
                      </Typography>
                    }
                  />
                ))}
              </FormGroup>
            </Box>
          </Stack>

          {/* Active Filter Chips */}
          {hasActiveFilters && (
            <Box sx={{ mt: 2, pt: 2, borderTop: '1px solid #e2e8f0' }}>
              <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                {(filters.scoreRange[0] > 0 || filters.scoreRange[1] < 100) && (
                  <Chip
                    label={`Score: ${filters.scoreRange[0]}-${filters.scoreRange[1]}`}
                    size="small"
                    onDelete={() => setFilters(prev => ({ ...prev, scoreRange: [0, 100] }))}
                    sx={{ backgroundColor: '#f0f9ff', color: '#0369a1' }}
                  />
                )}
                {filters.status.map(s => (
                  <Chip
                    key={s}
                    label={STATUS_LABELS[s as JobStatus]}
                    size="small"
                    onDelete={() => toggleFilter('status', s)}
                    sx={{ backgroundColor: '#faf5ff', color: '#7c3aed' }}
                  />
                ))}
                {filters.source.map(s => (
                  <Chip
                    key={s}
                    label={sourceLabels[s]}
                    size="small"
                    onDelete={() => toggleFilter('source', s)}
                    sx={{ backgroundColor: '#ecfdf5', color: '#047857' }}
                  />
                ))}
                {filters.remoteType.map(t => (
                  <Chip
                    key={t}
                    label={t}
                    size="small"
                    onDelete={() => toggleFilter('remoteType', t)}
                    sx={{ backgroundColor: '#fffbeb', color: '#b45309' }}
                  />
                ))}
              </Stack>
            </Box>
          )}
        </Paper>
      </Collapse>

      {/* Table */}
      <Paper sx={{ border: '1px solid #e2e8f0', overflow: 'hidden' }}>
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
          sx={{ borderRadius: 2 }}
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
}
