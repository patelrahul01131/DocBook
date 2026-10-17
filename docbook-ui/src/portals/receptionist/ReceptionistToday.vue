<script setup>
import { ref, onMounted, computed, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { call } from '../../api'

const router = useRouter()

const todayStr = new Date().toISOString().slice(0, 10)
const selectedDate = ref(todayStr)
const appointments = ref([])
const doctors = ref([])
const selectedDoctor = ref('')
const activeStage = ref('all')
const searchQuery = ref('')
const onlyFastTrack = ref(false)

const loading = ref(true)
const refreshing = ref(false)
const error = ref(null)
const actionBusy = ref(null)

let pollTimer = null

const stats = computed(() => {
  const all = appointments.value
  const checkedIn = all.filter(a => a.checked_in)
  const waiting = all.filter(a => a.visit_stage === 'Waiting')
  const inConsult = all.filter(a => a.visit_stage === 'In Consultation')
  const completed = all.filter(a => a.status === 'Completed' || a.visit_stage === 'Completed')
  const pendingCheckin = all.filter(a => !a.checked_in && a.status !== 'Completed' && a.status !== 'Cancelled')
  return {
    total: all.length,
    checkedIn: checkedIn.length,
    waiting: waiting.length,
    inConsult: inConsult.length,
    completed: completed.length,
    pendingCheckin: pendingCheckin.length,
  }
})

const filteredAppointments = computed(() => {
  let list = appointments.value

  // Doctor filter
  if (selectedDoctor.value) {
    list = list.filter(a => a.doctor === selectedDoctor.value || (a.doctor_name || '').toLowerCase() === selectedDoctor.value.toLowerCase())
  }

  // Fast track filter
  if (onlyFastTrack.value) {
    list = list.filter(a => a.fast_track || a.priority)
  }

  // Stage tab filter
  if (activeStage.value === 'waiting') {
    list = list.filter(a => a.checked_in && a.visit_stage === 'Waiting')
  } else if (activeStage.value === 'in_consultation') {
    list = list.filter(a => a.visit_stage === 'In Consultation')
  } else if (activeStage.value === 'pending_checkin') {
    list = list.filter(a => !a.checked_in && a.status !== 'Completed' && a.status !== 'Cancelled')
  } else if (activeStage.value === 'completed') {
    list = list.filter(a => a.status === 'Completed' || a.visit_stage === 'Completed')
  }

  // Search filter
  const q = searchQuery.value.trim().toLowerCase()
  if (q) {
    list = list.filter(a =>
      (a.patient_name || a.patient || '').toLowerCase().includes(q) ||
      (a.patient_phone || '').includes(q) ||
      (a.name || '').toLowerCase().includes(q) ||
      (a.doctor_name || '').toLowerCase().includes(q) ||
      (a.reason || '').toLowerCase().includes(q) ||
      String(a.queue_token || '').includes(q)
    )
  }

  return list
})

async function fetchTodayData(isQuiet = false) {
  if (!isQuiet) loading.value = true
  else refreshing.value = true
  error.value = null

  try {
    const res = await call('docbook.api.queue.get_receptionist_dashboard', {
      date: selectedDate.value,
    })
    appointments.value = Array.isArray(res?.appointments) ? res.appointments : []
    doctors.value = Array.isArray(res?.per_doctor) ? res.per_doctor : []
  } catch (err) {
    if (!isQuiet) {
      error.value = err.message || 'Failed to load today’s appointments.'
    }
  } finally {
    loading.value = false
    refreshing.value = false
  }
}

async function quickCheckIn(appt) {
  actionBusy.value = appt.name
  try {
    await call('docbook.api.queue.check_in_patient', { appointment: appt.name })
    await fetchTodayData(true)
  } catch (err) {
    alert(err.message || 'Check-in failed')
  } finally {
    actionBusy.value = null
  }
}

async function revertCheckIn(appt) {
  if (!confirm(`Revert check-in for ${appt.patient_name || appt.patient}? Token #${appt.queue_token} will be cleared.`)) return
  actionBusy.value = appt.name
  try {
    await call('docbook.api.queue.revert_check_in', { appointment: appt.name })
    await fetchTodayData(true)
  } catch (err) {
    alert(err.message || 'Revert failed')
  } finally {
    actionBusy.value = null
  }
}

function formatDate(d) {
  if (!d) return ''
  try {
    return new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
  } catch {
    return d
  }
}

function formatTime(t) {
  if (!t) return ''
  const parts = String(t).split(':')
  if (parts.length >= 2) {
    let h = parseInt(parts[0], 10)
    const m = parts[1]
    const ampm = h >= 12 ? 'PM' : 'AM'
    h = h % 12 || 12
    return `${h}:${m} ${ampm}`
  }
  return t
}

onMounted(() => {
  fetchTodayData()
  pollTimer = setInterval(() => {
    fetchTodayData(true)
  }, 20000)
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})
</script>

<template>
  <main class="rec-today-page">
    <div class="rec-shell">

      <!-- Header -->
      <header class="rec-header">
        <div>
          <div class="rec-eyebrow">
            <span class="icon-calendar"></span>
            RECEPTIONIST PORTAL
          </div>
          <h1>Today's Patient Schedule<span>.</span></h1>
          <p class="rec-sub">
            Patients booked for today ({{ formatDate(selectedDate) }}) — manage arrivals, filters, and desk check-ins.
          </p>
        </div>

        <div class="rec-actions">
          <button class="btn-primary" @click="router.push('/receptionist/checkin')">
            📷 Open Check-in Kiosk
          </button>
          <button class="btn-secondary" :disabled="loading || refreshing" @click="fetchTodayData(true)">
            {{ refreshing ? 'Refreshing…' : '↻ Refresh' }}
          </button>
        </div>
      </header>

      <!-- Stat Badges Strip -->
      <section class="stat-strip">
        <div class="stat-pill" :class="{ active: activeStage === 'all' }" @click="activeStage = 'all'">
          <span class="pill-label">Total Today</span>
          <strong class="pill-val">{{ stats.total }}</strong>
        </div>
        <div class="stat-pill stat-pill--pending" :class="{ active: activeStage === 'pending_checkin' }" @click="activeStage = 'pending_checkin'">
          <span class="pill-label">Expected / Pending Check-in</span>
          <strong class="pill-val">{{ stats.pendingCheckin }}</strong>
        </div>
        <div class="stat-pill stat-pill--waiting" :class="{ active: activeStage === 'waiting' }" @click="activeStage = 'waiting'">
          <span class="pill-label">Waiting in Queue</span>
          <strong class="pill-val">{{ stats.waiting }}</strong>
        </div>
        <div class="stat-pill stat-pill--consult" :class="{ active: activeStage === 'in_consultation' }" @click="activeStage = 'in_consultation'">
          <span class="pill-label">In Consultation</span>
          <strong class="pill-val">{{ stats.inConsult }}</strong>
        </div>
        <div class="stat-pill stat-pill--done" :class="{ active: activeStage === 'completed' }" @click="activeStage = 'completed'">
          <span class="pill-label">Completed</span>
          <strong class="pill-val">{{ stats.completed }}</strong>
        </div>
      </section>

      <!-- Filter Controls Bar -->
      <section class="filters-card">
        <div class="search-input-wrap">
          <span class="search-icon">🔍</span>
          <input
            v-model="searchQuery"
            type="text"
            class="filter-input"
            placeholder="Search patient name, phone, appointment #, doctor..."
          />
          <button v-if="searchQuery" class="clear-btn" @click="searchQuery = ''">✕</button>
        </div>

        <div class="dropdown-filter-wrap">
          <label class="filter-label">Doctor:</label>
          <select v-model="selectedDoctor" class="filter-select">
            <option value="">All Doctors ({{ doctors.length }})</option>
            <option v-for="d in doctors" :key="d.doctor" :value="d.doctor">
              Dr. {{ d.doctor_name || d.doctor }} ({{ d.count || 0 }})
            </option>
          </select>
        </div>

        <div class="date-filter-wrap">
          <label class="filter-label">Date:</label>
          <input v-model="selectedDate" type="date" class="filter-date" @change="fetchTodayData(false)" />
        </div>

        <label class="fast-track-toggle">
          <input v-model="onlyFastTrack" type="checkbox" />
          <span>⚡ Fast Track / Priority only</span>
        </label>
      </section>

      <!-- Error banner -->
      <div v-if="error" class="error-banner">
        <span>⚠️</span>
        <div class="flex-1">{{ error }}</div>
        <button class="btn-retry" @click="fetchTodayData(false)">Retry</button>
      </div>

      <!-- Loading skeleton -->
      <div v-if="loading" class="table-skeleton">
        <div v-for="i in 5" :key="i" class="skeleton-row"></div>
      </div>

      <!-- Empty State -->
      <div v-else-if="!filteredAppointments.length" class="empty-card">
        <div class="empty-icon">📋</div>
        <h3>No Patients Found</h3>
        <p v-if="searchQuery || selectedDoctor || onlyFastTrack">
          No patients matched your current filter criteria.
        </p>
        <p v-else>
          No appointments scheduled for {{ formatDate(selectedDate) }}.
        </p>
        <button
          v-if="searchQuery || selectedDoctor || onlyFastTrack"
          class="btn-secondary"
          @click="searchQuery = ''; selectedDoctor = ''; onlyFastTrack = false; activeStage = 'all'"
        >
          Reset Filters
        </button>
      </div>

      <!-- Patients List / Table -->
      <div v-else class="table-card">
        <table class="rec-table">
          <thead>
            <tr>
              <th>Token / Stage</th>
              <th>Patient</th>
              <th>Doctor</th>
              <th>Time</th>
              <th>Reason / Symptoms</th>
              <th>Check-in Status</th>
              <th style="text-align: right;">Action</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="appt in filteredAppointments"
              :key="appt.name"
              :class="{
                'row-in-consult': appt.visit_stage === 'In Consultation',
                'row-waiting': appt.visit_stage === 'Waiting',
                'row-done': appt.status === 'Completed',
              }"
            >
              <!-- Token / Stage -->
              <td>
                <div class="token-cell">
                  <span v-if="appt.queue_token" class="token-tag">#{{ appt.queue_token }}</span>
                  <span v-else class="token-none">—</span>
                  <span
                    class="stage-pill"
                    :class="`stage-${(appt.visit_stage || appt.status || 'pending').toLowerCase().replace(/\s+/g, '-')}`"
                  >
                    {{ appt.visit_stage || appt.status || 'Pending' }}
                  </span>
                </div>
              </td>

              <!-- Patient info -->
              <td>
                <div class="patient-cell">
                  <div class="patient-name">
                    {{ appt.patient_name || appt.patient || 'Unknown' }}
                    <span v-if="appt.fast_track" class="tag-fast" title="Fast Track / Emergency">⚡ Fast Track</span>
                    <span v-else-if="appt.priority" class="tag-priority" title="Priority Return">Priority</span>
                  </div>
                  <div class="patient-meta">
                    <span v-if="appt.age">{{ appt.age }}y</span>
                    <span v-if="appt.gender"> · {{ appt.gender }}</span>
                    <span v-if="appt.patient_phone"> · 📞 {{ appt.patient_phone }}</span>
                  </div>
                  <div class="patient-id text-xs text-slate-400">#{{ appt.name }}</div>
                </div>
              </td>

              <!-- Doctor info -->
              <td>
                <div class="doctor-cell">
                  <div class="doc-name">Dr. {{ appt.doctor_name || appt.doctor }}</div>
                  <div v-if="appt.doctor_specialty" class="doc-spec">{{ appt.doctor_specialty }}</div>
                </div>
              </td>

              <!-- Time -->
              <td>
                <div class="time-cell">
                  <strong>{{ formatTime(appt.appointment_time) }}</strong>
                </div>
              </td>

              <!-- Reason / Symptoms -->
              <td>
                <div class="clinical-preview">
                  <div v-if="appt.symptoms" class="symptom-text"><strong>Symptoms:</strong> {{ appt.symptoms }}</div>
                  <div v-if="appt.reason" class="reason-text"><strong>Reason:</strong> {{ appt.reason }}</div>
                  <div v-if="!appt.symptoms && !appt.reason" class="text-slate-400 text-xs">General consultation</div>
                </div>
              </td>

              <!-- Check-in status -->
              <td>
                <div v-if="appt.checked_in" class="status-checked-in">
                  <span class="ok-dot">●</span>
                  <span>Checked In</span>
                  <span v-if="appt.checked_in_at" class="checkin-time text-xs text-slate-400">
                    {{ formatTime(appt.checked_in_at) }}
                  </span>
                </div>
                <div v-else class="status-not-checked">
                  <span class="dim-dot">○</span>
                  <span>Not Checked In</span>
                </div>
              </td>

              <!-- Actions -->
              <td style="text-align: right;">
                <div class="actions-group">
                  <!-- Check-in button -->
                  <button
                    v-if="!appt.checked_in && appt.status !== 'Completed' && appt.status !== 'Cancelled'"
                    class="btn-table-checkin"
                    :disabled="actionBusy === appt.name"
                    @click="quickCheckIn(appt)"
                  >
                    ✓ Check In
                  </button>

                  <button
                    v-else-if="appt.checked_in && appt.visit_stage !== 'In Consultation' && appt.status !== 'Completed'"
                    class="btn-table-revert"
                    :disabled="actionBusy === appt.name"
                    title="Undo Check-in"
                    @click="revertCheckIn(appt)"
                  >
                    Undo
                  </button>

                  <button
                    class="btn-table-history"
                    title="View Patient Records & History"
                    @click="router.push(`/receptionist/patients?search=${encodeURIComponent(appt.patient_name || appt.patient)}`)"
                  >
                    History
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

    </div>
  </main>
</template>

<style scoped>
.rec-today-page {
  min-height: 100vh;
  background: #f8fafc;
  padding: 32px 24px;
  color: #0f172a;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}
.rec-shell {
  max-width: 1300px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 20px;
}
.rec-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  flex-wrap: wrap;
  gap: 16px;
}
.rec-eyebrow {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.08em;
  color: #059669;
  text-transform: uppercase;
  margin-bottom: 4px;
}
.rec-header h1 {
  font-size: 30px;
  font-weight: 800;
  color: #0f172a;
  margin: 0;
  letter-spacing: -0.02em;
}
.rec-header h1 span { color: #059669; }
.rec-sub {
  color: #64748b;
  font-size: 14px;
  margin: 6px 0 0;
}
.rec-actions {
  display: flex;
  gap: 10px;
}
.btn-primary {
  background: #059669;
  color: #ffffff;
  border: none;
  border-radius: 10px;
  padding: 10px 18px;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.2s;
  box-shadow: 0 2px 6px rgba(5,150,105,0.25);
}
.btn-primary:hover { background: #047857; }
.btn-secondary {
  background: #ffffff;
  color: #334155;
  border: 1px solid #cbd5e1;
  border-radius: 10px;
  padding: 10px 16px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
}
.btn-secondary:hover { background: #f1f5f9; }

/* Stat Strip */
.stat-strip {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 12px;
}
.stat-pill {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  cursor: pointer;
  transition: all 0.2s;
}
.stat-pill:hover { border-color: #cbd5e1; transform: translateY(-1px); }
.stat-pill.active {
  border-color: #059669;
  box-shadow: 0 0 0 2px rgba(5,150,105,0.15);
}
.pill-label { font-size: 12px; font-weight: 600; color: #64748b; }
.pill-val { font-size: 24px; font-weight: 800; color: #0f172a; }
.stat-pill--waiting .pill-val { color: #d97706; }
.stat-pill--consult .pill-val { color: #2563eb; }
.stat-pill--done .pill-val { color: #059669; }
.stat-pill--pending .pill-val { color: #64748b; }

/* Filter Controls */
.filters-card {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  padding: 14px 18px;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 14px;
}
.search-input-wrap {
  flex: 1;
  min-width: 260px;
  display: flex;
  align-items: center;
  background: #f8fafc;
  border: 1px solid #cbd5e1;
  border-radius: 10px;
  padding: 8px 12px;
  gap: 8px;
}
.search-icon { font-size: 14px; color: #94a3b8; }
.filter-input {
  border: none;
  background: transparent;
  outline: none;
  width: 100%;
  font-size: 14px;
  color: #0f172a;
}
.clear-btn { background: none; border: none; color: #94a3b8; cursor: pointer; font-size: 12px; }
.dropdown-filter-wrap, .date-filter-wrap {
  display: flex;
  align-items: center;
  gap: 8px;
}
.filter-label { font-size: 13px; font-weight: 600; color: #475569; }
.filter-select, .filter-date {
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  padding: 7px 10px;
  font-size: 13px;
  color: #0f172a;
  background: #ffffff;
  outline: none;
}
.fast-track-toggle {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
  color: #b45309;
  cursor: pointer;
  margin-left: auto;
}

/* Table */
.table-card {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 2px 10px rgba(0,0,0,0.03);
}
.rec-table {
  width: 100%;
  border-collapse: collapse;
  text-align: left;
  font-size: 13px;
}
.rec-table th {
  background: #f8fafc;
  padding: 12px 16px;
  font-size: 11px;
  font-weight: 800;
  text-transform: uppercase;
  color: #64748b;
  letter-spacing: 0.05em;
  border-bottom: 1px solid #e2e8f0;
}
.rec-table td {
  padding: 14px 16px;
  border-bottom: 1px solid #f1f5f9;
  vertical-align: middle;
}
.rec-table tbody tr:hover { background: #fbfdff; }
.row-in-consult { background: #f0fdf4 !important; }
.row-waiting { background: #fffbeb !important; }
.row-done { opacity: 0.75; }

.token-cell { display: flex; flex-direction: column; gap: 4px; }
.token-tag {
  background: #0f172a;
  color: #ffffff;
  font-weight: 800;
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 6px;
  display: inline-block;
  width: fit-content;
}
.token-none { color: #94a3b8; font-size: 12px; }
.stage-pill {
  font-size: 10px;
  font-weight: 700;
  padding: 2px 6px;
  border-radius: 4px;
  display: inline-block;
  width: fit-content;
  text-transform: uppercase;
}
.stage-waiting { background: #fef3c7; color: #92400e; }
.stage-in-consultation { background: #dcfce7; color: #166534; }
.stage-completed { background: #e2e8f0; color: #475569; }
.stage-pending { background: #f1f5f9; color: #64748b; }

.patient-name { font-weight: 700; color: #0f172a; font-size: 14px; }
.tag-fast {
  background: #fef3c7;
  color: #b45309;
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 4px;
  font-weight: 800;
  margin-left: 6px;
}
.tag-priority {
  background: #ede9fe;
  color: #6b21a8;
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 4px;
  font-weight: 800;
  margin-left: 6px;
}
.patient-meta { color: #64748b; font-size: 12px; margin-top: 2px; }
.doc-name { font-weight: 700; color: #1e293b; }
.doc-spec { color: #059669; font-size: 12px; font-weight: 600; }
.time-cell strong { font-size: 14px; color: #0f172a; }

.clinical-preview { max-width: 280px; font-size: 12px; line-height: 1.4; color: #475569; }
.status-checked-in { display: flex; align-items: center; gap: 6px; color: #059669; font-weight: 700; font-size: 13px; }
.ok-dot { color: #059669; }
.status-not-checked { display: flex; align-items: center; gap: 6px; color: #94a3b8; font-size: 13px; }
.dim-dot { color: #cbd5e1; }

.actions-group { display: flex; align-items: center; gap: 6px; justify-content: flex-end; flex-wrap: wrap; }
.btn-table-checkin {
  background: #059669;
  color: #ffffff;
  border: none;
  border-radius: 8px;
  padding: 6px 14px;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.15s;
}
.btn-table-checkin:hover { background: #047857; }
.btn-table-revert {
  background: #f8fafc;
  color: #dc2626;
  border: 1px solid #fecaca;
  border-radius: 8px;
  padding: 6px 10px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}
.btn-table-history {
  background: #f1f5f9;
  color: #334155;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  padding: 6px 12px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}
.btn-table-history:hover { background: #e2e8f0; }

.empty-card {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  padding: 48px 24px;
  text-align: center;
}
.empty-icon { font-size: 40px; margin-bottom: 12px; }
.empty-card h3 { font-size: 18px; font-weight: 700; color: #0f172a; margin: 0 0 6px; }
.empty-card p { color: #64748b; font-size: 14px; margin: 0 0 16px; }
.error-banner {
  background: #fef2f2;
  border: 1px solid #fca5a5;
  color: #991b1b;
  border-radius: 12px;
  padding: 12px 16px;
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 14px;
}
.btn-retry { background: #dc2626; color: #ffffff; border: none; padding: 6px 12px; border-radius: 6px; cursor: pointer; }
.table-skeleton { display: flex; flex-direction: column; gap: 8px; }
.skeleton-row { height: 48px; background: #e2e8f0; border-radius: 8px; animation: pulse 1.5s infinite; }
@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
</style>
