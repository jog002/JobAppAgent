import { Select, MenuItem, alpha } from '@mui/material';
import type { SelectChangeEvent } from '@mui/material';
import type { JobStatus } from '../types';
import { JOB_STATUSES, STATUS_LABELS } from '../types';

interface StatusDropdownProps {
  status: JobStatus | undefined;
  onChange: (newStatus: JobStatus) => void;
  disabled?: boolean;
  size?: 'small' | 'medium';
}

// Modern status color configuration
const statusConfig: Record<JobStatus, { color: string; bg: string }> = {
  new: { color: '#6366f1', bg: '#eef2ff' },
  reviewed: { color: '#0ea5e9', bg: '#f0f9ff' },
  applied: { color: '#10b981', bg: '#ecfdf5' },
  not_interested: { color: '#64748b', bg: '#f1f5f9' },
  deleted: { color: '#ef4444', bg: '#fef2f2' },
};

export default function StatusDropdown({
  status = 'new',
  onChange,
  disabled = false,
  size = 'small',
}: StatusDropdownProps) {
  const handleChange = (event: SelectChangeEvent<JobStatus>) => {
    onChange(event.target.value as JobStatus);
  };

  const currentConfig = statusConfig[status] || statusConfig.new;

  return (
    <Select
      value={status}
      onChange={handleChange}
      disabled={disabled}
      size={size}
      sx={{
        minWidth: 130,
        borderRadius: '8px',
        backgroundColor: currentConfig.bg,
        '& .MuiSelect-select': {
          py: size === 'small' ? 0.75 : 1,
          color: currentConfig.color,
          fontWeight: 600,
          fontSize: '0.8rem',
        },
        '& .MuiOutlinedInput-notchedOutline': {
          borderColor: alpha(currentConfig.color, 0.3),
        },
        '&:hover .MuiOutlinedInput-notchedOutline': {
          borderColor: alpha(currentConfig.color, 0.5),
        },
        '&.Mui-focused .MuiOutlinedInput-notchedOutline': {
          borderColor: currentConfig.color,
          borderWidth: 1.5,
        },
        '& .MuiSvgIcon-root': {
          color: currentConfig.color,
        },
      }}
    >
      {JOB_STATUSES.map((s) => {
        const config = statusConfig[s];
        return (
          <MenuItem
            key={s}
            value={s}
            sx={{
              color: config.color,
              fontWeight: 500,
              fontSize: '0.85rem',
              '&:hover': {
                backgroundColor: config.bg,
              },
              '&.Mui-selected': {
                backgroundColor: config.bg,
                '&:hover': {
                  backgroundColor: config.bg,
                },
              },
            }}
          >
            {STATUS_LABELS[s]}
          </MenuItem>
        );
      })}
    </Select>
  );
}
