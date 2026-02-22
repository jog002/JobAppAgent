import { Box, Card, CardContent, Typography, Link, Chip, Stack } from '@mui/material';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import LocationOnIcon from '@mui/icons-material/LocationOn';
import ScoreBadge from './ScoreBadge';
import StatusDropdown from './StatusDropdown';
import type { Job, JobStatus } from '../types';
import { getScoreColor, scoreColors } from '../theme';

interface JobCardProps {
  job: Job;
  onStatusChange?: (jobId: number, newStatus: JobStatus) => void;
  isUpdating?: boolean;
}

// Format source name for display
function formatSource(source?: string): string {
  if (!source) return '';
  const sourceMap: Record<string, string> = {
    web_scraping: 'Web',
    linkedin: 'LinkedIn',
    greenhouse: 'GH',
    lever: 'Lever',
    ashby: 'Ashby',
    bamboohr: 'BambooHR',
  };
  return sourceMap[source] || source;
}

export default function JobCard({ job, onStatusChange, isUpdating }: JobCardProps) {
  const colorKey = getScoreColor(job.score);
  const borderColor = scoreColors[colorKey].border;

  const handleStatusChange = (newStatus: JobStatus) => {
    if (onStatusChange) {
      onStatusChange(job.id, newStatus);
    }
  };

  return (
    <Card
      sx={{
        mb: 1.5,
        borderLeft: `4px solid ${borderColor}`,
        backgroundColor: '#f8f9fa',
        '&:hover': {
          backgroundColor: '#f0f1f2',
        },
      }}
    >
      <CardContent sx={{ py: 1.5, '&:last-child': { pb: 1.5 } }}>
        {/* Title row with score */}
        <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 1, mb: 0.5 }}>
          <Link
            href={job.url}
            target="_blank"
            rel="noopener noreferrer"
            sx={{
              flex: 1,
              fontWeight: 600,
              color: '#333',
              textDecoration: 'none',
              display: 'flex',
              alignItems: 'center',
              gap: 0.5,
              '&:hover': {
                color: '#667eea',
                textDecoration: 'underline',
              },
            }}
          >
            {job.title}
            <OpenInNewIcon sx={{ fontSize: 14, opacity: 0.6 }} />
          </Link>
          <ScoreBadge score={job.score} size="small" />
        </Box>

        {/* Company */}
        <Typography
          variant="body2"
          sx={{ color: '#666', fontWeight: 500, mb: 0.5 }}
        >
          {job.company}
        </Typography>

        {/* Meta info row */}
        <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" sx={{ mb: 1 }}>
          {job.location && (
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.25 }}>
              <LocationOnIcon sx={{ fontSize: 14, color: '#888' }} />
              <Typography variant="caption" sx={{ color: '#888' }}>
                {job.location}
              </Typography>
            </Box>
          )}
          {job.source && (
            <Chip
              label={formatSource(job.source)}
              size="small"
              sx={{
                height: 20,
                fontSize: '0.7rem',
                backgroundColor: '#e9ecef',
                color: '#495057',
              }}
            />
          )}
          {job.remote_type && job.remote_type !== 'Unknown' && (
            <Chip
              label={job.remote_type}
              size="small"
              sx={{
                height: 20,
                fontSize: '0.7rem',
                backgroundColor: job.remote_type === 'Remote' ? '#d4edda' : '#fff3cd',
                color: job.remote_type === 'Remote' ? '#155724' : '#856404',
              }}
            />
          )}
        </Stack>

        {/* Status dropdown */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <StatusDropdown
            status={job.status as JobStatus}
            onChange={handleStatusChange}
            disabled={isUpdating}
            size="small"
          />
        </Box>
      </CardContent>
    </Card>
  );
}
