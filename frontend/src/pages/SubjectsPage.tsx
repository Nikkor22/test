import { useEffect, useState, useRef } from 'react';
import { subjectsApi, materialsApi, summaryApi, Subject, Material, SubjectSummary } from '../api/client';

function SubjectsPage() {
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [materials, setMaterials] = useState<Material[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedSubject, setSelectedSubject] = useState<number | null>(null);
  const [summary, setSummary] = useState<SubjectSummary | null>(null);
  const [generatingSummary, setGeneratingSummary] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [newSubject, setNewSubject] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);
  const subjectDetailRef = useRef<HTMLDivElement>(null);

  const fetchData = async () => {
    try {
      const [subjectsRes, materialsRes] = await Promise.all([
        subjectsApi.getAll(),
        materialsApi.getAll(),
      ]);
      setSubjects(subjectsRes.data);
      setMaterials(materialsRes.data);
    } catch (error) {
      console.error('Error fetching data:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  useEffect(() => {
    if (selectedSubject) {
      summaryApi.get(selectedSubject).then((res) => setSummary(res.data)).catch(() => setSummary(null));
      // Scroll to detail section
      setTimeout(() => {
        subjectDetailRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }, 100);
    }
  }, [selectedSubject]);

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files?.[0] || !selectedSubject) return;
    const file = e.target.files[0];
    setUploading(true);
    try {
      await materialsApi.upload(selectedSubject, file);
      window.Telegram?.WebApp?.HapticFeedback?.notificationOccurred('success');
      const res = await materialsApi.getAll();
      setMaterials(res.data);
    } catch (error) {
      console.error('Error uploading:', error);
      window.Telegram?.WebApp?.HapticFeedback?.notificationOccurred('error');
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleGenerateSummary = async () => {
    if (!selectedSubject) return;
    setGeneratingSummary(true);
    try {
      const res = await summaryApi.generate(selectedSubject);
      setSummary(res.data);
      window.Telegram?.WebApp?.HapticFeedback?.notificationOccurred('success');
    } catch (error) {
      console.error('Error generating summary:', error);
    } finally {
      setGeneratingSummary(false);
    }
  };

  const handleDeleteMaterial = async (id: number) => {
    const doDelete = async () => {
      try {
        await materialsApi.delete(id);
        setMaterials(materials.filter((m) => m.id !== id));
        window.Telegram?.WebApp?.HapticFeedback?.notificationOccurred('success');
      } catch (error) {
        console.error('Error deleting material:', error);
      }
    };

    if (window.Telegram?.WebApp) {
      window.Telegram.WebApp.showConfirm('Удалить этот материал?', (confirmed) => {
        if (confirmed) doDelete();
      });
    } else if (confirm('Удалить этот материал?')) {
      doDelete();
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
    const doDelete = async () => {
      try {
        await subjectsApi.delete(id);
        if (selectedSubject === id) setSelectedSubject(null);
        fetchData();
      } catch (error) {
        console.error('Error:', error);
      }
    };

    if (window.Telegram?.WebApp) {
      window.Telegram.WebApp.showConfirm('Удалить предмет и все связанные данные?', (confirmed) => {
        if (confirmed) doDelete();
      });
    } else if (confirm('Удалить предмет и все связанные данные?')) {
      doDelete();
    }
  };

  const subjectMaterials = selectedSubject ? materials.filter((m) => m.subject_id === selectedSubject) : [];

  const getFileIcon = (type: string) => {
    switch (type) {
      case 'pdf': return '📕';
      case 'xlsx': case 'xls': return '📊';
      case 'docx': return '📘';
      case 'txt': return '📄';
      default: return '📎';
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
        <h1 className="page-title">Предметы</h1>
      </div>

      {/* Add Subject */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
        <input
          type="text"
          className="form-input"
          placeholder="Новый предмет..."
          value={newSubject}
          onChange={(e) => setNewSubject(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && addSubject()}
          style={{ flex: 1 }}
        />
        <button className="btn btn-primary" onClick={addSubject}>+</button>
      </div>

      {subjects.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon">📚</div>
          <div className="empty-state-title">Нет предметов</div>
          <div className="empty-state-text">Добавьте первый предмет или напишите боту заметку</div>
        </div>
      ) : (
        <>
          {/* Subject List */}
          <div className="subject-chips">
            {subjects.map((subject) => (
              <button
                key={subject.id}
                className={`subject-chip ${selectedSubject === subject.id ? 'active' : ''}`}
                onClick={() => setSelectedSubject(selectedSubject === subject.id ? null : subject.id)}
              >
                {subject.name}
              </button>
            ))}
          </div>

          {/* Selected Subject Detail */}
          {selectedSubject && (
            <div ref={subjectDetailRef} style={{ marginTop: 16 }}>
              {/* Summary */}
              <div className="card">
                <div className="card-header">
                  <div className="card-title">🧠 Выжимка по предмету</div>
                  <button
                    className="btn btn-sm btn-primary"
                    onClick={handleGenerateSummary}
                    disabled={generatingSummary}
                  >
                    {generatingSummary ? '⏳' : '🔄'} {generatingSummary ? 'Генерация...' : 'Сгенерировать'}
                  </button>
                </div>
                <div className="card-body">
                  {summary?.summary_text ? (
                    <div style={{ whiteSpace: 'pre-wrap', lineHeight: 1.6 }}>
                      {summary.summary_text}
                    </div>
                  ) : (
                    <div style={{ color: 'var(--text-muted)', fontStyle: 'italic' }}>
                      Нет выжимки. Загрузите материалы и нажмите "Сгенерировать".
                    </div>
                  )}
                </div>
              </div>

              {/* Materials */}
              <div className="card">
                <div className="card-header">
                  <div className="card-title">📎 Материалы</div>
                  <button
                    className="btn btn-sm btn-secondary"
                    onClick={() => fileInputRef.current?.click()}
                    disabled={uploading}
                  >
                    {uploading ? '⏳ Загрузка...' : '+ Загрузить'}
                  </button>
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".pdf,.xlsx,.xls,.docx,.txt"
                    onChange={handleUpload}
                    style={{ display: 'none' }}
                  />
                </div>
                <div className="card-body">
                  {subjectMaterials.length === 0 ? (
                    <div style={{ color: 'var(--text-muted)', fontStyle: 'italic' }}>
                      Нет загруженных материалов
                    </div>
                  ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                      {subjectMaterials.map((material) => (
                        <div key={material.id} className="material-row">
                          <span className="material-icon">{getFileIcon(material.file_type)}</span>
                          <div className="material-info">
                            <div className="material-name">{material.file_name}</div>
                            <div className="material-meta">{material.file_type.toUpperCase()}</div>
                          </div>
                          <button
                            className="btn btn-sm btn-danger"
                            onClick={() => handleDeleteMaterial(material.id)}
                          >
                            🗑️
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              {/* Delete Subject */}
              <button
                className="btn btn-danger"
                onClick={() => deleteSubject(selectedSubject)}
                style={{ width: '100%', marginTop: 8 }}
              >
                🗑️ Удалить предмет
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}

export default SubjectsPage;
