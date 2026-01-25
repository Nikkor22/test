import { useEffect, useState } from 'react';
import { format, differenceInDays, differenceInHours, parseISO } from 'date-fns';
import { ru } from 'date-fns/locale';
import { deadlinesApi, subjectsApi, Deadline, Subject } from '../api/client';

interface DeadlineFormData {
  subject_id: number;
  title: string;
  work_type: string;
  description: string;
  deadline_date: string;
}

function DeadlinesPage() {
  const [deadlines, setDeadlines] = useState<Deadline[]>([]);
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCompleted, setShowCompleted] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [editingDeadline, setEditingDeadline] = useState<Deadline | null>(null);
  const [formData, setFormData] = useState<DeadlineFormData>({
    subject_id: 0,
    title: '',
    work_type: '',
    description: '',
    deadline_date: '',
  });

  const fetchData = async () => {
    try {
      const [deadlinesRes, subjectsRes] = await Promise.all([
        deadlinesApi.getAll(showCompleted),
        subjectsApi.getAll(),
      ]);
      setDeadlines(deadlinesRes.data);
      setSubjects(subjectsRes.data);
    } catch (error) {
      console.error('Error fetching data:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [showCompleted]);

  const getDeadlineStatus = (dateStr: string) => {
    const date = parseISO(dateStr);
    const now = new Date();
    const daysLeft = differenceInDays(date, now);
    const hoursLeft = differenceInHours(date, now);

    if (hoursLeft < 0) {
      return { class: 'urgent', text: 'Просрочено!' };
    } else if (daysLeft <= 1) {
      return { class: 'urgent', text: hoursLeft <= 12 ? `${hoursLeft} ч.` : '1 день' };
    } else if (daysLeft <= 3) {
      return { class: 'warning', text: `${daysLeft} дн.` };
    } else {
      return { class: 'ok', text: `${daysLeft} дн.` };
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    try {
      if (editingDeadline) {
        await deadlinesApi.update(editingDeadline.id, {
          ...formData,
          deadline_date: new Date(formData.deadline_date).toISOString(),
        });
      } else {
        await deadlinesApi.create({
          ...formData,
          deadline_date: new Date(formData.deadline_date).toISOString(),
        });
      }

      // Haptic feedback
      window.Telegram?.WebApp?.HapticFeedback?.notificationOccurred('success');

      setShowModal(false);
      setEditingDeadline(null);
      resetForm();
      fetchData();
    } catch (error) {
      console.error('Error saving deadline:', error);
      window.Telegram?.WebApp?.HapticFeedback?.notificationOccurred('error');
    }
  };

  const handleEdit = (deadline: Deadline) => {
    setEditingDeadline(deadline);
    setFormData({
      subject_id: deadline.subject_id,
      title: deadline.title,
      work_type: deadline.work_type,
      description: deadline.description || '',
      deadline_date: format(parseISO(deadline.deadline_date), "yyyy-MM-dd'T'HH:mm"),
    });
    setShowModal(true);
  };

  const handleDelete = async (id: number) => {
    if (window.Telegram?.WebApp) {
      window.Telegram.WebApp.showConfirm('Удалить этот дедлайн?', async (confirmed) => {
        if (confirmed) {
          try {
            await deadlinesApi.delete(id);
            window.Telegram?.WebApp?.HapticFeedback?.notificationOccurred('success');
            fetchData();
          } catch (error) {
            console.error('Error deleting deadline:', error);
          }
        }
      });
    } else {
      if (confirm('Удалить этот дедлайн?')) {
        await deadlinesApi.delete(id);
        fetchData();
      }
    }
  };

  const handleToggleComplete = async (deadline: Deadline) => {
    try {
      await deadlinesApi.update(deadline.id, { is_completed: !deadline.is_completed });
      window.Telegram?.WebApp?.HapticFeedback?.impactOccurred('light');
      fetchData();
    } catch (error) {
      console.error('Error toggling deadline:', error);
    }
  };

  const resetForm = () => {
    setFormData({
      subject_id: subjects[0]?.id || 0,
      title: '',
      work_type: '',
      description: '',
      deadline_date: '',
    });
  };

  const openAddModal = () => {
    setEditingDeadline(null);
    resetForm();
    setShowModal(true);
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
        <h1 className="page-title">Дедлайны</h1>
        <button className="btn btn-primary" onClick={openAddModal}>
          + Добавить
        </button>
      </div>

      <div className="checkbox-group" onClick={() => setShowCompleted(!showCompleted)} style={{ marginBottom: 16 }}>
        <div className={`checkbox ${showCompleted ? 'checked' : ''}`}></div>
        <span>Показать выполненные</span>
      </div>

      {deadlines.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon">📅</div>
          <div className="empty-state-title">Нет дедлайнов</div>
          <div className="empty-state-text">
            Добавьте первый дедлайн или напишите боту
          </div>
        </div>
      ) : (
        deadlines.map((deadline) => {
          const status = getDeadlineStatus(deadline.deadline_date);
          return (
            <div key={deadline.id} className="card">
              <div className="card-header">
                <div>
                  <div className="card-title">{deadline.title}</div>
                  <div className="card-subtitle">{deadline.subject_name}</div>
                </div>
                <span className={`tag tag-deadline ${status.class}`}>
                  {status.text}
                </span>
              </div>

              <div className="card-body">
                <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
                  <span className="tag tag-type">{deadline.work_type}</span>
                </div>

                <div className="info-row">
                  <span className="info-row-icon">📆</span>
                  <span>
                    {format(parseISO(deadline.deadline_date), 'd MMMM yyyy, HH:mm', { locale: ru })}
                  </span>
                </div>

                {deadline.description && (
                  <div className="info-row">
                    <span className="info-row-icon">📝</span>
                    <span>{deadline.description}</span>
                  </div>
                )}
              </div>

              <div className="card-footer">
                <button
                  className={`btn btn-sm ${deadline.is_completed ? 'btn-secondary' : 'btn-primary'}`}
                  onClick={() => handleToggleComplete(deadline)}
                >
                  {deadline.is_completed ? '↩️ Вернуть' : '✓ Выполнено'}
                </button>
                <button className="btn btn-sm btn-secondary" onClick={() => handleEdit(deadline)}>
                  ✏️
                </button>
                <button className="btn btn-sm btn-danger" onClick={() => handleDelete(deadline.id)}>
                  🗑️
                </button>
              </div>
            </div>
          );
        })
      )}

      {/* Modal */}
      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2 className="modal-title">
                {editingDeadline ? 'Редактировать дедлайн' : 'Новый дедлайн'}
              </h2>
              <button className="modal-close" onClick={() => setShowModal(false)}>
                ×
              </button>
            </div>

            <form onSubmit={handleSubmit}>
              <div className="modal-body">
                <div className="form-group">
                  <label className="form-label">Предмет</label>
                  <select
                    className="form-select"
                    value={formData.subject_id}
                    onChange={(e) => setFormData({ ...formData, subject_id: Number(e.target.value) })}
                    required
                  >
                    <option value="">Выберите предмет</option>
                    {subjects.map((subject) => (
                      <option key={subject.id} value={subject.id}>
                        {subject.name}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="form-group">
                  <label className="form-label">Название</label>
                  <input
                    type="text"
                    className="form-input"
                    value={formData.title}
                    onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                    placeholder="Контрольная работа №1"
                    required
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">Тип работы</label>
                  <select
                    className="form-select"
                    value={formData.work_type}
                    onChange={(e) => setFormData({ ...formData, work_type: e.target.value })}
                    required
                  >
                    <option value="">Выберите тип</option>
                    <option value="Контрольная">Контрольная</option>
                    <option value="Лабораторная">Лабораторная</option>
                    <option value="Презентация">Презентация</option>
                    <option value="Реферат">Реферат</option>
                    <option value="Курсовая">Курсовая</option>
                    <option value="Экзамен">Экзамен</option>
                    <option value="Зачет">Зачет</option>
                    <option value="Домашняя работа">Домашняя работа</option>
                    <option value="Другое">Другое</option>
                  </select>
                </div>

                <div className="form-group">
                  <label className="form-label">Дата и время</label>
                  <input
                    type="datetime-local"
                    className="form-input"
                    value={formData.deadline_date}
                    onChange={(e) => setFormData({ ...formData, deadline_date: e.target.value })}
                    required
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">Описание (опционально)</label>
                  <textarea
                    className="form-textarea"
                    value={formData.description}
                    onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                    placeholder="Что нужно подготовить..."
                  />
                </div>
              </div>

              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={() => setShowModal(false)}>
                  Отмена
                </button>
                <button type="submit" className="btn btn-primary">
                  {editingDeadline ? 'Сохранить' : 'Добавить'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

export default DeadlinesPage;
