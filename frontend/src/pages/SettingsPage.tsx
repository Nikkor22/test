import { useEffect, useState } from 'react';
import { settingsApi, ReminderSettings } from '../api/client';

function SettingsPage() {
  const [settings, setSettings] = useState<ReminderSettings>({
    hours_before: [72, 24, 12],
    is_enabled: true,
  });
  const [loading, setLoading] = useState(true);
  const [customHours, setCustomHours] = useState('');

  const fetchData = async () => {
    try {
      const settingsRes = await settingsApi.getReminders();
      setSettings(settingsRes.data);
    } catch (error) {
      console.error('Error fetching data:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const toggleEnabled = async () => {
    try {
      const newSettings = await settingsApi.updateReminders({
        is_enabled: !settings.is_enabled,
      });
      setSettings(newSettings.data);
      window.Telegram?.WebApp?.HapticFeedback?.impactOccurred('light');
    } catch (error) {
      console.error('Error updating settings:', error);
    }
  };

  const presetOptions = [
    { label: '3 дня', hours: 72 },
    { label: '2 дня', hours: 48 },
    { label: '1 день', hours: 24 },
    { label: '12 часов', hours: 12 },
    { label: '6 часов', hours: 6 },
    { label: '3 часа', hours: 3 },
    { label: '1 час', hours: 1 },
  ];

  const toggleHours = async (hours: number) => {
    const newHours = settings.hours_before.includes(hours)
      ? settings.hours_before.filter((h) => h !== hours)
      : [...settings.hours_before, hours].sort((a, b) => b - a);

    try {
      const newSettings = await settingsApi.updateReminders({ hours_before: newHours });
      setSettings(newSettings.data);
      window.Telegram?.WebApp?.HapticFeedback?.selectionChanged();
    } catch (error) {
      console.error('Error updating settings:', error);
    }
  };

  const addCustomHours = async () => {
    const hours = parseInt(customHours);
    if (isNaN(hours) || hours <= 0) {
      window.Telegram?.WebApp?.showAlert?.('Введите корректное число часов');
      return;
    }

    if (settings.hours_before.includes(hours)) {
      window.Telegram?.WebApp?.showAlert?.('Это напоминание уже добавлено');
      return;
    }

    const newHours = [...settings.hours_before, hours].sort((a, b) => b - a);

    try {
      const newSettings = await settingsApi.updateReminders({ hours_before: newHours });
      setSettings(newSettings.data);
      setCustomHours('');
      window.Telegram?.WebApp?.HapticFeedback?.notificationOccurred('success');
    } catch (error) {
      console.error('Error updating settings:', error);
    }
  };

  if (loading) {
    return (
      <div className="loading">
        <div className="spinner"></div>
      </div>
    );
  }

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Настройки</h1>
      </div>

      {/* Reminder Settings */}
      <div className="card">
        <div className="card-header">
          <div className="card-title">⏰ Напоминания</div>
          <div
            className="checkbox-group"
            onClick={toggleEnabled}
            style={{ cursor: 'pointer' }}
          >
            <div className={`checkbox ${settings.is_enabled ? 'checked' : ''}`}></div>
          </div>
        </div>

        <div className="card-body">
          <p style={{ marginBottom: 16, color: 'var(--text-secondary)' }}>
            Выберите, за сколько времени до дедлайна вы хотите получать напоминания:
          </p>

          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
            {presetOptions.map((option) => (
              <button
                key={option.hours}
                className={`btn btn-sm ${
                  settings.hours_before.includes(option.hours) ? 'btn-primary' : 'btn-secondary'
                }`}
                onClick={() => toggleHours(option.hours)}
              >
                {option.label}
              </button>
            ))}
          </div>

          {/* Custom hours input */}
          <div style={{ marginTop: 16, display: 'flex', gap: 8 }}>
            <input
              type="number"
              className="form-input"
              placeholder="Свое кол-во часов"
              value={customHours}
              onChange={(e) => setCustomHours(e.target.value)}
              style={{ flex: 1 }}
            />
            <button className="btn btn-secondary" onClick={addCustomHours}>
              +
            </button>
          </div>

          {/* Current settings display */}
          <div style={{ marginTop: 16, padding: 12, background: 'var(--bg-secondary)', borderRadius: 8 }}>
            <div style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 8 }}>
              Текущие напоминания:
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
              {settings.hours_before.map((hours) => {
                const label = hours >= 24 ? `${Math.floor(hours / 24)} дн.` : `${hours} ч.`;
                return (
                  <span key={hours} className="tag tag-subject">
                    {label}
                    <button
                      onClick={() => toggleHours(hours)}
                      style={{
                        background: 'none',
                        border: 'none',
                        color: 'inherit',
                        cursor: 'pointer',
                        marginLeft: 4,
                        padding: 0,
                      }}
                    >
                      ×
                    </button>
                  </span>
                );
              })}
            </div>
          </div>
        </div>
      </div>

      {/* Info */}
      <div className="card">
        <div className="card-header">
          <div className="card-title">ℹ️ Информация</div>
        </div>

        <div className="card-body">
          <div className="info-row">
            <span className="info-row-icon">🕐</span>
            <span>Часовой пояс: Москва (UTC+3)</span>
          </div>
          <div className="info-row">
            <span className="info-row-icon">📝</span>
            <span>Добавляйте заметки через бота</span>
          </div>
          <div className="info-row">
            <span className="info-row-icon">🤖</span>
            <span>GPT автоматически распознает информацию</span>
          </div>
        </div>
      </div>
    </div>
  );
}

export default SettingsPage;
