import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const getTelegramId = (): number => {
  if (window.Telegram?.WebApp?.initDataUnsafe?.user?.id) {
    return window.Telegram.WebApp.initDataUnsafe.user.id;
  }
  return 7167288809;
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
};

export default api;
