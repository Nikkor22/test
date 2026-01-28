import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { teachersApi, Teacher } from '../api/client';

export default function TeacherDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [teacher, setTeacher] = useState<Teacher | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (id) {
      loadTeacher(parseInt(id));
    }
  }, [id]);

  const loadTeacher = async (teacherId: number) => {
    setLoading(true);
    try {
      const response = await teachersApi.getById(teacherId);
      setTeacher(response.data);
    } catch (error) {
      console.error('Error loading teacher:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleBack = () => {
    navigate('/teachers');
    window.Telegram?.WebApp?.HapticFeedback?.selectionChanged();
  };

  const navigateToSubject = (subjectId: number) => {
    navigate(`/subjects/${subjectId}`);
    window.Telegram?.WebApp?.HapticFeedback?.selectionChanged();
  };

  if (loading) {
    return (
      <div className="loading">
        <div className="spinner" />
      </div>
    );
  }

  if (!teacher) {
    return (
      <div className="error-state">
        <div className="error-icon">❌</div>
        <div className="error-text">Преподаватель не найден</div>
        <button className="btn btn-primary" onClick={handleBack}>
          Назад к преподавателям
        </button>
      </div>
    );
  }

  const getRoleName = (role: string) => {
    switch (role) {
      case 'lecturer':
        return 'Лектор';
      case 'practitioner':
        return 'Практикант';
      default:
        return role;
    }
  };

  return (
    <div className="detail-page">
      {/* Header */}
      <div className="detail-header">
        <button className="back-btn" onClick={handleBack}>
          ← Назад
        </button>
        <h1 className="detail-title">{teacher.name}</h1>
      </div>

      {/* Contact Info */}
      {teacher.contact_info && (
        <div className="card">
          <div className="card-header">
            <div className="card-title">📱 Контакты</div>
          </div>
          <div className="card-body">
            <p className="teacher-contact">{teacher.contact_info}</p>
          </div>
        </div>
      )}

      {/* Temperament */}
      {teacher.temperament && (
        <div className="card">
          <div className="card-header">
            <div className="card-title">🎭 Характер</div>
          </div>
          <div className="card-body">
            <p className="teacher-temperament">{teacher.temperament}</p>
          </div>
        </div>
      )}

      {/* Preferences */}
      {teacher.preferences && (
        <div className="card">
          <div className="card-header">
            <div className="card-title">⭐ Предпочтения</div>
          </div>
          <div className="card-body">
            <p className="teacher-preferences">{teacher.preferences}</p>
          </div>
        </div>
      )}

      {/* Notes */}
      {teacher.notes && (
        <div className="card">
          <div className="card-header">
            <div className="card-title">📝 Заметки</div>
          </div>
          <div className="card-body">
            <p className="teacher-notes">{teacher.notes}</p>
          </div>
        </div>
      )}

      {/* Subjects */}
      <div className="card">
        <div className="card-header">
          <div className="card-title">📚 Предметы</div>
          <span className="card-badge">{teacher.subjects.length}</span>
        </div>
        <div className="card-body">
          {teacher.subjects.length === 0 ? (
            <div className="empty-mini">Нет привязанных предметов</div>
          ) : (
            teacher.subjects.map((subj) => (
              <div
                key={subj.subject_id}
                className="subject-link-row"
                onClick={() => navigateToSubject(subj.subject_id)}
              >
                <div className="subject-link-info">
                  <span className="subject-link-name">{subj.subject_name}</span>
                  <span className={`role-badge ${subj.role}`}>{getRoleName(subj.role)}</span>
                </div>
                <span className="chevron">›</span>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
