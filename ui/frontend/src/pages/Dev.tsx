import { useState, useEffect, useRef } from 'react';
import {
  Box,
  Paper,
  Typography,
  IconButton,
  FormControlLabel,
  Switch,
  Select,
  MenuItem,
  Tooltip,
  CircularProgress,
  Alert,
  ToggleButton,
  ToggleButtonGroup,
} from '@mui/material';
import RefreshIcon from '@mui/icons-material/Refresh';
import { useQuery } from '@tanstack/react-query';
import { getLatestLogs } from '../api/logs';
import type { LogEntry } from '../types';

// Log level colors
const levelColors: Record<string, { bg: string; text: string }> = {
  INFO: { bg: 'transparent', text: '#333' },
  WARNING: { bg: '#fff3cd', text: '#856404' },
  ERROR: { bg: '#f8d7da', text: '#721c24' },
  DEBUG: { bg: '#e2e3e5', text: '#383d41' },
};

// Format log entry for display
function LogLine({ entry }: { entry: LogEntry }) {
  const colors = levelColors[entry.level] || levelColors.INFO;

  return (
    <Box
      sx={{
        fontFamily: 'monospace',
        fontSize: '0.85rem',
        py: 0.25,
        px: 1,
        backgroundColor: colors.bg,
        color: colors.text,
        borderBottom: '1px solid #f0f0f0',
        '&:hover': {
          backgroundColor: colors.bg === 'transparent' ? '#f5f5f5' : colors.bg,
        },
      }}
    >
      <Typography
        component="span"
        sx={{ color: '#888', mr: 1, fontFamily: 'inherit', fontSize: 'inherit' }}
      >
        {entry.timestamp}
      </Typography>
      <Typography
        component="span"
        sx={{
          color: colors.text,
          fontWeight: entry.level !== 'INFO' ? 600 : 400,
          mr: 1,
          fontFamily: 'inherit',
          fontSize: 'inherit',
        }}
      >
        [{entry.level}]
      </Typography>
      <Typography
        component="span"
        sx={{ color: '#666', mr: 1, fontFamily: 'inherit', fontSize: 'inherit' }}
      >
        {entry.module}
      </Typography>
      <Typography
        component="span"
        sx={{ fontFamily: 'inherit', fontSize: 'inherit' }}
      >
        {entry.message}
      </Typography>
    </Box>
  );
}

export default function Dev() {
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [lines, setLines] = useState(500);
  const [levelFilter, setLevelFilter] = useState<string>('');
  const [logSource, setLogSource] = useState<'agent' | 'batch'>('agent');
  const logContainerRef = useRef<HTMLDivElement>(null);

  // Fetch logs
  const { data, isLoading, error, refetch, isFetching } = useQuery({
    queryKey: ['logs', lines, levelFilter, logSource],
    queryFn: () => getLatestLogs(lines, levelFilter || undefined, logSource),
    refetchInterval: autoRefresh ? 5000 : false,
  });

  // Scroll to bottom on new data
  useEffect(() => {
    if (logContainerRef.current && data?.logs) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
    }
  }, [data?.logs]);

  return (
    <Box sx={{ p: 3, height: 'calc(100vh - 120px)', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <Paper
        sx={{
          p: 2,
          mb: 2,
          display: 'flex',
          alignItems: 'center',
          gap: 2,
          flexWrap: 'wrap',
        }}
      >
        <Typography variant="h6">
          Dev - Logs
        </Typography>

        {/* Log source toggle */}
        <ToggleButtonGroup
          value={logSource}
          exclusive
          onChange={(_, value) => value && setLogSource(value)}
          size="small"
          sx={{ ml: 2 }}
        >
          <ToggleButton value="agent">Agent Logs</ToggleButton>
          <ToggleButton value="batch">Batch Logs</ToggleButton>
        </ToggleButtonGroup>

        <Box sx={{ flex: 1 }} />

        {/* Lines selector */}
        <Select
          value={lines}
          onChange={(e) => setLines(Number(e.target.value))}
          size="small"
          sx={{ minWidth: 100 }}
        >
          <MenuItem value={100}>100 lines</MenuItem>
          <MenuItem value={500}>500 lines</MenuItem>
          <MenuItem value={1000}>1000 lines</MenuItem>
          <MenuItem value={2000}>2000 lines</MenuItem>
        </Select>

        {/* Level filter */}
        <Select
          value={levelFilter}
          onChange={(e) => setLevelFilter(e.target.value)}
          size="small"
          displayEmpty
          sx={{ minWidth: 100 }}
        >
          <MenuItem value="">All levels</MenuItem>
          <MenuItem value="INFO">INFO</MenuItem>
          <MenuItem value="WARNING">WARNING</MenuItem>
          <MenuItem value="ERROR">ERROR</MenuItem>
          <MenuItem value="DEBUG">DEBUG</MenuItem>
        </Select>

        {/* Auto refresh toggle */}
        <FormControlLabel
          control={
            <Switch
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
            />
          }
          label="Auto-refresh"
        />

        {/* Refresh button */}
        <Tooltip title="Refresh logs">
          <IconButton onClick={() => refetch()} disabled={isFetching}>
            {isFetching ? <CircularProgress size={24} /> : <RefreshIcon />}
          </IconButton>
        </Tooltip>
      </Paper>

      {/* Error display */}
      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          Failed to load logs: {(error as Error).message}
        </Alert>
      )}

      {data?.error && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          {data.error}
        </Alert>
      )}

      {/* Log viewer */}
      <Paper
        ref={logContainerRef}
        sx={{
          flex: 1,
          overflow: 'auto',
          backgroundColor: '#fafafa',
          border: '1px solid #e0e0e0',
        }}
      >
        {isLoading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
            <CircularProgress />
          </Box>
        ) : data?.logs && data.logs.length > 0 ? (
          data.logs.map((entry, index) => <LogLine key={index} entry={entry} />)
        ) : (
          <Typography sx={{ p: 3, color: '#888', textAlign: 'center' }}>
            No logs found
          </Typography>
        )}
      </Paper>

      {/* Footer with file info */}
      <Paper sx={{ p: 1.5, mt: 1, display: 'flex', gap: 2 }}>
        <Typography variant="caption" sx={{ color: '#666' }}>
          File: {data?.file || 'Unknown'}
        </Typography>
        <Typography variant="caption" sx={{ color: '#666' }}>
          Showing: {data?.returned_lines || 0} / {data?.total_lines || 0} lines
        </Typography>
        {autoRefresh && (
          <Typography variant="caption" sx={{ color: '#667eea' }}>
            Auto-refreshing every 5s
          </Typography>
        )}
      </Paper>
    </Box>
  );
}
