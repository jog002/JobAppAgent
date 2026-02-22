import { Box } from '@mui/material';
import { getScoreColor, scoreColors } from '../theme';

interface ScoreBadgeProps {
  score: number | undefined | null;
  size?: 'small' | 'medium';
}

export default function ScoreBadge({ score, size = 'medium' }: ScoreBadgeProps) {
  const colorKey = getScoreColor(score);
  const colors = scoreColors[colorKey];

  const displayScore = score !== undefined && score !== null ? score : '—';

  return (
    <Box
      component="span"
      sx={{
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        px: size === 'small' ? 1 : 1.5,
        py: size === 'small' ? 0.25 : 0.5,
        borderRadius: '12px',
        fontSize: size === 'small' ? '0.75rem' : '0.875rem',
        fontWeight: 600,
        backgroundColor: colors.bg,
        color: colors.text,
        border: `1px solid ${colors.border}`,
        minWidth: size === 'small' ? '36px' : '48px',
      }}
    >
      {displayScore}
    </Box>
  );
}
