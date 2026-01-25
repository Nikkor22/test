import { useEffect, useState } from 'react';
import { teachersApi, Teacher } from '../api/client';

interface TeacherFormData {
  name: string;
  temperament: string;
  preferences: string;
  notes: string;
}

function TeachersPage() {
  const [teachers, setTeachers] = useState<Teacher[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingTeacher, setEditingTeacher] = useState<Teacher | null>(null);
  const [formData, setFormData] = useState<TeacherFormData>({
    name: '',
    temperament: '',
    preferences: '',
    notes: '',
  });

  const fetchTeachers = async () => {
    try {
      const response = await teachersApi.getAll();
      setTeachers(response.data);
    } catch (error) {
      console.error('Error fetching teachers:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTeachers();
  }, []);

  const handleEdit = (teacher: Teacher) => {
    setEditingTeacher(teacher);
    setFormData({
      name: teacher.name,
      temperament: teacher.temperament || '',
      preferences: teacher.preferences || '',
      notes: teacher.notes || '',
    });
    setShowModal(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!editingTeacher) return;

    try {
      await teachersApi.update(editingTeacher.id, formData);
      window.Telegram?.WebApp?.HapticFeedback?.notificationOccurred('success');
      setShowModal(false);
      setEditingTeacher(null);
      fetchTeachers();
    } catch (error) {
      console.error('Error updating teacher:', error);
      window.Telegram?.WebApp?.HapticFeedback?.notificationOccurred('error');
    }
  };

  const handleDelete = async (id: number) => {
    if (window.Telegram?.WebApp) {
      window.Telegram.WebApp.showConfirm('Удалить этого преподавателя?', async (confirmed) => {
        if (confirmed) {
          try {
            await teachersApi.delete(id);
            window.Telegram?.WebApp?.HapticFeedback?.notificationOccurred('success');
            fetchTeachers();
          } catch (error) {
            console.error('Error deleting teacher:', error);
          }
        }
      });
    } else {
      if (confirm('Удалить этого преподавателя?')) {
        await teachersApi.delete(id);
        fetchTeachers();
      }
    }
  };

  const getTemperamentEmoji = (temperament: string | null) => {
    if (!temperament) return '😐';
    const lower = temperament.toLowerCase();
    if (lower.includes('строг') || lower.includes('злой') || lower.includes('требоват')) return '😠';
    if (lower.includes('добр') || lower.includes('мягк') || lower.includes('лояльн')) return '😊';
    if (lower.includes('нейтрал') || lower.includes('норм')) return '😐';
    return '🎭';
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
        <h1 className="page-title">Преподаватели</h1>
      </div>

      {teachers.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon">👨‍🏫</div>
          <div className="empty-state-title">Нет преподавателей</div>
          <div className="empty-state-text">
            Напишите боту заметку о преподавателе,<br />
            и он появится здесь автоматически
          </div>
        </div>
      ) : (
        teachers.map((teacher) => (
          <div key={teacher.id} className="card">
            <div className="card-header">
              <div>
                <div className="card-title">
                  {getTemperamentEmoji(teacher.temperament)} {teacher.name}
                </div>
                <div className="card-subtitle">
                  <span className="tag tag-subject">{teacher.subject_name}</span>
                </div>
              </div>
            </div>

            <div className="card-body">
              {teacher.temperament && (
                <div className="info-row">
                  <span className="info-row-icon">🎭</span>
                  <span className="info-row-label">Характер:</span>
                  <span className="info-row-value">{teacher.temperament}</span>
                </div>
              )}

              {teacher.preferences && (
                <div className="info-row">
                  <span className="info-row-icon">💡</span>
                  <span className="info-row-label">Предпочтения:</span>
                  <span className="info-row-value">{teacher.preferences}</span>
                </div>
              )}

              {teacher.notes && (
                <div className="info-row">
                  <span className="info-row-icon">📝</span>
                  <span className="info-row-label">Заметки:</span>
                  <span className="info-row-value">{teacher.notes}</span>
                </div>
              )}

              {!teacher.temperament && !teacher.preferences && !teacher.notes && (
                <div style={{ color: 'var(--text-muted)', fontStyle: 'italic' }}>
                  Нет дополнительной информации. Напишите боту заметку об этом преподавателе.
                </div>
              )}
            </div>

            <div className="card-footer">
              <button className="btn btn-sm btn-secondary" onClick={() => handleEdit(teacher)}>
                ✏️ Редактировать
              </button>
              <button className="btn btn-sm btn-danger" onClick={() => handleDelete(teacher.id)}>
                🗑️
              </button>
            </div>
          </div>
        ))
      )}

      {/* Edit Modal */}
      {showModal && editingTeacher && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2 className="modal-title">Редактировать преподавателя</h2>
              <button className="modal-close" onClick={() => setShowModal(false)}>
                ×
              </button>
            </div>

            <form onSubmit={handleSubmit}>
              <div className="modal-body">
                <div className="form-group">
                  <label className="form-label">Предмет</label>
                  <input
                    type="text"
                    className="form-input"
                    value={editingTeacher.subject_name}
                    disabled
                    style={{ opacity: 0.6 }}
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">Имя преподавателя</label>
                  <input
                    type="text"
                    className="form-input"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    placeholder="Иванов И.И."
                    required
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">Характер/темперамент</label>
                  <input
                    type="text"
                    className="form-input"
                    value={formData.temperament}
                    onChange={(e) => setFormData({ ...formData, temperament: e.target.value })}
                    placeholder="Строгий, требовательный..."
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">Предпочтения</label>
                  <textarea
                    className="form-textarea"
                    value={formData.preferences}
                    onChange={(e) => setFormData({ ...formData, preferences: e.target.value })}
                    placeholder="Что любит спрашивать, на что обращает внимание..."
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">Заметки</label>
                  <textarea
                    className="form-textarea"
                    value={formData.notes}
                    onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                    placeholder="Дополнительная информация..."
                  />
                </div>
              </div>

              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={() => setShowModal(false)}>
                  Отмена
                </button>
                <button type="submit" className="btn btn-primary">
                  Сохранить
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

export default TeachersPage;
