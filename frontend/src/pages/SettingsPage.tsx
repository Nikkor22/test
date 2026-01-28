import { useEffect, useState, useRef } from 'react';
import { settingsApi, subjectsApi, semesterApi, ReminderSettings, Subject } from '../api/client';

function SettingsPage() {
  const [settings, setSettings] = useState<ReminderSettings>({
    hours_before: [72, 24, 12],
    is_enabled: true,
  });
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [loading, setLoading] = useState(true);
  const [newSubject, setNewSubject] = useState('');
  const [customHours, setCustomHours] = useState('');
  const [semesterText, setSemesterText] = useState('');
  const [uploadingFile, setUploadingFile] = useState(false);
  const [uploadingText, setUploadingText] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const fetchData = async () => {
    try {
      const [settingsRes, subjectsRes] = await Promise.all([
        settingsApi.getReminders(),
        subjectsApi.getAll(),
      ]);
      setSettings(settingsRes.data);
      setSubjects(subjectsRes.data);
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

  const addSubject = async () => {
    if (!newSubject.trim()) return;

    try {
      await subjectsApi.create(newSubject.trim());
      setNewSubject('');
      fetchData();
      window.Telegram?.WebApp?.HapticFeedback?.notificationOccurred('success');
    } catch (error) {
      console.error('Error adding subject:', error);
    }
  };

  const deleteSubject = async (id: number) => {
    if (window.Telegram?.WebApp) {
      window.Telegram.WebApp.showConfirm(
        'Удалить предмет? Это также удалит всех преподавателей и дедлайны по этому предмету.',
        async (confirmed) => {
          if (confirmed) {
            try {
              await subjectsApi.delete(id);
              fetchData();
              window.Telegram?.WebApp?.HapticFeedback?.notificationOccurred('success');
            } catch (error) {
              console.error('Error deleting subject:', error);
            }
          }
        }
      );
    } else {
      if (confirm('Удалить предмет? Это также удалит всех преподавателей и дедлайны по этому предмету.')) {
        await subjectsApi.delete(id);
        fetchData();
      }
    }
  };

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    const allowedTypes = ['application/json', 'text/plain', 'application/pdf'];
    const allowedExtensions = ['.json', '.txt', '.pdf'];
    const fileExtension = file.name.toLowerCase().substring(file.name.lastIndexOf('.'));

    if (!allowedTypes.includes(file.type) && !allowedExtensions.includes(fileExtension)) {
      window.Telegram?.WebApp?.showAlert?.('Поддерживаются только файлы JSON, TXT и PDF');
      return;
    }

    setUploadingFile(true);
    try {
      const formData = new FormData();
      formData.append('file', file);

      await semesterApi.uploadFile(formData);
      window.Telegram?.WebApp?.HapticFeedback?.notificationOccurred('success');
      window.Telegram?.WebApp?.showAlert?.('Данные семестра успешно загружены!');
      fetchData();
    } catch (error) {
      console.error('Error uploading file:', error);
      window.Telegram?.WebApp?.showAlert?.('Ошибка при загрузке файла');
    } finally {
      setUploadingFile(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleTextUpload = async () => {
    if (!semesterText.trim()) {
      window.Telegram?.WebApp?.showAlert?.('Введите данные для загрузки');
      return;
    }

    setUploadingText(true);
    try {
      await semesterApi.uploadText(semesterText.trim());
      window.Telegram?.WebApp?.HapticFeedback?.notificationOccurred('success');
      window.Telegram?.WebApp?.showAlert?.('Данные семестра успешно загружены!');
      setSemesterText('');
      fetchData();
    } catch (error) {
      console.error('Error uploading text:', error);
      window.Telegram?.WebApp?.showAlert?.('Ошибка при загрузке данных');
    } finally {
      setUploadingText(false);
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

      {/* Subjects */}
      <div className="card">
        <div className="card-header">
          <div className="card-title">📚 Предметы</div>
        </div>

        <div className="card-body">
          <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
            <input
              type="text"
              className="form-input"
              placeholder="Название предмета"
              value={newSubject}
              onChange={(e) => setNewSubject(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && addSubject()}
              style={{ flex: 1 }}
            />
            <button className="btn btn-primary" onClick={addSubject}>
              +
            </button>
          </div>

          {subjects.length === 0 ? (
            <div style={{ color: 'var(--text-muted)', fontStyle: 'italic' }}>
              Нет добавленных предметов
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {subjects.map((subject) => (
                <div
                  key={subject.id}
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    padding: '10px 12px',
                    background: 'var(--bg-secondary)',
                    borderRadius: 8,
                  }}
                >
                  <span>{subject.name}</span>
                  <button
                    className="btn btn-sm btn-danger"
                    onClick={() => deleteSubject(subject.id)}
                    style={{ padding: '4px 8px' }}
                  >
                    🗑️
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Semester Upload */}
      <div className="card">
        <div className="card-header">
          <div className="card-title">📂 Загрузка семестра</div>
        </div>

        <div className="card-body">
          <p style={{ marginBottom: 16, color: 'var(--text-secondary)', fontSize: 13 }}>
            Загрузите расписание, материалы и информацию о семестре. Поддерживаются форматы JSON, TXT и PDF.
          </p>

          {/* File Upload */}
          <div style={{ marginBottom: 16 }}>
            <input
              ref={fileInputRef}
              type="file"
              accept=".json,.txt,.pdf,application/json,text/plain,application/pdf"
              onChange={handleFileUpload}
              style={{ display: 'none' }}
              id="semester-file-input"
            />
            <button
              className="btn btn-secondary"
              onClick={() => fileInputRef.current?.click()}
              disabled={uploadingFile}
              style={{ width: '100%' }}
            >
              {uploadingFile ? 'Загрузка...' : '📁 Выбрать файл (JSON, TXT, PDF)'}
            </button>
          </div>

          {/* Text Upload */}
          <div style={{ marginBottom: 12 }}>
            <textarea
              className="form-input"
              placeholder="Или вставьте данные семестра сюда (расписание, предметы, преподаватели)..."
              value={semesterText}
              onChange={(e) => setSemesterText(e.target.value)}
              style={{
                width: '100%',
                minHeight: 120,
                resize: 'vertical',
                fontFamily: 'inherit',
              }}
            />
          </div>

          <button
            className="btn btn-primary"
            onClick={handleTextUpload}
            disabled={uploadingText || !semesterText.trim()}
            style={{ width: '100%' }}
          >
            {uploadingText ? 'Обработка...' : '🚀 Загрузить данные'}
          </button>

          <div style={{ marginTop: 12, padding: 12, background: 'var(--bg-secondary)', borderRadius: 8 }}>
            <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
              💡 AI автоматически распознает и структурирует данные: расписание, предметы, преподавателей и материалы.
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
