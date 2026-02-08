import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const getTelegramId = (): number => {
  if (window.Telegram?.WebApp?.initDataUnsafe?.user?.id) {
    return window.Telegram.WebApp.initDataUnsafe.user.id;
  }
  // Fallback for development - change this to your telegram_id
  const fallbackId = 7167288809;
  console.log('[API] Using fallback telegram_id:', fallbackId);
  return fallbackId;
};

const api = axios.create({
  baseURL: API_URL,
});

api.interceptors.request.use((config) => {
  const telegramId = getTelegramId();
  config.params = {
    ...config.params,
    telegram_id: telegramId,
  };
  return config;
});

// Types
export interface Teacher {
  id: number;
  name: string;
  role: string;
  temperament: string | null;
  preferences: string | null;
  peculiarities: string | null;
  notes: string | null;
  subject_name: string;
  subject_id: number;
}

export interface Deadline {
  id: number;
  title: string;
  work_type: string;
  description: string | null;
  gpt_description: string | null;
  deadline_date: string;
  is_completed: boolean;
  subject_name: string;
  subject_id: number;
}

export interface Subject {
  id: number;
  name: string;
}

export interface SubjectDetail {
  id: number;
  name: string;
  teachers: Teacher[];
  summary: string | null;
}

export interface ScheduleEntry {
  id: number;
  subject_id: number;
  subject_name: string;
  day_of_week: number;
  start_time: string;
  end_time: string;
  room: string | null;
  class_type: string;
  week_type: string;
  teacher_name: string | null;
}

export interface Material {
  id: number;
  subject_id: number;
  subject_name: string;
  file_name: string;
  file_type: string;
  created_at: string;
}

export interface SubjectSummary {
  subject_id: number;
  subject_name: string;
  summary_text: string | null;
  generated_at: string | null;
}

export interface ReminderSettings {
  hours_before: number[];
  is_enabled: boolean;
}

export interface TitleTemplate {
  id: number;
  name: string;
  file_name: string;
  is_default: boolean;
  created_at: string;
}

export interface GeneratedWork {
  id: number;
  deadline_id: number;
  deadline_title: string;
  subject_name: string;
  work_type: string;
  work_number: number | null;
  file_name: string | null;
  file_type: string;
  status: 'pending' | 'generating' | 'ready' | 'confirmed' | 'sent';
  scheduled_send_at: string | null;
  auto_send: boolean;
  generated_at: string | null;
  confirmed_at: string | null;
  sent_at: string | null;
  deadline_date: string;
}

export interface DeadlineWithWork {
  id: number;
  title: string;
  work_type: string;
  work_number: number | null;
  description: string | null;
  gpt_description: string | null;
  deadline_date: string;
  is_completed: boolean;
  subject_name: string;
  subject_id: number;
  has_generated_work: boolean;
  generated_work_status: string | null;
}

export interface UserWorkSettings {
  reminder_days_before: number[];
  auto_generate: boolean;
  generate_days_before: number;
  require_confirmation: boolean;
  default_send_days_before: number;
}

// Teachers API
export const teachersApi = {
  getAll: () => api.get<Teacher[]>('/api/teachers'),
  get: (id: number) => api.get<Teacher>(`/api/teachers/${id}`),
  create: (data: { subject_id: number; name: string; role: string; temperament?: string; preferences?: string; peculiarities?: string; notes?: string }) =>
    api.post<Teacher>('/api/teachers', data),
  update: (id: number, data: Partial<Teacher>) =>
    api.put<Teacher>(`/api/teachers/${id}`, data),
  delete: (id: number) => api.delete(`/api/teachers/${id}`),
};

// Deadlines API
export const deadlinesApi = {
  getAll: (showCompleted = false) =>
    api.get<Deadline[]>('/api/deadlines', { params: { show_completed: showCompleted } }),
  create: (data: { subject_id: number; title: string; work_type: string; description?: string; deadline_date: string }) =>
    api.post<Deadline>('/api/deadlines', data),
  update: (id: number, data: Partial<Deadline>) =>
    api.put<Deadline>(`/api/deadlines/${id}`, data),
  delete: (id: number) => api.delete(`/api/deadlines/${id}`),
};

// Subjects API
export const subjectsApi = {
  getAll: () => api.get<Subject[]>('/api/subjects'),
  get: (id: number) => api.get<SubjectDetail>(`/api/subjects/${id}`),
  create: (name: string) => api.post<Subject>('/api/subjects', { name }),
  delete: (id: number) => api.delete(`/api/subjects/${id}`),
};

// Schedule API
export const scheduleApi = {
  getAll: (dayOfWeek?: number, weekType?: string) =>
    api.get<ScheduleEntry[]>('/api/schedule', {
      params: { day_of_week: dayOfWeek, week_type: weekType },
    }),
  create: (data: { subject_id: number; day_of_week: number; start_time: string; end_time: string; room?: string; class_type?: string; week_type?: string; teacher_name?: string }) =>
    api.post<ScheduleEntry>('/api/schedule', data),
  update: (id: number, data: Partial<ScheduleEntry>) =>
    api.put<ScheduleEntry>(`/api/schedule/${id}`, data),
  delete: (id: number) => api.delete(`/api/schedule/${id}`),
};

// Materials API
export const materialsApi = {
  getAll: (subjectId?: number) =>
    api.get<Material[]>('/api/materials', { params: { subject_id: subjectId } }),
  upload: (subjectId: number, file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post<Material>('/api/materials/upload', formData, {
      params: { subject_id: subjectId },
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
  delete: (id: number) => api.delete(`/api/materials/${id}`),
};

// Summary API
export const summaryApi = {
  get: (subjectId: number) => api.get<SubjectSummary>(`/api/subjects/${subjectId}/summary`),
  generate: (subjectId: number) => api.post<SubjectSummary>(`/api/subjects/${subjectId}/summary`),
};

// Settings API
export const settingsApi = {
  getReminders: () => api.get<ReminderSettings>('/api/settings/reminders'),
  updateReminders: (data: Partial<ReminderSettings>) =>
    api.put<ReminderSettings>('/api/settings/reminders', data),
  getWorkSettings: () => api.get<UserWorkSettings>('/api/settings/work'),
  updateWorkSettings: (data: Partial<UserWorkSettings>) =>
    api.put<UserWorkSettings>('/api/settings/work', data),
};

// Title Templates API
export const templatesApi = {
  getAll: () => api.get<TitleTemplate[]>('/api/title-templates'),
  upload: (name: string, file: File, isDefault = false) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post<TitleTemplate>('/api/title-templates', formData, {
      params: { name, is_default: isDefault },
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
  setDefault: (id: number) => api.put(`/api/title-templates/${id}/set-default`),
  delete: (id: number) => api.delete(`/api/title-templates/${id}`),
};

// Generated Works API
export const worksApi = {
  getAll: (status?: string) =>
    api.get<GeneratedWork[]>('/api/generated-works', { params: { status } }),
  get: (id: number) => api.get<GeneratedWork>(`/api/generated-works/${id}`),
  create: (data: { deadline_id: number; title_template_id?: number; scheduled_send_at?: string; auto_send?: boolean }) =>
    api.post<GeneratedWork>('/api/generated-works', data),
  generate: (id: number) => api.post(`/api/generated-works/${id}/generate`),
  confirm: (id: number) => api.post(`/api/generated-works/${id}/confirm`),
  update: (id: number, data: { scheduled_send_at?: string; auto_send?: boolean }) =>
    api.put<GeneratedWork>(`/api/generated-works/${id}`, data),
  delete: (id: number) => api.delete(`/api/generated-works/${id}`),
};

// Deadlines with Works API
export const deadlinesWithWorksApi = {
  getAll: (showCompleted = false) =>
    api.get<DeadlineWithWork[]>('/api/deadlines-with-works', { params: { show_completed: showCompleted } }),
  create: (data: { subject_id: number; title: string; work_type: string; work_number?: number; description?: string; deadline_date: string }) =>
    api.post<DeadlineWithWork>('/api/deadlines-with-work', data),
};

// Course Import Response
export interface CourseImportResult {
  success: boolean;
  courses_imported?: number;
  subjects_created: number;
  deadlines_created: number;
  materials_imported: number;
  errors: string[];
}

// Course Import API
export const importApi = {
  uploadZip: (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post<CourseImportResult>('/api/import/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 120000, // 2 minute timeout for large files
    });
  },
};

// Smart Upload Types
export interface FileAnalysis {
  original_filename: string;
  detected_subject: string | null;
  detected_work_type: string | null;
  detected_work_number: number | null;
  detected_deadline: string | null;
  suggested_title: string;
  confidence: number;
}

export interface AnalyzeFilesResponse {
  files: FileAnalysis[];
  common_subject: string | null;
  common_work_type: string | null;
  suggested_deadline: string | null;
  total_files: number;
}

export interface QuickUploadResponse {
  success: boolean;
  subject_id?: number;
  subject_name?: string;
  deadline_id?: number;
  deadline_title?: string;
  deadline_date?: string;
  materials_saved: number;
  error?: string;
}

// Smart Upload API
export const uploadApi = {
  analyze: (filenames: string[]) =>
    api.post<AnalyzeFilesResponse>('/api/upload/analyze', { filenames }),

  quick: (
    files: File[],
    options?: {
      subject_name?: string;
      work_type?: string;
      work_number?: number;
      title?: string;
      deadline_date?: string;
      description?: string;
    }
  ) => {
    const formData = new FormData();
    files.forEach((file) => formData.append('files', file));
    return api.post<QuickUploadResponse>('/api/upload/quick', formData, {
      params: options,
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 60000,
    });
  },
};

export default api;
