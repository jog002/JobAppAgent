import { BrowserRouter, Routes, Route, NavLink, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider, useQuery } from '@tanstack/react-query';
import { ThemeProvider, CssBaseline, Box, Tabs, Tab } from '@mui/material';
import HomeIcon from '@mui/icons-material/Home';
import ListIcon from '@mui/icons-material/List';
import CodeIcon from '@mui/icons-material/Code';

import theme from './theme';
import Header from './components/Header';
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
  return (
    <Box
      sx={{
        borderBottom: 1,
        borderColor: 'divider',
        backgroundColor: 'white',
      }}
    >
      <Tabs
        value={false} // Let NavLink handle active state
        sx={{
          '& .MuiTab-root': {
            textTransform: 'none',
            minHeight: 48,
            fontWeight: 500,
          },
        }}
      >
        <Tab
          component={NavLink}
          to="/"
          icon={<HomeIcon />}
          iconPosition="start"
          label="Suggested Jobs"
          sx={{
            '&.active': {
              color: '#667eea',
              backgroundColor: 'rgba(102, 126, 234, 0.08)',
            },
          }}
        />
        <Tab
          component={NavLink}
          to="/all-jobs"
          icon={<ListIcon />}
          iconPosition="start"
          label="All Jobs"
          sx={{
            '&.active': {
              color: '#667eea',
              backgroundColor: 'rgba(102, 126, 234, 0.08)',
            },
          }}
        />
        <Tab
          component={NavLink}
          to="/dev"
          icon={<CodeIcon />}
          iconPosition="start"
          label="Dev"
          sx={{
            '&.active': {
              color: '#667eea',
              backgroundColor: 'rgba(102, 126, 234, 0.08)',
            },
          }}
        />
      </Tabs>
    </Box>
  );
}

// Main app content
function AppContent() {
  const { data: latestRun } = useQuery({
    queryKey: ['latestRun'],
    queryFn: getLatestRun,
    retry: false,
  });

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
      <Header runNumber={latestRun?.run_number} />
      <NavTabs />
      <Box sx={{ flex: 1, backgroundColor: '#f5f5f5' }}>
        <Routes>
          <Route path="/" element={<SuggestedJobs />} />
          <Route path="/all-jobs" element={<AllJobs />} />
          <Route path="/dev" element={<Dev />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Box>
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
