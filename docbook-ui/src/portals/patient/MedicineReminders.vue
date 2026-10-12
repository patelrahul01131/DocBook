<script setup>
import { ref, onMounted, computed } from 'vue'
import { call } from '../../api'

const reminders = ref([])
const loading = ref(false)
const error = ref(null)
const activeFilter = ref('all')

const filters = [
  { key: 'all', label: 'All' },
  { key: 'Pending', label: '⏳ Upcoming' },
  { key: 'Sent', label: '✅ Sent' },
  { key: 'Failed', label: '❌ Failed' },
  { key: 'Cancelled', label: '🚫 Cancelled' },
]

const filtered = computed(() => {
  if (activeFilter.value === 'all') return reminders.value
  return reminders.value.filter(r => r.reminder_status === activeFilter.value)
})

const grouped = computed(() => {
  const g = {}
  for (const r of filtered.value) {
    const date = r.scheduled_at ? r.scheduled_at.split(' ')[0] : 'Unknown'
    if (!g[date]) g[date] = []
    g[date].push(r)
  }
  return g
})

const sortedDates = computed(() =>
  Object.keys(grouped.value).sort((a, b) => new Date(b) - new Date(a))
)

async function fetchReminders() {
  loading.value = true
  error.value = null
  try {
    const res = await call('docbook.api.reminder.get_my_reminders')
    reminders.value = Array.isArray(res) ? res : []
  } catch (e) {
    error.value = e.message || 'Unable to load reminders.'
  } finally {
    loading.value = false
  }
}

function formatGroupDate(d) {
  const date = new Date(`${d}T00:00:00`)
  const today = new Date()
  const tomorrow = new Date(today)
  tomorrow.setDate(today.getDate() + 1)

  const dateOnly = date.toDateString()
  if (dateOnly === today.toDateString()) return 'Today'
  if (dateOnly === tomorrow.toDateString()) return 'Tomorrow'

  return date.toLocaleDateString('en-IN', {
    weekday: 'long', day: 'numeric', month: 'short', year: 'numeric',
  })
}

function formatTime(dt) {
  if (!dt) return '—'
  const parts = dt.split(' ')
  if (parts.length < 2) return '—'
  const [h, m] = parts[1].split(':')
  const hNum = parseInt(h, 10)
  const ampm = hNum >= 12 ? 'PM' : 'AM'
  const h12 = hNum % 12 || 12
  return `${h12}:${m} ${ampm}`
}

function statusClass(s) {
  const cls = {
    Pending: 'db-badge db-badge--pending',
    Sent: 'db-badge db-badge--sent',
    Failed: 'db-badge db-badge--failed',
    Cancelled: 'db-badge db-badge--cancelled',
  }
  return cls[s] || 'db-badge db-badge--inactive'
}

function reminderCardClass(r) {
  const now = new Date()
  const sched = new Date(r.scheduled_at)
  if (r.reminder_status !== 'Pending') return ''
  if (sched <= now) return 'reminder-overdue'
  const diff = (sched - now) / 60000 // minutes
  if (diff <= 30) return 'reminder-soon'
  return ''
}

onMounted(fetchReminders)
</script>

<template>
  <div class="db-page">
    <div class="db-container">
      <!-- Header -->
      <header style="margin-bottom: 28px;">
        <div class="db-eyebrow">PATIENT PORTAL</div>
        <h1 class="db-page-title">Medicine Reminders</h1>
        <p class="db-section-subtitle">Automated email reminders for your scheduled medicines.</p>
      </header>

      <!-- Error -->
      <div v-if="error" class="db-error-panel" style="margin-bottom: 24px;">
        <span style="font-size: 18px; flex-shrink:0;">⚠️</span>
        <span>{{ error }}</span>
        <button class="db-btn db-btn--secondary" style="margin-left:auto" @click="fetchReminders">Retry</button>
      </div>

      <!-- Info banner -->
      <div class="info-banner">
        <span>🔔</span>
        <div>
          <strong>How reminders work:</strong>
          Reminders are scheduled automatically when your doctor prescribes medicines.
          You'll receive an email at each scheduled time. The server checks for due reminders every 15 minutes.
        </div>
      </div>

      <!-- Filter bar -->
      <div class="filter-bar">
        <button
          v-for="f in filters"
          :key="f.key"
          class="filter-btn"
          :class="{ active: activeFilter === f.key }"
          @click="activeFilter = f.key"
        >
          {{ f.label }}
          <span class="filter-count">
            {{ f.key === 'all' ? reminders.length : reminders.filter(r => r.reminder_status === f.key).length }}
          </span>
        </button>
      </div>

      <!-- Loading -->
      <div v-if="loading" class="reminder-list">
        <div v-for="i in 5" :key="i" class="reminder-skeleton">
          <div class="db-skeleton" style="height:12px; width:30%; margin-bottom:10px;"></div>
          <div class="db-skeleton" style="height:14px; width:55%; margin-bottom:8px;"></div>
          <div class="db-skeleton" style="height:11px; width:40%;"></div>
        </div>
      </div>

      <!-- Empty -->
      <div v-else-if="filtered.length === 0" class="db-empty">
        <div class="db-empty-icon" style="font-size:24px;">🔔</div>
        <h3>No reminders found</h3>
        <p>Reminders will appear here once your doctor prescribes medicines with a schedule.</p>
      </div>

      <!-- Grouped reminders -->
      <div v-else>
        <div v-for="date in sortedDates" :key="date" class="date-group">
          <div class="date-group-header">
            <span class="date-dot"></span>
            {{ formatGroupDate(date) }}
          </div>

          <div class="reminder-list">
            <div
              v-for="reminder in grouped[date]"
              :key="reminder.name"
              class="reminder-card"
              :class="reminderCardClass(reminder)"
            >
              <div class="reminder-time">{{ formatTime(reminder.scheduled_at) }}</div>

              <div class="reminder-content">
                <div class="reminder-med-name">
                  {{ reminder.prescribed_medicine_name || reminder.medicine_name || 'Medicine' }}
                </div>
                <div class="reminder-meta">
                  <span v-if="reminder.dosage">{{ reminder.dosage }}</span>
                  <span v-if="reminder.frequency">· {{ reminder.frequency }}</span>
                </div>
                <div v-if="reminder.instructions" class="reminder-instruction">
                  {{ reminder.instructions }}
                </div>
              </div>

              <div class="reminder-status">
                <span :class="statusClass(reminder.reminder_status)">{{ reminder.reminder_status }}</span>
                <div v-if="reminder.sent_at" class="reminder-sent-at">
                  Sent {{ formatTime(reminder.sent_at) }}
                </div>
                <div v-if="reminder.retry_count > 0 && reminder.reminder_status === 'Failed'" class="reminder-retry">
                  {{ reminder.retry_count }} retries
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.info-banner {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 14px 18px;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  border-radius: 10px;
  font-size: 13px;
  color: #1e40af;
  margin-bottom: 24px;
}

.info-banner span {
  font-size: 18px;
  flex-shrink: 0;
}

/* Filter bar */
.filter-bar {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin-bottom: 24px;
}

.filter-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  border-radius: 999px;
  border: 1px solid #e2e8f0;
  background: white;
  font-size: 12px;
  font-weight: 600;
  color: #64748b;
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s, color 0.15s;
}

.filter-btn:hover {
  background: #f0fdfa;
  border-color: #99f6e4;
  color: #0d9488;
}

.filter-btn.active {
  background: var(--db-primary);
  border-color: var(--db-primary);
  color: white;
}

.filter-count {
  background: rgba(255,255,255,0.25);
  border-radius: 999px;
  padding: 0 6px;
  font-size: 10px;
}

.filter-btn.active .filter-count {
  background: rgba(255,255,255,0.3);
}

/* Date group */
.date-group {
  margin-bottom: 28px;
}

.date-group-header {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 14px;
  font-weight: 700;
  color: #475569;
  margin-bottom: 12px;
}

.date-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--db-primary);
  flex-shrink: 0;
}

/* Reminder list */
.reminder-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.reminder-skeleton {
  padding: 16px;
  background: white;
  border-radius: 10px;
  border: 1px solid #e2e8f0;
}

.reminder-card {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  padding: 14px 18px;
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  transition: box-shadow 0.15s, border-color 0.15s;
}

.reminder-card:hover {
  box-shadow: 0 4px 12px rgba(15, 23, 42, 0.06);
}

.reminder-card.reminder-overdue {
  border-color: #fecaca;
  background: #fff5f5;
}

.reminder-card.reminder-soon {
  border-color: #fde68a;
  background: #fffbeb;
}

.reminder-time {
  min-width: 64px;
  font-size: 15px;
  font-weight: 800;
  color: #0d9488;
  font-variant-numeric: tabular-nums;
  flex-shrink: 0;
}

.reminder-content {
  flex: 1;
}

.reminder-med-name {
  font-size: 14px;
  font-weight: 700;
  color: #0f172a;
  margin-bottom: 3px;
}

.reminder-meta {
  font-size: 12px;
  color: #64748b;
  margin-bottom: 4px;
}

.reminder-instruction {
  font-size: 11px;
  color: #94a3b8;
  font-style: italic;
}

.reminder-status {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 5px;
  flex-shrink: 0;
}

.reminder-sent-at {
  font-size: 10px;
  color: #94a3b8;
}

.reminder-retry {
  font-size: 10px;
  color: #ef4444;
}

@media (max-width: 480px) {
  .reminder-card { flex-wrap: wrap; }
  .reminder-time { min-width: unset; }
}
</style>
