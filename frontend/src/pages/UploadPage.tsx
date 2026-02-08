import { useState, useRef, useCallback, useEffect } from 'react';
import { format, addDays } from 'date-fns';
import { ru } from 'date-fns/locale';
import {
  uploadApi,
  subjectsApi,
  Subject,
  FileAnalysis,
  QuickUploadResponse,
} from '../api/client';

const WORK_TYPE_LABELS: Record<string, string> = {
  auto: 'Автоопределение',
  homework: 'Домашнее задание',
  lab: 'Лабораторная',
  practical: 'Практическая',
  lecture: 'Лекция',
  test: 'Контрольная',
  coursework: 'Курсовая',
  report: 'Реферат',
  presentation: 'Презентация',
};

function UploadPage() {
  const [files, setFiles] = useState<File[]>([]);
  const [analysis, setAnalysis] = useState<FileAnalysis[]>([]);
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<QuickUploadResponse | null>(null);
  const [dragActive, setDragActive] = useState(false);

  // Form state
  const [selectedSubject, setSelectedSubject] = useState<string>('');
  const [newSubject, setNewSubject] = useState('');
  const [workType, setWorkType] = useState('auto');
  const [workNumber, setWorkNumber] = useState<string>('');
  const [title, setTitle] = useState('');
  const [deadlineDate, setDeadlineDate] = useState(
    format(addDays(new Date(), 7), 'yyyy-MM-dd')
  );
  const [description, setDescription] = useState('');

  const fileInputRef = useRef<HTMLInputElement>(null);

  // Fetch subjects on mount
  useEffect(() => {
    subjectsApi.getAll().then((res) => setSubjects(res.data));
  }, []);

  const analyzeFiles = async (fileList: File[]) => {
    if (fileList.length === 0) return;

    setLoading(true);
    try {
      const filenames = fileList.map((f) => f.name);
      const res = await uploadApi.analyze(filenames);

      setAnalysis(res.data.files);

      // Auto-fill form from analysis
      if (res.data.common_subject) {
        // Check if subject exists
        const existing = subjects.find(
          (s) => s.name.toLowerCase() === res.data.common_subject?.toLowerCase()
        );
        if (existing) {
          setSelectedSubject(existing.id.toString());
        } else {
          setNewSubject(res.data.common_subject);
        }
      }

      if (res.data.common_work_type) {
        setWorkType(res.data.common_work_type);
      }

      if (res.data.suggested_deadline) {
        setDeadlineDate(res.data.suggested_deadline.split('T')[0]);
      }

      // Get work number and title from first file
      if (res.data.files[0]) {
        if (res.data.files[0].detected_work_number) {
          setWorkNumber(res.data.files[0].detected_work_number.toString());
        }
        if (res.data.files[0].suggested_title) {
          setTitle(res.data.files[0].suggested_title);
        }
      }
    } catch (error) {
      console.error('Error analyzing files:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const fileList = Array.from(e.target.files);
      setFiles(fileList);
      analyzeFiles(fileList);
    }
  };

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const fileList = Array.from(e.dataTransfer.files);
      setFiles(fileList);
      analyzeFiles(fileList);
    }
  }, [subjects]);

  const handleUpload = async () => {
    if (files.length === 0) return;

    const subjectName = newSubject || subjects.find((s) => s.id.toString() === selectedSubject)?.name;

    if (!subjectName) {
      window.Telegram?.WebApp?.showAlert?.('Выберите или введите название предмета');
      return;
    }

    setUploading(true);
    setResult(null);

    try {
      // If workType is 'auto', don't pass it - let backend auto-group by detected types
      const res = await uploadApi.quick(files, {
        subject_name: subjectName,
        work_type: workType === 'auto' ? undefined : workType,
        work_number: workType === 'auto' ? undefined : (workNumber ? parseInt(workNumber) : undefined),
        title: workType === 'auto' ? undefined : (title || undefined),
        deadline_date: deadlineDate,
        description: description || undefined,
      });

      setResult(res.data);

      if (res.data.success) {
        window.Telegram?.WebApp?.HapticFeedback?.notificationOccurred('success');
        // Reset form
        setFiles([]);
        setAnalysis([]);
        setTitle('');
        setWorkNumber('');
        setDescription('');
        // Refresh subjects
        const subjectsRes = await subjectsApi.getAll();
        setSubjects(subjectsRes.data);
      }
    } catch (error) {
      console.error('Error uploading:', error);
      setResult({
        success: false,
        error: 'Ошибка загрузки',
        materials_saved: 0,
      });
      window.Telegram?.WebApp?.HapticFeedback?.notificationOccurred('error');
    } finally {
      setUploading(false);
    }
  };

  const removeFile = (index: number) => {
    const newFiles = files.filter((_, i) => i !== index);
    setFiles(newFiles);
    if (newFiles.length > 0) {
      analyzeFiles(newFiles);
    } else {
      setAnalysis([]);
    }
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.6) return '#22c55e';
    if (confidence >= 0.3) return '#f59e0b';
    return '#ef4444';
  };

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Быстрая загрузка</h1>
      </div>

      {/* Drop Zone */}
      <div
        className={`card ${dragActive ? 'drag-active' : ''}`}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        style={{
          border: dragActive ? '2px dashed #7c3aed' : '2px dashed var(--border)',
          background: dragActive ? 'rgba(124, 58, 237, 0.1)' : 'var(--bg-card)',
          transition: 'all 0.2s',
        }}
      >
        <div
          className="card-body"
          style={{
            textAlign: 'center',
            padding: 32,
            cursor: 'pointer',
          }}
          onClick={() => fileInputRef.current?.click()}
        >
          <div style={{ fontSize: 48, marginBottom: 16 }}>📎</div>
          <div style={{ fontWeight: 500, marginBottom: 8 }}>
            Перетащите файлы сюда
          </div>
          <div style={{ fontSize: 13, color: 'var(--text-muted)' }}>
            или нажмите для выбора
          </div>
          <input
            ref={fileInputRef}
            type="file"
            multiple
            onChange={handleFileChange}
            style={{ display: 'none' }}
            accept=".pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt,.zip"
          />
        </div>
      </div>

      {/* Loading */}
      {loading && (
        <div className="card">
          <div className="card-body" style={{ textAlign: 'center', padding: 24 }}>
            <div className="spinner" style={{ margin: '0 auto 12px' }}></div>
            <div>Анализ файлов...</div>
          </div>
        </div>
      )}

      {/* Files List */}
      {files.length > 0 && !loading && (
        <div className="card">
          <div className="card-header">
            <div className="card-title">📄 Выбранные файлы ({files.length})</div>
          </div>
          <div className="card-body" style={{ padding: 0 }}>
            {files.map((file, index) => {
              const fileAnalysis = analysis[index];
              return (
                <div
                  key={index}
                  style={{
                    padding: 12,
                    borderBottom: '1px solid var(--border)',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 12,
                  }}
                >
                  <div style={{ flex: 1 }}>
                    <div style={{ fontWeight: 500, fontSize: 14 }}>{file.name}</div>
                    {fileAnalysis && (
                      <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>
                        {fileAnalysis.detected_subject && (
                          <span className="tag tag-subject" style={{ marginRight: 4 }}>
                            {fileAnalysis.detected_subject}
                          </span>
                        )}
                        {fileAnalysis.detected_work_type && (
                          <span className="tag tag-type" style={{ marginRight: 4 }}>
                            {WORK_TYPE_LABELS[fileAnalysis.detected_work_type] || fileAnalysis.detected_work_type}
                          </span>
                        )}
                        <span
                          style={{
                            color: getConfidenceColor(fileAnalysis.confidence),
                            fontSize: 11,
                          }}
                        >
                          {Math.round(fileAnalysis.confidence * 100)}% уверенность
                        </span>
                      </div>
                    )}
                  </div>
                  <button
                    className="btn btn-sm btn-secondary"
                    onClick={() => removeFile(index)}
                  >
                    ✕
                  </button>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Form */}
      {files.length > 0 && !loading && (
        <div className="card">
          <div className="card-header">
            <div className="card-title">⚙️ Настройки</div>
          </div>
          <div className="card-body">
            {/* Subject */}
            <div style={{ marginBottom: 16 }}>
              <label style={{ display: 'block', marginBottom: 6, fontSize: 13, fontWeight: 500 }}>
                Предмет
              </label>
              {subjects.length > 0 ? (
                <select
                  className="form-input"
                  value={selectedSubject}
                  onChange={(e) => {
                    setSelectedSubject(e.target.value);
                    if (e.target.value) setNewSubject('');
                  }}
                  style={{ width: '100%', marginBottom: 8 }}
                >
                  <option value="">-- Выбрать существующий --</option>
                  {subjects.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name}
                    </option>
                  ))}
                </select>
              ) : null}
              <input
                type="text"
                className="form-input"
                placeholder="Или введите новый предмет..."
                value={newSubject}
                onChange={(e) => {
                  setNewSubject(e.target.value);
                  if (e.target.value) setSelectedSubject('');
                }}
                style={{ width: '100%' }}
              />
            </div>

            {/* Work Type */}
            <div style={{ marginBottom: 16 }}>
              <label style={{ display: 'block', marginBottom: 6, fontSize: 13, fontWeight: 500 }}>
                Тип работы
              </label>
              <select
                className="form-input"
                value={workType}
                onChange={(e) => setWorkType(e.target.value)}
                style={{ width: '100%' }}
              >
                {Object.entries(WORK_TYPE_LABELS).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
              {workType === 'auto' && (
                <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>
                  Система автоматически определит тип каждого файла и создаст отдельные задания
                </div>
              )}
            </div>

            {/* Work Number & Title - only show if not auto mode */}
            {workType !== 'auto' && (
              <div style={{ display: 'flex', gap: 12, marginBottom: 16 }}>
                <div style={{ width: 80 }}>
                  <label style={{ display: 'block', marginBottom: 6, fontSize: 13, fontWeight: 500 }}>
                    №
                  </label>
                  <input
                    type="number"
                    className="form-input"
                    value={workNumber}
                    onChange={(e) => setWorkNumber(e.target.value)}
                    placeholder="1"
                    style={{ width: '100%' }}
                  />
                </div>
                <div style={{ flex: 1 }}>
                  <label style={{ display: 'block', marginBottom: 6, fontSize: 13, fontWeight: 500 }}>
                    Название
                  </label>
                  <input
                    type="text"
                    className="form-input"
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    placeholder="Автоматически"
                    style={{ width: '100%' }}
                  />
                </div>
              </div>
            )}

            {/* Deadline */}
            <div style={{ marginBottom: 16 }}>
              <label style={{ display: 'block', marginBottom: 6, fontSize: 13, fontWeight: 500 }}>
                Дедлайн
              </label>
              <input
                type="date"
                className="form-input"
                value={deadlineDate}
                onChange={(e) => setDeadlineDate(e.target.value)}
                style={{ width: '100%' }}
              />
            </div>

            {/* Description */}
            <div style={{ marginBottom: 16 }}>
              <label style={{ display: 'block', marginBottom: 6, fontSize: 13, fontWeight: 500 }}>
                Описание (опционально)
              </label>
              <textarea
                className="form-input"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Дополнительная информация..."
                rows={2}
                style={{ width: '100%', resize: 'vertical' }}
              />
            </div>

            {/* Upload Button */}
            <button
              className="btn btn-primary"
              onClick={handleUpload}
              disabled={uploading}
              style={{ width: '100%' }}
            >
              {uploading ? '⏳ Загрузка...' : '📤 Загрузить'}
            </button>
          </div>
        </div>
      )}

      {/* Result */}
      {result && (
        <div
          className="card"
          style={{
            background: result.success ? 'rgba(34, 197, 94, 0.1)' : 'rgba(239, 68, 68, 0.1)',
            border: `1px solid ${result.success ? '#22c55e' : '#ef4444'}`,
          }}
        >
          <div className="card-body">
            <div
              style={{
                fontWeight: 500,
                marginBottom: 8,
                color: result.success ? '#22c55e' : '#ef4444',
              }}
            >
              {result.success ? '✅ Загрузка завершена!' : '❌ Ошибка'}
            </div>

            {result.success && (
              <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
                <div style={{ marginBottom: 8 }}>📖 Предмет: <strong>{result.subject_name}</strong></div>
                <div>📎 Файлов загружено: {result.materials_saved}</div>
                {result.deadlines_created !== undefined && (
                  <div>📝 Заданий создано: {result.deadlines_created}</div>
                )}

                {/* Show created deadlines grouped by type */}
                {result.created_deadlines && result.created_deadlines.length > 0 && (
                  <div style={{ marginTop: 12 }}>
                    <div style={{ fontWeight: 500, marginBottom: 6 }}>Созданные задания:</div>
                    {result.created_deadlines.map((dl, i) => (
                      <div
                        key={i}
                        style={{
                          padding: '6px 10px',
                          background: 'var(--bg-secondary)',
                          borderRadius: 6,
                          marginBottom: 4,
                          display: 'flex',
                          justifyContent: 'space-between',
                          alignItems: 'center',
                        }}
                      >
                        <span>
                          {WORK_TYPE_LABELS[dl.work_type] || dl.work_type}
                          {dl.work_number && ` №${dl.work_number}`}
                        </span>
                        <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                          {dl.files_count} файл(ов)
                        </span>
                      </div>
                    ))}
                  </div>
                )}

                {/* Single deadline mode */}
                {result.deadline_title && !result.created_deadlines && (
                  <>
                    <div>📝 Задание: {result.deadline_title}</div>
                    <div>
                      📅 Дедлайн:{' '}
                      {result.deadline_date
                        ? format(new Date(result.deadline_date), 'd MMMM yyyy', { locale: ru })
                        : '—'}
                    </div>
                  </>
                )}
              </div>
            )}

            {result.error && (
              <div style={{ fontSize: 13, color: '#ef4444' }}>{result.error}</div>
            )}
          </div>
        </div>
      )}

      {/* Help */}
      <div className="card">
        <div className="card-header">
          <div className="card-title">💡 Подсказка</div>
        </div>
        <div className="card-body" style={{ fontSize: 13, color: 'var(--text-muted)' }}>
          <p style={{ marginBottom: 8 }}>
            Система автоматически определяет предмет и тип работы из имени файла.
          </p>
          <p style={{ marginBottom: 8 }}>
            <strong>Примеры хороших имён:</strong>
          </p>
          <ul style={{ margin: 0, paddingLeft: 20 }}>
            <li>Математика_ЛР_1.pdf</li>
            <li>Физика Лаб 2 15.03.2024.docx</li>
            <li>ПР3_Программирование.pdf</li>
          </ul>
        </div>
      </div>
    </div>
  );
}

export default UploadPage;
