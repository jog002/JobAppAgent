import { useState } from 'react';
import { BrowserRouter, Routes, Route, NavLink, Navigate, useLocation } from 'react-router-dom';
import { QueryClient, QueryClientProvider, useQuery, useQueryClient } from '@tanstack/react-query';
import { ThemeProvider, CssBaseline, Box, Tabs, Tab, alpha } from '@mui/material';
import HomeIcon from '@mui/icons-material/Home';
import TableChartIcon from '@mui/icons-material/TableChart';
import TerminalIcon from '@mui/icons-material/Terminal';

import theme from './theme';
import Header from './components/Header';
import SettingsDialog from './components/SettingsDialog';
import SuggestedJobs from './pages/SuggestedJobs';
import AllJobs from './pages/AllJobs';
import Dev from './pages/Dev';
import { getLatestRun } from './api/logs';

// Create a client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30000, // 30 seconds
      retry: 1,
    },
  },
});

// Navigation tabs component
function NavTabs() {
  const location = useLocation();

  // Map paths to tab indices
  const pathToIndex: Record<string, number> = {
    '/': 0,
    '/all-jobs': 1,
    '/dev': 2,
  };

  const currentTab = pathToIndex[location.pathname] ?? 0;

  return (
    <Box
      sx={{
        borderBottom: 1,
        borderColor: 'divider',
        backgroundColor: 'white',
        px: 2,
      }}
    >
      <Tabs
        value={currentTab}
        sx={{
          '& .MuiTabs-indicator': {
            backgroundColor: '#6366f1',
            height: 3,
            borderRadius: '3px 3px 0 0',
          },
          '& .MuiTab-root': {
            textTransform: 'none',
            minHeight: 52,
            fontWeight: 500,
            fontSize: '0.9rem',
            color: '#64748b',
            px: 2.5,
            gap: 1,
            '&:hover': {
              color: '#6366f1',
              backgroundColor: alpha('#6366f1', 0.04),
            },
            '&.Mui-selected': {
              color: '#6366f1',
              fontWeight: 600,
            },
          },
        }}
      >
        <Tab
          component={NavLink}
          to="/"
          icon={<HomeIcon sx={{ fontSize: 20 }} />}
          iconPosition="start"
          label="Dashboard"
        />
        <Tab
          component={NavLink}
          to="/all-jobs"
          icon={<TableChartIcon sx={{ fontSize: 20 }} />}
          iconPosition="start"
          label="All Jobs"
        />
        <Tab
          component={NavLink}
          to="/dev"
          icon={<TerminalIcon sx={{ fontSize: 20 }} />}
          iconPosition="start"
          label="Developer"
        />
      </Tabs>
    </Box>
  );
}

// Main app content
function AppContent() {
  const queryClientInner = useQueryClient();
  const [settingsOpen, setSettingsOpen] = useState(false);

  const { data: latestRun } = useQuery({
    queryKey: ['latestRun'],
    queryFn: getLatestRun,
    retry: false,
  });

  const handleRefresh = () => {
    queryClientInner.invalidateQueries();
  };

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
      <Header
        runNumber={latestRun?.run_number}
        onSettingsClick={() => setSettingsOpen(true)}
        onRefresh={handleRefresh}
      />
      <NavTabs />
      <Box
        sx={{
          flex: 1,
          backgroundColor: '#f8fafc',
          overflow: 'auto',
        }}
      >
        <Routes>
          <Route path="/" element={<SuggestedJobs />} />
          <Route path="/all-jobs" element={<AllJobs />} />
          <Route path="/dev" element={<Dev />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Box>
      <SettingsDialog
        open={settingsOpen}
        onClose={() => setSettingsOpen(false)}
      />
    </Box>
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <BrowserRouter>
          <AppContent />
        </BrowserRouter>
      </ThemeProvider>
    </QueryClientProvider>
  );
}

export default App;
