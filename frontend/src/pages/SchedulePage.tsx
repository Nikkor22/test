import { useEffect, useState } from 'react';
import {
  format,
  addDays,
  addWeeks,
  addMonths,
  startOfWeek,
  startOfMonth,
  isToday,
  isSameMonth,
  isSameDay,
  parseISO,
  differenceInDays,
  getWeek
} from 'date-fns';
import { ru } from 'date-fns/locale';
import { scheduleApi, deadlinesApi, ScheduleEntry, Deadline } from '../api/client';

const DAY_NAMES = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'];
const DAY_NAMES_FULL = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье'];

const CLASS_TYPE_LABELS: Record<string, string> = {
  lecture: 'Лекция',
  practice: 'Практика',
  lab: 'Лабораторная',
};

const CLASS_TYPE_COLORS: Record<string, string> = {
  lecture: '#7c3aed',
  practice: '#3b82f6',
  lab: '#22c55e',
};

type ViewMode = 'week' | 'month';

function SchedulePage() {
  const [schedule, setSchedule] = useState<ScheduleEntry[]>([]);
  const [deadlines, setDeadlines] = useState<Deadline[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedDate, setSelectedDate] = useState(new Date());
  const [currentMonth, setCurrentMonth] = useState(new Date());
  const [viewMode, setViewMode] = useState<ViewMode>('week');

  // Calculate week type based on selected date
  const getWeekType = (date: Date): 'even' | 'odd' => {
    const weekNum = getWeek(date, { weekStartsOn: 1 });
    return weekNum % 2 === 0 ? 'even' : 'odd';
  };

  const [weekType, setWeekType] = useState<'even' | 'odd'>(getWeekType(new Date()));

  const fetchData = async () => {
    try {
      const [scheduleRes, deadlinesRes] = await Promise.all([
        scheduleApi.getAll(),
        deadlinesApi.getAll(false),
      ]);
      console.log('[Schedule] Fetched entries:', scheduleRes.data.length);
      setSchedule(scheduleRes.data);
      setDeadlines(deadlinesRes.data);
    } catch (error) {
      console.error('Error fetching schedule:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  // Update week type when selected date changes
  useEffect(() => {
    setWeekType(getWeekType(selectedDate));
  }, [selectedDate]);

  // Get filtered schedule for current view
  const getScheduleForDate = (date: Date) => {
    const dayOfWeek = date.getDay() === 0 ? 6 : date.getDay() - 1; // Convert to Mon=0
    const dateWeekType = getWeekType(date);
    return schedule.filter(
      (e) => e.day_of_week === dayOfWeek &&
             (e.week_type === 'both' || e.week_type === dateWeekType)
    );
  };

  const selectedDaySchedule = getScheduleForDate(selectedDate);
  const selectedDayOfWeek = selectedDate.getDay() === 0 ? 6 : selectedDate.getDay() - 1;

  // Week navigation
  const currentWeekStart = startOfWeek(selectedDate, { weekStartsOn: 1 });
  const weekDays = Array.from({ length: 7 }, (_, i) => addDays(currentWeekStart, i));

  const goToPrevWeek = () => {
    const newDate = addWeeks(selectedDate, -1);
    setSelectedDate(newDate);
    setCurrentMonth(newDate);
  };

  const goToNextWeek = () => {
    const newDate = addWeeks(selectedDate, 1);
    setSelectedDate(newDate);
    setCurrentMonth(newDate);
  };

  // Month navigation
  const goToPrevMonth = () => {
    setCurrentMonth(addMonths(currentMonth, -1));
  };

  const goToNextMonth = () => {
    setCurrentMonth(addMonths(currentMonth, 1));
  };

  const goToToday = () => {
    const today = new Date();
    setSelectedDate(today);
    setCurrentMonth(today);
  };

  // Generate month calendar days
  const getMonthDays = () => {
    const monthStart = startOfMonth(currentMonth);
    const startDate = startOfWeek(monthStart, { weekStartsOn: 1 });

    const days = [];
    let day = startDate;

    // Generate 6 weeks of days
    for (let i = 0; i < 42; i++) {
      days.push(day);
      day = addDays(day, 1);
    }

    return days;
  };

  // Check if date has classes
  const hasClasses = (date: Date) => {
    return getScheduleForDate(date).length > 0;
  };

  // Check if date has deadline
  const hasDeadline = (date: Date) => {
    return deadlines.some(d => isSameDay(parseISO(d.deadline_date), date));
  };

  const upcomingDeadlines = deadlines
    .filter((d) => !d.is_completed)
    .sort((a, b) => new Date(a.deadline_date).getTime() - new Date(b.deadline_date).getTime())
    .slice(0, 5);

  if (loading) {
    return (
      <div className="loading">
        <div className="spinner"></div>
      </div>
    );
  }

  return (
    <div>
      {/* Deadline Feed */}
      {upcomingDeadlines.length > 0 && (
        <div className="deadline-feed">
          <div className="deadline-feed-title">Ближайшие дедлайны</div>
          <div className="deadline-feed-scroll">
            {upcomingDeadlines.map((deadline) => {
              const daysLeft = differenceInDays(parseISO(deadline.deadline_date), new Date());
              const urgencyClass = daysLeft <= 1 ? 'urgent' : daysLeft <= 3 ? 'warning' : 'ok';
              return (
                <div key={deadline.id} className={`deadline-chip ${urgencyClass}`}>
                  <div className="deadline-chip-title">{deadline.title}</div>
                  <div className="deadline-chip-meta">
                    {deadline.subject_name} — {daysLeft <= 0 ? 'Сегодня!' : `${daysLeft} дн.`}
                  </div>
                  {deadline.gpt_description && (
                    <div className="deadline-chip-desc">{deadline.gpt_description.slice(0, 60)}...</div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* View Mode Toggle */}
      <div className="view-toggle">
        <button
          className={`view-toggle-btn ${viewMode === 'week' ? 'active' : ''}`}
          onClick={() => setViewMode('week')}
        >
          Неделя
        </button>
        <button
          className={`view-toggle-btn ${viewMode === 'month' ? 'active' : ''}`}
          onClick={() => setViewMode('month')}
        >
          Месяц
        </button>
        <button className="today-btn" onClick={goToToday}>
          Сегодня
        </button>
      </div>

      {viewMode === 'week' ? (
        <>
          {/* Week Navigation */}
          <div className="calendar-nav">
            <button className="nav-btn" onClick={goToPrevWeek}>
              ←
            </button>
            <span className="nav-title">
              {format(currentWeekStart, 'd MMM', { locale: ru })} — {format(addDays(currentWeekStart, 6), 'd MMM yyyy', { locale: ru })}
            </span>
            <button className="nav-btn" onClick={goToNextWeek}>
              →
            </button>
          </div>

          {/* Week Type Indicator */}
          <div className="week-indicator">
            {weekType === 'even' ? 'Чётная неделя' : 'Нечётная неделя'}
          </div>

          {/* Week Day Selector */}
          <div className="day-selector">
            {weekDays.map((day, idx) => {
              const dayHasClasses = hasClasses(day);
              const dayHasDeadline = hasDeadline(day);
              return (
                <button
                  key={idx}
                  className={`day-btn ${isSameDay(selectedDate, day) ? 'active' : ''} ${isToday(day) ? 'today' : ''}`}
                  onClick={() => {
                    setSelectedDate(day);
                    window.Telegram?.WebApp?.HapticFeedback?.selectionChanged();
                  }}
                >
                  <span className="day-btn-name">{DAY_NAMES[idx]}</span>
                  <span className="day-btn-date">{format(day, 'd')}</span>
                  <div className="day-btn-dots">
                    {dayHasClasses && <span className="day-btn-dot classes"></span>}
                    {dayHasDeadline && <span className="day-btn-dot deadline"></span>}
                  </div>
                </button>
              );
            })}
          </div>
        </>
      ) : (
        <>
          {/* Month Navigation */}
          <div className="calendar-nav">
            <button className="nav-btn" onClick={goToPrevMonth}>
              ←
            </button>
            <span className="nav-title">
              {format(currentMonth, 'LLLL yyyy', { locale: ru })}
            </span>
            <button className="nav-btn" onClick={goToNextMonth}>
              →
            </button>
          </div>

          {/* Month Calendar Grid */}
          <div className="month-calendar">
            <div className="month-header">
              {DAY_NAMES.map((name) => (
                <div key={name} className="month-header-cell">{name}</div>
              ))}
            </div>
            <div className="month-grid">
              {getMonthDays().map((day, idx) => {
                const dayHasClasses = hasClasses(day);
                const dayHasDeadline = hasDeadline(day);
                const isCurrentMonth = isSameMonth(day, currentMonth);
                return (
                  <button
                    key={idx}
                    className={`month-day ${isSameDay(selectedDate, day) ? 'active' : ''} ${isToday(day) ? 'today' : ''} ${!isCurrentMonth ? 'other-month' : ''}`}
                    onClick={() => {
                      setSelectedDate(day);
                      window.Telegram?.WebApp?.HapticFeedback?.selectionChanged();
                    }}
                  >
                    <span className="month-day-num">{format(day, 'd')}</span>
                    <div className="month-day-dots">
                      {dayHasClasses && <span className="month-day-dot classes"></span>}
                      {dayHasDeadline && <span className="month-day-dot deadline"></span>}
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        </>
      )}

      {/* Day Title */}
      <div className="schedule-day-title">
        {DAY_NAMES_FULL[selectedDayOfWeek]}, {format(selectedDate, 'd MMMM yyyy', { locale: ru })}
        <span className="schedule-day-week">
          ({getWeekType(selectedDate) === 'even' ? 'чёт.' : 'нечёт.'} неделя)
        </span>
      </div>

      {/* Schedule Cards */}
      {selectedDaySchedule.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon">📅</div>
          <div className="empty-state-title">Нет занятий</div>
          <div className="empty-state-text">
            {schedule.length === 0
              ? 'Расписание не загружено. Используй /schedule_url и /sync в боте для синхронизации.'
              : 'В этот день пар нет.'}
          </div>
        </div>
      ) : (
        <div className="schedule-list">
          {selectedDaySchedule
            .sort((a, b) => a.start_time.localeCompare(b.start_time))
            .map((entry) => (
              <div key={entry.id} className="schedule-card">
                <div
                  className="schedule-card-indicator"
                  style={{ backgroundColor: CLASS_TYPE_COLORS[entry.class_type] || '#7c3aed' }}
                />
                <div className="schedule-card-time">
                  <div className="schedule-card-start">{entry.start_time}</div>
                  <div className="schedule-card-end">{entry.end_time}</div>
                </div>
                <div className="schedule-card-content">
                  <div className="schedule-card-subject">{entry.subject_name}</div>
                  <div className="schedule-card-details">
                    <span className="schedule-card-type">
                      {CLASS_TYPE_LABELS[entry.class_type] || entry.class_type}
                    </span>
                    {entry.room && <span className="schedule-card-room">ауд. {entry.room}</span>}
                  </div>
                  {entry.teacher_name && (
                    <div className="schedule-card-teacher">{entry.teacher_name}</div>
                  )}
                </div>
              </div>
            ))}
        </div>
      )}

      {/* Deadlines for selected day */}
      {deadlines.filter(d => isSameDay(parseISO(d.deadline_date), selectedDate)).length > 0 && (
        <div className="day-deadlines">
          <div className="day-deadlines-title">📌 Дедлайны в этот день</div>
          {deadlines
            .filter(d => isSameDay(parseISO(d.deadline_date), selectedDate))
            .map(deadline => (
              <div key={deadline.id} className={`day-deadline-card ${deadline.is_completed ? 'completed' : ''}`}>
                <div className="day-deadline-title">{deadline.title}</div>
                <div className="day-deadline-meta">
                  {deadline.subject_name} — {deadline.work_type}
                </div>
              </div>
            ))}
        </div>
      )}
    </div>
  );
}

export default SchedulePage;
