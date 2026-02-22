import { createTheme } from '@mui/material/styles';

// Score thresholds
export const SCORE_THRESHOLDS = {
  HIGH: 75,
  MID: 60,
};

// Get score color based on value
export const getScoreColor = (score: number | undefined | null) => {
  if (score === undefined || score === null) return 'default';
  if (score >= SCORE_THRESHOLDS.HIGH) return 'high';
  if (score >= SCORE_THRESHOLDS.MID) return 'mid';
  return 'low';
};

// Score color definitions
export const scoreColors = {
  high: {
    bg: '#d4edda',
    text: '#155724',
    border: '#28a745',
  },
  mid: {
    bg: '#fff3cd',
    text: '#856404',
    border: '#ffc107',
  },
  low: {
    bg: '#f8d7da',
    text: '#721c24',
    border: '#dc3545',
  },
  default: {
    bg: '#e9ecef',
    text: '#495057',
    border: '#6c757d',
  },
};

// Main theme matching email design
const theme = createTheme({
  palette: {
    primary: {
      main: '#667eea',
      dark: '#764ba2',
    },
    secondary: {
      main: '#764ba2',
    },
    background: {
      default: '#f5f5f5',
      paper: '#ffffff',
    },
    text: {
      primary: '#333333',
      secondary: '#666666',
    },
    success: {
      main: '#28a745',
      light: '#d4edda',
    },
    warning: {
      main: '#ffc107',
      light: '#fff3cd',
    },
    error: {
      main: '#dc3545',
      light: '#f8d7da',
    },
  },
  typography: {
    fontFamily: [
      '-apple-system',
      'BlinkMacSystemFont',
      '"Segoe UI"',
      'Roboto',
      'sans-serif',
    ].join(','),
  },
  shape: {
    borderRadius: 8,
  },
  components: {
    MuiCard: {
      styleOverrides: {
        root: {
          boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: 'none',
        },
      },
    },
  },
});

export default theme;
