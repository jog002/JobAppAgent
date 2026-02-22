import { AppBar, Toolbar, Typography, Chip } from '@mui/material';
import WorkIcon from '@mui/icons-material/Work';

interface HeaderProps {
  runNumber?: number;
}

export default function Header({ runNumber }: HeaderProps) {
  return (
    <AppBar
      position="static"
      sx={{
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
      }}
    >
      <Toolbar>
        <WorkIcon sx={{ mr: 1.5 }} />
        <Typography variant="h6" component="div" sx={{ flexGrow: 1, fontWeight: 600 }}>
          Job Search Agent
        </Typography>
        {runNumber !== undefined && (
          <Chip
            label={`Run #${runNumber}`}
            size="small"
            sx={{
              backgroundColor: 'rgba(255,255,255,0.2)',
              color: 'white',
              fontWeight: 500,
            }}
          />
        )}
      </Toolbar>
    </AppBar>
  );
}
