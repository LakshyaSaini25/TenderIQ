import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { MainLayout } from './components/layout/MainLayout';
import { Dashboard } from './pages/Dashboard';
import { Sources } from './pages/Sources';
import { Content } from './pages/Content';
import { Opportunities } from './pages/Opportunities';
import { ExploreTenders } from './pages/ExploreTenders';
import { useEffect, useState } from 'react';
import { api } from './services/api';

function App() {
  const [systemCheck, setSystemCheck] = useState<{api: string, db: string}>({ api: 'Checking...', db: 'Checking...' });

  useEffect(() => {
    const checkSystem = async () => {
      try {
        await api.checkHealth();
        setSystemCheck(prev => ({ ...prev, api: 'Connected' }));
      } catch (_e) {
        setSystemCheck(prev => ({ ...prev, api: 'Error' }));
      }

      try {
        await api.checkDbHealth();
        setSystemCheck(prev => ({ ...prev, db: 'Connected' }));
      } catch (_e) {
        setSystemCheck(prev => ({ ...prev, db: 'Error' }));
      }
    };
    checkSystem();
  }, []);

  return (
    <Router>
      <MainLayout>
        {/* System warning banner */}
        {(systemCheck.api === 'Error' || systemCheck.db === 'Error') && (
          <div style={{ background: '#fee2e2', color: '#991b1b', padding: '12px', borderRadius: '8px', marginBottom: '24px' }}>
            <strong>System Status Warning:</strong> Backend: {systemCheck.api} | Database: {systemCheck.db}
          </div>
        )}

        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/explore" element={<ExploreTenders />} />
          <Route path="/opportunities" element={<Opportunities />} />
          <Route path="/sources" element={<Sources />} />
          <Route path="/content" element={<Content />} />
          <Route path="*" element={<Dashboard />} />
        </Routes>
      </MainLayout>
    </Router>
  );
}

export default App;
