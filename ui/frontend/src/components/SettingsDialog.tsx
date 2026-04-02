import { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Box,
  Typography,
  TextField,
  ToggleButton,
  ToggleButtonGroup,
  Alert,
  CircularProgress,
  Divider,
  IconButton,
  Chip,
} from '@mui/material';
import CloseIcon from '@mui/icons-material/Close';
import StorageIcon from '@mui/icons-material/Storage';
import CloudIcon from '@mui/icons-material/Cloud';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ErrorIcon from '@mui/icons-material/Error';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getConfig, updateConfig, testConnection } from '../api/config';

interface SettingsDialogProps {
  open: boolean;
  onClose: () => void;
}

export default function SettingsDialog({ open, onClose }: SettingsDialogProps) {
  const queryClient = useQueryClient();
  const [databaseMode, setDatabaseMode] = useState<'local' | 'turso'>('local');
  const [tursoUrl, setTursoUrl] = useState('');
  const [tursoToken, setTursoToken] = useState('');
  const [connectionStatus, setConnectionStatus] = useState<'idle' | 'testing' | 'success' | 'error'>('idle');
  const [connectionError, setConnectionError] = useState('');

  // Fetch current config
  const { data: config, isLoading } = useQuery({
    queryKey: ['config'],
    queryFn: getConfig,
    enabled: open,
  });

  // Update form when config loads
  useEffect(() => {
    if (config) {
      setDatabaseMode(config.database_mode);
      setTursoUrl(config.turso_url || '');
      setTursoToken(config.turso_token ? '********' : '');
    }
  }, [config]);

  // Save config mutation
  const saveMutation = useMutation({
    mutationFn: updateConfig,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['config'] });
      queryClient.invalidateQueries({ queryKey: ['jobs'] });
      queryClient.invalidateQueries({ queryKey: ['suggestedJobs'] });
      onClose();
    },
  });

  // Test connection mutation
  const testMutation = useMutation({
    mutationFn: testConnection,
    onMutate: () => {
      setConnectionStatus('testing');
      setConnectionError('');
    },
    onSuccess: (result) => {
      if (result.success) {
        setConnectionStatus('success');
      } else {
        setConnectionStatus('error');
        setConnectionError(result.error || 'Connection failed');
      }
    },
    onError: (error: Error) => {
      setConnectionStatus('error');
      setConnectionError(error.message);
    },
  });

  const handleModeChange = (_: React.MouseEvent<HTMLElement>, newMode: 'local' | 'turso' | null) => {
    if (newMode) {
      setDatabaseMode(newMode);
      setConnectionStatus('idle');
    }
  };

  const handleTestConnection = () => {
    testMutation.mutate({
      mode: databaseMode,
      turso_url: databaseMode === 'turso' ? tursoUrl : undefined,
      turso_token: databaseMode === 'turso' && tursoToken !== '********' ? tursoToken : undefined,
    });
  };

  const handleSave = () => {
    saveMutation.mutate({
      database_mode: databaseMode,
      turso_url: databaseMode === 'turso' ? tursoUrl : undefined,
      turso_token: databaseMode === 'turso' && tursoToken !== '********' ? tursoToken : undefined,
    });
  };

  const isValid = databaseMode === 'local' || (tursoUrl && tursoToken);

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="sm"
      fullWidth
      PaperProps={{
        sx: {
          borderRadius: 3,
          boxShadow: '0 25px 50px -12px rgb(0 0 0 / 0.25)',
        },
      }}
    >
      <DialogTitle
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          pb: 1,
        }}
      >
        <Box>
          <Typography variant="h6" fontWeight={600}>
            Settings
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Configure your JobAgent preferences
          </Typography>
        </Box>
        <IconButton onClick={onClose} size="small">
          <CloseIcon />
        </IconButton>
      </DialogTitle>

      <Divider />

      <DialogContent sx={{ pt: 3 }}>
        {isLoading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
            <CircularProgress />
          </Box>
        ) : (
          <Box>
            {/* Database Mode Section */}
            <Typography variant="subtitle1" fontWeight={600} gutterBottom>
              Database Configuration
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              Choose where to store your job data
            </Typography>

            <ToggleButtonGroup
              value={databaseMode}
              exclusive
              onChange={handleModeChange}
              fullWidth
              sx={{ mb: 3 }}
            >
              <ToggleButton
                value="local"
                sx={{
                  py: 2,
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 0.5,
                  '&.Mui-selected': {
                    backgroundColor: 'rgba(99, 102, 241, 0.08)',
                    borderColor: '#6366f1',
                    '&:hover': {
                      backgroundColor: 'rgba(99, 102, 241, 0.12)',
                    },
                  },
                }}
              >
                <StorageIcon sx={{ fontSize: 28, color: databaseMode === 'local' ? '#6366f1' : '#64748b' }} />
                <Typography variant="body2" fontWeight={500}>
                  Local SQLite
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  Store data on this machine
                </Typography>
              </ToggleButton>
              <ToggleButton
                value="turso"
                sx={{
                  py: 2,
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 0.5,
                  '&.Mui-selected': {
                    backgroundColor: 'rgba(99, 102, 241, 0.08)',
                    borderColor: '#6366f1',
                    '&:hover': {
                      backgroundColor: 'rgba(99, 102, 241, 0.12)',
                    },
                  },
                }}
              >
                <CloudIcon sx={{ fontSize: 28, color: databaseMode === 'turso' ? '#6366f1' : '#64748b' }} />
                <Typography variant="body2" fontWeight={500}>
                  Turso Cloud
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  Sync across devices
                </Typography>
              </ToggleButton>
            </ToggleButtonGroup>

            {/* Turso Configuration */}
            {databaseMode === 'turso' && (
              <Box
                sx={{
                  p: 2.5,
                  backgroundColor: '#f8fafc',
                  borderRadius: 2,
                  border: '1px solid #e2e8f0',
                }}
              >
                <Typography variant="subtitle2" fontWeight={600} gutterBottom>
                  Turso Credentials
                </Typography>
                <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 2 }}>
                  Get your credentials from{' '}
                  <a
                    href="https://turso.tech"
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{ color: '#6366f1' }}
                  >
                    turso.tech
                  </a>
                </Typography>

                <TextField
                  label="Database URL"
                  value={tursoUrl}
                  onChange={(e) => setTursoUrl(e.target.value)}
                  fullWidth
                  size="small"
                  placeholder="libsql://your-db.turso.io"
                  sx={{ mb: 2 }}
                />

                <TextField
                  label="Auth Token"
                  value={tursoToken}
                  onChange={(e) => setTursoToken(e.target.value)}
                  fullWidth
                  size="small"
                  type="password"
                  placeholder="Enter your Turso auth token"
                />

                {/* Connection Status */}
                <Box sx={{ mt: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Button
                    variant="outlined"
                    size="small"
                    onClick={handleTestConnection}
                    disabled={!tursoUrl || !tursoToken || connectionStatus === 'testing'}
                    sx={{ borderRadius: 2 }}
                  >
                    {connectionStatus === 'testing' ? (
                      <>
                        <CircularProgress size={16} sx={{ mr: 1 }} />
                        Testing...
                      </>
                    ) : (
                      'Test Connection'
                    )}
                  </Button>

                  {connectionStatus === 'success' && (
                    <Chip
                      icon={<CheckCircleIcon />}
                      label="Connected"
                      size="small"
                      color="success"
                      sx={{ borderRadius: 1.5 }}
                    />
                  )}

                  {connectionStatus === 'error' && (
                    <Chip
                      icon={<ErrorIcon />}
                      label="Failed"
                      size="small"
                      color="error"
                      sx={{ borderRadius: 1.5 }}
                    />
                  )}
                </Box>

                {connectionStatus === 'error' && connectionError && (
                  <Alert severity="error" sx={{ mt: 2 }}>
                    {connectionError}
                  </Alert>
                )}
              </Box>
            )}

            {/* Local mode info */}
            {databaseMode === 'local' && (
              <Box
                sx={{
                  p: 2.5,
                  backgroundColor: '#f8fafc',
                  borderRadius: 2,
                  border: '1px solid #e2e8f0',
                }}
              >
                <Typography variant="body2" color="text.secondary">
                  Jobs will be stored in a local SQLite database at{' '}
                  <code style={{ backgroundColor: '#e2e8f0', padding: '2px 6px', borderRadius: 4 }}>
                    ./data/jobs.db
                  </code>
                </Typography>
              </Box>
            )}
          </Box>
        )}
      </DialogContent>

      <Divider />

      <DialogActions sx={{ px: 3, py: 2 }}>
        <Button onClick={onClose} sx={{ borderRadius: 2 }}>
          Cancel
        </Button>
        <Button
          variant="contained"
          onClick={handleSave}
          disabled={!isValid || saveMutation.isPending}
          sx={{
            borderRadius: 2,
            px: 3,
            background: 'linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)',
          }}
        >
          {saveMutation.isPending ? 'Saving...' : 'Save Changes'}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
