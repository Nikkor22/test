import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const getTelegramId = (): number => {
  if (window.Telegram?.WebApp?.initDataUnsafe?.user?.id) {
    return window.Telegram.WebApp.initDataUnsafe.user.id;
  }
  return 123456789;
};

const api = axios.create({
  baseURL: API_URL,
});

api.interceptors.request.use((config) => {
  config.params = { ...config.params, telegram_id: getTelegramId() };
  return config;
});

// Types
export interface Teacher {
  id: number;
  name: string;
  temperament: string | null;
  preferences: string | null;
  notes: string | null;
  contact_info: string | null;
  subjects: { subject_id: number; subject_name: string; role: string }[];
}

export interface Subject {
  id: number;
  name: string;
  description: string | null;
  ai_summary: string | null;
  teachers: { teacher_id: number; teacher_name: string; role: string }[];
}

export interface Deadline {
  id: number;
  title: string;
  work_type: string;
  description: string | null;
  ai_hint: string | null;
  deadline_date: string;
  is_completed: boolean;
  subject_name: string;
  subject_id: number;
}

export interface Schedule {
  id: number;
  subject_id: number;
  subject_name: string;
  day_of_week: number;
  start_time: string;
  end_time: string;
  lesson_type: string;
  pair_number: number | null;
  teacher_name: string | null;
}

export interface Material {
  id: number;
  subject_id: number;
  material_type: string;
  title: string;
  description: string | null;
  ai_summary: string | null;
  scheduled_date: string | null;
  order_index: number;
}

export interface Note {
  id: number;
  note_type: string;
  raw_text: string;
  parsed_data: Record<string, unknown> | null;
  subject_id: number | null;
  subject_name: string | null;
  created_at: string;
}

export interface ReminderSettings {
  hours_before: number[];
  is_enabled: boolean;
}

// Teachers API
export const teachersApi = {
  getAll: () => api.get<Teacher[]>('/api/teachers'),
  create: (data: Partial<Teacher>) => api.post<Teacher>('/api/teachers', data),
  update: (id: number, data: Partial<Teacher>) => api.put<Teacher>(`/api/teachers/${id}`, data),
  delete: (id: number) => api.delete(`/api/teachers/${id}`),
};

// Subjects API
export const subjectsApi = {
  getAll: () => api.get<Subject[]>('/api/subjects'),
  create: (data: { name: string; description?: string }) => api.post<Subject>('/api/subjects', data),
  delete: (id: number) => api.delete(`/api/subjects/${id}`),
  linkTeacher: (subjectId: number, teacherId: number, role: string) =>
    api.post(`/api/subjects/${subjectId}/link-teacher`, { teacher_id: teacherId, role }),
  unlinkTeacher: (subjectId: number, teacherId: number) =>
    api.delete(`/api/subjects/${subjectId}/unlink-teacher/${teacherId}`),
  generateSummary: (subjectId: number) =>
    api.post<{ summary: string }>(`/api/subjects/${subjectId}/summary`),
};

// Deadlines API
export const deadlinesApi = {
  getAll: (showCompleted = false) =>
    api.get<Deadline[]>('/api/deadlines', { params: { show_completed: showCompleted } }),
  create: (data: { subject_id: number; title: string; work_type: string; description?: string; deadline_date: string }) =>
    api.post<Deadline>('/api/deadlines', data),
  update: (id: number, data: Partial<Deadline>) => api.put<Deadline>(`/api/deadlines/${id}`, data),
  delete: (id: number) => api.delete(`/api/deadlines/${id}`),
};

// Schedule API
export const scheduleApi = {
  getAll: (dayOfWeek?: number) =>
    api.get<Schedule[]>('/api/schedule', { params: dayOfWeek !== undefined ? { day_of_week: dayOfWeek } : {} }),
  create: (data: { subject_id: number; day_of_week: number; start_time: string; end_time: string; lesson_type: string; pair_number?: number }) =>
    api.post<Schedule>('/api/schedule', data),
  delete: (id: number) => api.delete(`/api/schedule/${id}`),
};

// Materials API
export const materialsApi = {
  getAll: (subjectId?: number, materialType?: string) =>
    api.get<Material[]>('/api/materials', { params: { subject_id: subjectId, material_type: materialType } }),
  create: (data: { subject_id: number; material_type: string; title: string; description?: string; content_text?: string; scheduled_date?: string }) =>
    api.post<Material>('/api/materials', data),
  delete: (id: number) => api.delete(`/api/materials/${id}`),
};

// Notes API
export const notesApi = {
  getAll: (noteType?: string, subjectId?: number) =>
    api.get<Note[]>('/api/notes', { params: { note_type: noteType, subject_id: subjectId } }),
};

// Semester upload API
export const semesterApi = {
  uploadText: (text: string) => api.post('/api/semester/upload-text', { text }),
  uploadFile: (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post('/api/semester/upload-file', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
};

// Settings API
export const settingsApi = {
  getReminders: () => api.get<ReminderSettings>('/api/settings/reminders'),
  updateReminders: (data: Partial<ReminderSettings>) => api.put<ReminderSettings>('/api/settings/reminders', data),
};

export default api;
