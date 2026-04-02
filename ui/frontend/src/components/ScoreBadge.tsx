import { Box } from '@mui/material';
import { getScoreColor, scoreColors } from '../theme';

interface ScoreBadgeProps {
  score: number | undefined | null;
  size?: 'small' | 'medium' | 'large';
}

export default function ScoreBadge({ score, size = 'medium' }: ScoreBadgeProps) {
  const colorKey = getScoreColor(score);
  const colors = scoreColors[colorKey];

  const displayScore = score !== undefined && score !== null ? score : '—';

  const sizeStyles = {
    small: {
      px: 1,
      py: 0.25,
      fontSize: '0.75rem',
      minWidth: '36px',
      borderRadius: '8px',
    },
    medium: {
      px: 1.5,
      py: 0.5,
      fontSize: '0.875rem',
      minWidth: '44px',
      borderRadius: '10px',
    },
    large: {
      px: 2,
      py: 0.75,
      fontSize: '1rem',
      minWidth: '52px',
      borderRadius: '12px',
    },
  };

  const styles = sizeStyles[size];

  return (
    <Box
      component="span"
      sx={{
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontWeight: 700,
        fontVariantNumeric: 'tabular-nums',
        backgroundColor: colors.bg,
        color: colors.text,
        border: `1.5px solid ${colors.border}`,
        boxShadow: `0 1px 2px 0 ${colors.border}20`,
        transition: 'all 0.15s ease',
        ...styles,
      }}
    >
      {displayScore}
    </Box>
  );
}
