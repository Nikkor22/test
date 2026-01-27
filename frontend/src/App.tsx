import { useEffect, useState } from 'react';
import { Routes, Route, useNavigate, useLocation } from 'react-router-dom';
import SchedulePage from './pages/SchedulePage';
import SubjectsPage from './pages/SubjectsPage';
import TeachersPage from './pages/TeachersPage';
import SettingsPage from './pages/SettingsPage';

type Tab = 'schedule' | 'subjects' | 'teachers' | 'settings';

function App() {
  const navigate = useNavigate();
  const location = useLocation();
  const [activeTab, setActiveTab] = useState<Tab>('schedule');

  useEffect(() => {
    if (window.Telegram?.WebApp) {
      window.Telegram.WebApp.ready();
      window.Telegram.WebApp.expand();
      window.Telegram.WebApp.setHeaderColor('#0f0f1a');
      window.Telegram.WebApp.setBackgroundColor('#0f0f1a');
    }
  }, []);

  useEffect(() => {
    const path = location.pathname;
    if (path.includes('subjects')) {
      setActiveTab('subjects');
    } else if (path.includes('teachers')) {
      setActiveTab('teachers');
    } else if (path.includes('settings')) {
      setActiveTab('settings');
    } else {
      setActiveTab('schedule');
    }
  }, [location]);

  const handleTabChange = (tab: Tab) => {
    setActiveTab(tab);
    const routes: Record<Tab, string> = {
      schedule: '/',
      subjects: '/subjects',
      teachers: '/teachers',
      settings: '/settings',
    };
    navigate(routes[tab]);

    if (window.Telegram?.WebApp?.HapticFeedback) {
      window.Telegram.WebApp.HapticFeedback.selectionChanged();
    }
  };

  return (
    <div className="app">
      <nav className="nav">
        <button
          className={`nav-item ${activeTab === 'schedule' ? 'active' : ''}`}
          onClick={() => handleTabChange('schedule')}
        >
          <span>📅</span>
          Расписание
        </button>
        <button
          className={`nav-item ${activeTab === 'subjects' ? 'active' : ''}`}
          onClick={() => handleTabChange('subjects')}
        >
          <span>📚</span>
          Предметы
        </button>
        <button
          className={`nav-item ${activeTab === 'teachers' ? 'active' : ''}`}
          onClick={() => handleTabChange('teachers')}
        >
          <span>👨‍🏫</span>
          Препод.
        </button>
        <button
          className={`nav-item ${activeTab === 'settings' ? 'active' : ''}`}
          onClick={() => handleTabChange('settings')}
        >
          <span>⚙️</span>
          Настройки
        </button>
      </nav>

      <div className="container">
        <Routes>
          <Route path="/" element={<SchedulePage />} />
          <Route path="/subjects" element={<SubjectsPage />} />
          <Route path="/teachers" element={<TeachersPage />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Routes>
      </div>
    </div>
  );
}

export default App;
