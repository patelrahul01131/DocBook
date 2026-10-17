
<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { Badge, Button } from 'frappe-ui'
import { useRouter } from 'vue-router'
import { call } from '../../api'
import { useAuthStore } from '../../stores/auth'

const router = useRouter()
const auth = useAuthStore()

const appointments = ref([])
const chartPeriod = ref(14)
const hoveredBar = ref(null)
const doctors = ref([])
const searchQuery = ref('')
const loading = ref(true)
const refreshing = ref(false)
const error = ref('')

// Live queue / check-in status for today's appointment
const queueStatus = ref(null)
let queuePoll = null

// --------------------------------------------------
// Authenticated patient
// --------------------------------------------------

const patientEmail = computed(() => {
  const user = auth.user || auth.currentUser || null

  return String(
    user?.email ||
    user?.name ||
    ''
  ).trim().toLowerCase()
})

const patientName = computed(() => {
  const user = auth.user || auth.currentUser || null
  const fullName = user?.full_name || user?.fullname

  if (fullName) return fullName.split(' ')[0]

  const email = patientEmail.value
  return email ? email.split('@')[0] : 'there'
})

// --------------------------------------------------
// Fetch existing APIs
// --------------------------------------------------

async function fetchDashboard(isRefresh = false) {
  if (isRefresh) {
    refreshing.value = true
  } else {
    loading.value = true
  }

  error.value = ''

  try {
    if (!patientEmail.value) {
      throw new Error('Please sign in to view your dashboard.')
    }

    const [appointmentResult, doctorResult] = await Promise.all([
      call('docbook.api.appointment.list_appointment',{
        patient: auth.user.email
      }),
      call('docbook.api.doctor.list_doctors').catch((err) => {
        console.error('Could not load doctor directory:', err)
        return []
      }),
    ])

    const appointmentRows = Array.isArray(appointmentResult)
      ? appointmentResult
      : appointmentResult?.data ||
        appointmentResult?.message ||
        []

    // Display records belonging to the signed-in patient as returned by the backend
    appointments.value = appointmentRows

    doctors.value = Array.isArray(doctorResult)
      ? doctorResult
      : doctorResult?.data || doctorResult?.message || []
  } catch (err) {
    console.error('Patient dashboard error:', err)
    error.value = err.message ||
      'Unable to load your dashboard. Please try again.'
  } finally {
    loading.value = false
    refreshing.value = false
  }
}

// --------------------------------------------------
// Appointment helpers
// --------------------------------------------------

function appointmentDateTime(appointment) {
  const date = appointment.appointment_date || appointment.date
  const time = appointment.appointment_time || appointment.time || '00:00:00'

  if (!date) return null

  const parsed = new Date(`${date}T${time}`)

  return Number.isNaN(parsed.getTime()) ? null : parsed
}

function formatDate(appointment) {
  const date = appointmentDateTime(appointment)

  if (!date) return 'Date not available'

  return new Intl.DateTimeFormat('en-IN', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  }).format(date)
}

function formatTime(appointment) {
  const date = appointmentDateTime(appointment)

  if (!date) return 'Time not available'

  return new Intl.DateTimeFormat('en-IN', {
    hour: 'numeric',
    minute: '2-digit',
  }).format(date)
}

function formatFee(fee) {
  if (fee == null || fee === '') return 'Not specified'

  const amount = Number(fee)

  if (!Number.isFinite(amount)) return 'Not specified'

  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 2,
  }).format(amount)
}

function statusOf(appointment) {
  return String(
    appointment.status || 'Pending'
  ).trim().toLowerCase()
}

function isCompleted(appointment) {
  return ['completed', 'resolved'].includes(statusOf(appointment))
}

function isCancelled(appointment) {
  return ['cancelled', 'canceled'].includes(statusOf(appointment))
}

function isUpcoming(appointment) {
  const date = appointmentDateTime(appointment)

  return Boolean(
    date &&
    date >= new Date() &&
    !isCompleted(appointment) &&
    !isCancelled(appointment)
  )
}

function doctorName(appointment) {
  const doctorId = appointment.doctor

  const doctor = doctors.value.find((item) =>
    item.user === doctorId ||
    item.name === doctorId
  )

  return (
    appointment.doctor_name ||
    doctor?.full_name ||
    doctor?.doctor_name ||
    doctor?.name ||
    doctorId ||
    'Doctor'
  )
}

function doctorSpecialty(appointment) {
  const doctor = doctors.value.find((item) =>
    item.user === appointment.doctor ||
    item.name === appointment.doctor
  )

  return appointment.specialty || doctor?.specialty || 'Healthcare professional'
}

// --------------------------------------------------
// Dashboard statistics
// --------------------------------------------------

const upcomingAppointments = computed(() =>
  appointments.value
    .filter(isUpcoming)
    .sort((a, b) =>
      appointmentDateTime(a) - appointmentDateTime(b)
    )
)

const nextAppointments = computed(() =>
  upcomingAppointments.value.slice(0, 3)
)

const pendingAppointments = computed(() =>
  appointments.value.filter((appointment) =>
    ['pending', 'booked', 'confirmed'].includes(statusOf(appointment))
  ).length
)

const completedAppointments = computed(() =>
  appointments.value.filter(isCompleted).length
)

// --------------------------------------------------
// Chart / Analytics
// --------------------------------------------------
const activityChartData = computed(() => {
  const period = Number(chartPeriod.value) || 14
  const list = []
  const today = new Date()

  // Window covering past days, today, and upcoming schedule
  const pastDays = Math.floor(period / 2)
  const totalDays = period

  for (let i = pastDays; i > (pastDays - totalDays); i--) {
    const d = new Date()
    d.setDate(today.getDate() - i)
    const yyyy = d.getFullYear()
    const mm = String(d.getMonth() + 1).padStart(2, '0')
    const dd = String(d.getDate()).padStart(2, '0')
    const dateStr = `${yyyy}-${mm}-${dd}`
    const dayNum = String(d.getDate())
    const monthShort = d.toLocaleDateString('en-IN', { month: 'short' })
    const dayLabel = `${dayNum} ${monthShort}`
    const fullDateLabel = d.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })

    const dayAppts = appointments.value.filter(a => {
      const aDate = a.appointment_date || a.date
      return aDate === dateStr
    })
    const completed = dayAppts.filter(a => isCompleted(a)).length
    const upcoming = dayAppts.filter(a => isUpcoming(a)).length
    const cancelled = dayAppts.filter(a => isCancelled(a)).length
    const pending = dayAppts.filter(a => ['pending', 'booked', 'confirmed'].includes(statusOf(a))).length

    list.push({
      date: dateStr,
      dayNum,
      monthShort,
      dayLabel,
      fullDateLabel,
      total: dayAppts.length,
      completed,
      upcoming,
      cancelled,
      pending,
    })
  }

  const maxTotal = Math.max(...list.map(i => i.total), 3)
  return list.map(item => ({
    ...item,
    heightPct: Math.max(Math.round((item.total / maxTotal) * 100), item.total > 0 ? 20 : 6),
  }))
})


const totalPeriodAppts = computed(() =>
  activityChartData.value.reduce((acc, curr) => acc + curr.total, 0)
)

const avgDailyAppts = computed(() => {
  if (!chartPeriod.value) return 0
  return (totalPeriodAppts.value / chartPeriod.value).toFixed(1)
})

const filteredDoctors = computed(() => {
  const query = searchQuery.value.trim().toLowerCase()

  if (!query) return doctors.value.slice(0, 3)

  return doctors.value
    .filter((doctor) =>
      [
        doctor.full_name,
        doctor.doctor_name,
        doctor.specialty,
        doctor.qualification,
      ].some((value) =>
        String(value || '').toLowerCase().includes(query)
      )
    )
    .slice(0, 3)
})

function viewDoctor(doctor) {
  const identifier = doctor.user || doctor.name

  if (!identifier) return

  router.push({
    path: '/doctor_profile',
    query: { doctor: identifier },
  })
}

function findDoctors() {
  router.push('/home')
}

async function fetchQueueStatus() {
  try {
    const res = await call('docbook.api.queue.get_my_queue_position', {})
    queueStatus.value = res && res.found ? res : null
  } catch (err) {
    queueStatus.value = null
  }
}

function viewAppointments(slot_name) {
  if (slot_name && typeof slot_name === 'string') {
    router.push(`/show-appointment/${slot_name}`)
  } else {
    router.push('/my-appointments')
  }
}

onMounted(() => {
  fetchDashboard()
  fetchQueueStatus()
  // Keep wait-time / check-in info fresh while the patient waits.
  queuePoll = setInterval(fetchQueueStatus, 30000)
})

onUnmounted(() => {
  if (queuePoll) clearInterval(queuePoll)
})
</script>

<template>
  <main class="patient-dashboard">
    <div class="dashboard-shell">

      <!-- Welcome -->
      <header class="welcome-header">
        <div class="welcome-copy">
          <div class="eyebrow">
            <span class="lucide-heart-pulse"></span>
            DOCBOOK PATIENT PORTAL
          </div>

          <h1>
            Hello, {{ patientName }}<span></span>
          </h1>

          <p>
            Your health journey, appointments, and care —
            all in one place.
          </p>
        </div>

        <div class="welcome-actions">
          <Button
            label="Find a doctor"
            icon-left="lucide-search"
            @click="findDoctors"
          />

          <Button
            label="Refresh"
            icon-left="lucide-refresh-cw"
            :loading="refreshing"
            :disabled="loading || refreshing"
            @click="fetchDashboard(true)"
          />
        </div>
      </header>

      <!-- Error -->
      <section v-if="error" class="error-panel">
        <span class="lucide-circle-alert"></span>

        <div class="error-copy">
          <strong>Unable to load your dashboard</strong>
          <p>{{ error }}</p>
        </div>

        <Button
          label="Try again"
          @click="fetchDashboard()"
        />
      </section>

      <template v-else>

        <!-- Statistics -->
        <section class="stats-grid">
          <article class="stat-card">
            <div class="stat-icon blue">
              <span class="lucide-calendar-days"></span>
            </div>

            <p>Total appointments</p>

            <h2>{{ loading ? '—' : appointments.length }}</h2>

            <span class="stat-caption">
              Your appointment records
            </span>
          </article>

          <article class="stat-card">
            <div class="stat-icon teal">
              <span class="lucide-calendar-check"></span>
            </div>

            <p>Upcoming visits</p>

            <h2>{{ loading ? '—' : upcomingAppointments.length }}</h2>

            <span class="stat-caption">
              Scheduled for now or later
            </span>
          </article>

          <article class="stat-card">
            <div class="stat-icon amber">
              <span class="lucide-clock-3"></span>
            </div>

            <p>Pending bookings</p>

            <h2>{{ loading ? '—' : pendingAppointments }}</h2>

            <span class="stat-caption">
              Awaiting the next step
            </span>
          </article>

          <article class="stat-card">
            <div class="stat-icon purple">
              <span class="lucide-check-circle-2"></span>
            </div>

            <p>Completed visits</p>

            <h2>{{ loading ? '—' : completedAppointments }}</h2>

            <span class="stat-caption">
              Completed appointments
            </span>
          </article>
        </section>

        <!-- Live Queue Status -->
        <section v-if="queueStatus && queueStatus.found" class="section-block queue-section">
          <div class="section-heading">
            <div>
              <div class="eyebrow">LIVE QUEUE</div>
              <h2>Today's Check-in &amp; Wait Time</h2>
              <p>Updates automatically while you wait for your turn.</p>
            </div>
          </div>

          <div class="queue-grid">
            <article class="queue-card">
              <span class="queue-label">Check-in</span>
              <strong class="queue-value" :class="{ ok: queueStatus.checked_in }">
                {{ queueStatus.checked_in ? '✅ Checked In' : 'Not checked in yet' }}
              </strong>
              <span class="queue-hint">Show your QR pass at reception to check in.</span>
            </article>

            <article v-if="queueStatus.queue_token" class="queue-card">
              <span class="queue-label">Token</span>
              <strong class="queue-value">#{{ queueStatus.queue_token }}</strong>
              <span class="queue-hint">Your queue token for today</span>
            </article>

            <article v-if="queueStatus.queue_position" class="queue-card">
              <span class="queue-label">Position in queue</span>
              <strong class="queue-value">{{ queueStatus.queue_position }}</strong>
              <span v-if="queueStatus.patients_ahead != null" class="queue-hint">
                {{ queueStatus.patients_ahead }} patient{{ queueStatus.patients_ahead === 1 ? '' : 's' }} ahead of you
              </span>
            </article>

            <article v-if="queueStatus.estimated_wait_minutes != null" class="queue-card">
              <span class="queue-label">Estimated wait</span>
              <strong class="queue-value">~{{ queueStatus.estimated_wait_minutes }} min</strong>
              <span class="queue-hint">Based on today's consultation pace</span>
            </article>

            <article v-if="queueStatus.average_wait_minutes" class="queue-card">
              <span class="queue-label">Average wait today</span>
              <strong class="queue-value">{{ queueStatus.average_wait_minutes }} min</strong>
              <span class="queue-hint">Average wait for this doctor today</span>
            </article>

            <article v-if="queueStatus.visit_stage" class="queue-card">
              <span class="queue-label">Stage</span>
              <strong class="queue-value">{{ queueStatus.visit_stage }}</strong>
              <span v-if="queueStatus.urgency_score" class="queue-hint">Urgency score: {{ queueStatus.urgency_score }}/100</span>
            </article>
          </div>
        </section>

        <!-- Activity Chart Section -->
        <section class="section-block chart-section">
          <div class="section-heading">
            <div>
              <div class="eyebrow">APPOINTMENT ACTIVITY</div>
              <h2>Your Health Timeline</h2>
              <p>Visual overview of your appointment history.</p>
            </div>
            <div class="chart-period-btns">
              <button
                v-for="p in [7, 14, 30]"
                :key="p"
                class="period-btn"
                :class="{ active: chartPeriod === p }"
                @click="chartPeriod = p"
              >
                {{ p }}d
              </button>
            </div>
          </div>

          <div class="chart-card">
            <!-- Summary row -->
            <div class="chart-summary">
              <div class="chart-stat">
                <span class="chart-stat-val">{{ totalPeriodAppts }}</span>
                <span class="chart-stat-label">Total ({{ chartPeriod }}d)</span>
              </div>
              <div class="chart-stat">
                <span class="chart-stat-val">{{ avgDailyAppts }}</span>
                <span class="chart-stat-label">Avg / day</span>
              </div>
              <div class="chart-stat">
                <span class="chart-stat-val">{{ completedAppointments }}</span>
                <span class="chart-stat-label">Completed</span>
              </div>
              <div class="chart-stat">
                <span class="chart-stat-val">{{ upcomingAppointments.length }}</span>
                <span class="chart-stat-label">Upcoming</span>
              </div>
            </div>

            <!-- Bar chart -->
            <div class="bar-chart-wrap">
              <div
                v-for="bar in activityChartData"
                :key="bar.date"
                class="bar-col"
                @mouseenter="hoveredBar = bar"
                @mouseleave="hoveredBar = null"
              >
                <!-- Tooltip -->
                <div v-if="hoveredBar === bar" class="bar-tooltip">
                  <div class="tooltip-date">{{ bar.dayLabel }}</div>
                  <div class="tooltip-row"><span class="t-dot completed"></span> Completed: {{ bar.completed }}</div>
                  <div class="tooltip-row"><span class="t-dot upcoming"></span> Upcoming: {{ bar.upcoming }}</div>
                  <div v-if="bar.pending" class="tooltip-row"><span class="t-dot pending"></span> Pending: {{ bar.pending }}</div>
                  <div v-if="bar.cancelled" class="tooltip-row"><span class="t-dot cancelled"></span> Cancelled: {{ bar.cancelled }}</div>
                </div>

                <div class="bar-track">
                  <div
                    class="bar-fill"
                    :style="{ height: bar.heightPct + '%' }"
                    :class="{
                      'bar-active': bar.total > 0,
                      'bar-today': bar.date === new Date().toISOString().slice(0,10)
                    }"
                  ></div>
                </div>
                <div class="bar-label">
                  <span class="bar-date-num">{{ bar.dayNum }}</span>
                  <span class="bar-date-mon">{{ bar.monthShort }}</span>
                </div>
              </div>
            </div>

            <!-- Legend -->
            <div class="chart-legend">
              <span class="legend-item"><span class="legend-dot completed"></span> Completed</span>
              <span class="legend-item"><span class="legend-dot upcoming"></span> Upcoming</span>
              <span class="legend-item"><span class="legend-dot pending"></span> Pending</span>
            </div>
          </div>
        </section>

        <!-- Upcoming appointments -->
        <section class="section-block">
          <div class="section-heading">
            <div>
              <div class="eyebrow">YOUR HEALTH SCHEDULE</div>
              <h2>Upcoming appointments</h2>
              <p>Keep track of your next visits.</p>
            </div>

            <button
              class="text-action"
              type="button"
              @click="viewAppointments"
            >
              View all
              <span class="lucide-arrow-up-right"></span>
            </button>
          </div>

          <!-- Loading -->
          <div v-if="loading" class="appointment-grid">
            <div
              v-for="item in 3"
              :key="item"
              class="appointment-card skeleton-card"
            >
              <div class="skeleton skeleton-line"></div>
              <div class="skeleton skeleton-line wide"></div>
              <div class="skeleton skeleton-block"></div>
            </div>
          </div>

          <!-- Empty state -->
          <div
            v-else-if="!upcomingAppointments.length"
            class="empty-panel"
          >
            <div class="empty-icon">
              <span class="lucide-calendar-plus"></span>
            </div>

            <h3>No upcoming appointments</h3>

            <p>
              When you book your next visit, its details will
              appear here.
            </p>

            <Button
              label="Find a doctor"
              icon-left="lucide-search"
              @click="findDoctors"
            />
          </div>

          <!-- Appointment cards -->
          <div v-else class="appointment-grid">
            <article
              v-for="appointment in nextAppointments"
              :key="appointment.name"
              class="appointment-card"
            >
              <div class="appointment-top">
                <div class="appointment-icon">
                  <span class="lucide-stethoscope"></span>
                </div>

                <Badge
                  :theme="
                    statusOf(appointment) === 'confirmed'
                      ? 'green'
                      : statusOf(appointment) === 'pending'
                        ? 'amber'
                        : 'blue'
                  "
                >
                  {{ appointment.status || 'Pending' }}
                </Badge>
              </div>

              <h3>{{ doctorName(appointment) }}</h3>

              <p class="doctor-specialty">
                {{ doctorSpecialty(appointment) }}
              </p>

              <div class="appointment-meta">
                <div>
                  <span class="lucide-calendar-days"></span>
                  {{ formatDate(appointment) }}
                </div>

                <div>
                  <span class="lucide-clock-3"></span>
                  {{ formatTime(appointment) }}
                </div>
              </div>

              <div class="appointment-footer">
                <div class="fee-info">
                  <span>Consultation fee</span>
                  <strong>{{ formatFee(appointment.fee) }}</strong>
                </div>

                <Button
                  label="Details"
                  icon-right="lucide-arrow-up-right"
                  @click="viewAppointments(appointment.slot)"
                />
              </div>
            </article>
          </div>
        </section>

        <!-- Find a doctor -->
        <section class="section-block doctor-section">
          <div class="section-heading">
            <div>
              <div class="eyebrow">PERSONALIZED CARE</div>
              <h2>Discover doctors</h2>
              <p>Explore available healthcare professionals.</p>
            </div>

            <button
              class="text-action"
              type="button"
              @click="findDoctors"
            >
              Explore all
              <span class="lucide-arrow-up-right"></span>
            </button>
          </div>

          <div class="doctor-search">
            <span class="lucide-search"></span>

            <Input
              v-model="searchQuery"
              placeholder="Search by doctor or specialty..."
            />
          </div>

          <div v-if="loading" class="doctor-grid">
            <div
              v-for="item in 3"
              :key="item"
              class="doctor-card skeleton-card"
            >
              <div class="skeleton skeleton-avatar"></div>
              <div class="skeleton skeleton-line wide"></div>
              <div class="skeleton skeleton-line"></div>
            </div>
          </div>

          <div
            v-else-if="!filteredDoctors.length"
            class="empty-panel compact-empty"
          >
            <span class="lucide-search"></span>
            <h3>No doctors found</h3>
            <p>Try a different search or explore the full directory.</p>
            <Button
              label="Browse doctors"
              @click="findDoctors"
            />
          </div>

          <div v-else class="doctor-grid">
            <article
              v-for="doctor in filteredDoctors"
              :key="doctor.name || doctor.user"
              class="doctor-card"
            >
              <div class="doctor-avatar">
                <span class="lucide-user-round"></span>
              </div>

              <div class="doctor-info">
                <h3>
                  {{
                    doctor.full_name ||
                    doctor.doctor_name ||
                    doctor.name
                  }}
                </h3>

                <p>
                  {{ doctor.specialty || 'General practice' }}
                </p>

                <span class="qualification">
                  {{ doctor.qualification || 'Qualification not specified' }}
                </span>
              </div>

              <Button
                label="View profile"
                icon-right="lucide-arrow-up-right"
                @click="viewDoctor(doctor)"
              />
            </article>
          </div>
        </section>

        <!-- Quick Access: Health Records -->
        <section class="section-block">
          <div class="section-heading">
            <div>
              <div class="eyebrow">YOUR HEALTH RECORDS</div>
              <h2>Health & Prescriptions</h2>
              <p>Access your medical information and medicine schedule.</p>
            </div>
          </div>
          <div class="quick-links-grid">
            <button class="quick-link-card" @click="router.push('/medical-history')">
              <div class="ql-icon" style="background:#f0fdfa; color:#0d9488;">📋</div>
              <div class="ql-title">Medical History</div>
              <div class="ql-desc">Conditions, allergies & past treatments</div>
            </button>
            <button class="quick-link-card" @click="router.push('/prescriptions')">
              <div class="ql-icon" style="background:#eff6ff; color:#2563eb;">💊</div>
              <div class="ql-title">Prescriptions</div>
              <div class="ql-desc">All prescriptions from your doctors</div>
            </button>
            <button class="quick-link-card" @click="router.push('/medicine-reminders')">
              <div class="ql-icon" style="background:#fef3c7; color:#b45309;">🔔</div>
              <div class="ql-title">Medicine Reminders</div>
              <div class="ql-desc">Scheduled medicine dose reminders</div>
            </button>
            <button class="quick-link-card" @click="router.push('/medicines')">
              <div class="ql-icon" style="background:#ede9fe; color:#7c3aed;">📖</div>
              <div class="ql-title">Medicine Catalog</div>
              <div class="ql-desc">Browse medicines and health info</div>
            </button>
          </div>
        </section>

        <!-- CTA -->
        <section class="health-banner">
          <div class="banner-icon">
            <span class="lucide-heart-pulse"></span>
          </div>

          <div class="banner-copy">
            <h2>Your health deserves attention.</h2>
            <p>
              Find the right healthcare professional for your
              next appointment with DocBook.
            </p>
          </div>

          <Button
            label="Book an appointment"
            icon-right="lucide-arrow-right"
            @click="findDoctors"
          />
        </section>
      </template>

      <footer class="dashboard-footer">
        <span>DocBook · Healthcare made simple</span>
        <button type="button" @click="viewAppointments">
          My appointments
        </button>
      </footer>
    </div>
  </main>
</template>

<style scoped>
.patient-dashboard {
  --blue: #2563eb;
  --teal: #0d9488;
  --ink: #0f172a;
  --muted: #64748b;
  --border: #e2e8f0;

  min-height: 100%;
  padding: 34px 24px;
  color: var(--ink);
  background:
    radial-gradient(ellipse at 0% 0%, rgba(37,99,235,.08), transparent 35%),
    radial-gradient(ellipse at 100% 50%, rgba(20,184,166,.07), transparent 30%),
    #f4f7fb;
}

.dashboard-shell {
  width: 100%;
  max-width: 1320px;
  margin: 0 auto;
}

.welcome-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 24px;
  margin-bottom: 30px;
}

.eyebrow {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--blue);
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 1.4px;
}

.welcome-copy h1 {
  margin: 12px 0 8px;
  font-size: clamp(32px, 4vw, 46px);
  font-weight: 800;
  letter-spacing: -1.8px;
}

.welcome-copy h1 span {
  color: var(--teal);
}

.welcome-copy > p,
.section-heading p {
  margin: 0;
  color: var(--muted);
  font-size: 13px;
  line-height: 1.7;
}

.welcome-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
  margin-bottom: 42px;
}

.stat-card,
.appointment-card,
.doctor-card {
  min-width: 0;
  border: 1px solid rgba(255,255,255,.95);
  border-radius: 22px;
  background: rgba(255,255,255,.82);
  box-shadow: 0 12px 32px rgba(15,23,42,.045);
  backdrop-filter: blur(18px);
}

.stat-card {
  padding: 21px;
}

.stat-icon,
.appointment-icon,
.empty-icon,
.banner-icon {
  display: grid;
  width: 44px;
  height: 44px;
  flex-shrink: 0;
  place-items: center;
  border-radius: 14px;
  font-size: 19px;
}

.stat-icon.blue {
  color: #2563eb;
  background: #eff6ff;
}

.stat-icon.teal {
  color: #0f766e;
  background: #ccfbf1;
}

.stat-icon.amber {
  color: #b45309;
  background: #fef3c7;
}

.stat-icon.purple {
  color: #7c3aed;
  background: #f3e8ff;
}

.stat-card > p {
  margin: 18px 0 5px;
  color: var(--muted);
  font-size: 12px;
}

.stat-card h2 {
  margin: 0;
  font-size: 31px;
  font-weight: 800;
  letter-spacing: -1px;
}

.stat-caption {
  display: block;
  margin-top: 8px;
  color: #94a3b8;
  font-size: 10px;
  line-height: 1.5;
}

.section-block {
  margin-top: 38px;
}

.section-heading {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 18px;
  margin-bottom: 21px;
}

.section-heading h2 {
  margin: 8px 0 5px;
  font-size: 24px;
  font-weight: 780;
  letter-spacing: -.7px;
}

.text-action {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 9px 0;
  border: 0;
  background: transparent;
  color: var(--blue);
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
}

.appointment-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 17px;
}

.appointment-card {
  display: flex;
  flex-direction: column;
  padding: 21px;
  transition: transform .2s ease, box-shadow .2s ease;
}

.appointment-card:hover,
.doctor-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 20px 40px rgba(15,23,42,.075);
}

.appointment-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  margin-bottom: 18px;
}

.appointment-icon {
  color: var(--blue);
  background: linear-gradient(135deg,#eff6ff,#ccfbf1);
}

.appointment-card h3 {
  overflow-wrap: anywhere;
  margin: 0;
  font-size: 16px;
  font-weight: 750;
}

.doctor-specialty {
  margin: 6px 0 17px;
  color: var(--muted);
  font-size: 12px;
}

.appointment-meta {
  display: grid;
  gap: 11px;
  padding: 15px 0;
  border-top: 1px solid #f1f5f9;
  border-bottom: 1px solid #f1f5f9;
}

.appointment-meta div {
  display: flex;
  align-items: center;
  gap: 9px;
  color: #475569;
  font-size: 12px;
}

.appointment-meta span {
  color: var(--teal);
}

.appointment-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  margin-top: auto;
  padding-top: 17px;
}

.fee-info {
  display: flex;
  flex-direction: column;
  gap: 5px;
  min-width: 0;
}

.fee-info span {
  color: #94a3b8;
  font-size: 10px;
}

.fee-info strong {
  overflow-wrap: anywhere;
  font-size: 14px;
}

.doctor-search {
  display: flex;
  align-items: center;
  gap: 10px;
  max-width: 530px;
  margin-bottom: 18px;
  padding: 5px 12px;
  border: 1px solid var(--border);
  border-radius: 14px;
  background: rgba(255,255,255,.9);
  color: #94a3b8;
}

.doctor-search > span {
  flex-shrink: 0;
}

.doctor-search :deep(input) {
  min-width: 0;
  border: 0;
  box-shadow: none;
}

.doctor-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
}

.doctor-card {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 15px;
  padding: 20px;
  transition: transform .2s ease, box-shadow .2s ease;
}

.doctor-avatar {
  display: grid;
  width: 52px;
  height: 52px;
  place-items: center;
  border: 1px solid #dbeafe;
  border-radius: 16px;
  background: linear-gradient(135deg,#eff6ff,#ccfbf1);
  color: var(--blue);
  font-size: 22px;
}

.doctor-info {
  flex: 1;
  min-width: 0;
}

.doctor-info h3 {
  overflow-wrap: anywhere;
  margin: 0;
  font-size: 15px;
  font-weight: 750;
}

.doctor-info p {
  margin: 6px 0;
  color: var(--teal);
  font-size: 12px;
}

.qualification {
  display: block;
  color: var(--muted);
  font-size: 11px;
  line-height: 1.5;
}

.doctor-card > :last-child {
  width: 100%;
}

.empty-panel {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 45px 20px;
  border: 1px dashed #cbd5e1;
  border-radius: 22px;
  background: rgba(255,255,255,.65);
  text-align: center;
}

.empty-icon {
  width: 54px;
  height: 54px;
  color: var(--blue);
  background: #eff6ff;
  font-size: 23px;
}

.empty-panel h3 {
  margin: 17px 0 7px;
  font-size: 16px;
}

.empty-panel p {
  max-width: 390px;
  margin: 0 0 20px;
  color: var(--muted);
  font-size: 12px;
  line-height: 1.7;
}

.compact-empty {
  padding: 32px 20px;
}

.error-panel {
  display: flex;
  align-items: center;
  gap: 15px;
  padding: 20px;
  border: 1px solid #fecaca;
  border-radius: 18px;
  background: #fffafa;
  color: #dc2626;
}

.error-copy {
  flex: 1;
  min-width: 0;
}

.error-copy strong {
  font-size: 13px;
}

.error-copy p {
  margin: 5px 0 0;
  color: #7f1d1d;
  font-size: 12px;
}

.health-banner {
  display: flex;
  align-items: center;
  gap: 20px;
  margin-top: 42px;
  padding: 26px;
  border-radius: 25px;
  background: linear-gradient(125deg,#0f172a,#172554 65%,#134e4a);
  color: white;
  box-shadow: 0 22px 48px rgba(15,23,42,.13);
}

.banner-icon {
  width: 52px;
  height: 52px;
  background: rgba(255,255,255,.1);
  color: #5eead4;
  font-size: 23px;
}

.banner-copy {
  flex: 1;
  min-width: 0;
}

.banner-copy h2 {
  margin: 0 0 7px;
  font-size: 18px;
}

.banner-copy p {
  max-width: 570px;
  margin: 0;
  color: #cbd5e1;
  font-size: 12px;
  line-height: 1.7;
}

.dashboard-footer {
  display: flex;
  justify-content: space-between;
  gap: 15px;
  margin-top: 25px;
  padding-top: 19px;
  border-top: 1px solid var(--border);
  color: #94a3b8;
  font-size: 11px;
}

.dashboard-footer button {
  border: 0;
  background: transparent;
  color: var(--blue);
  cursor: pointer;
}

.skeleton {
  border-radius: 9px;
  background: linear-gradient(90deg,#f1f5f9,#e2e8f0,#f1f5f9);
  background-size: 200% 100%;
  animation: shimmer 1.5s linear infinite;
}

.skeleton-card {
  gap: 15px;
}

.skeleton-line {
  width: 60%;
  height: 13px;
}

.skeleton-line.wide {
  width: 85%;
  height: 18px;
}

.skeleton-block {
  width: 100%;
  height: 70px;
}

.skeleton-avatar {
  width: 52px;
  height: 52px;
  border-radius: 16px;
}

@keyframes shimmer {
  to { background-position: -200% 0; }
}

@media (max-width: 1050px) {
  .stats-grid {
    grid-template-columns: repeat(2,minmax(0,1fr));
  }

  .appointment-grid,
  .doctor-grid {
    grid-template-columns: repeat(2,minmax(0,1fr));
  }

  .welcome-header {
    align-items: flex-start;
    flex-direction: column;
  }
}

@media (max-width: 650px) {
  .patient-dashboard {
    padding: 23px 15px;
  }

  .welcome-copy h1 {
    font-size: 34px;
  }

  .welcome-actions {
    width: 100%;
  }

  .stats-grid {
    gap: 12px;
  }

  .stat-card {
    padding: 16px;
  }

  .appointment-grid,
  .doctor-grid {
    grid-template-columns: 1fr;
  }

  .section-heading {
    align-items: flex-start;
    flex-direction: column;
    gap: 8px;
  }

  .health-banner {
    align-items: flex-start;
    flex-wrap: wrap;
    padding: 21px;
  }

  .banner-copy {
    flex-basis: calc(100% - 75px);
  }

  .health-banner > :last-child {
    width: 100%;
  }

  .error-panel {
    align-items: flex-start;
    flex-wrap: wrap;
  }

  .dashboard-footer {
    flex-direction: column;
  }
}

@media (max-width: 380px) {
  .stats-grid {
    grid-template-columns: 1fr;
  }

  .welcome-copy h1 {
    font-size: 29px;
  }

  .appointment-footer {
    align-items: flex-start;
    flex-direction: column;
  }
}

@media (prefers-reduced-motion: reduce) {
  .skeleton {
    animation: none;
  }

  .appointment-card,
  .doctor-card {
    transition: none;
  }
}

/* Quick links grid */
.quick-links-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 16px;
}

.quick-link-card {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 10px;
  padding: 20px;
  background: rgba(255,255,255,.86);
  border: 1px solid rgba(226, 232, 240, 0.8);
  border-radius: 18px;
  box-shadow: 0 4px 12px rgba(15,23,42,.05);
  cursor: pointer;
  text-align: left;
  font-family: inherit;
  transition: transform 0.2s, box-shadow 0.2s, border-color 0.2s;
  backdrop-filter: blur(12px);
}

.quick-link-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 32px rgba(15,23,42,.10);
  border-color: rgba(99, 202, 185, 0.6);
}

.ql-icon {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  flex-shrink: 0;
}

.ql-title {
  font-size: 14px;
  font-weight: 700;
  color: #0f172a;
}

.ql-desc {
  font-size: 12px;
  color: #64748b;
  line-height: 1.5;
}

/* ===== Activity Chart Styles ===== */
.chart-period-btns {
  display: flex;
  gap: 6px;
}

.period-btn {
  padding: 6px 14px;
  border-radius: 20px;
  border: 1.5px solid #e2e8f0;
  background: white;
  font-size: 12px;
  font-weight: 700;
  color: #64748b;
  cursor: pointer;
  transition: all 0.15s;
}

.period-btn.active {
  background: #2563eb;
  border-color: #2563eb;
  color: white;
}

.period-btn:hover:not(.active) {
  border-color: #2563eb;
  color: #2563eb;
}

.chart-card {
  background: rgba(255,255,255,0.88);
  border: 1px solid rgba(226, 232, 240, 0.8);
  border-radius: 22px;
  padding: 24px;
  box-shadow: 0 8px 24px rgba(15,23,42,0.06);
  backdrop-filter: blur(16px);
}

.chart-summary {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 24px;
  padding-bottom: 20px;
  border-bottom: 1px solid #f1f5f9;
}

.chart-stat {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.chart-stat-val {
  font-size: 28px;
  font-weight: 800;
  color: #0f172a;
  letter-spacing: -1px;
}

.chart-stat-label {
  font-size: 11px;
  color: #94a3b8;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.6px;
}

.bar-chart-wrap {
  display: flex;
  align-items: flex-end;
  gap: 4px;
  height: 140px;
  margin-bottom: 12px;
}

.bar-col {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  position: relative;
  cursor: pointer;
  min-width: 0;
}

.bar-tooltip {
  position: absolute;
  bottom: calc(100% + 8px);
  left: 50%;
  transform: translateX(-50%);
  background: #0f172a;
  color: white;
  border-radius: 10px;
  padding: 10px 12px;
  font-size: 11px;
  white-space: nowrap;
  z-index: 10;
  box-shadow: 0 8px 20px rgba(15,23,42,0.3);
  pointer-events: none;
}

.tooltip-date {
  font-weight: 700;
  font-size: 12px;
  margin-bottom: 6px;
  color: #94a3b8;
}

.tooltip-row {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 3px;
}

.t-dot, .legend-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
  display: inline-block;
}

.t-dot.completed, .legend-dot.completed { background: #10b981; }
.t-dot.upcoming, .legend-dot.upcoming { background: #2563eb; }
.t-dot.pending, .legend-dot.pending { background: #f59e0b; }
.t-dot.cancelled { background: #ef4444; }

.bar-track {
  width: 100%;
  height: 110px;
  display: flex;
  align-items: flex-end;
  background: #f8fafc;
  border-radius: 6px;
  overflow: hidden;
}

.bar-fill {
  width: 100%;
  background: linear-gradient(180deg, #dbeafe, #bfdbfe);
  border-radius: 6px 6px 0 0;
  transition: height 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
  min-height: 4px;
}

.bar-fill.bar-active {
  background: linear-gradient(180deg, #3b82f6, #2563eb);
}

.bar-fill.bar-today.bar-active {
  background: linear-gradient(180deg, #10b981, #059669);
}

.bar-label {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1px;
  font-size: 10px;
  color: #64748b;
  font-weight: 600;
  text-align: center;
  min-height: 28px;
}

.bar-date-num {
  font-size: 11px;
  font-weight: 700;
  color: #1e293b;
  line-height: 1.1;
}

.bar-date-mon {
  font-size: 8px;
  font-weight: 700;
  text-transform: uppercase;
  color: #94a3b8;
  letter-spacing: 0.5px;
  line-height: 1.1;
}

.chart-legend {
  display: flex;
  gap: 16px;
  padding-top: 12px;
  border-top: 1px solid #f1f5f9;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  color: #64748b;
  font-weight: 500;
}

@media (max-width: 640px) {
  .chart-summary {
    grid-template-columns: repeat(2, 1fr);
  }

  .bar-chart-wrap {
    gap: 2px;
  }
}

/* Live queue status */
.queue-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 14px;
}

.queue-card {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.queue-label {
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: #64748b;
}

.queue-value {
  font-size: 20px;
  font-weight: 800;
  color: #0f172a;
}

.queue-value.ok {
  color: #047857;
}

.queue-hint {
  font-size: 12px;
  color: #94a3b8;
}
</style>