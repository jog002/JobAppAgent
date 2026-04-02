import { AppBar, Toolbar, Typography, Chip, Box, IconButton, Tooltip } from '@mui/material';
import WorkOutlineIcon from '@mui/icons-material/WorkOutline';
import SettingsIcon from '@mui/icons-material/Settings';
import RefreshIcon from '@mui/icons-material/Refresh';

interface HeaderProps {
  runNumber?: number;
  onSettingsClick?: () => void;
  onRefresh?: () => void;
}

export default function Header({ runNumber, onSettingsClick, onRefresh }: HeaderProps) {
  return (
    <AppBar
      position="static"
      elevation={0}
      sx={{
        background: 'linear-gradient(135deg, #6366f1 0%, #8b5cf6 50%, #a855f7 100%)',
        borderBottom: '1px solid rgba(255,255,255,0.1)',
      }}
    >
      <Toolbar sx={{ minHeight: { xs: 56, sm: 64 } }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
          <Box
            sx={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              width: 40,
              height: 40,
              borderRadius: '10px',
              backgroundColor: 'rgba(255,255,255,0.15)',
              backdropFilter: 'blur(10px)',
            }}
          >
            <WorkOutlineIcon sx={{ fontSize: 24 }} />
          </Box>
          <Box>
            <Typography
              variant="h6"
              component="div"
              sx={{
                fontWeight: 700,
                fontSize: '1.25rem',
                letterSpacing: '-0.02em',
                lineHeight: 1.2,
              }}
            >
              JobAgent
            </Typography>
            <Typography
              variant="caption"
              sx={{
                opacity: 0.8,
                fontSize: '0.7rem',
                letterSpacing: '0.05em',
                textTransform: 'uppercase',
              }}
            >
              Smart Job Discovery
            </Typography>
          </Box>
        </Box>

        <Box sx={{ flexGrow: 1 }} />

        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          {runNumber !== undefined && (
            <Chip
              label={`Run #${runNumber}`}
              size="small"
              sx={{
                backgroundColor: 'rgba(255,255,255,0.15)',
                color: 'white',
                fontWeight: 600,
                fontSize: '0.75rem',
                height: 28,
                backdropFilter: 'blur(10px)',
                border: '1px solid rgba(255,255,255,0.2)',
                '& .MuiChip-label': {
                  px: 1.5,
                },
              }}
            />
          )}
          {onRefresh && (
            <Tooltip title="Refresh data">
              <IconButton
                onClick={onRefresh}
                size="small"
                sx={{
                  color: 'rgba(255,255,255,0.9)',
                  '&:hover': {
                    backgroundColor: 'rgba(255,255,255,0.15)',
                  },
                }}
              >
                <RefreshIcon fontSize="small" />
              </IconButton>
            </Tooltip>
          )}
          {onSettingsClick && (
            <Tooltip title="Settings">
              <IconButton
                onClick={onSettingsClick}
                size="small"
                sx={{
                  color: 'rgba(255,255,255,0.9)',
                  '&:hover': {
                    backgroundColor: 'rgba(255,255,255,0.15)',
                  },
                }}
              >
                <SettingsIcon fontSize="small" />
              </IconButton>
            </Tooltip>
          )}
        </Box>
      </Toolbar>
    </AppBar>
  );
}
