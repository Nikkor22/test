import { useEffect, useState } from 'react';
import { teachersApi, Teacher } from '../api/client';

interface TeacherFormData {
  name: string;
  temperament: string;
  preferences: string;
  notes: string;
  contact_info: string;
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
    contact_info: '',
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
      contact_info: teacher.contact_info || '',
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
    const doDelete = async () => {
      try {
        await teachersApi.delete(id);
        window.Telegram?.WebApp?.HapticFeedback?.notificationOccurred('success');
        fetchTeachers();
      } catch (error) {
        console.error('Error deleting teacher:', error);
      }
    };

    if (window.Telegram?.WebApp) {
      window.Telegram.WebApp.showConfirm('Удалить преподавателя?', (confirmed) => {
        if (confirmed) doDelete();
      });
    } else if (confirm('Удалить преподавателя?')) {
      doDelete();
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

  const getRoleLabel = (role: string) => {
    return role === 'lecturer' ? '📖 Лектор' : '✏️ Практикант';
  };

  if (loading) {
    return (
      <div className="loading">
        <div className="spinner" />
      </div>
    );
  }

  return (
    <div className="teachers-page">
      <div className="page-header">
        <h1 className="page-title">Преподаватели</h1>
      </div>

      {teachers.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon">👨‍🏫</div>
          <div className="empty-state-title">Нет преподавателей</div>
          <div className="empty-state-text">
            Напиши боту заметку о преподавателе или загрузи данные семестра
          </div>
        </div>
      ) : (
        <div className="teachers-list">
          {teachers.map((teacher) => (
            <div key={teacher.id} className="card teacher-card">
              <div className="card-header">
                <div className="teacher-main-info">
                  <div className="card-title">
                    {getTemperamentEmoji(teacher.temperament)} {teacher.name}
                  </div>
                  <div className="teacher-subjects">
                    {teacher.subjects.map((s, idx) => (
                      <span key={idx} className="tag tag-subject">
                        {getRoleLabel(s.role)} {s.subject_name}
                      </span>
                    ))}
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

                {teacher.contact_info && (
                  <div className="info-row">
                    <span className="info-row-icon">📞</span>
                    <span className="info-row-label">Контакты:</span>
                    <span className="info-row-value">{teacher.contact_info}</span>
                  </div>
                )}

                {!teacher.temperament && !teacher.preferences && !teacher.notes && (
                  <div className="no-info-text">
                    Нет дополнительной информации
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
          ))}
        </div>
      )}

      {/* Edit Modal */}
      {showModal && editingTeacher && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2 className="modal-title">Редактировать</h2>
              <button className="modal-close" onClick={() => setShowModal(false)}>×</button>
            </div>

            <form onSubmit={handleSubmit}>
              <div className="modal-body">
                <div className="form-group">
                  <label className="form-label">Имя</label>
                  <input
                    type="text"
                    className="form-input"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    required
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">Характер</label>
                  <input
                    type="text"
                    className="form-input"
                    value={formData.temperament}
                    onChange={(e) => setFormData({ ...formData, temperament: e.target.value })}
                    placeholder="Строгий, добрый..."
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">Предпочтения</label>
                  <textarea
                    className="form-textarea"
                    value={formData.preferences}
                    onChange={(e) => setFormData({ ...formData, preferences: e.target.value })}
                    placeholder="Что спрашивает, на что обращает внимание..."
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

                <div className="form-group">
                  <label className="form-label">Контакты</label>
                  <input
                    type="text"
                    className="form-input"
                    value={formData.contact_info}
                    onChange={(e) => setFormData({ ...formData, contact_info: e.target.value })}
                    placeholder="Email, телефон..."
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
