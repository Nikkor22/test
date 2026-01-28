import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { subjectsApi, Subject } from '../api/client';

export default function SubjectsPage() {
  const navigate = useNavigate();
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [generatingSummary, setGeneratingSummary] = useState<number | null>(null);

  useEffect(() => {
    loadSubjects();
  }, []);

  const loadSubjects = async () => {
    try {
      const response = await subjectsApi.getAll();
      setSubjects(response.data);
    } catch (error) {
      console.error('Error loading subjects:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateSummary = async (subjectId: number) => {
    setGeneratingSummary(subjectId);
    try {
      const response = await subjectsApi.generateSummary(subjectId);
      setSubjects((prev) =>
        prev.map((s) => (s.id === subjectId ? { ...s, ai_summary: response.data.summary } : s))
      );
    } catch (error) {
      console.error('Error generating summary:', error);
    } finally {
      setGeneratingSummary(null);
    }
  };

  const toggleExpand = (id: number, e: React.MouseEvent) => {
    e.stopPropagation();
    setExpandedId(expandedId === id ? null : id);
  };

  const openSubjectDetail = (id: number) => {
    navigate(`/subjects/${id}`);
    window.Telegram?.WebApp?.HapticFeedback?.selectionChanged();
  };

  if (loading) {
    return (
      <div className="loading">
        <div className="spinner" />
      </div>
    );
  }

  return (
    <div className="subjects-page">
      <div className="page-header">
        <h1 className="page-title">Предметы</h1>
      </div>

      {subjects.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon">📚</div>
          <div className="empty-state-title">Нет предметов</div>
          <div className="empty-state-text">
            Загрузи данные семестра через бот или добавь предмет вручную
          </div>
        </div>
      ) : (
        <div className="subjects-list">
          {subjects.map((subject) => {
            const isExpanded = expandedId === subject.id;
            const lecturer = subject.teachers.find((t) => t.role === 'lecturer');
            const practitioner = subject.teachers.find((t) => t.role === 'practitioner');

            return (
              <div key={subject.id} className={`subject-card card ${isExpanded ? 'expanded' : ''}`}>
                <div className="subject-header" onClick={() => openSubjectDetail(subject.id)}>
                  <div className="subject-info">
                    <h3 className="subject-name">{subject.name}</h3>
                    {subject.description && (
                      <p className="subject-description">{subject.description}</p>
                    )}
                  </div>
                  <div className="subject-actions">
                    <button
                      className="expand-btn"
                      onClick={(e) => toggleExpand(subject.id, e)}
                    >
                      {isExpanded ? '▲' : '▼'}
                    </button>
                    <span className="chevron">›</span>
                  </div>
                </div>

                {isExpanded && (
                  <div className="subject-details">
                    {/* Преподаватели */}
                    <div className="subject-teachers">
                      {lecturer && (
                        <div className="teacher-row">
                          <span className="teacher-role">📖 Лектор:</span>
                          <span className="teacher-name">{lecturer.teacher_name}</span>
                        </div>
                      )}
                      {practitioner && (
                        <div className="teacher-row">
                          <span className="teacher-role">✏️ Практикант:</span>
                          <span className="teacher-name">{practitioner.teacher_name}</span>
                        </div>
                      )}
                      {!lecturer && !practitioner && (
                        <div className="no-teachers">Преподаватели не назначены</div>
                      )}
                    </div>

                    {/* AI выжимка */}
                    <div className="subject-summary-section">
                      {subject.ai_summary ? (
                        <div className="ai-summary">
                          <div className="ai-summary-header">
                            <span className="ai-icon">🤖</span>
                            <span>AI выжимка</span>
                          </div>
                          <p className="ai-summary-text">{subject.ai_summary}</p>
                          <button
                            className="btn btn-sm btn-secondary"
                            onClick={() => handleGenerateSummary(subject.id)}
                            disabled={generatingSummary === subject.id}
                          >
                            {generatingSummary === subject.id ? 'Обновляю...' : 'Обновить выжимку'}
                          </button>
                        </div>
                      ) : (
                        <button
                          className="btn btn-primary"
                          onClick={() => handleGenerateSummary(subject.id)}
                          disabled={generatingSummary === subject.id}
                        >
                          {generatingSummary === subject.id ? (
                            <>
                              <span className="spinner-sm" /> Генерирую...
                            </>
                          ) : (
                            <>🤖 Сгенерировать AI выжимку</>
                          )}
                        </button>
                      )}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
