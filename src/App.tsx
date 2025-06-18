import React from 'react';
import { Box, Tab, Tabs } from '@mui/material';
import AccountManagement from './components/AccountManagement';
import Messaging from './components/Messaging';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`simple-tabpanel-${index}`}
      aria-labelledby={`simple-tab-${index}`}
      {...other}
    >
      {value === index && (
        <Box sx={{ p: 3 }}>
          {children}
        </Box>
      )}
    </div>
  );
}

function App() {
  const [value, setValue] = React.useState(0);

  const handleChange = (event: React.SyntheticEvent, newValue: number) => {
    setValue(newValue);
  };

  return (
    <Box sx={{ width: '100%' }}>
      <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
        <Tabs value={value} onChange={handleChange} aria-label="instagram tabs">
          <Tab label="Quản lý tài khoản" />
          <Tab label="Nhắn tin" />
          <Tab label="Quét dữ liệu" />
          <Tab label="Quản lý proxy" />
        </Tabs>
      </Box>
      <TabPanel value={value} index={0}>
        <AccountManagement />
      </TabPanel>
      <TabPanel value={value} index={1}>
        <Messaging />
      </TabPanel>
      <TabPanel value={value} index={2}>
        Quét dữ liệu (Đang phát triển)
      </TabPanel>
      <TabPanel value={value} index={3}>
        Quản lý proxy (Đang phát triển)
      </TabPanel>
    </Box>
  );
}

export default App; 