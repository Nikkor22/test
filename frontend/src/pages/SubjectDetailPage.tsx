import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  subjectsApi,
  deadlinesApi,
  materialsApi,
  notesApi,
  Subject,
  Deadline,
  Material,
  Note,
} from '../api/client';

type NoteType = 'note' | 'preference' | 'tip' | 'material';

const NOTE_TYPE_LABELS: Record<NoteType, { label: string; icon: string }> = {
  note: { label: 'Заметки', icon: '📝' },
  preference: { label: 'Предпочтения', icon: '⭐' },
  tip: { label: 'Советы', icon: '💡' },
  material: { label: 'Материалы', icon: '📄' },
};

export default function SubjectDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [subject, setSubject] = useState<Subject | null>(null);
  const [deadlines, setDeadlines] = useState<Deadline[]>([]);
  const [materials, setMaterials] = useState<Material[]>([]);
  const [notes, setNotes] = useState<Note[]>([]);
  const [loading, setLoading] = useState(true);
  const [generatingSummary, setGeneratingSummary] = useState(false);
  const [activeNotesTab, setActiveNotesTab] = useState<NoteType>('note');

  useEffect(() => {
    if (id) {
      loadData(parseInt(id));
    }
  }, [id]);

  const loadData = async (subjectId: number) => {
    setLoading(true);
    try {
      const [subjectRes, deadlinesRes, materialsRes, notesRes] = await Promise.all([
        subjectsApi.getById(subjectId),
        deadlinesApi.getAll(true),
        materialsApi.getAll(subjectId),
        notesApi.getAll(undefined, subjectId),
      ]);
      setSubject(subjectRes.data);
      setDeadlines(deadlinesRes.data.filter((d) => d.subject_id === subjectId));
      setMaterials(materialsRes.data);
      setNotes(notesRes.data);
    } catch (error) {
      console.error('Error loading subject data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateSummary = async () => {
    if (!subject) return;
    setGeneratingSummary(true);
    try {
      const response = await subjectsApi.generateSummary(subject.id);
      setSubject({ ...subject, ai_summary: response.data.summary });
      window.Telegram?.WebApp?.HapticFeedback?.notificationOccurred('success');
    } catch (error) {
      console.error('Error generating summary:', error);
    } finally {
      setGeneratingSummary(false);
    }
  };

  const handleBack = () => {
    navigate('/subjects');
    window.Telegram?.WebApp?.HapticFeedback?.selectionChanged();
  };

  const navigateToTeacher = (teacherId: number) => {
    navigate(`/teachers/${teacherId}`);
    window.Telegram?.WebApp?.HapticFeedback?.selectionChanged();
  };

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' });
  };

  const notesByType = (type: NoteType) => notes.filter((n) => n.note_type === type);

  if (loading) {
    return (
      <div className="loading">
        <div className="spinner" />
      </div>
    );
  }

  if (!subject) {
    return (
      <div className="error-state">
        <div className="error-icon">❌</div>
        <div className="error-text">Предмет не найден</div>
        <button className="btn btn-primary" onClick={handleBack}>
          Назад к предметам
        </button>
      </div>
    );
  }

  const lecturer = subject.teachers.find((t) => t.role === 'lecturer');
  const practitioner = subject.teachers.find((t) => t.role === 'practitioner');
  const upcomingDeadlines = deadlines.filter((d) => !d.is_completed);
  const completedDeadlines = deadlines.filter((d) => d.is_completed);

  return (
    <div className="detail-page">
      {/* Header */}
      <div className="detail-header">
        <button className="back-btn" onClick={handleBack}>
          ← Назад
        </button>
        <h1 className="detail-title">{subject.name}</h1>
      </div>

      {/* Description */}
      {subject.description && (
        <div className="card">
          <p className="subject-full-description">{subject.description}</p>
        </div>
      )}

      {/* Teachers */}
      <div className="card">
        <div className="card-header">
          <div className="card-title">👨‍🏫 Преподаватели</div>
        </div>
        <div className="card-body">
          {lecturer && (
            <div
              className="teacher-link-row"
              onClick={() => navigateToTeacher(lecturer.teacher_id)}
            >
              <span className="teacher-role-badge lecturer">Лектор</span>
              <span className="teacher-link-name">{lecturer.teacher_name}</span>
              <span className="chevron">›</span>
            </div>
          )}
          {practitioner && (
            <div
              className="teacher-link-row"
              onClick={() => navigateToTeacher(practitioner.teacher_id)}
            >
              <span className="teacher-role-badge practitioner">Практикант</span>
              <span className="teacher-link-name">{practitioner.teacher_name}</span>
              <span className="chevron">›</span>
            </div>
          )}
          {!lecturer && !practitioner && (
            <div className="empty-mini">Преподаватели не назначены</div>
          )}
        </div>
      </div>

      {/* AI Summary */}
      <div className="card">
        <div className="card-header">
          <div className="card-title">🤖 AI Выжимка</div>
        </div>
        <div className="card-body">
          {subject.ai_summary ? (
            <>
              <p className="ai-summary-full">{subject.ai_summary}</p>
              <button
                className="btn btn-sm btn-secondary"
                onClick={handleGenerateSummary}
                disabled={generatingSummary}
                style={{ marginTop: 12 }}
              >
                {generatingSummary ? 'Обновляю...' : '🔄 Обновить выжимку'}
              </button>
            </>
          ) : (
            <div className="empty-mini">
              <p style={{ marginBottom: 12 }}>Выжимка ещё не сгенерирована</p>
              <button
                className="btn btn-primary"
                onClick={handleGenerateSummary}
                disabled={generatingSummary}
              >
                {generatingSummary ? (
                  <>
                    <span className="spinner-sm" /> Генерирую...
                  </>
                ) : (
                  '🤖 Сгенерировать'
                )}
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Deadlines */}
      <div className="card">
        <div className="card-header">
          <div className="card-title">📅 Дедлайны</div>
          <span className="card-badge">{upcomingDeadlines.length}</span>
        </div>
        <div className="card-body">
          {upcomingDeadlines.length === 0 && completedDeadlines.length === 0 ? (
            <div className="empty-mini">Нет дедлайнов</div>
          ) : (
            <>
              {upcomingDeadlines.map((deadline) => (
                <div key={deadline.id} className="deadline-item">
                  <div className="deadline-item-header">
                    <span className="deadline-type-badge">{deadline.work_type}</span>
                    <span className="deadline-date">{formatDate(deadline.deadline_date)}</span>
                  </div>
                  <div className="deadline-item-title">{deadline.title}</div>
                  {deadline.ai_hint && (
                    <div className="deadline-item-hint">💡 {deadline.ai_hint}</div>
                  )}
                </div>
              ))}
              {completedDeadlines.length > 0 && (
                <details className="completed-section">
                  <summary className="completed-summary">
                    ✅ Выполнено ({completedDeadlines.length})
                  </summary>
                  {completedDeadlines.map((deadline) => (
                    <div key={deadline.id} className="deadline-item completed">
                      <div className="deadline-item-header">
                        <span className="deadline-type-badge">{deadline.work_type}</span>
                        <span className="deadline-date">{formatDate(deadline.deadline_date)}</span>
                      </div>
                      <div className="deadline-item-title">{deadline.title}</div>
                    </div>
                  ))}
                </details>
              )}
            </>
          )}
        </div>
      </div>

      {/* Materials */}
      {materials.length > 0 && (
        <div className="card">
          <div className="card-header">
            <div className="card-title">📁 Материалы</div>
            <span className="card-badge">{materials.length}</span>
          </div>
          <div className="card-body">
            {materials.map((material) => (
              <div key={material.id} className="material-item">
                <div className="material-item-header">
                  <span className="material-type-badge">{material.material_type}</span>
                  {material.scheduled_date && (
                    <span className="material-date">{formatDate(material.scheduled_date)}</span>
                  )}
                </div>
                <div className="material-item-title">{material.title}</div>
                {material.description && (
                  <div className="material-item-desc">{material.description}</div>
                )}
                {material.ai_summary && (
                  <div className="material-item-summary">🤖 {material.ai_summary}</div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Notes by type */}
      <div className="card">
        <div className="card-header">
          <div className="card-title">📝 Заметки</div>
        </div>
        <div className="card-body">
          {/* Notes tabs */}
          <div className="notes-tabs">
            {(Object.keys(NOTE_TYPE_LABELS) as NoteType[]).map((type) => {
              const count = notesByType(type).length;
              return (
                <button
                  key={type}
                  className={`notes-tab ${activeNotesTab === type ? 'active' : ''}`}
                  onClick={() => setActiveNotesTab(type)}
                >
                  {NOTE_TYPE_LABELS[type].icon} {NOTE_TYPE_LABELS[type].label}
                  {count > 0 && <span className="notes-tab-count">{count}</span>}
                </button>
              );
            })}
          </div>

          {/* Notes content */}
          <div className="notes-content">
            {notesByType(activeNotesTab).length === 0 ? (
              <div className="empty-mini">
                Нет {NOTE_TYPE_LABELS[activeNotesTab].label.toLowerCase()}
              </div>
            ) : (
              notesByType(activeNotesTab).map((note) => (
                <div key={note.id} className="note-item">
                  <div className="note-item-text">{note.raw_text}</div>
                  <div className="note-item-date">
                    {new Date(note.created_at).toLocaleDateString('ru-RU')}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
