import { useEffect, useState } from 'react';
import { format, addDays, startOfWeek, isToday, parseISO, differenceInDays } from 'date-fns';
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

function SchedulePage() {
  const [schedule, setSchedule] = useState<ScheduleEntry[]>([]);
  const [deadlines, setDeadlines] = useState<Deadline[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedDay, setSelectedDay] = useState(new Date().getDay() === 0 ? 6 : new Date().getDay() - 1);
  const [weekType, setWeekType] = useState<'even' | 'odd'>(() => {
    const weekNum = Math.ceil((new Date().getTime() - new Date(new Date().getFullYear(), 0, 1).getTime()) / (7 * 24 * 60 * 60 * 1000));
    return weekNum % 2 === 0 ? 'even' : 'odd';
  });
  const [currentWeekStart, setCurrentWeekStart] = useState(() => startOfWeek(new Date(), { weekStartsOn: 1 }));

  const fetchData = async () => {
    try {
      const [scheduleRes, deadlinesRes] = await Promise.all([
        scheduleApi.getAll(undefined, weekType),
        deadlinesApi.getAll(false),
      ]);
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
  }, [weekType]);

  const weekDays = Array.from({ length: 7 }, (_, i) => addDays(currentWeekStart, i));
  const todaySchedule = schedule.filter((e) => e.day_of_week === selectedDay);
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

      {/* Week Type Toggle */}
      <div className="week-toggle">
        <button
          className={`week-toggle-btn ${weekType === 'odd' ? 'active' : ''}`}
          onClick={() => setWeekType('odd')}
        >
          Нечетная
        </button>
        <button
          className={`week-toggle-btn ${weekType === 'even' ? 'active' : ''}`}
          onClick={() => setWeekType('even')}
        >
          Четная
        </button>
      </div>

      {/* Week Day Selector */}
      <div className="day-selector">
        {weekDays.map((day, idx) => {
          const dayIdx = idx; // 0=Mon ... 6=Sun
          const hasClasses = schedule.some((e) => e.day_of_week === dayIdx);
          return (
            <button
              key={idx}
              className={`day-btn ${selectedDay === dayIdx ? 'active' : ''} ${isToday(day) ? 'today' : ''}`}
              onClick={() => {
                setSelectedDay(dayIdx);
                window.Telegram?.WebApp?.HapticFeedback?.selectionChanged();
              }}
            >
              <span className="day-btn-name">{DAY_NAMES[idx]}</span>
              <span className="day-btn-date">{format(day, 'd')}</span>
              {hasClasses && <span className="day-btn-dot"></span>}
            </button>
          );
        })}
      </div>

      {/* Day Title */}
      <div className="schedule-day-title">
        {DAY_NAMES_FULL[selectedDay]}, {format(weekDays[selectedDay], 'd MMMM', { locale: ru })}
      </div>

      {/* Schedule Cards */}
      {todaySchedule.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon">📅</div>
          <div className="empty-state-title">Нет занятий</div>
          <div className="empty-state-text">
            В этот день пар нет. Добавьте расписание через бота или в настройках.
          </div>
        </div>
      ) : (
        <div className="schedule-list">
          {todaySchedule
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
                    {entry.week_type !== 'both' && (
                      <span className="schedule-card-week">
                        {entry.week_type === 'even' ? 'чет.' : 'нечет.'}
                      </span>
                    )}
                  </div>
                  {entry.teacher_name && (
                    <div className="schedule-card-teacher">{entry.teacher_name}</div>
                  )}
                </div>
              </div>
            ))}
        </div>
      )}
    </div>
  );
}

export default SchedulePage;
