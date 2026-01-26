import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Получаем telegram_id из Telegram WebApp
const getTelegramId = (): number => {
  if (window.Telegram?.WebApp?.initDataUnsafe?.user?.id) {
    console.log('Telegram user ID:', window.Telegram.WebApp.initDataUnsafe.user.id);
    return window.Telegram.WebApp.initDataUnsafe.user.id;
  }
  // Fallback - твой реальный telegram_id
  console.log('Using fallback telegram_id');
  return 7167288809;
};

const api = axios.create({
  baseURL: API_URL,
});

// Добавляем telegram_id ко всем запросам
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
  temperament: string | null;
  preferences: string | null;
  notes: string | null;
  subject_name: string;
  subject_id: number;
}

export interface Deadline {
  id: number;
  title: string;
  work_type: string;
  description: string | null;
  deadline_date: string;
  is_completed: boolean;
  subject_name: string;
  subject_id: number;
}

export interface Subject {
  id: number;
  name: string;
}

export interface ReminderSettings {
  hours_before: number[];
  is_enabled: boolean;
}

// Teachers API
export const teachersApi = {
  getAll: () => api.get<Teacher[]>('/api/teachers'),
  get: (id: number) => api.get<Teacher>(`/api/teachers/${id}`),
  update: (id: number, data: Partial<Teacher>) =>
    api.put<Teacher>(`/api/teachers/${id}`, data),
  delete: (id: number) => api.delete(`/api/teachers/${id}`),
};

// Deadlines API
export const deadlinesApi = {
  getAll: (showCompleted = false) =>
    api.get<Deadline[]>('/api/deadlines', { params: { show_completed: showCompleted } }),
  create: (data: Omit<Deadline, 'id' | 'is_completed' | 'subject_name'>) =>
    api.post<Deadline>('/api/deadlines', data),
  update: (id: number, data: Partial<Deadline>) =>
    api.put<Deadline>(`/api/deadlines/${id}`, data),
  delete: (id: number) => api.delete(`/api/deadlines/${id}`),
};

// Subjects API
export const subjectsApi = {
  getAll: () => api.get<Subject[]>('/api/subjects'),
  create: (name: string) => api.post<Subject>('/api/subjects', { name }),
  delete: (id: number) => api.delete(`/api/subjects/${id}`),
};

// Settings API
export const settingsApi = {
  getReminders: () => api.get<ReminderSettings>('/api/settings/reminders'),
  updateReminders: (data: Partial<ReminderSettings>) =>
    api.put<ReminderSettings>('/api/settings/reminders', data),
};

export default api;
