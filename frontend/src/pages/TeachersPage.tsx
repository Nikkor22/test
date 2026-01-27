import { useEffect, useState } from 'react';
import { teachersApi, subjectsApi, Teacher, Subject } from '../api/client';

interface TeacherFormData {
  name: string;
  role: string;
  temperament: string;
  preferences: string;
  peculiarities: string;
  notes: string;
}

function TeachersPage() {
  const [teachers, setTeachers] = useState<Teacher[]>([]);
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingTeacher, setEditingTeacher] = useState<Teacher | null>(null);
  const [isCreating, setIsCreating] = useState(false);
  const [formData, setFormData] = useState<TeacherFormData & { subject_id?: number }>({
    name: '',
    role: 'lecturer',
    temperament: '',
    preferences: '',
    peculiarities: '',
    notes: '',
  });

  const fetchData = async () => {
    try {
      const [teachersRes, subjectsRes] = await Promise.all([
        teachersApi.getAll(),
        subjectsApi.getAll(),
      ]);
      setTeachers(teachersRes.data);
      setSubjects(subjectsRes.data);
    } catch (error) {
      console.error('Error fetching teachers:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleEdit = (teacher: Teacher) => {
    setEditingTeacher(teacher);
    setIsCreating(false);
    setFormData({
      name: teacher.name,
      role: teacher.role,
      temperament: teacher.temperament || '',
      preferences: teacher.preferences || '',
      peculiarities: teacher.peculiarities || '',
      notes: teacher.notes || '',
    });
    setShowModal(true);
  };

  const handleCreate = () => {
    setEditingTeacher(null);
    setIsCreating(true);
    setFormData({
      name: '',
      role: 'lecturer',
      temperament: '',
      preferences: '',
      peculiarities: '',
      notes: '',
      subject_id: subjects[0]?.id,
    });
    setShowModal(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (isCreating && formData.subject_id) {
        await teachersApi.create({
          subject_id: formData.subject_id,
          name: formData.name,
          role: formData.role,
          temperament: formData.temperament || undefined,
          preferences: formData.preferences || undefined,
          peculiarities: formData.peculiarities || undefined,
          notes: formData.notes || undefined,
        });
      } else if (editingTeacher) {
        await teachersApi.update(editingTeacher.id, formData);
      }
      window.Telegram?.WebApp?.HapticFeedback?.notificationOccurred('success');
      setShowModal(false);
      setEditingTeacher(null);
      setIsCreating(false);
      fetchData();
    } catch (error) {
      console.error('Error saving teacher:', error);
      window.Telegram?.WebApp?.HapticFeedback?.notificationOccurred('error');
    }
  };

  const handleDelete = async (id: number) => {
    const doDelete = async () => {
      try {
        await teachersApi.delete(id);
        window.Telegram?.WebApp?.HapticFeedback?.notificationOccurred('success');
        fetchData();
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

  const getRoleLabel = (role: string) => role === 'lecturer' ? 'Лектор' : 'Практикант';
  const getRoleEmoji = (role: string) => role === 'lecturer' ? '📖' : '📝';

  const getTemperamentEmoji = (temperament: string | null) => {
    if (!temperament) return '😐';
    const lower = temperament.toLowerCase();
    if (lower.includes('строг') || lower.includes('злой') || lower.includes('требоват')) return '😠';
    if (lower.includes('добр') || lower.includes('мягк') || lower.includes('лояльн')) return '😊';
    if (lower.includes('нейтрал') || lower.includes('норм')) return '😐';
    return '🎭';
  };

  // Group teachers by subject
  const teachersBySubject: Record<string, Teacher[]> = {};
  teachers.forEach((t) => {
    if (!teachersBySubject[t.subject_name]) teachersBySubject[t.subject_name] = [];
    teachersBySubject[t.subject_name].push(t);
  });

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
        {subjects.length > 0 && (
          <button className="btn btn-primary" onClick={handleCreate}>+ Добавить</button>
        )}
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
        Object.entries(teachersBySubject).map(([subjectName, subjectTeachers]) => (
          <div key={subjectName} style={{ marginBottom: 16 }}>
            <div style={{ fontSize: 14, color: 'var(--accent-secondary)', fontWeight: 600, marginBottom: 8, paddingLeft: 4 }}>
              📚 {subjectName}
            </div>
            {subjectTeachers.map((teacher) => (
              <div key={teacher.id} className="card">
                <div className="card-header">
                  <div>
                    <div className="card-title">
                      {getTemperamentEmoji(teacher.temperament)} {teacher.name}
                    </div>
                    <div className="card-subtitle">
                      <span className="tag tag-subject">
                        {getRoleEmoji(teacher.role)} {getRoleLabel(teacher.role)}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="card-body">
                  {teacher.temperament && (
                    <div className="teacher-info-section">
                      <div className="teacher-info-label">🎭 Характер</div>
                      <div className="teacher-info-value">{teacher.temperament}</div>
                    </div>
                  )}

                  {teacher.preferences && (
                    <div className="teacher-info-section">
                      <div className="teacher-info-label">💡 Предпочтения</div>
                      <div className="teacher-info-value">{teacher.preferences}</div>
                    </div>
                  )}

                  {teacher.peculiarities && (
                    <div className="teacher-info-section">
                      <div className="teacher-info-label">⚡ Особенности</div>
                      <div className="teacher-info-value">{teacher.peculiarities}</div>
                    </div>
                  )}

                  {teacher.notes && (
                    <div className="teacher-info-section">
                      <div className="teacher-info-label">📝 Заметки</div>
                      <div className="teacher-info-value">{teacher.notes}</div>
                    </div>
                  )}

                  {!teacher.temperament && !teacher.preferences && !teacher.peculiarities && !teacher.notes && (
                    <div style={{ color: 'var(--text-muted)', fontStyle: 'italic' }}>
                      Нет информации. Напишите боту заметку об этом преподавателе.
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
        ))
      )}

      {/* Modal */}
      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2 className="modal-title">
                {isCreating ? 'Добавить преподавателя' : 'Редактировать преподавателя'}
              </h2>
              <button className="modal-close" onClick={() => setShowModal(false)}>×</button>
            </div>

            <form onSubmit={handleSubmit}>
              <div className="modal-body">
                {isCreating && (
                  <div className="form-group">
                    <label className="form-label">Предмет</label>
                    <select
                      className="form-select"
                      value={formData.subject_id}
                      onChange={(e) => setFormData({ ...formData, subject_id: Number(e.target.value) })}
                      required
                    >
                      {subjects.map((s) => (
                        <option key={s.id} value={s.id}>{s.name}</option>
                      ))}
                    </select>
                  </div>
                )}

                {!isCreating && editingTeacher && (
                  <div className="form-group">
                    <label className="form-label">Предмет</label>
                    <input type="text" className="form-input" value={editingTeacher.subject_name} disabled style={{ opacity: 0.6 }} />
                  </div>
                )}

                <div className="form-group">
                  <label className="form-label">Имя</label>
                  <input
                    type="text" className="form-input"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    placeholder="Иванов И.И." required
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">Роль</label>
                  <select
                    className="form-select"
                    value={formData.role}
                    onChange={(e) => setFormData({ ...formData, role: e.target.value })}
                  >
                    <option value="lecturer">📖 Лектор</option>
                    <option value="practitioner">📝 Практикант</option>
                  </select>
                </div>

                <div className="form-group">
                  <label className="form-label">🎭 Характер/темперамент</label>
                  <input
                    type="text" className="form-input"
                    value={formData.temperament}
                    onChange={(e) => setFormData({ ...formData, temperament: e.target.value })}
                    placeholder="Строгий, требовательный..."
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">💡 Предпочтения</label>
                  <textarea
                    className="form-textarea"
                    value={formData.preferences}
                    onChange={(e) => setFormData({ ...formData, preferences: e.target.value })}
                    placeholder="Что любит спрашивать, на что обращает внимание..."
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">⚡ Особенности</label>
                  <textarea
                    className="form-textarea"
                    value={formData.peculiarities}
                    onChange={(e) => setFormData({ ...formData, peculiarities: e.target.value })}
                    placeholder="Опаздывает, отпускает раньше, не ставит автоматы..."
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">📝 Заметки</label>
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
                  {isCreating ? 'Добавить' : 'Сохранить'}
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
