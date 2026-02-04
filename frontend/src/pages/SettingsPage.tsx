import { useEffect, useState, useRef } from 'react';
import { format, differenceInDays, parseISO } from 'date-fns';
import {
  settingsApi,
  templatesApi,
  worksApi,
  ReminderSettings,
  TitleTemplate,
  GeneratedWork,
  UserWorkSettings,
} from '../api/client';

const WORK_TYPE_LABELS: Record<string, string> = {
  homework: 'Домашняя работа',
  lab: 'Лабораторная',
  practical: 'Практическая',
  coursework: 'Курсовая',
  report: 'Реферат',
  essay: 'Эссе',
  presentation: 'Презентация',
  exam: 'Экзамен',
  test: 'Контрольная',
};

const STATUS_LABELS: Record<string, string> = {
  pending: 'Ожидает',
  generating: 'Генерируется',
  ready: 'Готова',
  confirmed: 'Подтверждена',
  sent: 'Отправлена',
};

const STATUS_COLORS: Record<string, string> = {
  pending: '#f59e0b',
  generating: '#3b82f6',
  ready: '#22c55e',
  confirmed: '#8b5cf6',
  sent: '#10b981',
};

function SettingsPage() {
  const [activeSection, setActiveSection] = useState<'reminders' | 'works' | 'templates'>('works');
  const [reminderSettings, setReminderSettings] = useState<ReminderSettings>({
    hours_before: [72, 24, 12],
    is_enabled: true,
  });
  const [workSettings, setWorkSettings] = useState<UserWorkSettings>({
    reminder_days_before: [3, 1],
    auto_generate: true,
    generate_days_before: 5,
    require_confirmation: true,
    default_send_days_before: 1,
  });
  const [templates, setTemplates] = useState<TitleTemplate[]>([]);
  const [works, setWorks] = useState<GeneratedWork[]>([]);
  const [loading, setLoading] = useState(true);
  const [customHours, setCustomHours] = useState('');
  const [templateName, setTemplateName] = useState('');
  const [generatingWorkId, setGeneratingWorkId] = useState<number | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const fetchData = async () => {
    try {
      const [reminderRes, workSettingsRes, templatesRes, worksRes] = await Promise.all([
        settingsApi.getReminders(),
        settingsApi.getWorkSettings(),
        templatesApi.getAll(),
        worksApi.getAll(),
      ]);
      setReminderSettings(reminderRes.data);
      setWorkSettings(workSettingsRes.data);
      setTemplates(templatesRes.data);
      setWorks(worksRes.data);
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
        is_enabled: !reminderSettings.is_enabled,
      });
      setReminderSettings(newSettings.data);
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
  ];

  const toggleHours = async (hours: number) => {
    const newHours = reminderSettings.hours_before.includes(hours)
      ? reminderSettings.hours_before.filter((h) => h !== hours)
      : [...reminderSettings.hours_before, hours].sort((a, b) => b - a);

    try {
      const newSettings = await settingsApi.updateReminders({ hours_before: newHours });
      setReminderSettings(newSettings.data);
      window.Telegram?.WebApp?.HapticFeedback?.selectionChanged();
    } catch (error) {
      console.error('Error updating settings:', error);
    }
  };

  const addCustomHours = async () => {
    const hours = parseInt(customHours);
    if (isNaN(hours) || hours <= 0) return;
    if (reminderSettings.hours_before.includes(hours)) return;

    const newHours = [...reminderSettings.hours_before, hours].sort((a, b) => b - a);
    try {
      const newSettings = await settingsApi.updateReminders({ hours_before: newHours });
      setReminderSettings(newSettings.data);
      setCustomHours('');
    } catch (error) {
      console.error('Error updating settings:', error);
    }
  };

  const updateWorkSetting = async (key: keyof UserWorkSettings, value: unknown) => {
    try {
      const newSettings = await settingsApi.updateWorkSettings({ [key]: value });
      setWorkSettings(newSettings.data);
      window.Telegram?.WebApp?.HapticFeedback?.selectionChanged();
    } catch (error) {
      console.error('Error updating work settings:', error);
    }
  };

  const handleTemplateUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files?.[0] || !templateName) return;
    const file = e.target.files[0];

    try {
      const isDefault = templates.length === 0;
      await templatesApi.upload(templateName, file, isDefault);
      setTemplateName('');
      const templatesRes = await templatesApi.getAll();
      setTemplates(templatesRes.data);
      window.Telegram?.WebApp?.HapticFeedback?.notificationOccurred('success');
    } catch (error) {
      console.error('Error uploading template:', error);
    }
  };

  const setDefaultTemplate = async (id: number) => {
    try {
      await templatesApi.setDefault(id);
      const templatesRes = await templatesApi.getAll();
      setTemplates(templatesRes.data);
    } catch (error) {
      console.error('Error setting default template:', error);
    }
  };

  const deleteTemplate = async (id: number) => {
    try {
      await templatesApi.delete(id);
      setTemplates(templates.filter((t) => t.id !== id));
    } catch (error) {
      console.error('Error deleting template:', error);
    }
  };

  const generateWork = async (workId: number) => {
    setGeneratingWorkId(workId);
    try {
      await worksApi.generate(workId);
      const worksRes = await worksApi.getAll();
      setWorks(worksRes.data);
      window.Telegram?.WebApp?.HapticFeedback?.notificationOccurred('success');
    } catch (error) {
      console.error('Error generating work:', error);
      window.Telegram?.WebApp?.showAlert?.('Ошибка генерации работы');
    } finally {
      setGeneratingWorkId(null);
    }
  };

  const confirmWork = async (workId: number) => {
    try {
      await worksApi.confirm(workId);
      const worksRes = await worksApi.getAll();
      setWorks(worksRes.data);
      window.Telegram?.WebApp?.HapticFeedback?.notificationOccurred('success');
    } catch (error) {
      console.error('Error confirming work:', error);
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

      {/* Section Tabs */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
        <button
          className={`btn btn-sm ${activeSection === 'works' ? 'btn-primary' : 'btn-secondary'}`}
          onClick={() => setActiveSection('works')}
        >
          📝 Работы
        </button>
        <button
          className={`btn btn-sm ${activeSection === 'templates' ? 'btn-primary' : 'btn-secondary'}`}
          onClick={() => setActiveSection('templates')}
        >
          📄 Шаблоны
        </button>
        <button
          className={`btn btn-sm ${activeSection === 'reminders' ? 'btn-primary' : 'btn-secondary'}`}
          onClick={() => setActiveSection('reminders')}
        >
          ⏰ Напоминания
        </button>
      </div>

      {/* Works Section */}
      {activeSection === 'works' && (
        <>
          {/* Work Settings */}
          <div className="card">
            <div className="card-header">
              <div className="card-title">⚙️ Автогенерация</div>
              <div
                className="checkbox-group"
                onClick={() => updateWorkSetting('auto_generate', !workSettings.auto_generate)}
                style={{ cursor: 'pointer' }}
              >
                <div className={`checkbox ${workSettings.auto_generate ? 'checked' : ''}`}></div>
              </div>
            </div>

            <div className="card-body">
              <div style={{ marginBottom: 12 }}>
                <label style={{ fontSize: 13, color: 'var(--text-secondary)', display: 'block', marginBottom: 4 }}>
                  Генерировать за N дней до дедлайна:
                </label>
                <select
                  className="form-input"
                  value={workSettings.generate_days_before}
                  onChange={(e) => updateWorkSetting('generate_days_before', parseInt(e.target.value))}
                  style={{ width: '100%' }}
                >
                  {[1, 2, 3, 5, 7, 10, 14].map((d) => (
                    <option key={d} value={d}>{d} дн.</option>
                  ))}
                </select>
              </div>

              <div style={{ marginBottom: 12 }}>
                <label style={{ fontSize: 13, color: 'var(--text-secondary)', display: 'block', marginBottom: 4 }}>
                  Отправлять за N дней до дедлайна:
                </label>
                <select
                  className="form-input"
                  value={workSettings.default_send_days_before}
                  onChange={(e) => updateWorkSetting('default_send_days_before', parseInt(e.target.value))}
                  style={{ width: '100%' }}
                >
                  {[0, 1, 2, 3, 5, 7].map((d) => (
                    <option key={d} value={d}>{d === 0 ? 'В день дедлайна' : `${d} дн.`}</option>
                  ))}
                </select>
              </div>

              <div
                className="checkbox-group"
                onClick={() => updateWorkSetting('require_confirmation', !workSettings.require_confirmation)}
                style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 8 }}
              >
                <div className={`checkbox ${workSettings.require_confirmation ? 'checked' : ''}`}></div>
                <span style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
                  Требовать подтверждение перед отправкой
                </span>
              </div>
            </div>
          </div>

          {/* Works List */}
          <div className="card">
            <div className="card-header">
              <div className="card-title">📋 Мои работы</div>
            </div>

            <div className="card-body" style={{ padding: 0 }}>
              {works.length === 0 ? (
                <div style={{ padding: 16, textAlign: 'center', color: 'var(--text-secondary)' }}>
                  Нет работ. Добавьте дедлайн с типом работы через бота.
                </div>
              ) : (
                works.map((work) => {
                  const daysLeft = differenceInDays(parseISO(work.deadline_date), new Date());
                  const workTypeLabel = WORK_TYPE_LABELS[work.work_type] || work.work_type;
                  const workTitle = work.work_number ? `${workTypeLabel} №${work.work_number}` : workTypeLabel;

                  return (
                    <div
                      key={work.id}
                      style={{
                        padding: 12,
                        borderBottom: '1px solid var(--border)',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: 8,
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                        <div>
                          <div style={{ fontWeight: 500, fontSize: 14 }}>{workTitle}</div>
                          <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                            {work.subject_name} — {work.deadline_title}
                          </div>
                        </div>
                        <span
                          style={{
                            padding: '2px 8px',
                            borderRadius: 12,
                            fontSize: 11,
                            fontWeight: 500,
                            background: `${STATUS_COLORS[work.status]}20`,
                            color: STATUS_COLORS[work.status],
                          }}
                        >
                          {STATUS_LABELS[work.status] || work.status}
                        </span>
                      </div>

                      <div style={{ display: 'flex', gap: 8, fontSize: 12, color: 'var(--text-muted)' }}>
                        <span>📅 {format(parseISO(work.deadline_date), 'dd.MM.yyyy')}</span>
                        <span style={{ color: daysLeft <= 3 ? '#ef4444' : 'inherit' }}>
                          ({daysLeft <= 0 ? 'Сегодня!' : `${daysLeft} дн.`})
                        </span>
                      </div>

                      {/* Actions based on status */}
                      <div style={{ display: 'flex', gap: 8 }}>
                        {work.status === 'pending' && (
                          <button
                            className="btn btn-sm btn-primary"
                            onClick={() => generateWork(work.id)}
                            disabled={generatingWorkId === work.id}
                          >
                            {generatingWorkId === work.id ? '⏳ Генерация...' : '🤖 Сгенерировать'}
                          </button>
                        )}
                        {work.status === 'ready' && (
                          <>
                            <button className="btn btn-sm btn-primary" onClick={() => confirmWork(work.id)}>
                              ✅ Подтвердить
                            </button>
                            <button
                              className="btn btn-sm btn-secondary"
                              onClick={() => {
                                // Download will be handled by bot notification
                                window.Telegram?.WebApp?.showAlert?.(
                                  'Файл будет отправлен вам в личку бота'
                                );
                              }}
                            >
                              📥 Скачать
                            </button>
                          </>
                        )}
                        {(work.status === 'confirmed' || work.status === 'sent') && work.file_name && (
                          <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                            📄 {work.file_name}
                          </span>
                        )}
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>
        </>
      )}

      {/* Templates Section */}
      {activeSection === 'templates' && (
        <div className="card">
          <div className="card-header">
            <div className="card-title">📄 Шаблоны титульных листов</div>
          </div>

          <div className="card-body">
            <p style={{ marginBottom: 12, fontSize: 13, color: 'var(--text-secondary)' }}>
              Загрузите DOCX шаблон с плейсхолдерами:
              <br />
              <code style={{ fontSize: 11 }}>
                {'{{subject_name}}, {{date}}, {{work_type}}, {{work_number}}, {{student_name}}, {{group_number}}'}
              </code>
            </p>

            {/* Upload Form */}
            <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
              <input
                type="text"
                className="form-input"
                placeholder="Название шаблона"
                value={templateName}
                onChange={(e) => setTemplateName(e.target.value)}
                style={{ flex: 1 }}
              />
              <input
                ref={fileInputRef}
                type="file"
                accept=".docx"
                style={{ display: 'none' }}
                onChange={handleTemplateUpload}
              />
              <button
                className="btn btn-primary"
                onClick={() => {
                  if (!templateName) {
                    window.Telegram?.WebApp?.showAlert?.('Введите название шаблона');
                    return;
                  }
                  fileInputRef.current?.click();
                }}
              >
                📤 Загрузить
              </button>
            </div>

            {/* Templates List */}
            {templates.length === 0 ? (
              <div style={{ textAlign: 'center', color: 'var(--text-secondary)', padding: 16 }}>
                Нет шаблонов. Загрузите DOCX файл с плейсхолдерами.
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {templates.map((template) => (
                  <div
                    key={template.id}
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      padding: 12,
                      background: 'var(--bg-secondary)',
                      borderRadius: 8,
                    }}
                  >
                    <div>
                      <div style={{ fontWeight: 500, fontSize: 14 }}>
                        {template.name}
                        {template.is_default && (
                          <span style={{ marginLeft: 8, color: '#22c55e', fontSize: 12 }}>⭐ По умолчанию</span>
                        )}
                      </div>
                      <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>{template.file_name}</div>
                    </div>
                    <div style={{ display: 'flex', gap: 4 }}>
                      {!template.is_default && (
                        <button
                          className="btn btn-sm btn-secondary"
                          onClick={() => setDefaultTemplate(template.id)}
                          title="Сделать по умолчанию"
                        >
                          ⭐
                        </button>
                      )}
                      <button
                        className="btn btn-sm btn-secondary"
                        onClick={() => deleteTemplate(template.id)}
                        title="Удалить"
                      >
                        🗑
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Reminders Section */}
      {activeSection === 'reminders' && (
        <div className="card">
          <div className="card-header">
            <div className="card-title">⏰ Напоминания</div>
            <div
              className="checkbox-group"
              onClick={toggleEnabled}
              style={{ cursor: 'pointer' }}
            >
              <div className={`checkbox ${reminderSettings.is_enabled ? 'checked' : ''}`}></div>
            </div>
          </div>

          <div className="card-body">
            <p style={{ marginBottom: 16, color: 'var(--text-secondary)' }}>
              Выберите, за сколько времени до дедлайна получать напоминания:
            </p>

            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
              {presetOptions.map((option) => (
                <button
                  key={option.hours}
                  className={`btn btn-sm ${
                    reminderSettings.hours_before.includes(option.hours) ? 'btn-primary' : 'btn-secondary'
                  }`}
                  onClick={() => toggleHours(option.hours)}
                >
                  {option.label}
                </button>
              ))}
            </div>

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

            <div style={{ marginTop: 16, padding: 12, background: 'var(--bg-secondary)', borderRadius: 8 }}>
              <div style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 8 }}>
                Текущие напоминания:
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                {reminderSettings.hours_before.map((hours) => {
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
      )}

      {/* Info */}
      <div className="card">
        <div className="card-header">
          <div className="card-title">ℹ️ Как это работает</div>
        </div>

        <div className="card-body">
          <div className="info-row">
            <span className="info-row-icon">📝</span>
            <span>Добавляйте дедлайны через бота или заметки</span>
          </div>
          <div className="info-row">
            <span className="info-row-icon">🤖</span>
            <span>AI автоматически генерирует работы</span>
          </div>
          <div className="info-row">
            <span className="info-row-icon">📄</span>
            <span>Используйте свой шаблон титульника</span>
          </div>
          <div className="info-row">
            <span className="info-row-icon">📤</span>
            <span>Готовые работы отправляются в бот</span>
          </div>
        </div>
      </div>
    </div>
  );
}

export default SettingsPage;
