import { Box, Card, CardContent, Typography, Link, Chip, Stack } from '@mui/material';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import LocationOnIcon from '@mui/icons-material/LocationOn';
import BusinessIcon from '@mui/icons-material/Business';
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
const sourceConfig: Record<string, { label: string; bg: string; text: string }> = {
  web_scraping: { label: 'Web', bg: '#f0f9ff', text: '#0369a1' },
  linkedin: { label: 'LinkedIn', bg: '#eff6ff', text: '#1d4ed8' },
  greenhouse: { label: 'Greenhouse', bg: '#ecfdf5', text: '#047857' },
  lever: { label: 'Lever', bg: '#faf5ff', text: '#7c3aed' },
  ashby: { label: 'Ashby', bg: '#fff7ed', text: '#c2410c' },
  bamboohr: { label: 'BambooHR', bg: '#ecfdf5', text: '#059669' },
  indeed: { label: 'Indeed', bg: '#faf5ff', text: '#7c3aed' },
  glassdoor: { label: 'Glassdoor', bg: '#ecfdf5', text: '#059669' },
};

// Remote type colors
const remoteTypeConfig: Record<string, { bg: string; text: string }> = {
  Remote: { bg: '#ecfdf5', text: '#047857' },
  Hybrid: { bg: '#fffbeb', text: '#b45309' },
  'On-site': { bg: '#fef2f2', text: '#b91c1c' },
};

export default function JobCard({ job, onStatusChange, isUpdating }: JobCardProps) {
  const colorKey = getScoreColor(job.score);
  const borderColor = scoreColors[colorKey].border;

  const handleStatusChange = (newStatus: JobStatus) => {
    if (onStatusChange) {
      onStatusChange(job.id, newStatus);
    }
  };

  const source = sourceConfig[job.source || ''] || { label: job.source || 'Unknown', bg: '#f3f4f6', text: '#4b5563' };
  const remoteType = remoteTypeConfig[job.remote_type || ''];

  return (
    <Card
      sx={{
        mb: 1.5,
        borderLeft: `4px solid ${borderColor}`,
        backgroundColor: 'white',
        border: '1px solid #e2e8f0',
        borderLeftColor: borderColor,
        borderLeftWidth: 4,
        transition: 'all 0.2s ease-in-out',
        '&:hover': {
          backgroundColor: '#fafbfc',
          boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)',
          transform: 'translateY(-1px)',
        },
      }}
    >
      <CardContent sx={{ py: 2, px: 2.5, '&:last-child': { pb: 2 } }}>
        {/* Title row with score */}
        <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 1.5, mb: 1 }}>
          <Link
            href={job.url}
            target="_blank"
            rel="noopener noreferrer"
            sx={{
              flex: 1,
              fontWeight: 600,
              fontSize: '0.95rem',
              color: '#1e293b',
              textDecoration: 'none',
              display: 'flex',
              alignItems: 'center',
              gap: 0.5,
              lineHeight: 1.4,
              '&:hover': {
                color: '#6366f1',
                textDecoration: 'underline',
              },
            }}
          >
            {job.title}
            <OpenInNewIcon sx={{ fontSize: 14, opacity: 0.5, flexShrink: 0 }} />
          </Link>
          <ScoreBadge score={job.score} size="small" />
        </Box>

        {/* Company */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mb: 1 }}>
          <BusinessIcon sx={{ fontSize: 14, color: '#94a3b8' }} />
          <Typography
            variant="body2"
            sx={{ color: '#64748b', fontWeight: 500 }}
          >
            {job.company}
          </Typography>
        </Box>

        {/* Meta info row */}
        <Stack direction="row" spacing={0.75} alignItems="center" flexWrap="wrap" useFlexGap sx={{ mb: 1.5 }}>
          {job.location && (
            <Box
              sx={{
                display: 'flex',
                alignItems: 'center',
                gap: 0.25,
                backgroundColor: '#f8fafc',
                px: 1,
                py: 0.25,
                borderRadius: 1,
              }}
            >
              <LocationOnIcon sx={{ fontSize: 13, color: '#94a3b8' }} />
              <Typography variant="caption" sx={{ color: '#64748b', fontWeight: 500 }}>
                {job.location}
              </Typography>
            </Box>
          )}
          {job.source && (
            <Chip
              label={source.label}
              size="small"
              sx={{
                height: 22,
                fontSize: '0.7rem',
                fontWeight: 600,
                backgroundColor: source.bg,
                color: source.text,
                '& .MuiChip-label': { px: 1 },
              }}
            />
          )}
          {remoteType && (
            <Chip
              label={job.remote_type}
              size="small"
              sx={{
                height: 22,
                fontSize: '0.7rem',
                fontWeight: 600,
                backgroundColor: remoteType.bg,
                color: remoteType.text,
                '& .MuiChip-label': { px: 1 },
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
