import { useEffect, useState } from 'react';
import { Routes, Route, useNavigate, useLocation } from 'react-router-dom';
import TeachersPage from './pages/TeachersPage';
import DeadlinesPage from './pages/DeadlinesPage';
import SettingsPage from './pages/SettingsPage';

type Tab = 'teachers' | 'deadlines' | 'settings';

function App() {
  const navigate = useNavigate();
  const location = useLocation();
  const [activeTab, setActiveTab] = useState<Tab>('deadlines');

  useEffect(() => {
    // Инициализация Telegram WebApp
    if (window.Telegram?.WebApp) {
      window.Telegram.WebApp.ready();
      window.Telegram.WebApp.expand();
      window.Telegram.WebApp.setHeaderColor('#0f0f1a');
      window.Telegram.WebApp.setBackgroundColor('#0f0f1a');
    }
  }, []);

  useEffect(() => {
    // Определяем активную вкладку по URL
    const path = location.pathname;
    if (path.includes('teachers')) {
      setActiveTab('teachers');
    } else if (path.includes('settings')) {
      setActiveTab('settings');
    } else {
      setActiveTab('deadlines');
    }
  }, [location]);

  const handleTabChange = (tab: Tab) => {
    setActiveTab(tab);
    const routes: Record<Tab, string> = {
      teachers: '/teachers',
      deadlines: '/',
      settings: '/settings',
    };
    navigate(routes[tab]);

    // Haptic feedback
    if (window.Telegram?.WebApp?.HapticFeedback) {
      window.Telegram.WebApp.HapticFeedback.selectionChanged();
    }
  };

  return (
    <div className="app">
      <nav className="nav">
        <button
          className={`nav-item ${activeTab === 'deadlines' ? 'active' : ''}`}
          onClick={() => handleTabChange('deadlines')}
        >
          <span>📅</span>
          Дедлайны
        </button>
        <button
          className={`nav-item ${activeTab === 'teachers' ? 'active' : ''}`}
          onClick={() => handleTabChange('teachers')}
        >
          <span>👨‍🏫</span>
          Преподаватели
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
          <Route path="/" element={<DeadlinesPage />} />
          <Route path="/teachers" element={<TeachersPage />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Routes>
      </div>
    </div>
  );
}

export default App;
