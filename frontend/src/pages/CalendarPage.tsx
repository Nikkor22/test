import { useState, useEffect, useMemo } from 'react';
import { format, addMonths, subMonths, startOfMonth, endOfMonth, startOfWeek, endOfWeek, eachDayOfInterval, isSameMonth, isSameDay, isToday } from 'date-fns';
import { ru } from 'date-fns/locale';
import { scheduleApi, deadlinesApi, Schedule, Deadline } from '../api/client';

const DAYS = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'];
const LESSON_TYPES: Record<string, string> = {
  lecture: 'Лекция',
  practice: 'Практика',
  lab: 'Лабораторная',
};

export default function CalendarPage() {
  const [currentMonth, setCurrentMonth] = useState(new Date());
  const [selectedDate, setSelectedDate] = useState(new Date());
  const [schedule, setSchedule] = useState<Schedule[]>([]);
  const [deadlines, setDeadlines] = useState<Deadline[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [scheduleRes, deadlinesRes] = await Promise.all([
        scheduleApi.getAll(),
        deadlinesApi.getAll(false),
      ]);
      setSchedule(scheduleRes.data);
      setDeadlines(deadlinesRes.data);
    } catch (error) {
      console.error('Error loading data:', error);
    } finally {
      setLoading(false);
    }
  };

  // Генерируем дни календаря
  const calendarDays = useMemo(() => {
    const monthStart = startOfMonth(currentMonth);
    const monthEnd = endOfMonth(monthStart);
    const startDate = startOfWeek(monthStart, { weekStartsOn: 1 });
    const endDate = endOfWeek(monthEnd, { weekStartsOn: 1 });
    return eachDayOfInterval({ start: startDate, end: endDate });
  }, [currentMonth]);

  // Даты с дедлайнами
  const deadlineDates = useMemo(() => {
    const dates = new Set<string>();
    deadlines.forEach((d) => {
      dates.add(format(new Date(d.deadline_date), 'yyyy-MM-dd'));
    });
    return dates;
  }, [deadlines]);

  // Даты с занятиями
  const scheduleDates = useMemo(() => {
    const dates = new Set<string>();
    // Для повторяющегося расписания проверяем день недели
    calendarDays.forEach((day) => {
      const dayOfWeek = (day.getDay() + 6) % 7; // Конвертируем в 0=Пн формат
      if (schedule.some((s) => s.day_of_week === dayOfWeek)) {
        dates.add(format(day, 'yyyy-MM-dd'));
      }
    });
    return dates;
  }, [schedule, calendarDays]);

  // Занятия на выбранный день
  const selectedDaySchedule = useMemo(() => {
    const dayOfWeek = (selectedDate.getDay() + 6) % 7;
    return schedule
      .filter((s) => s.day_of_week === dayOfWeek)
      .sort((a, b) => a.start_time.localeCompare(b.start_time));
  }, [schedule, selectedDate]);

  // Дедлайны на выбранный день и ближайшие
  const selectedDayDeadlines = useMemo(() => {
    const dateStr = format(selectedDate, 'yyyy-MM-dd');
    return deadlines.filter((d) => {
      const deadlineDate = format(new Date(d.deadline_date), 'yyyy-MM-dd');
      return deadlineDate === dateStr;
    });
  }, [deadlines, selectedDate]);

  const upcomingDeadlines = useMemo(() => {
    const now = new Date();
    return deadlines
      .filter((d) => new Date(d.deadline_date) >= now)
      .sort((a, b) => new Date(a.deadline_date).getTime() - new Date(b.deadline_date).getTime())
      .slice(0, 5);
  }, [deadlines]);

  const prevMonth = () => setCurrentMonth(subMonths(currentMonth, 1));
  const nextMonth = () => setCurrentMonth(addMonths(currentMonth, 1));

  const getDaysLeft = (dateStr: string) => {
    const diff = Math.ceil((new Date(dateStr).getTime() - new Date().getTime()) / (1000 * 60 * 60 * 24));
    if (diff < 0) return 'просрочено';
    if (diff === 0) return 'сегодня';
    if (diff === 1) return 'завтра';
    return `${diff} дн.`;
  };

  const getDeadlineClass = (dateStr: string) => {
    const diff = Math.ceil((new Date(dateStr).getTime() - new Date().getTime()) / (1000 * 60 * 60 * 24));
    if (diff < 0) return 'urgent';
    if (diff <= 2) return 'urgent';
    if (diff <= 7) return 'warning';
    return 'ok';
  };

  if (loading) {
    return (
      <div className="loading">
        <div className="spinner" />
      </div>
    );
  }

  return (
    <div className="calendar-page">
      {/* Календарь */}
      <div className="calendar-container card">
        <div className="calendar-header">
          <button className="btn btn-icon btn-secondary" onClick={prevMonth}>
            ‹
          </button>
          <span className="calendar-month">
            {format(currentMonth, 'LLLL yyyy', { locale: ru })}
          </span>
          <button className="btn btn-icon btn-secondary" onClick={nextMonth}>
            ›
          </button>
        </div>

        <div className="calendar-grid">
          {DAYS.map((day) => (
            <div key={day} className="calendar-day-header">
              {day}
            </div>
          ))}

          {calendarDays.map((day) => {
            const dateStr = format(day, 'yyyy-MM-dd');
            const hasDeadline = deadlineDates.has(dateStr);
            const hasSchedule = scheduleDates.has(dateStr);
            const isSelected = isSameDay(day, selectedDate);

            return (
              <div
                key={dateStr}
                className={`calendar-day ${!isSameMonth(day, currentMonth) ? 'other-month' : ''} ${isToday(day) ? 'today' : ''} ${isSelected ? 'selected' : ''}`}
                onClick={() => setSelectedDate(day)}
              >
                <span className="calendar-day-number">{format(day, 'd')}</span>
                <div className="calendar-day-dots">
                  {hasSchedule && <span className="dot dot-schedule" />}
                  {hasDeadline && <span className="dot dot-deadline" />}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Расписание на выбранный день */}
      <div className="day-details">
        <h3 className="section-title">
          {format(selectedDate, 'd MMMM, EEEE', { locale: ru })}
        </h3>

        {selectedDaySchedule.length > 0 && (
          <div className="schedule-list">
            {selectedDaySchedule.map((item) => (
              <div key={item.id} className="schedule-item card">
                <div className="schedule-item-header">
                  <span className="schedule-subject">{item.subject_name}</span>
                  <span className="tag tag-type">{LESSON_TYPES[item.lesson_type] || item.lesson_type}</span>
                </div>
                <div className="schedule-item-time">
                  <span className="time-icon">🕐</span>
                  {item.start_time} - {item.end_time}
                  {item.pair_number && <span className="pair-number">{item.pair_number} пара</span>}
                </div>
                {item.teacher_name && (
                  <div className="schedule-item-teacher">
                    <span className="teacher-icon">👤</span>
                    {item.teacher_name}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {selectedDayDeadlines.length > 0 && (
          <div className="deadlines-list">
            <h4 className="subsection-title">Дедлайны в этот день</h4>
            {selectedDayDeadlines.map((d) => (
              <div key={d.id} className="deadline-item card">
                <div className="deadline-item-header">
                  <span className="deadline-title">{d.title}</span>
                  <span className={`tag tag-deadline ${getDeadlineClass(d.deadline_date)}`}>
                    {d.work_type}
                  </span>
                </div>
                <div className="deadline-item-subject">{d.subject_name}</div>
                <div className="deadline-item-time">
                  {format(new Date(d.deadline_date), 'HH:mm')}
                </div>
                {d.ai_hint && (
                  <div className="deadline-ai-hint">
                    <span className="hint-icon">💡</span>
                    {d.ai_hint}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {selectedDaySchedule.length === 0 && selectedDayDeadlines.length === 0 && (
          <div className="empty-state-mini">
            <span>Нет занятий и дедлайнов</span>
          </div>
        )}
      </div>

      {/* Ближайшие дедлайны */}
      {upcomingDeadlines.length > 0 && (
        <div className="upcoming-section">
          <h3 className="section-title">Ближайшие дедлайны</h3>
          {upcomingDeadlines.map((d) => (
            <div key={d.id} className="upcoming-item card">
              <div className="upcoming-item-main">
                <div className="upcoming-item-info">
                  <span className="upcoming-title">{d.title}</span>
                  <span className="upcoming-subject">{d.subject_name}</span>
                </div>
                <div className="upcoming-item-date">
                  <span className={`tag tag-deadline ${getDeadlineClass(d.deadline_date)}`}>
                    {getDaysLeft(d.deadline_date)}
                  </span>
                </div>
              </div>
              {d.ai_hint && (
                <div className="upcoming-hint">
                  <span className="hint-icon">💡</span>
                  {d.ai_hint}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
