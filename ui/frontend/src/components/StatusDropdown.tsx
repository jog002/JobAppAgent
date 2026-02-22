import { Select, MenuItem } from '@mui/material';
import type { SelectChangeEvent } from '@mui/material';
import type { JobStatus } from '../types';
import { JOB_STATUSES, STATUS_LABELS } from '../types';

interface StatusDropdownProps {
  status: JobStatus | undefined;
  onChange: (newStatus: JobStatus) => void;
  disabled?: boolean;
  size?: 'small' | 'medium';
}

// Status colors for visual distinction
const statusColors: Record<JobStatus, string> = {
  new: '#667eea',
  reviewed: '#17a2b8',
  applied: '#28a745',
  not_interested: '#6c757d',
  deleted: '#dc3545',
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

  return (
    <Select
      value={status}
      onChange={handleChange}
      disabled={disabled}
      size={size}
      sx={{
        minWidth: 120,
        '& .MuiSelect-select': {
          py: size === 'small' ? 0.5 : 1,
          color: statusColors[status] || '#333',
          fontWeight: 500,
        },
      }}
    >
      {JOB_STATUSES.map((s) => (
        <MenuItem
          key={s}
          value={s}
          sx={{
            color: statusColors[s],
            fontWeight: 500,
          }}
        >
          {STATUS_LABELS[s]}
        </MenuItem>
      ))}
    </Select>
  );
}
