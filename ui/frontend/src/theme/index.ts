import { createTheme, alpha } from '@mui/material/styles';

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

// Modern score color definitions
export const scoreColors = {
  high: {
    bg: '#ecfdf5',
    text: '#047857',
    border: '#10b981',
  },
  mid: {
    bg: '#fffbeb',
    text: '#b45309',
    border: '#f59e0b',
  },
  low: {
    bg: '#fef2f2',
    text: '#b91c1c',
    border: '#ef4444',
  },
  default: {
    bg: '#f3f4f6',
    text: '#4b5563',
    border: '#9ca3af',
  },
};

// Modern color palette
const primaryColor = '#6366f1'; // Indigo
const secondaryColor = '#8b5cf6'; // Purple

// Main theme with modern design
const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: primaryColor,
      light: '#818cf8',
      dark: '#4f46e5',
      contrastText: '#ffffff',
    },
    secondary: {
      main: secondaryColor,
      light: '#a78bfa',
      dark: '#7c3aed',
    },
    background: {
      default: '#f8fafc',
      paper: '#ffffff',
    },
    text: {
      primary: '#1e293b',
      secondary: '#64748b',
    },
    success: {
      main: '#10b981',
      light: '#ecfdf5',
      dark: '#047857',
    },
    warning: {
      main: '#f59e0b',
      light: '#fffbeb',
      dark: '#b45309',
    },
    error: {
      main: '#ef4444',
      light: '#fef2f2',
      dark: '#b91c1c',
    },
    info: {
      main: '#0ea5e9',
      light: '#f0f9ff',
      dark: '#0369a1',
    },
    divider: '#e2e8f0',
  },
  typography: {
    fontFamily: [
      'Inter',
      '-apple-system',
      'BlinkMacSystemFont',
      '"Segoe UI"',
      'Roboto',
      'sans-serif',
    ].join(','),
    h1: {
      fontWeight: 700,
      letterSpacing: '-0.02em',
    },
    h2: {
      fontWeight: 700,
      letterSpacing: '-0.01em',
    },
    h3: {
      fontWeight: 600,
      letterSpacing: '-0.01em',
    },
    h4: {
      fontWeight: 600,
    },
    h5: {
      fontWeight: 600,
    },
    h6: {
      fontWeight: 600,
    },
    subtitle1: {
      fontWeight: 500,
    },
    body1: {
      lineHeight: 1.6,
    },
    body2: {
      lineHeight: 1.5,
    },
  },
  shape: {
    borderRadius: 12,
  },
  shadows: [
    'none',
    '0 1px 2px 0 rgb(0 0 0 / 0.05)',
    '0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1)',
    '0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)',
    '0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)',
    '0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1)',
    '0 25px 50px -12px rgb(0 0 0 / 0.25)',
    '0 25px 50px -12px rgb(0 0 0 / 0.25)',
    '0 25px 50px -12px rgb(0 0 0 / 0.25)',
    '0 25px 50px -12px rgb(0 0 0 / 0.25)',
    '0 25px 50px -12px rgb(0 0 0 / 0.25)',
    '0 25px 50px -12px rgb(0 0 0 / 0.25)',
    '0 25px 50px -12px rgb(0 0 0 / 0.25)',
    '0 25px 50px -12px rgb(0 0 0 / 0.25)',
    '0 25px 50px -12px rgb(0 0 0 / 0.25)',
    '0 25px 50px -12px rgb(0 0 0 / 0.25)',
    '0 25px 50px -12px rgb(0 0 0 / 0.25)',
    '0 25px 50px -12px rgb(0 0 0 / 0.25)',
    '0 25px 50px -12px rgb(0 0 0 / 0.25)',
    '0 25px 50px -12px rgb(0 0 0 / 0.25)',
    '0 25px 50px -12px rgb(0 0 0 / 0.25)',
    '0 25px 50px -12px rgb(0 0 0 / 0.25)',
    '0 25px 50px -12px rgb(0 0 0 / 0.25)',
    '0 25px 50px -12px rgb(0 0 0 / 0.25)',
    '0 25px 50px -12px rgb(0 0 0 / 0.25)',
  ],
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        body: {
          scrollbarWidth: 'thin',
          '&::-webkit-scrollbar': {
            width: '8px',
            height: '8px',
          },
          '&::-webkit-scrollbar-track': {
            background: '#f1f5f9',
          },
          '&::-webkit-scrollbar-thumb': {
            backgroundColor: '#cbd5e1',
            borderRadius: '4px',
          },
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          boxShadow: '0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1)',
          border: '1px solid #e2e8f0',
          transition: 'box-shadow 0.2s ease-in-out, transform 0.2s ease-in-out',
          '&:hover': {
            boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)',
          },
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: 'none',
          fontWeight: 500,
          borderRadius: '8px',
          padding: '8px 16px',
        },
        contained: {
          boxShadow: 'none',
          '&:hover': {
            boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)',
          },
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          fontWeight: 500,
          borderRadius: '6px',
        },
        sizeSmall: {
          height: '24px',
          fontSize: '0.75rem',
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          backgroundImage: 'none',
        },
        elevation1: {
          boxShadow: '0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1)',
        },
      },
    },
    MuiAppBar: {
      styleOverrides: {
        root: {
          boxShadow: '0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1)',
        },
      },
    },
    MuiTab: {
      styleOverrides: {
        root: {
          textTransform: 'none',
          fontWeight: 500,
          minHeight: 48,
        },
      },
    },
    MuiTabs: {
      styleOverrides: {
        indicator: {
          height: 3,
          borderRadius: '3px 3px 0 0',
        },
      },
    },
    MuiTableCell: {
      styleOverrides: {
        root: {
          borderColor: '#e2e8f0',
        },
        head: {
          fontWeight: 600,
          backgroundColor: '#f8fafc',
        },
      },
    },
    MuiSelect: {
      styleOverrides: {
        root: {
          borderRadius: '8px',
        },
      },
    },
    MuiOutlinedInput: {
      styleOverrides: {
        root: {
          borderRadius: '8px',
          '&:hover .MuiOutlinedInput-notchedOutline': {
            borderColor: alpha(primaryColor, 0.5),
          },
        },
      },
    },
    MuiSwitch: {
      styleOverrides: {
        root: {
          padding: 8,
        },
        switchBase: {
          '&.Mui-checked': {
            '& + .MuiSwitch-track': {
              opacity: 1,
            },
          },
        },
        track: {
          borderRadius: 22 / 2,
          opacity: 0.3,
        },
        thumb: {
          boxShadow: '0 2px 4px 0 rgb(0 0 0 / 0.2)',
        },
      },
    },
    MuiAlert: {
      styleOverrides: {
        root: {
          borderRadius: '8px',
        },
        standardSuccess: {
          backgroundColor: '#ecfdf5',
          color: '#047857',
        },
        standardError: {
          backgroundColor: '#fef2f2',
          color: '#b91c1c',
        },
        standardWarning: {
          backgroundColor: '#fffbeb',
          color: '#b45309',
        },
        standardInfo: {
          backgroundColor: '#f0f9ff',
          color: '#0369a1',
        },
      },
    },
  },
});

export default theme;
